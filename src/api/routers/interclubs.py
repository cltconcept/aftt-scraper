"""
Routes: Interclubs (CRUD + scraping)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
import asyncio
import logging
from datetime import datetime

from src.database import queries
from src.api.cache import cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Interclubs"])

# État global du scraping interclubs
_current_interclubs_scrape = None
_interclubs_scrape_logs = {}


@router.get("/interclubs/divisions")
async def list_interclubs_divisions(
    category: Optional[str] = Query(None, description="Filtrer par categorie (ex: National, Prov. Hainaut)"),
    gender: Optional[str] = Query(None, description="Filtrer par genre (Hommes, Dames)")
):
    """Liste les divisions interclubs, filtrable par categorie (National, Provincial) et genre."""
    divisions = queries.get_interclubs_divisions(category=category, gender=gender)
    return {"count": len(divisions), "divisions": divisions}


@router.get("/interclubs/rankings")
async def get_interclubs_ranking(
    division_index: int = Query(..., description="Index de la division"),
    week: int = Query(..., ge=1, le=22, description="Numero de semaine (1-22)")
):
    """Classement d'une division interclubs pour une semaine donnee (position, points, matchs)."""
    rankings = queries.get_interclubs_ranking(division_index, week)
    return {"division_index": division_index, "week": week, "count": len(rankings), "rankings": rankings}


@router.get("/interclubs/team/{team_name}/history")
async def get_team_history(
    team_name: str,
    division_index: Optional[int] = Query(None, description="Filtrer par division")
):
    """Evolution d'une equipe semaine par semaine : points, position, victoires/defaites."""
    history = queries.get_interclubs_team_history(team_name, division_index)
    return {"team_name": team_name, "count": len(history), "history": history}


@router.get("/interclubs/search")
async def search_teams(
    q: str = Query(..., min_length=2, description="Terme de recherche"),
    limit: int = Query(50, ge=1, le=200, description="Nombre max de résultats")
):
    """Recherche des équipes interclubs par nom."""
    teams = queries.search_interclubs_teams(q, limit=limit)
    return {"query": q, "count": len(teams), "teams": teams}


@router.get("/interclubs/stats")
async def get_interclubs_stats():
    """Récupère des statistiques sur les données interclubs."""
    cached = cache.get("interclubs_stats")
    if cached is not None:
        return cached
    result = queries.get_interclubs_stats()
    cache.set("interclubs_stats", result, ttl=120)
    return result


# --- Interclubs Scraping ---

async def run_interclubs_scrape(task_id: str, weeks: Optional[List[int]], division_indices: Optional[List[int]], resume_from: Optional[dict]):
    """Exécute le scraping interclubs en arrière-plan."""
    global _current_interclubs_scrape

    from src.scraper.interclubs_scraper import scrape_all_interclubs_rankings_async

    _interclubs_scrape_logs[task_id] = []

    def add_log(msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        _interclubs_scrape_logs[task_id].append({"timestamp": timestamp, "message": msg})
        logger.info(msg)
        if len(_interclubs_scrape_logs[task_id]) > 2000:
            _interclubs_scrape_logs[task_id] = _interclubs_scrape_logs[task_id][-2000:]

    _current_interclubs_scrape = {
        'task_id': task_id, 'status': 'running',
        'started_at': datetime.now().isoformat(),
        'total_rankings': 0, 'errors_count': 0, 'last_success': None,
    }

    def is_cancelled():
        return _current_interclubs_scrape.get('status') != 'running'

    try:
        add_log(f"[INTERCLUBS] Demarrage tache {task_id}")
        stats = await scrape_all_interclubs_rankings_async(
            callback=add_log, weeks=weeks,
            division_indices=division_indices, resume_from=resume_from,
            is_cancelled=is_cancelled,
        )
        _current_interclubs_scrape['status'] = 'success'
        _current_interclubs_scrape['finished_at'] = datetime.now().isoformat()
        _current_interclubs_scrape['total_rankings'] = stats.get('total_rankings', 0)
        _current_interclubs_scrape['errors_count'] = len(stats.get('errors', []))
        _current_interclubs_scrape['last_success'] = stats.get('last_success')
        add_log(f"[INTERCLUBS] Termine: {stats.get('total_rankings', 0)} classements, {len(stats.get('errors', []))} erreurs")

    except Exception as e:
        _current_interclubs_scrape['status'] = 'failed'
        _current_interclubs_scrape['finished_at'] = datetime.now().isoformat()
        _current_interclubs_scrape['errors_count'] += 1
        add_log(f"[INTERCLUBS] Erreur fatale: {e}")


@router.post("/scrape/interclubs", tags=["Interclubs Scraping"])
async def start_interclubs_scrape(
    weeks: Optional[str] = Query(None, description="Semaines a scraper (ex: 1,2,3 ou 1-5). Defaut: 1-22"),
    divisions: Optional[str] = Query(None, description="Indices de divisions (ex: 1,5,10). Defaut: toutes"),
    resume_division: Optional[int] = Query(None, description="Reprendre depuis cette division"),
    resume_week: Optional[int] = Query(None, description="Reprendre depuis cette semaine"),
):
    """Lance le scraping interclubs en arriere-plan. Supporte filtrage par semaines et divisions."""
    global _current_interclubs_scrape

    if _current_interclubs_scrape and _current_interclubs_scrape.get('status') == 'running':
        raise HTTPException(status_code=409, detail={
            "error": "Interclubs scraping already in progress",
            "task_id": _current_interclubs_scrape['task_id'],
        })

    week_list = None
    if weeks:
        week_list = []
        for part in weeks.split(','):
            part = part.strip()
            if '-' in part:
                start, end = part.split('-', 1)
                week_list.extend(range(int(start), int(end) + 1))
            else:
                week_list.append(int(part))

    div_list = None
    if divisions:
        div_list = [int(d.strip()) for d in divisions.split(',')]

    resume_from = None
    if resume_division is not None and resume_week is not None:
        resume_from = {'division_index': resume_division, 'week': resume_week}

    task_id = f"interclubs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    asyncio.create_task(run_interclubs_scrape(task_id, week_list, div_list, resume_from))

    return {
        "status": "started", "task_id": task_id,
        "weeks": week_list or list(range(1, 23)),
        "divisions": div_list or "all",
        "message": "Scraping interclubs demarre en arriere-plan"
    }


@router.get("/scrape/interclubs/status", tags=["Interclubs Scraping"])
async def get_interclubs_scrape_status():
    """Récupère le statut du scraping interclubs en cours."""
    global _current_interclubs_scrape
    if not _current_interclubs_scrape:
        return {"running": False, "message": "Aucun scraping interclubs en cours ou recent"}

    elapsed = None
    if _current_interclubs_scrape.get('started_at'):
        try:
            start = datetime.fromisoformat(_current_interclubs_scrape['started_at'])
            elapsed = (datetime.now() - start).total_seconds()
        except (ValueError, TypeError):
            pass

    return {
        "running": _current_interclubs_scrape['status'] == 'running',
        "task_id": _current_interclubs_scrape['task_id'],
        "status": _current_interclubs_scrape['status'],
        "started_at": _current_interclubs_scrape.get('started_at'),
        "finished_at": _current_interclubs_scrape.get('finished_at'),
        "elapsed_seconds": elapsed,
        "total_rankings": _current_interclubs_scrape.get('total_rankings', 0),
        "errors_count": _current_interclubs_scrape.get('errors_count', 0),
        "last_success": _current_interclubs_scrape.get('last_success'),
    }


@router.get("/scrape/interclubs/logs/{task_id}", tags=["Interclubs Scraping"])
async def get_interclubs_scrape_logs(task_id: str):
    """Récupère les logs d'une tache de scraping interclubs."""
    if task_id not in _interclubs_scrape_logs:
        return {"task_id": task_id, "logs": []}
    return {"task_id": task_id, "logs": _interclubs_scrape_logs[task_id]}


@router.post("/scrape/interclubs/cancel", tags=["Interclubs Scraping"])
async def cancel_interclubs_scrape():
    """Annule le scraping interclubs en cours."""
    global _current_interclubs_scrape
    if not _current_interclubs_scrape or _current_interclubs_scrape.get('status') != 'running':
        raise HTTPException(status_code=404, detail="Aucun scraping interclubs en cours")
    _current_interclubs_scrape['status'] = 'cancelled'
    _current_interclubs_scrape['finished_at'] = datetime.now().isoformat()
    return {"status": "cancelled", "task_id": _current_interclubs_scrape['task_id'], "message": "Scraping interclubs annule"}

"""
Routes: Tournaments (CRUD + scraping)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import asyncio
import logging
from datetime import datetime

from src.database import queries
from src.api.cache import cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Tournaments"])

# État global du scraping tournois
_current_tournament_scrape = None
_tournament_scrape_logs = {}


@router.get("/tournaments")
async def list_tournaments(
    level: Optional[str] = Query(None, description="Filtrer par niveau"),
    date_from: Optional[str] = Query(None, description="Date de début (DD/MM/YYYY)"),
    date_to: Optional[str] = Query(None, description="Date de fin (DD/MM/YYYY)"),
    search: Optional[str] = Query(None, description="Recherche par nom ou référence"),
    limit: int = Query(200, ge=1, le=1000, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Offset pour pagination")
):
    """Liste les tournois avec filtres par niveau, dates et recherche textuelle."""
    tournaments = queries.get_all_tournaments(
        level=level, date_from=date_from, date_to=date_to,
        search=search, limit=limit, offset=offset
    )
    return {"count": len(tournaments), "tournaments": tournaments}


@router.get("/tournaments/levels")
async def list_tournament_levels():
    """Liste tous les niveaux de tournois disponibles."""
    cached = cache.get("tournament_levels")
    if cached is not None:
        return cached
    levels = queries.get_tournament_levels()
    result = {"levels": levels}
    cache.set("tournament_levels", result, ttl=600)
    return result


@router.get("/tournaments/{t_id}")
async def get_tournament(t_id: int):
    """Récupère un tournoi par son ID."""
    tournament = queries.get_tournament(t_id)
    if not tournament:
        raise HTTPException(status_code=404, detail=f"Tournoi {t_id} non trouvé")
    return tournament


@router.get("/tournaments/{t_id}/series")
async def get_tournament_series(t_id: int):
    """Récupère les séries d'un tournoi."""
    tournament = queries.get_tournament(t_id)
    if not tournament:
        raise HTTPException(status_code=404, detail=f"Tournoi {t_id} non trouvé")
    series = queries.get_tournament_series(t_id)
    return {"tournament": tournament, "count": len(series), "series": series}


@router.get("/tournaments/{t_id}/inscriptions")
async def get_tournament_inscriptions(
    t_id: int,
    series_name: Optional[str] = Query(None, description="Filtrer par série")
):
    """Récupère les inscriptions d'un tournoi."""
    tournament = queries.get_tournament(t_id)
    if not tournament:
        raise HTTPException(status_code=404, detail=f"Tournoi {t_id} non trouvé")
    inscriptions = queries.get_tournament_inscriptions(t_id, series_name)
    return {"tournament": tournament, "count": len(inscriptions), "inscriptions": inscriptions}


@router.get("/tournaments/{t_id}/results")
async def get_tournament_results(
    t_id: int,
    series_name: Optional[str] = Query(None, description="Filtrer par série")
):
    """Récupère les résultats d'un tournoi."""
    tournament = queries.get_tournament(t_id)
    if not tournament:
        raise HTTPException(status_code=404, detail=f"Tournoi {t_id} non trouvé")
    results = queries.get_tournament_results(t_id, series_name)
    return {"tournament": tournament, "count": len(results), "results": results}


# --- Tournament Scraping ---

async def run_tournament_scrape(task_id: str):
    """Exécute le scraping des tournois en arrière-plan."""
    global _current_tournament_scrape

    from src.scraper.tournament_scraper import (
        get_all_tournaments, get_tournament_series,
        get_tournament_inscriptions, get_tournament_results
    )

    _tournament_scrape_logs[task_id] = []

    def add_log(msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        _tournament_scrape_logs[task_id].append({"timestamp": timestamp, "message": msg})
        logger.info(msg)
        if len(_tournament_scrape_logs[task_id]) > 1000:
            _tournament_scrape_logs[task_id] = _tournament_scrape_logs[task_id][-1000:]

    _current_tournament_scrape = {
        'task_id': task_id, 'status': 'running',
        'started_at': datetime.now().isoformat(),
        'total_tournaments': 0, 'completed_tournaments': 0,
        'total_series': 0, 'total_inscriptions': 0,
        'total_results': 0, 'current_tournament': None, 'errors': []
    }

    try:
        add_log("[TOURNAMENTS] Récupération de la liste des tournois...")
        tournaments = get_all_tournaments()
        _current_tournament_scrape['total_tournaments'] = len(tournaments)
        add_log(f"[TOURNAMENTS] {len(tournaments)} tournois trouvés")

        for tournament in tournaments:
            queries.insert_tournament(tournament.to_dict())
        add_log("[TOURNAMENTS] Tournois sauvegardés dans la base")

        for i, tournament in enumerate(tournaments, 1):
            # Vérifier si le scraping a été annulé
            if _current_tournament_scrape.get('status') != 'running':
                add_log(f"[TOURNAMENTS] Scraping annulé par l'utilisateur")
                return

            _current_tournament_scrape['current_tournament'] = tournament.name
            _current_tournament_scrape['completed_tournaments'] = i - 1
            add_log(f"[TOURNAMENTS] {i}/{len(tournaments)} - {tournament.name}...")

            try:
                series = get_tournament_series(tournament.t_id)
                for s in series:
                    queries.insert_tournament_series(s.to_dict())
                _current_tournament_scrape['total_series'] += len(series)
                await asyncio.sleep(0.2)

                inscriptions = get_tournament_inscriptions(tournament.t_id)
                for insc in inscriptions:
                    queries.insert_tournament_inscription(insc.to_dict())
                _current_tournament_scrape['total_inscriptions'] += len(inscriptions)
                await asyncio.sleep(0.2)

                results = get_tournament_results(tournament.t_id)
                for res in results:
                    queries.insert_tournament_result(res.to_dict())
                _current_tournament_scrape['total_results'] += len(results)

                add_log(f"[TOURNAMENTS]   -> {len(series)} séries, {len(inscriptions)} inscriptions, {len(results)} résultats")
            except Exception as e:
                _current_tournament_scrape['errors'].append(f"Erreur pour {tournament.name}: {str(e)}")
                add_log(f"[TOURNAMENTS]   -> Erreur: {e}")

            await asyncio.sleep(0.3)

        _current_tournament_scrape['completed_tournaments'] = len(tournaments)
        _current_tournament_scrape['status'] = 'success'
        _current_tournament_scrape['finished_at'] = datetime.now().isoformat()
        add_log(f"[TOURNAMENTS] Terminé: {len(tournaments)} tournois, "
                f"{_current_tournament_scrape['total_series']} séries, "
                f"{_current_tournament_scrape['total_inscriptions']} inscriptions, "
                f"{_current_tournament_scrape['total_results']} résultats")

    except Exception as e:
        _current_tournament_scrape['status'] = 'failed'
        _current_tournament_scrape['errors'].append(str(e))
        _current_tournament_scrape['finished_at'] = datetime.now().isoformat()
        add_log(f"[TOURNAMENTS] Erreur fatale: {e}")


@router.post("/scrape/tournaments", tags=["Tournament Scraping"])
async def start_tournament_scrape():
    """Lance un scraping complet de tous les tournois."""
    global _current_tournament_scrape

    if _current_tournament_scrape and _current_tournament_scrape.get('status') == 'running':
        raise HTTPException(status_code=409, detail={
            "error": "Tournament scraping already in progress",
            "task_id": _current_tournament_scrape['task_id'],
            "started_at": _current_tournament_scrape['started_at'],
            "progress": f"{_current_tournament_scrape['completed_tournaments']}/{_current_tournament_scrape['total_tournaments']} tournois"
        })

    task_id = f"tournaments_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    asyncio.create_task(run_tournament_scrape(task_id))
    return {"status": "started", "task_id": task_id, "message": "Scraping des tournois démarré en arrière-plan"}


@router.get("/scrape/tournaments/status", tags=["Tournament Scraping"])
async def get_tournament_scrape_status():
    """Récupère le statut du scraping des tournois en cours."""
    global _current_tournament_scrape
    if not _current_tournament_scrape:
        return {"running": False, "message": "Aucun scraping de tournois en cours ou récent"}

    elapsed = None
    if _current_tournament_scrape.get('started_at'):
        try:
            start = datetime.fromisoformat(_current_tournament_scrape['started_at'])
            elapsed = (datetime.now() - start).total_seconds()
        except (ValueError, TypeError):
            pass

    progress_percent = 0
    if _current_tournament_scrape['total_tournaments'] > 0:
        progress_percent = round(
            _current_tournament_scrape['completed_tournaments'] /
            _current_tournament_scrape['total_tournaments'] * 100, 1
        )

    return {
        "running": _current_tournament_scrape['status'] == 'running',
        "task_id": _current_tournament_scrape['task_id'],
        "status": _current_tournament_scrape['status'],
        "started_at": _current_tournament_scrape.get('started_at'),
        "finished_at": _current_tournament_scrape.get('finished_at'),
        "elapsed_seconds": elapsed,
        "total_tournaments": _current_tournament_scrape['total_tournaments'],
        "completed_tournaments": _current_tournament_scrape['completed_tournaments'],
        "total_series": _current_tournament_scrape['total_series'],
        "total_inscriptions": _current_tournament_scrape['total_inscriptions'],
        "total_results": _current_tournament_scrape['total_results'],
        "current_tournament": _current_tournament_scrape.get('current_tournament'),
        "errors_count": len(_current_tournament_scrape.get('errors', [])),
        "progress_percent": progress_percent
    }


@router.get("/scrape/tournaments/logs/{task_id}", tags=["Tournament Scraping"])
async def get_tournament_scrape_logs(task_id: str):
    """Récupère les logs d'une tâche de scraping de tournois."""
    if task_id not in _tournament_scrape_logs:
        return {"task_id": task_id, "logs": []}
    return {"task_id": task_id, "logs": _tournament_scrape_logs[task_id]}


@router.post("/scrape/tournaments/cancel", tags=["Tournament Scraping"])
async def cancel_tournament_scrape():
    """Annule le scraping des tournois en cours."""
    global _current_tournament_scrape
    if not _current_tournament_scrape or _current_tournament_scrape.get('status') != 'running':
        raise HTTPException(status_code=404, detail="Aucun scraping de tournois en cours")
    _current_tournament_scrape['status'] = 'cancelled'
    _current_tournament_scrape['finished_at'] = datetime.now().isoformat()
    return {"status": "cancelled", "task_id": _current_tournament_scrape['task_id'], "message": "Scraping des tournois annulé"}


@router.post("/tournaments/{t_id}/scrape", tags=["Tournament Scraping"])
async def scrape_single_tournament(t_id: int):
    """Rescrape un tournoi : supprime les anciennes donnees puis reimporte series, inscriptions et resultats."""
    from src.scraper.tournament_scraper import (
        get_tournament_series as scrape_series,
        get_tournament_inscriptions as scrape_inscriptions,
        get_tournament_results as scrape_results
    )

    try:
        tournament = queries.get_tournament(t_id)
        if not tournament:
            raise HTTPException(status_code=404, detail=f"Tournoi {t_id} non trouvé. Lancez d'abord /api/scrape/tournaments")

        queries.delete_tournament_data(t_id)

        series = scrape_series(t_id)
        for s in series:
            queries.insert_tournament_series(s.to_dict())

        inscriptions = scrape_inscriptions(t_id)
        for insc in inscriptions:
            queries.insert_tournament_inscription(insc.to_dict())

        results = scrape_results(t_id)
        for res in results:
            queries.insert_tournament_result(res.to_dict())

        return {
            "success": True, "tournament_id": t_id,
            "tournament_name": tournament['name'],
            "series_count": len(series),
            "inscriptions_count": len(inscriptions),
            "results_count": len(results),
            "message": f"Tournoi {tournament['name']} scrapé avec succès"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur scraping tournoi {t_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors du scraping du tournoi")

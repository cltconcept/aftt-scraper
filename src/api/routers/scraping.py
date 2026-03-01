"""
Routes: Scraping automatique (full scrape management)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import asyncio
import json
import logging
from datetime import datetime

from src.database import queries
from src.api.cache import cache
from src.scraper.members_scraper import get_club_members
from src.scraper.player_scraper import get_player_info
from src.scraper.clubs_scraper import get_all_clubs
from src.scraper.ranking_scraper import get_club_ranking_players_async

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/scrape", tags=["Scraping"])

# État global du scraping
_current_task_id = None
_scrape_logs = {}


def _add_log(task_id: int, message: str):
    """Ajoute un log pour une tâche."""
    if task_id not in _scrape_logs:
        _scrape_logs[task_id] = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    _scrape_logs[task_id].append({"timestamp": timestamp, "message": message})
    if len(_scrape_logs[task_id]) > 1000:
        _scrape_logs[task_id] = _scrape_logs[task_id][-1000:]
    logger.info(message)


async def run_full_scrape(task_id: int, trigger_type: str):
    """Exécute le scraping complet en arrière-plan."""
    global _current_task_id
    _current_task_id = task_id
    _scrape_logs[task_id] = []
    _add_log(task_id, f"[SCRAPE] Démarrage tâche #{task_id} (trigger: {trigger_type})")

    try:
        all_clubs = queries.get_all_clubs()
        total_clubs = len(all_clubs)
        queries.update_scrape_task(task_id, total_clubs=total_clubs if total_clubs else 0)
        _add_log(task_id, f"[SCRAPE] {total_clubs} clubs à traiter")

        clubs_by_province = {}
        for club in all_clubs:
            prov = club.get('province', 'Non spécifié') or 'Non spécifié'
            if prov not in clubs_by_province:
                clubs_by_province[prov] = []
            clubs_by_province[prov].append(club)

        completed = 0
        total_players = 0
        total_matches_scraped = 0
        total_fiches_scraped = 0
        errors = []

        for province, clubs in clubs_by_province.items():
            for club in clubs:
                # Vérifier si le scraping a été annulé
                current = queries.get_scrape_task_by_id(task_id)
                if current and current.get('status') == 'cancelled':
                    _add_log(task_id, f"[SCRAPE] Tâche #{task_id} annulée par l'utilisateur")
                    return

                code = club.get('code')
                if not code:
                    continue

                queries.update_scrape_task(
                    task_id, completed_clubs=completed, total_players=total_players,
                    current_club=code, current_province=province
                )

                try:
                    from src.scraper.clubs_scraper import extract_province_from_code

                    members_data = get_club_members(code)
                    members_list = members_data.get('members', [])
                    club_info = members_data.get('club_info', {})
                    club_name = members_data.get('club_name', code)

                    existing_club = queries.get_club(code)
                    prov = None
                    if existing_club and existing_club.get('province'):
                        prov = existing_club['province']
                    else:
                        prov = extract_province_from_code(code)

                    if club_info:
                        club_data = {'code': code, 'name': club_name, 'province': prov, **club_info}
                        queries.insert_club(club_data)
                        _add_log(task_id, f"[DB] Club {code} ({club_name}) sauvegardé")

                    all_players = {}
                    try:
                        ranking_data = await get_club_ranking_players_async(code)
                        for player in ranking_data.get('players_men', []):
                            licence = player.get('licence')
                            if licence:
                                all_players[licence] = {
                                    'licence': licence, 'name': player.get('name'),
                                    'club_code': code, 'ranking': player.get('ranking'),
                                    'points_current': player.get('points'), 'category': 'SEN',
                                }
                        for player in ranking_data.get('players_women', []):
                            licence = player.get('licence')
                            if licence:
                                all_players[licence] = {
                                    'licence': licence, 'name': player.get('name'),
                                    'club_code': code, 'ranking': player.get('ranking'),
                                    'points_current': player.get('points'), 'category': 'SEN',
                                }
                    except Exception as e:
                        _add_log(task_id, f"[WARNING] Erreur ranking_scraper pour {code}: {e}")

                    for member in members_list:
                        licence = member.get('licence')
                        if licence:
                            if licence in all_players:
                                all_players[licence]['category'] = member.get('category', 'SEN')
                            else:
                                all_players[licence] = {
                                    'licence': licence, 'name': member.get('name'),
                                    'club_code': code, 'ranking': member.get('ranking'),
                                    'category': member.get('category', 'SEN'),
                                }

                    players_inserted = 0
                    for licence, player_data in all_players.items():
                        queries.insert_player(player_data)
                        players_inserted += 1
                        if players_inserted % 10 == 0:
                            _add_log(task_id, f"[DB] {players_inserted}/{len(all_players)} joueurs de base sauvegardés")

                    if players_inserted > 0:
                        _add_log(task_id, f"[DB] {players_inserted} joueurs de base sauvegardés pour {code}")

                    total_players += len(all_players)

                    players_scraped = 0
                    players_errors = []

                    for licence, player_data in all_players.items():
                        if not licence:
                            continue
                        # Vérifier annulation tous les 10 joueurs
                        if players_scraped % 10 == 0 and players_scraped > 0:
                            current = queries.get_scrape_task_by_id(task_id)
                            if current and current.get('status') == 'cancelled':
                                _add_log(task_id, f"[SCRAPE] Tâche #{task_id} annulée par l'utilisateur")
                                return
                        try:
                            player_info = get_player_info(licence)
                            updated_data = {
                                'licence': licence,
                                'name': player_info.get('name') or player_data.get('name'),
                                'club_code': code,
                                'ranking': player_info.get('ranking') or player_data.get('ranking'),
                                'category': player_data.get('category', 'SEN'),
                                'points_start': player_info.get('points_start'),
                                'points_current': player_info.get('points_current') or player_data.get('points_current'),
                                'ranking_position': player_info.get('ranking_position'),
                                'total_wins': player_info.get('total_wins', 0),
                                'total_losses': player_info.get('total_losses', 0),
                                'last_update': player_info.get('last_update'),
                            }

                            women_stats = player_info.get('women_stats')
                            if women_stats:
                                updated_data['women_ranking'] = women_stats.get('ranking')
                                updated_data['women_points_start'] = women_stats.get('points_start')
                                updated_data['women_points_current'] = women_stats.get('points_current')
                                updated_data['women_total_wins'] = women_stats.get('total_wins', 0)
                                updated_data['women_total_losses'] = women_stats.get('total_losses', 0)

                            queries.insert_player(updated_data)

                            matches_m = player_info.get('matches', [])
                            matches_m_count = len(matches_m)
                            queries.insert_matches_batch([
                                {**match, 'player_licence': licence, 'fiche_type': 'masculine'}
                                for match in matches_m
                            ])
                            queries.insert_player_stats_batch([
                                {**stat, 'player_licence': licence, 'fiche_type': 'masculine'}
                                for stat in player_info.get('stats_by_ranking', [])
                            ])

                            matches_f_count = 0
                            if women_stats:
                                matches_f = women_stats.get('matches', [])
                                matches_f_count = len(matches_f)
                                queries.insert_matches_batch([
                                    {**match, 'player_licence': licence, 'fiche_type': 'feminine'}
                                    for match in matches_f
                                ])
                                queries.insert_player_stats_batch([
                                    {**stat, 'player_licence': licence, 'fiche_type': 'feminine'}
                                    for stat in women_stats.get('stats_by_ranking', [])
                                ])

                            total_matches_scraped += matches_m_count + matches_f_count
                            total_fiches_scraped += 1

                            player_name = updated_data.get('name', 'N/A')[:25]
                            player_ranking = updated_data.get('ranking', '?')
                            player_pts = updated_data.get('points_current', 0) or 0
                            player_wins = updated_data.get('total_wins', 0)
                            player_losses = updated_data.get('total_losses', 0)
                            _add_log(task_id, f"[JOUEUR] {licence} - {player_name} ({player_ranking}) | {player_pts:.0f}pts | {player_wins}V-{player_losses}D | {matches_m_count} matchs")

                            players_scraped += 1
                            if players_scraped % 5 == 0:
                                _add_log(task_id, f"[DB] {players_scraped}/{len(all_players)} fiches scrapées pour {code} (total matchs: {total_matches_scraped})")

                            await asyncio.sleep(0.3)

                        except Exception as e:
                            error_msg = f"Erreur fiche joueur {licence}: {str(e)[:100]}"
                            players_errors.append(error_msg)
                            _add_log(task_id, f"[WARNING] {error_msg}")
                            await asyncio.sleep(2.0)

                    summary_parts = [f"[SCRAPE] {code}", f"{len(all_players)} joueurs", f"{players_scraped} fiches", f"Total matchs global: {total_matches_scraped}"]
                    if players_errors:
                        summary_parts.append(f"{len(players_errors)} erreurs fiches")
                    _add_log(task_id, " | ".join(summary_parts))

                except Exception as e:
                    error_msg = f"{code}: {str(e)}"
                    errors.append(error_msg)
                    _add_log(task_id, f"[SCRAPE] {code}: {e}")

                completed += 1
                await asyncio.sleep(1.0)

        queries.update_scrape_task(
            task_id, completed_clubs=completed, total_players=total_players,
            status='success', errors_count=len(errors),
            errors_detail=json.dumps(errors) if errors else None,
            current_club=None, current_province=None
        )
        cache.clear()
        _add_log(task_id, f"[SCRAPE] Tâche #{task_id} terminée: {completed} clubs, {total_players} joueurs, {total_fiches_scraped} fiches, {total_matches_scraped} matchs, {len(errors)} erreurs clubs")

    except Exception as e:
        _add_log(task_id, f"[SCRAPE] Tâche #{task_id} échouée: {e}")
        queries.update_scrape_task(task_id, status='failed', errors_detail=json.dumps([str(e)]))
    finally:
        _current_task_id = None


@router.post("/all")
async def start_full_scrape_endpoint(
    trigger: str = Query("manual", description="Type de déclencheur (manual, cron)")
):
    """Lance un scraping complet en arriere-plan : parcourt tous les clubs, scrape membres et fiches joueurs."""
    current = queries.get_current_scrape_task()
    if current:
        raise HTTPException(status_code=409, detail={
            "error": "Scraping already in progress",
            "task_id": current['id'],
            "started_at": current['started_at'],
            "progress": f"{current['completed_clubs']}/{current['total_clubs']} clubs"
        })

    all_clubs = queries.get_all_clubs()
    total_clubs = len(all_clubs)
    task_id = queries.create_scrape_task(trigger_type=trigger, total_clubs=total_clubs)
    asyncio.create_task(run_full_scrape(task_id, trigger))

    return {
        "status": "started", "task_id": task_id,
        "total_clubs": total_clubs,
        "message": f"Scraping de {total_clubs} clubs démarré en arrière-plan"
    }


@router.get("/status")
async def get_scrape_status():
    """Statut du scraping global en cours : progression, club actuel, nombre de joueurs traites."""
    current = queries.get_current_scrape_task()
    if not current:
        return {"running": False, "message": "Aucun scraping en cours"}

    elapsed = None
    if current['started_at']:
        try:
            start = datetime.fromisoformat(current['started_at'].replace('Z', '+00:00'))
            elapsed = (datetime.now() - start.replace(tzinfo=None)).total_seconds()
        except (ValueError, TypeError, AttributeError):
            pass

    return {
        "running": True,
        "task_id": current['id'],
        "started_at": current['started_at'],
        "elapsed_seconds": elapsed,
        "total_clubs": current['total_clubs'],
        "completed_clubs": current['completed_clubs'],
        "total_players": current['total_players'],
        "current_club": current['current_club'],
        "current_province": current['current_province'],
        "errors_count": current['errors_count'],
        "progress_percent": round((current['completed_clubs'] / current['total_clubs'] * 100), 1) if current['total_clubs'] > 0 else 0
    }


@router.get("/logs/{task_id}")
async def get_scrape_logs(task_id: int):
    """Logs en temps reel d'une tache de scraping (1000 derniers messages)."""
    if task_id not in _scrape_logs:
        return {"task_id": task_id, "logs": []}
    return {"task_id": task_id, "logs": _scrape_logs[task_id]}


@router.get("/history")
async def get_scrape_history(
    limit: int = Query(20, ge=1, le=100, description="Nombre de tâches à récupérer")
):
    """Récupère l'historique des tâches de scraping."""
    tasks = queries.get_scrape_task_history(limit=limit)
    for task in tasks:
        if task['started_at'] and task['finished_at']:
            try:
                start = datetime.fromisoformat(task['started_at'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(task['finished_at'].replace('Z', '+00:00'))
                task['duration_seconds'] = (end - start).total_seconds()
            except (ValueError, TypeError, AttributeError):
                task['duration_seconds'] = None
        else:
            task['duration_seconds'] = None
    return {"count": len(tasks), "tasks": tasks}


@router.get("/task/{task_id}")
async def get_scrape_task_detail(task_id: int):
    """Récupère les détails d'une tâche de scraping par son ID."""
    task = queries.get_scrape_task_by_id(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    if task.get('errors_detail'):
        try:
            task['errors_list'] = json.loads(task['errors_detail'])
        except (json.JSONDecodeError, TypeError):
            task['errors_list'] = []
    else:
        task['errors_list'] = []
    return task


@router.post("/cancel")
async def cancel_scrape():
    """Annule la tâche de scraping en cours."""
    current = queries.get_current_scrape_task()
    if not current:
        raise HTTPException(status_code=404, detail="Aucun scraping en cours")
    queries.update_scrape_task(current['id'], status='cancelled')
    return {"status": "cancelled", "task_id": current['id'], "message": "Scraping annulé"}


@router.post("/refresh-clubs")
async def refresh_clubs_names():
    """Rafraichit la liste et les noms des clubs depuis le site AFTT sans scraper les joueurs."""
    try:
        all_clubs_from_web = get_all_clubs()
        updated_count = 0
        for club_obj in all_clubs_from_web:
            club_dict = club_obj.to_dict() if hasattr(club_obj, 'to_dict') else {
                'code': club_obj.code, 'name': club_obj.name, 'province': club_obj.province
            }
            if club_dict.get('name'):
                queries.insert_club(club_dict)
                updated_count += 1
        return {"status": "success", "message": f"{updated_count} clubs mis à jour", "total_clubs": len(all_clubs_from_web)}
    except Exception as e:
        logger.error(f"Erreur lors du rafraîchissement des clubs: {e}")
        raise HTTPException(status_code=500, detail="Erreur interne lors du rafraîchissement des clubs")

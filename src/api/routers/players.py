"""
Routes: Players, Rankings, Search
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from src.database import queries
from src.scraper.player_scraper import get_player_info
from src.api.validators import validate_licence

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Players"])


@router.get("/players")
async def list_players(
    club_code: Optional[str] = Query(None, description="Code du club (ex: H004)"),
    ranking: Optional[str] = Query(None, description="Classement (ex: B2, C0, D6)"),
    min_points: Optional[float] = Query(None, description="Points minimum"),
    max_points: Optional[float] = Query(None, description="Points maximum"),
    search: Optional[str] = Query(None, description="Recherche par nom ou numero de licence"),
    order_by: str = Query("points_current DESC", description="Ordre de tri SQL"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Offset pour pagination")
):
    """Liste les joueurs avec filtres optionnels et pagination."""
    players = queries.get_all_players(
        club_code=club_code.upper() if club_code else None,
        ranking=ranking,
        min_points=min_points,
        max_points=max_points,
        search=search,
        order_by=order_by,
        limit=limit,
        offset=offset
    )
    return {
        "count": len(players),
        "players": players
    }


@router.get("/players/{licence}", tags=["Players"])
async def get_player(licence: str):
    """Recupere la fiche complete d'un joueur : infos, stats et matchs (masculin et feminin)."""
    licence = validate_licence(licence)
    player = queries.get_player(licence)
    if not player:
        raise HTTPException(status_code=404, detail=f"Joueur {licence} non trouvé")

    player['stats_masculine'] = queries.get_player_stats(licence, 'masculine')
    player['stats_feminine'] = queries.get_player_stats(licence, 'feminine')
    player['matches_masculine'] = queries.get_player_matches(licence, 'masculine')
    player['matches_feminine'] = queries.get_player_matches(licence, 'feminine')

    return player


@router.post("/players/{licence}/scrape", tags=["Players"])
async def scrape_single_player(licence: str):
    """Rescrape la fiche d'un joueur depuis le site AFTT. Supprime ses matchs/stats puis reimporte."""
    licence = validate_licence(licence)
    existing = queries.get_player(licence)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Joueur {licence} non trouvé")

    try:
        player_info = get_player_info(licence)

        queries.delete_player_matches_and_stats(licence)

        updated_data = {
            'licence': licence,
            'name': player_info.get('name') or existing['name'],
            'club_code': existing.get('club_code'),
            'ranking': player_info.get('ranking') or existing.get('ranking'),
            'category': existing.get('category'),
            'points_start': player_info.get('points_start'),
            'points_current': player_info.get('points_current'),
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

        queries.insert_matches_batch([
            {**match, 'player_licence': licence, 'fiche_type': 'masculine'}
            for match in player_info.get('matches', [])
        ])
        queries.insert_player_stats_batch([
            {**stat, 'player_licence': licence, 'fiche_type': 'masculine'}
            for stat in player_info.get('stats_by_ranking', [])
        ])

        if women_stats:
            queries.insert_matches_batch([
                {**match, 'player_licence': licence, 'fiche_type': 'feminine'}
                for match in women_stats.get('matches', [])
            ])
            queries.insert_player_stats_batch([
                {**stat, 'player_licence': licence, 'fiche_type': 'feminine'}
                for stat in women_stats.get('stats_by_ranking', [])
            ])

        updated = queries.get_player(licence)
        updated['stats_masculine'] = queries.get_player_stats(licence, 'masculine')
        updated['stats_feminine'] = queries.get_player_stats(licence, 'feminine')
        updated['matches_masculine'] = queries.get_player_matches(licence, 'masculine')
        updated['matches_feminine'] = queries.get_player_matches(licence, 'feminine')

        return {
            "success": True,
            "message": f"Joueur {licence} rescrappé avec succès",
            "player": updated
        }

    except Exception as e:
        logger.error(f"Erreur rescrape joueur {licence}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors du scraping du joueur")


@router.get("/players/{licence}/matches", tags=["Players"])
async def get_player_matches(
    licence: str,
    fiche_type: Optional[str] = Query(None, description="Type de fiche : 'masculine' ou 'feminine'"),
    opponent: Optional[str] = Query(None, description="Filtrer par licence adversaire"),
    limit: int = Query(100, ge=1, le=500, description="Nombre max de resultats")
):
    """Recupere l'historique des matchs d'un joueur, avec filtres optionnels par fiche et adversaire."""
    licence = validate_licence(licence)
    player = queries.get_player(licence)
    if not player:
        raise HTTPException(status_code=404, detail=f"Joueur {licence} non trouvé")

    matches = queries.get_player_matches(
        licence=licence, fiche_type=fiche_type,
        opponent_licence=opponent, limit=limit
    )

    return {
        "player": {"licence": licence, "name": player['name']},
        "count": len(matches),
        "matches": matches
    }


@router.get("/players/{licence1}/vs/{licence2}", tags=["Players"])
async def get_head_to_head(licence1: str, licence2: str):
    """Confrontations directes entre deux joueurs : victoires, defaites et liste des matchs."""
    player1 = queries.get_player(licence1)
    player2 = queries.get_player(licence2)

    if not player1:
        raise HTTPException(status_code=404, detail=f"Joueur {licence1} non trouvé")
    if not player2:
        raise HTTPException(status_code=404, detail=f"Joueur {licence2} non trouvé")

    h2h = queries.get_head_to_head(licence1, licence2)
    h2h['player1'] = {"licence": licence1, "name": player1['name']}
    h2h['player2'] = {"licence": licence2, "name": player2['name']}

    return h2h


@router.get("/rankings/top", tags=["Rankings"])
async def get_top_players(
    limit: int = Query(100, ge=1, le=500, description="Nombre de joueurs"),
    province: Optional[str] = Query(None, description="Filtrer par province (ex: Hainaut)"),
    club_code: Optional[str] = Query(None, description="Filtrer par club (ex: H004)"),
    ranking: Optional[str] = Query(None, description="Filtrer par classement (ex: B2)")
):
    """Classement des joueurs par points decroissants, avec filtres province/club/classement."""
    players = queries.get_top_players(
        limit=limit, province=province,
        club_code=club_code.upper() if club_code else None,
        ranking=ranking
    )
    return {"count": len(players), "players": players}


@router.get("/rankings/progressions", tags=["Rankings"])
async def get_top_progressions(
    limit: int = Query(100, ge=1, le=500, description="Nombre de joueurs")
):
    """Joueurs avec la plus grande progression de points sur la saison en cours."""
    players = queries.get_top_progressions(limit=limit)
    return {"count": len(players), "players": players}


@router.get("/search", tags=["Search"])
async def search(
    q: str = Query(..., min_length=2, description="Terme de recherche"),
    limit: int = Query(50, ge=1, le=200, description="Nombre max de résultats")
):
    """Recherche de joueurs par nom (partiel) ou numero de licence dans toute la base."""
    players = queries.search_players(q, limit=limit)
    return {"query": q, "count": len(players), "players": players}

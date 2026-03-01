"""
Routes: Clubs (CRUD + scraping individuel)
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from src.database import queries
from src.api.cache import cache
from src.scraper.members_scraper import get_club_members
from src.scraper.player_scraper import get_player_info
from src.scraper.clubs_scraper import get_all_clubs
from src.scraper.ranking_scraper import get_club_ranking_players_async
from src.api.validators import validate_club_code

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["Clubs"])


@router.get("/clubs")
async def list_clubs(
    province: Optional[str] = Query(None, description="Filtrer par province"),
    limit: int = Query(500, ge=1, le=10000, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Offset pour pagination")
):
    """Liste tous les clubs AFTT avec filtre par province et pagination."""
    clubs = queries.get_all_clubs(province=province, limit=limit, offset=offset)
    return {
        "count": len(clubs),
        "clubs": clubs
    }


@router.get("/clubs/provinces")
async def list_provinces():
    """Liste toutes les provinces disponibles."""
    cached = cache.get("provinces")
    if cached is not None:
        return cached
    provinces = queries.get_provinces()
    result = {"provinces": provinces}
    cache.set("provinces", result, ttl=600)
    return result


@router.get("/clubs/{code}")
async def get_club(code: str):
    """Recupere les informations d'un club par son code (ex: H004, BW023)."""
    code = validate_club_code(code)
    club = queries.get_club(code)
    if not club:
        raise HTTPException(status_code=404, detail=f"Club {code} non trouvé")
    return club


@router.get("/clubs/{code}/players")
async def get_club_players(code: str):
    """Liste tous les joueurs affilies a un club, avec classements et points."""
    code = validate_club_code(code)
    club = queries.get_club(code)
    if not club:
        raise HTTPException(status_code=404, detail=f"Club {code} non trouvé")

    players = queries.get_club_players(code)
    return {
        "club": club,
        "count": len(players),
        "players": players
    }


@router.post("/clubs/{code}/scrape")
async def scrape_club(code: str, include_ranking: bool = True):
    """Scrape un club complet : membres, classement numerique et fiches individuelles de chaque joueur."""
    from src.scraper.clubs_scraper import extract_province_from_code

    code = validate_club_code(code)

    try:
        # 1. Scraper les membres actifs du club
        members_data = get_club_members(code)
        members_count = len(members_data.get('members', []))
        club_info = members_data.get('club_info', {})
        club_name = members_data.get('club_name', code)

        # Récupérer la province
        existing_club = queries.get_club(code)
        province = None
        if existing_club and existing_club.get('province'):
            province = existing_club['province']
        else:
            province = extract_province_from_code(code)

        # Mettre à jour les infos du club
        if club_info:
            club_data = {
                'code': code,
                'name': club_name,
                'province': province,
                **club_info
            }
            queries.insert_club(club_data)

        # 2. Scraper le classement numérique si demandé
        all_players = {}
        ranking_count = 0

        if include_ranking:
            try:
                logger.info(f"Scraping ranking pour {code}...")
                ranking_data = await get_club_ranking_players_async(code)

                for player in ranking_data.get('players_men', []):
                    licence = player.get('licence')
                    if licence:
                        all_players[licence] = {
                            'licence': licence,
                            'name': player.get('name'),
                            'club_code': code,
                            'ranking': player.get('ranking'),
                            'points_current': player.get('points'),
                            'category': 'SEN',
                        }

                for player in ranking_data.get('players_women', []):
                    licence = player.get('licence')
                    if licence:
                        all_players[licence] = {
                            'licence': licence,
                            'name': player.get('name'),
                            'club_code': code,
                            'ranking': player.get('ranking'),
                            'points_current': player.get('points'),
                            'category': 'SEN',
                        }

                ranking_count = len(all_players)
                logger.info(f"Ranking: {ranking_count} joueurs trouvés")
            except Exception as e:
                logger.warning(f"Erreur ranking_scraper: {e}", exc_info=True)

        # 3. Enrichir avec les données de l'annuaire
        for member in members_data.get('members', []):
            licence = member.get('licence')
            if licence:
                if licence in all_players:
                    all_players[licence]['category'] = member.get('category', 'SEN')
                else:
                    all_players[licence] = {
                        'licence': licence,
                        'name': member.get('name'),
                        'club_code': code,
                        'ranking': member.get('ranking'),
                        'category': member.get('category', 'SEN'),
                    }

        # 4. Importer les joueurs
        for licence, player_data in all_players.items():
            queries.insert_player(player_data)

        # 5. Scraper les fiches individuelles
        players_scraped = 0
        players_errors = []

        for licence, player_data in all_players.items():
            if not licence:
                continue
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

                players_scraped += 1
            except Exception as e:
                players_errors.append({
                    'licence': licence,
                    'name': player_data.get('name'),
                    'error': str(e)
                })

        return {
            "success": True,
            "club_code": code,
            "members_from_annuaire": members_count,
            "members_from_ranking": ranking_count,
            "total_players": len(all_players),
            "players_scraped": players_scraped,
            "players_errors": players_errors,
            "message": f"Scraping terminé: {len(all_players)} joueurs ({members_count} annuaire + {ranking_count} ranking), {players_scraped} fiches"
        }

    except Exception as e:
        logger.error(f"Erreur scraping club {code}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors du scraping du club")


@router.post("/clubs/province/{province}/scrape")
async def scrape_province_clubs(province: str):
    """Scrape tous les clubs d'une province : membres et fiches joueurs pour chaque club."""
    try:
        all_clubs_from_web = get_all_clubs()

        normalized_province = province.strip()
        province_mapping = {
            'Hainaut': 'Hainaut', 'hainaut': 'Hainaut', 'HAINAUT': 'Hainaut',
        }
        normalized_province = province_mapping.get(normalized_province, normalized_province)

        clubs_to_scrape = []
        for club_obj in all_clubs_from_web:
            club_dict = club_obj.to_dict() if hasattr(club_obj, 'to_dict') else {
                'code': club_obj.code, 'name': club_obj.name, 'province': club_obj.province
            }
            queries.insert_club(club_dict)
            if club_dict.get('province') == normalized_province:
                clubs_to_scrape.append(club_dict)

        if not clubs_to_scrape:
            raise HTTPException(status_code=404, detail=f"Aucun club trouvé pour la province '{province}'")

        clubs_scraped = 0
        clubs_errors = []
        total_members = 0
        total_players = 0
        all_players_errors = []

        for club_dict in clubs_to_scrape:
            code = club_dict['code']
            name = club_dict.get('name', code)

            try:
                members_data = get_club_members(code)
                members = members_data.get('members', [])
                total_members += len(members)
                club_info = members_data.get('club_info', {})
                club_name = members_data.get('club_name', name)

                if club_info:
                    club_data_full = {
                        'code': code, 'name': club_name,
                        'province': normalized_province, **club_info
                    }
                    queries.insert_club(club_data_full)

                for member in members:
                    licence = member.get('licence')
                    if not licence:
                        continue
                    try:
                        player_data = {
                            'licence': licence, 'name': member.get('name'),
                            'club_code': code, 'ranking': member.get('ranking'),
                            'category': member.get('category', 'SEN'),
                        }
                        queries.insert_player(player_data)

                        player_info = get_player_info(licence)
                        updated_data = {
                            'licence': licence,
                            'name': player_info.get('name') or member.get('name'),
                            'club_code': code,
                            'ranking': player_info.get('ranking') or member.get('ranking'),
                            'category': member.get('category', 'SEN'),
                            'points_start': player_info.get('points_start'),
                            'points_current': player_info.get('points_current'),
                            'ranking_position': player_info.get('ranking_position'),
                            'total_wins': player_info.get('total_wins', 0),
                            'total_losses': player_info.get('total_losses', 0),
                            'last_update': player_info.get('last_update'),
                        }
                        queries.insert_player(updated_data)

                        queries.insert_matches_batch([
                            {**match, 'player_licence': licence, 'fiche_type': 'masculine'}
                            for match in player_info.get('matches', [])
                        ])
                        queries.insert_player_stats_batch([
                            {**stat, 'player_licence': licence, 'fiche_type': 'masculine'}
                            for stat in player_info.get('stats_by_ranking', [])
                        ])

                        total_players += 1
                    except Exception as e:
                        all_players_errors.append({
                            'club_code': code, 'licence': licence,
                            'name': member.get('name'), 'error': str(e)
                        })

                clubs_scraped += 1

            except Exception as e:
                clubs_errors.append({'club_code': code, 'club_name': name, 'error': str(e)})

        return {
            "success": True,
            "province": province,
            "clubs_total": len(clubs_to_scrape),
            "clubs_scraped": clubs_scraped,
            "clubs_errors": clubs_errors,
            "members_scraped": total_members,
            "players_scraped": total_players,
            "players_errors": all_players_errors,
            "message": f"Scraping terminé: {clubs_scraped}/{len(clubs_to_scrape)} clubs, {total_members} membres, {total_players} fiches joueurs"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erreur scraping province {province}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Erreur interne lors du scraping de la province")

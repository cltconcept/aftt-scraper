"""
API FastAPI pour les données AFTT
"""
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, List
import sys
import os
import json as json_lib
import asyncio
from datetime import datetime

# Ajouter le chemin parent pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.database.connection import init_database, get_stats
from src.database import queries
from src.database.import_json import import_members, import_player
from src.scraper.members_scraper import get_club_members, save_members_to_json
from src.scraper.player_scraper import get_player_info
from src.scraper.clubs_scraper import get_all_clubs
from src.scraper.ranking_scraper import get_club_ranking_players_async
import json
import logging

logger = logging.getLogger(__name__)

# Initialiser la base de données
init_database()

# Charger les clubs si la base est vide
def init_clubs_if_empty():
    """Charge la liste des clubs depuis le site AFTT si la base est vide."""
    try:
        stats = get_stats()
        if stats.get('clubs', 0) == 0:
            logger.info("Base de données vide, chargement des clubs...")
            print("[INIT] Base de données vide, chargement des clubs depuis AFTT...")
            clubs = get_all_clubs()
            for club in clubs:
                club_dict = {
                    'code': club.code,
                    'name': club.name,
                    'province': club.province
                }
                queries.insert_club(club_dict)
            print(f"[INIT] {len(clubs)} clubs chargés !")
            logger.info(f"{len(clubs)} clubs chargés")
    except Exception as e:
        logger.error(f"Erreur lors du chargement initial des clubs: {e}")
        print(f"[INIT] Erreur: {e}")

# Initialiser les clubs au démarrage
init_clubs_if_empty()

# Chemin vers le dossier web
WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'web')

# Créer l'application FastAPI
app = FastAPI(
    title="AFTT Data API",
    description="API pour accéder aux données du tennis de table belge (AFTT)",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =============================================================================
# ROUTES: Stats & Health
# =============================================================================

@app.get("/", tags=["Health"], include_in_schema=False)
async def root():
    """Sert l'interface web principale."""
    index_path = os.path.join(WEB_DIR, 'index.html')
    if os.path.exists(index_path):
        return FileResponse(index_path, media_type='text/html')
    return {
        "name": "AFTT Data API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "clubs": "/api/clubs",
            "players": "/api/players",
            "matches": "/api/matches",
            "rankings": "/api/rankings",
            "search": "/api/search"
        }
    }


@app.get("/api-docs.html", include_in_schema=False)
async def api_docs_page():
    """Sert la page de documentation API."""
    docs_path = os.path.join(WEB_DIR, 'api-docs.html')
    if os.path.exists(docs_path):
        return FileResponse(docs_path, media_type='text/html')
    raise HTTPException(status_code=404, detail="Documentation not found")


@app.get("/api", tags=["Health"])
async def api_info():
    """Information sur l'API."""
    return {
        "name": "AFTT Data API",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "clubs": "/api/clubs",
            "players": "/api/players",
            "matches": "/api/matches",
            "rankings": "/api/rankings",
            "search": "/api/search"
        }
    }


@app.get("/health", tags=["Health"])
async def health():
    """Vérification de l'état de l'API."""
    return {"status": "ok"}


@app.get("/api/stats", tags=["Stats"])
async def get_database_stats():
    """Retourne les statistiques de la base de données."""
    return get_stats()


@app.get("/api/stats/last-scrape-date", tags=["Stats"])
async def get_last_scrape_date():
    """Retourne la date du dernier scrap réussi."""
    last_date = queries.get_last_scrape_date()
    if not last_date:
        return {
            "last_scrape_date": None,
            "message": "Aucun scrap réussi trouvé"
        }
    return {
        "last_scrape_date": last_date
    }


@app.get("/api/stats/clubs-count", tags=["Stats"])
async def get_clubs_count():
    """Retourne le nombre total de clubs."""
    count = queries.get_clubs_count()
    return {
        "clubs_count": count
    }


@app.get("/api/stats/active-players-count", tags=["Stats"])
async def get_active_players_count():
    """Retourne le nombre total de joueurs actifs (avec points ou classement)."""
    count = queries.get_active_players_count()
    return {
        "active_players_count": count
    }


@app.get("/api/stats/detailed", tags=["Stats"])
async def get_detailed_stats():
    """Retourne des statistiques détaillées pour le diagnostic."""
    stats = get_stats()
    
    # Ajouter des stats supplémentaires
    from src.database.connection import get_db
    with get_db() as db:
        # Matchs par type
        cursor = db.execute("SELECT fiche_type, COUNT(*) FROM matches GROUP BY fiche_type")
        matches_by_type = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Matchs récents (derniers 7 jours au format DD/MM/YYYY)
        cursor = db.execute("""
            SELECT date, COUNT(*) 
            FROM matches 
            WHERE date IS NOT NULL 
            GROUP BY date 
            ORDER BY 
                SUBSTR(date, 7, 4) || SUBSTR(date, 4, 2) || SUBSTR(date, 1, 2) DESC 
            LIMIT 10
        """)
        recent_match_dates = [{"date": row[0], "count": row[1]} for row in cursor.fetchall()]
        
        # Joueurs avec le plus de matchs
        cursor = db.execute("""
            SELECT p.licence, p.name, p.club_code, COUNT(m.id) as match_count
            FROM players p
            LEFT JOIN matches m ON p.licence = m.player_licence
            GROUP BY p.licence
            ORDER BY match_count DESC
            LIMIT 10
        """)
        top_players_by_matches = [
            {"licence": row[0], "name": row[1], "club": row[2], "matches": row[3]}
            for row in cursor.fetchall()
        ]
        
        # Dernière mise à jour d'un joueur
        cursor = db.execute("SELECT MAX(last_update) FROM players WHERE last_update IS NOT NULL")
        last_player_update = cursor.fetchone()[0]
    
    return {
        **stats,
        "matches_by_type": matches_by_type,
        "recent_match_dates": recent_match_dates,
        "top_players_by_matches": top_players_by_matches,
        "last_player_update": last_player_update
    }


# =============================================================================
# ROUTES: Clubs
# =============================================================================

@app.get("/api/clubs", tags=["Clubs"])
async def list_clubs(
    province: Optional[str] = Query(None, description="Filtrer par province"),
    limit: Optional[int] = Query(None, ge=1, le=10000, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Offset pour pagination")
):
    """Liste tous les clubs avec filtres optionnels."""
    from src.scraper.clubs_scraper import extract_province_from_code
    
    # Si un filtre de province est demandé, charger tous les clubs pour détecter les provinces manquantes
    if province:
        # Charger tous les clubs (sans filtre) pour pouvoir détecter les provinces manquantes
        all_clubs = queries.get_all_clubs(province=None, limit=None, offset=0)
        
        # Détecter et corriger automatiquement les provinces manquantes
        filtered_clubs = []
        for club in all_clubs:
            # Détecter la province si elle est manquante
            if not club.get('province') and club.get('code'):
                detected_province = extract_province_from_code(club['code'])
                if detected_province:
                    # Mettre à jour dans la base de données
                    club['province'] = detected_province
                    queries.insert_club({
                        'code': club['code'],
                        'name': club.get('name'),
                        'province': detected_province
                    })
            
            # Filtrer par province (exacte ou détectée)
            club_province = club.get('province', '').strip()
            if club_province and (club_province == province or province.lower() in club_province.lower() or club_province.lower() in province.lower()):
                filtered_clubs.append(club)
        
        # Appliquer la pagination
        if limit:
            filtered_clubs = filtered_clubs[offset:offset+limit]
        else:
            filtered_clubs = filtered_clubs[offset:]
        
        clubs = filtered_clubs
    else:
        # Pas de filtre, charger normalement
        clubs = queries.get_all_clubs(province=None, limit=limit, offset=offset)
        
        # Détecter et corriger automatiquement les provinces manquantes
        for club in clubs:
            if not club.get('province') and club.get('code'):
                detected_province = extract_province_from_code(club['code'])
                if detected_province:
                    # Mettre à jour dans la base de données
                    club['province'] = detected_province
                    queries.insert_club({
                        'code': club['code'],
                        'name': club.get('name'),
                        'province': detected_province
                    })
    
    return {
        "count": len(clubs),
        "clubs": clubs
    }


@app.get("/api/clubs/provinces", tags=["Clubs"])
async def list_provinces():
    """Liste toutes les provinces disponibles."""
    provinces = queries.get_provinces()
    return {"provinces": provinces}


@app.get("/api/clubs/{code}", tags=["Clubs"])
async def get_club(code: str):
    """Récupère un club par son code."""
    club = queries.get_club(code.upper())
    if not club:
        raise HTTPException(status_code=404, detail=f"Club {code} non trouvé")
    return club


@app.get("/api/clubs/{code}/players", tags=["Clubs"])
async def get_club_players(code: str):
    """Récupère tous les joueurs d'un club."""
    club = queries.get_club(code.upper())
    if not club:
        raise HTTPException(status_code=404, detail=f"Club {code} non trouvé")
    
    players = queries.get_club_players(code.upper())
    return {
        "club": club,
        "count": len(players),
        "players": players
    }


@app.post("/api/clubs/{code}/scrape", tags=["Clubs"])
async def scrape_club(code: str, include_ranking: bool = True):
    """
    Scrape toutes les données d'un club (membres + fiches joueurs) et les importe directement dans la base.
    
    Args:
        code: Code du club (ex: H004)
        include_ranking: Si True, scrape aussi le classement numérique pour inclure les joueurs inactifs
    """
    from src.scraper.clubs_scraper import extract_province_from_code
    
    code = code.upper()
    
    try:
        # 1. Scraper les membres actifs du club (pour les infos du club)
        members_data = get_club_members(code)
        members_count = len(members_data.get('members', []))
        club_info = members_data.get('club_info', {})
        club_name = members_data.get('club_name', code)
        
        # Récupérer la province existante ou la détecter depuis le code
        existing_club = queries.get_club(code)
        province = None
        if existing_club and existing_club.get('province'):
            province = existing_club['province']
        else:
            province = extract_province_from_code(code)
        
        # Mettre à jour les infos du club dans la base (en préservant la province)
        if club_info:
            club_data = {
                'code': code,
                'name': club_name,
                'province': province,  # Toujours inclure la province
                **club_info
            }
            queries.insert_club(club_data)
        
        # 2. Scraper le classement numérique pour avoir TOUS les joueurs (actifs + inactifs)
        all_players = {}  # licence -> player_data
        ranking_count = 0
        
        if include_ranking:
            try:
                print(f"[INFO] Scraping ranking pour {code}...")
                ranking_data = await get_club_ranking_players_async(code)
                
                # Ajouter les joueurs messieurs
                for player in ranking_data.get('players_men', []):
                    licence = player.get('licence')
                    if licence:
                        all_players[licence] = {
                            'licence': licence,
                            'name': player.get('name'),
                            'club_code': code,
                            'ranking': player.get('ranking'),
                            'points_current': player.get('points'),
                            'category': 'SEN',  # Par défaut
                        }
                
                # Ajouter les joueuses
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
                print(f"[INFO] Ranking: {ranking_count} joueurs trouvés")
            except Exception as e:
                # Si le scraping ranking échoue, continuer avec les membres classiques
                print(f"[WARNING] Erreur ranking_scraper: {e}")
                import traceback
                traceback.print_exc()
        
        # 3. Enrichir avec les données de l'annuaire (pour les catégories)
        for member in members_data.get('members', []):
            licence = member.get('licence')
            if licence:
                if licence in all_players:
                    # Mettre à jour avec les infos de l'annuaire
                    all_players[licence]['category'] = member.get('category', 'SEN')
                else:
                    # Ajouter le membre s'il n'existe pas
                    all_players[licence] = {
                        'licence': licence,
                        'name': member.get('name'),
                        'club_code': code,
                        'ranking': member.get('ranking'),
                        'category': member.get('category'),
                    }
        
        # 4. Importer tous les joueurs dans la base
        for licence, player_data in all_players.items():
            queries.insert_player(player_data)
        
        # 5. Scraper les fiches de tous les joueurs du club
        players_scraped = 0
        players_errors = []
        
        for licence, member in all_players.items():
            if not licence:
                continue
            
            try:
                # Scraper la fiche du joueur
                player_info = get_player_info(licence)
                
                # Préparer les données du joueur
                player_data = {
                    'licence': licence,
                    'name': player_info.get('name') or member.get('name'),
                    'club_code': code,
                    'ranking': player_info.get('ranking') or member.get('ranking'),
                    'category': member.get('category'),
                    'points_start': player_info.get('points_start'),
                    'points_current': player_info.get('points_current') or member.get('points_current'),
                    'ranking_position': player_info.get('ranking_position'),
                    'total_wins': player_info.get('total_wins', 0),
                    'total_losses': player_info.get('total_losses', 0),
                    'last_update': player_info.get('last_update'),
                }
                
                # Données féminines si présentes
                women_stats = player_info.get('women_stats')
                if women_stats:
                    player_data['women_points_start'] = women_stats.get('points_start')
                    player_data['women_points_current'] = women_stats.get('points_current')
                    player_data['women_total_wins'] = women_stats.get('total_wins', 0)
                    player_data['women_total_losses'] = women_stats.get('total_losses', 0)
                
                # Insérer/mettre à jour le joueur
                queries.insert_player(player_data)
                
                # Insérer les matchs masculins
                matches_masculine = player_info.get('matches', [])
                for match in matches_masculine:
                    queries.insert_match({
                        **match,
                        'player_licence': licence,
                        'fiche_type': 'masculine'
                    })
                
                # Insérer les statistiques masculines
                stats_by_ranking = player_info.get('stats_by_ranking', [])
                for stat in stats_by_ranking:
                    queries.insert_player_stat({
                        **stat,
                        'player_licence': licence,
                        'fiche_type': 'masculine'
                    })
                
                # Insérer les matchs et stats féminins si présents
                if women_stats:
                    for match in women_stats.get('matches', []):
                        queries.insert_match({
                            **match,
                            'player_licence': licence,
                            'fiche_type': 'feminine'
                        })
                    
                    for stat in women_stats.get('stats_by_ranking', []):
                        queries.insert_player_stat({
                            **stat,
                            'player_licence': licence,
                            'fiche_type': 'feminine'
                        })
                
                players_scraped += 1
            except Exception as e:
                players_errors.append({
                    'licence': licence,
                    'name': member.get('name'),
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
        raise HTTPException(status_code=500, detail=f"Erreur lors du scraping: {str(e)}")


@app.post("/api/clubs/province/{province}/scrape", tags=["Clubs"])
async def scrape_province_clubs(province: str):
    """
    Scrape toutes les données de tous les clubs d'une province (membres + fiches joueurs) et les importe dans la base.
    D'abord, met à jour la liste des clubs depuis le site web pour corriger les provinces manquantes.
    """
    try:
        # 1. Scraper tous les clubs depuis le site web pour mettre à jour les provinces
        all_clubs_from_web = get_all_clubs()
        
        # Normaliser le nom de la province pour la comparaison
        normalized_province = province.strip()
        
        # Mapper les variations possibles du nom de la province
        province_mapping = {
            'Hainaut': 'Hainaut',
            'hainaut': 'Hainaut',
            'HAINAUT': 'Hainaut',
        }
        normalized_province = province_mapping.get(normalized_province, normalized_province)
        
        # Mettre à jour les clubs dans la base de données avec les bonnes provinces
        clubs_to_scrape = []
        for club_obj in all_clubs_from_web:
            club_dict = club_obj.to_dict() if hasattr(club_obj, 'to_dict') else {
                'code': club_obj.code,
                'name': club_obj.name,
                'province': club_obj.province
            }
            
            # Insérer/mettre à jour le club dans la base (cela corrigera les provinces manquantes)
            queries.insert_club(club_dict)
            
            # Filtrer les clubs de la province demandée
            club_province = club_dict.get('province', '').strip()
            if club_province == normalized_province:
                clubs_to_scrape.append(club_dict)
        
        if not clubs_to_scrape:
            raise HTTPException(status_code=404, detail=f"Aucun club trouvé pour la province {province}")
        
        data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        total_members = 0
        total_players = 0
        clubs_scraped = 0
        clubs_errors = []
        all_players_errors = []
        
        for i, club in enumerate(clubs_to_scrape, 1):
            code = club['code']
            name = club.get('name', code)
            
            # Skip les clubs "Individueel" ou génériques
            if 'individueel' in name.lower() or 'indiv.' in name.lower():
                continue
            
            try:
                # 1. Scraper les membres du club
                members_data = get_club_members(code)
                members_count = len(members_data.get('members', []))
                
                # Sauvegarder en JSON
                members_json_path = save_members_to_json(members_data, code, data_dir)
                
                # Importer dans la base
                import_members(members_json_path)
                total_members += members_count
                
                # 2. Scraper les fiches de tous les joueurs du club
                players_scraped = 0
                
                for member in members_data.get('members', []):
                    licence = member.get('licence')
                    if not licence:
                        continue
                    
                    try:
                        # Scraper la fiche du joueur
                        player_data = get_player_info(licence)
                        
                        # Sauvegarder en JSON
                        player_json_path = os.path.join(data_dir, f'player_{licence}.json')
                        with open(player_json_path, 'w', encoding='utf-8') as f:
                            json.dump(player_data, f, ensure_ascii=False, indent=2)
                        
                        # Importer dans la base
                        import_player(player_json_path)
                        players_scraped += 1
                        total_players += 1
                    except Exception as e:
                        all_players_errors.append({
                            'club_code': code,
                            'licence': licence,
                            'name': member.get('name'),
                            'error': str(e)
                        })
                
                clubs_scraped += 1
                
            except Exception as e:
                clubs_errors.append({
                    'club_code': code,
                    'club_name': name,
                    'error': str(e)
                })
        
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
        raise HTTPException(status_code=500, detail=f"Erreur lors du scraping: {str(e)}")


# =============================================================================
# ROUTES: Players
# =============================================================================

@app.get("/api/players", tags=["Players"])
async def list_players(
    club_code: Optional[str] = Query(None, description="Filtrer par club"),
    ranking: Optional[str] = Query(None, description="Filtrer par classement"),
    min_points: Optional[float] = Query(None, description="Points minimum"),
    max_points: Optional[float] = Query(None, description="Points maximum"),
    search: Optional[str] = Query(None, description="Recherche par nom/licence"),
    order_by: str = Query("points_current DESC", description="Ordre de tri"),
    limit: int = Query(100, ge=1, le=1000, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Offset pour pagination")
):
    """Liste les joueurs avec filtres."""
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


@app.get("/api/players/{licence}", tags=["Players"])
async def get_player(licence: str):
    """Récupère un joueur par sa licence."""
    player = queries.get_player(licence)
    if not player:
        raise HTTPException(status_code=404, detail=f"Joueur {licence} non trouvé")
    
    # Ajouter les stats et matchs
    player['stats_masculine'] = queries.get_player_stats(licence, 'masculine')
    player['stats_feminine'] = queries.get_player_stats(licence, 'feminine')
    player['matches_masculine'] = queries.get_player_matches(licence, 'masculine')
    player['matches_feminine'] = queries.get_player_matches(licence, 'feminine')
    
    return player


@app.post("/api/players/{licence}/scrape", tags=["Players"])
async def scrape_single_player(licence: str):
    """Rescrape la fiche d'un seul joueur depuis le site AFTT."""
    # Vérifier que le joueur existe en base
    existing = queries.get_player(licence)
    if not existing:
        raise HTTPException(status_code=404, detail=f"Joueur {licence} non trouvé")

    try:
        # Scraper la fiche du joueur
        player_info = get_player_info(licence)

        # Supprimer les anciens matchs et stats
        queries.delete_player_matches_and_stats(licence)

        # Mettre à jour le joueur
        player_data = {
            'licence': licence,
            'name': player_info.get('name') or existing.get('name'),
            'club_code': existing.get('club_code'),
            'ranking': player_info.get('ranking') or existing.get('ranking'),
            'category': existing.get('category'),
            'points_start': player_info.get('points_start'),
            'points_current': player_info.get('points_current') or existing.get('points_current'),
            'ranking_position': player_info.get('ranking_position'),
            'total_wins': player_info.get('total_wins', 0),
            'total_losses': player_info.get('total_losses', 0),
            'last_update': player_info.get('last_update'),
        }

        # Données féminines si présentes
        women_stats = player_info.get('women_stats')
        if women_stats:
            player_data['women_points_start'] = women_stats.get('points_start')
            player_data['women_points_current'] = women_stats.get('points_current')
            player_data['women_total_wins'] = women_stats.get('total_wins', 0)
            player_data['women_total_losses'] = women_stats.get('total_losses', 0)

        queries.insert_player(player_data)

        # Insérer les matchs masculins
        for match in player_info.get('matches', []):
            queries.insert_match({
                **match,
                'player_licence': licence,
                'fiche_type': 'masculine'
            })

        # Insérer les statistiques masculines
        for stat in player_info.get('stats_by_ranking', []):
            queries.insert_player_stat({
                **stat,
                'player_licence': licence,
                'fiche_type': 'masculine'
            })

        # Insérer les matchs et stats féminins si présents
        if women_stats:
            for match in women_stats.get('matches', []):
                queries.insert_match({
                    **match,
                    'player_licence': licence,
                    'fiche_type': 'feminine'
                })
            for stat in women_stats.get('stats_by_ranking', []):
                queries.insert_player_stat({
                    **stat,
                    'player_licence': licence,
                    'fiche_type': 'feminine'
                })

        # Retourner le joueur mis à jour
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
        raise HTTPException(status_code=500, detail=f"Erreur lors du scraping: {str(e)}")


@app.get("/api/players/{licence}/matches", tags=["Players"])
async def get_player_matches(
    licence: str,
    fiche_type: Optional[str] = Query(None, description="masculine ou feminine"),
    opponent: Optional[str] = Query(None, description="Licence de l'adversaire"),
    limit: Optional[int] = Query(None, ge=1, le=500, description="Nombre max")
):
    """Récupère les matchs d'un joueur."""
    player = queries.get_player(licence)
    if not player:
        raise HTTPException(status_code=404, detail=f"Joueur {licence} non trouvé")
    
    matches = queries.get_player_matches(
        licence=licence,
        fiche_type=fiche_type,
        opponent_licence=opponent,
        limit=limit
    )
    
    return {
        "player": {"licence": licence, "name": player['name']},
        "count": len(matches),
        "matches": matches
    }


@app.get("/api/players/{licence1}/vs/{licence2}", tags=["Players"])
async def get_head_to_head(licence1: str, licence2: str):
    """Récupère l'historique des confrontations entre deux joueurs."""
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


# =============================================================================
# ROUTES: Rankings
# =============================================================================

@app.get("/api/rankings/top", tags=["Rankings"])
async def get_top_players(
    limit: int = Query(100, ge=1, le=500, description="Nombre de joueurs"),
    province: Optional[str] = Query(None, description="Filtrer par province"),
    club_code: Optional[str] = Query(None, description="Filtrer par club"),
    ranking: Optional[str] = Query(None, description="Filtrer par classement")
):
    """Récupère le classement des meilleurs joueurs."""
    players = queries.get_top_players(
        limit=limit,
        province=province,
        club_code=club_code.upper() if club_code else None,
        ranking=ranking
    )
    return {
        "count": len(players),
        "players": players
    }


@app.get("/api/rankings/progressions", tags=["Rankings"])
async def get_top_progressions(
    limit: int = Query(100, ge=1, le=500, description="Nombre de joueurs")
):
    """Récupère les meilleures progressions de la saison."""
    players = queries.get_top_progressions(limit=limit)
    return {
        "count": len(players),
        "players": players
    }


# =============================================================================
# ROUTES: Search
# =============================================================================

@app.get("/api/search", tags=["Search"])
async def search(
    q: str = Query(..., min_length=2, description="Terme de recherche"),
    limit: int = Query(50, ge=1, le=200, description="Nombre max de résultats")
):
    """Recherche de joueurs par nom ou licence."""
    players = queries.search_players(q, limit=limit)
    return {
        "query": q,
        "count": len(players),
        "players": players
    }


# =============================================================================
# ROUTES: Scraping automatique
# =============================================================================

# Variable globale pour suivre la tâche en cours
_current_task_id = None

# Stockage des logs par task_id
_scrape_logs = {}  # {task_id: [{"timestamp": "...", "message": "..."}, ...]}

def _add_log(task_id: int, message: str):
    """Ajoute un log pour une tâche."""
    if task_id not in _scrape_logs:
        _scrape_logs[task_id] = []
    timestamp = datetime.now().strftime("%H:%M:%S")
    _scrape_logs[task_id].append({
        "timestamp": timestamp,
        "message": message
    })
    # Garder seulement les 1000 derniers logs par tâche
    if len(_scrape_logs[task_id]) > 1000:
        _scrape_logs[task_id] = _scrape_logs[task_id][-1000:]
    # Afficher aussi dans la console
    print(message)

async def run_full_scrape(task_id: int, trigger_type: str):
    """Exécute le scraping complet en arrière-plan."""
    global _current_task_id
    _current_task_id = task_id
    
    # Initialiser les logs pour cette tâche
    _scrape_logs[task_id] = []
    
    _add_log(task_id, f"[SCRAPE] Démarrage tâche #{task_id} (trigger: {trigger_type})")
    
    try:
        # 1. Récupérer tous les clubs
        all_clubs = queries.get_all_clubs()
        total_clubs = len(all_clubs)
        
        queries.update_scrape_task(task_id, total_clubs=total_clubs if total_clubs else 0)
        _add_log(task_id, f"[SCRAPE] {total_clubs} clubs à traiter")
        
        # Organiser par province
        clubs_by_province = {}
        for club in all_clubs:
            prov = club.get('province', 'Non spécifié') or 'Non spécifié'
            if prov not in clubs_by_province:
                clubs_by_province[prov] = []
            clubs_by_province[prov].append(club)
        
        completed = 0
        total_players = 0
        total_matches_scraped = 0  # Compteur de matchs scrapés
        total_fiches_scraped = 0   # Compteur de fiches individuelles scrapées
        errors = []
        
        # 2. Scraper chaque club
        for province, clubs in clubs_by_province.items():
            for club in clubs:
                code = club.get('code')
                if not code:
                    continue
                
                queries.update_scrape_task(
                    task_id,
                    completed_clubs=completed,
                    total_players=total_players,
                    current_club=code,
                    current_province=province
                )
                
                try:
                    from src.scraper.clubs_scraper import extract_province_from_code
                    
                    # 1. Scraper les membres actifs du club (pour les infos du club)
                    members_data = get_club_members(code)
                    members_list = members_data.get('members', [])
                    club_info = members_data.get('club_info', {})
                    club_name = members_data.get('club_name', code)
                    
                    # Récupérer la province existante ou la détecter depuis le code
                    existing_club = queries.get_club(code)
                    province = None
                    if existing_club and existing_club.get('province'):
                        province = existing_club['province']
                    else:
                        province = extract_province_from_code(code)
                    
                    # Mettre à jour les infos du club dans la base (en préservant la province)
                    if club_info:
                        club_data = {
                            'code': code,
                            'name': club_name,
                            'province': province,  # Toujours inclure la province
                            **club_info
                        }
                        queries.insert_club(club_data)
                        _add_log(task_id, f"[DB] ✅ Club {code} ({club_name}) sauvegardé")
                    
                    # 2. Scraper le classement numérique pour avoir TOUS les joueurs (actifs + inactifs)
                    all_players = {}  # licence -> player_data
                    
                    try:
                        ranking_data = await get_club_ranking_players_async(code)
                        
                        # Ajouter les joueurs messieurs
                        for player in ranking_data.get('players_men', []):
                            licence = player.get('licence')
                            if licence:
                                all_players[licence] = {
                                    'licence': licence,
                                    'name': player.get('name'),
                                    'club_code': code,
                                    'ranking': player.get('ranking'),
                                    'points_current': player.get('points'),
                                    'category': 'SEN',  # Par défaut
                                }
                        
                        # Ajouter les joueuses
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
                    except Exception as e:
                        # Si le scraping ranking échoue, continuer avec les membres classiques
                        _add_log(task_id, f"[WARNING] Erreur ranking_scraper pour {code}: {e}")
                    
                    # 3. Enrichir avec les données de l'annuaire (pour les catégories)
                    for member in members_list:
                        licence = member.get('licence')
                        if licence:
                            if licence in all_players:
                                # Mettre à jour avec les infos de l'annuaire
                                all_players[licence]['category'] = member.get('category', 'SEN')
                            else:
                                # Ajouter le membre s'il n'existe pas
                                all_players[licence] = {
                                    'licence': licence,
                                    'name': member.get('name'),
                                    'club_code': code,
                                    'ranking': member.get('ranking'),
                                    'category': member.get('category', 'SEN'),
                                }
                    
                    # 4. Importer tous les joueurs dans la base
                    players_inserted = 0
                    for licence, player_data in all_players.items():
                        queries.insert_player(player_data)
                        players_inserted += 1
                        if players_inserted % 10 == 0:  # Log tous les 10 joueurs pour ne pas surcharger
                            _add_log(task_id, f"[DB] 📝 {players_inserted}/{len(all_players)} joueurs de base sauvegardés")
                    
                    if players_inserted > 0:
                        _add_log(task_id, f"[DB] ✅ {players_inserted} joueurs de base sauvegardés pour {code}")
                    
                    total_players += len(all_players)
                    
                    # 5. Scraper les fiches de tous les joueurs du club (comme dans scrape_club)
                    players_scraped = 0
                    players_errors = []
                    
                    for licence, player_data in all_players.items():
                        if not licence:
                            continue
                        
                        try:
                            # Scraper la fiche du joueur
                            player_info = get_player_info(licence)
                            
                            # Préparer les données du joueur (comme dans scrape_club)
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
                            
                            # Données féminines si présentes
                            women_stats = player_info.get('women_stats')
                            if women_stats:
                                updated_data['women_points_start'] = women_stats.get('points_start')
                                updated_data['women_points_current'] = women_stats.get('points_current')
                                updated_data['women_total_wins'] = women_stats.get('total_wins', 0)
                                updated_data['women_total_losses'] = women_stats.get('total_losses', 0)
                            
                            # Insérer/mettre à jour le joueur
                            queries.insert_player(updated_data)
                            
                            # Insérer les matchs masculins
                            matches_masculine = player_info.get('matches', [])
                            matches_m_count = 0
                            for match in matches_masculine:
                                queries.insert_match({
                                    **match,
                                    'player_licence': licence,
                                    'fiche_type': 'masculine'
                                })
                                matches_m_count += 1
                            
                            # Insérer les statistiques masculines
                            stats_by_ranking = player_info.get('stats_by_ranking', [])
                            stats_m_count = 0
                            for stat in stats_by_ranking:
                                queries.insert_player_stat({
                                    **stat,
                                    'player_licence': licence,
                                    'fiche_type': 'masculine'
                                })
                                stats_m_count += 1
                            
                            # Insérer les matchs et stats féminins si présents
                            matches_f_count = 0
                            stats_f_count = 0
                            if women_stats:
                                for match in women_stats.get('matches', []):
                                    queries.insert_match({
                                        **match,
                                        'player_licence': licence,
                                        'fiche_type': 'feminine'
                                    })
                                    matches_f_count += 1
                                
                                for stat in women_stats.get('stats_by_ranking', []):
                                    queries.insert_player_stat({
                                        **stat,
                                        'player_licence': licence,
                                        'fiche_type': 'feminine'
                                    })
                                    stats_f_count += 1
                            
                            # Compter les matchs scrapés pour ce joueur
                            player_matches_count = matches_m_count + matches_f_count
                            total_matches_scraped += player_matches_count
                            total_fiches_scraped += 1
                            
                            # Log détaillé avec les données récupérées
                            player_name = updated_data.get('name', 'N/A')[:25]
                            player_ranking = updated_data.get('ranking', '?')
                            player_pts = updated_data.get('points_current', 0) or 0
                            player_wins = updated_data.get('total_wins', 0)
                            player_losses = updated_data.get('total_losses', 0)
                            
                            # Log principal du joueur
                            _add_log(task_id, f"[JOUEUR] 👤 {licence} - {player_name} ({player_ranking}) | {player_pts:.0f}pts | {player_wins}V-{player_losses}D | {matches_m_count} matchs")
                            
                            # Afficher les 3 derniers matchs s'il y en a
                            if matches_masculine and len(matches_masculine) > 0:
                                recent_matches = matches_masculine[:3]
                                for m in recent_matches:
                                    m_date = m.get('date', '?')
                                    m_opponent = m.get('opponent_name', '?')[:20]
                                    m_score = m.get('score', '?')
                                    m_result = '✅' if m.get('won') else '❌'
                                    m_pts = m.get('points_change', 0) or 0
                                    pts_str = f"+{m_pts:.1f}" if m_pts >= 0 else f"{m_pts:.1f}"
                                    _add_log(task_id, f"  └─ {m_result} {m_date} vs {m_opponent} {m_score} ({pts_str}pts)")
                            
                            players_scraped += 1
                            
                            # Log tous les 5 joueurs pour le résumé
                            if players_scraped % 5 == 0:
                                _add_log(task_id, f"[DB] 📊 {players_scraped}/{len(all_players)} fiches scrapées pour {code} (total matchs: {total_matches_scraped})")
                            
                            # Petit délai entre chaque joueur pour ne pas surcharger le serveur AFTT
                            await asyncio.sleep(0.3)
                            
                        except Exception as e:
                            # Erreur sur une fiche individuelle, continuer
                            error_msg = f"Erreur fiche joueur {licence}: {str(e)[:100]}"
                            players_errors.append(error_msg)
                            _add_log(task_id, f"[WARNING] {error_msg}")
                            # Pause plus longue après une erreur
                            await asyncio.sleep(2.0)
                    
                    # Résumé final pour le club
                    club_matches = sum(1 for l, p in all_players.items() if l)  # Pour le décompte
                    summary_parts = [f"[SCRAPE] ✅ {code}"]
                    summary_parts.append(f"{len(all_players)} joueurs")
                    summary_parts.append(f"{players_scraped} fiches")
                    summary_parts.append(f"Total matchs global: {total_matches_scraped}")
                    if players_errors:
                        summary_parts.append(f"{len(players_errors)} erreurs fiches")
                    _add_log(task_id, " | ".join(summary_parts))
                    
                except Exception as e:
                    error_msg = f"{code}: {str(e)}"
                    errors.append(error_msg)
                    _add_log(task_id, f"[SCRAPE] ❌ {code}: {e}")
                
                completed += 1
                
                # Pause entre les clubs pour ne pas surcharger le serveur AFTT
                await asyncio.sleep(1.0)
        
        # 3. Terminer la tâche
        queries.update_scrape_task(
            task_id,
            completed_clubs=completed,
            total_players=total_players,
            status='success',
            errors_count=len(errors),
            errors_detail=json_lib.dumps(errors) if errors else None,
            current_club=None,
            current_province=None
        )
        
        _add_log(task_id, f"[SCRAPE] ✅ Tâche #{task_id} terminée: {completed} clubs, {total_players} joueurs, {total_fiches_scraped} fiches, {total_matches_scraped} matchs, {len(errors)} erreurs clubs")
        
    except Exception as e:
        _add_log(task_id, f"[SCRAPE] ❌ Tâche #{task_id} échouée: {e}")
        queries.update_scrape_task(
            task_id,
            status='failed',
            errors_detail=json_lib.dumps([str(e)])
        )
    finally:
        _current_task_id = None
        # Nettoyer les logs après 1 heure (garder pour consultation)
        # Les logs seront supprimés automatiquement après un certain temps si nécessaire


@app.post("/api/scrape/all", tags=["Scraping"])
async def start_full_scrape(
    trigger: str = Query("manual", description="Type de déclencheur (manual, cron)")
):
    """
    Lance un scraping complet de tous les clubs et joueurs.
    Le scraping s'exécute en arrière-plan et retourne immédiatement.
    """
    # Vérifier si une tâche est déjà en cours
    current = queries.get_current_scrape_task()
    if current:
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Scraping already in progress",
                "task_id": current['id'],
                "started_at": current['started_at'],
                "progress": f"{current['completed_clubs']}/{current['total_clubs']} clubs"
            }
        )
    
    # Compter les clubs
    all_clubs = queries.get_all_clubs()
    total_clubs = len(all_clubs)
    
    # Créer la tâche
    task_id = queries.create_scrape_task(trigger_type=trigger, total_clubs=total_clubs)
    
    # Lancer en arrière-plan avec asyncio.create_task (coroutine async)
    asyncio.create_task(run_full_scrape(task_id, trigger))
    
    return {
        "status": "started",
        "task_id": task_id,
        "total_clubs": total_clubs,
        "message": f"Scraping de {total_clubs} clubs démarré en arrière-plan"
    }


@app.get("/api/scrape/status", tags=["Scraping"])
async def get_scrape_status():
    """
    Récupère le statut de la tâche de scraping en cours.
    """
    current = queries.get_current_scrape_task()
    
    if not current:
        return {
            "running": False,
            "message": "Aucun scraping en cours"
        }
    
    elapsed = None
    if current['started_at']:
        try:
            start = datetime.fromisoformat(current['started_at'].replace('Z', '+00:00'))
            elapsed = (datetime.now() - start.replace(tzinfo=None)).total_seconds()
        except:
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


@app.get("/api/scrape/logs/{task_id}", tags=["Scraping"])
async def get_scrape_logs(task_id: int):
    """
    Récupère les logs d'une tâche de scraping.
    """
    if task_id not in _scrape_logs:
        return {
            "task_id": task_id,
            "logs": []
        }
    
    return {
        "task_id": task_id,
        "logs": _scrape_logs[task_id]
    }


@app.get("/api/scrape/history", tags=["Scraping"])
async def get_scrape_history(
    limit: int = Query(20, ge=1, le=100, description="Nombre de tâches à récupérer")
):
    """
    Récupère l'historique des tâches de scraping.
    """
    tasks = queries.get_scrape_task_history(limit=limit)
    
    # Calculer la durée pour chaque tâche terminée
    for task in tasks:
        if task['started_at'] and task['finished_at']:
            try:
                start = datetime.fromisoformat(task['started_at'].replace('Z', '+00:00'))
                end = datetime.fromisoformat(task['finished_at'].replace('Z', '+00:00'))
                task['duration_seconds'] = (end - start).total_seconds()
            except:
                task['duration_seconds'] = None
        else:
            task['duration_seconds'] = None
    
    return {
        "count": len(tasks),
        "tasks": tasks
    }


@app.get("/api/scrape/task/{task_id}", tags=["Scraping"])
async def get_scrape_task_detail(task_id: int):
    """
    Récupère les détails d'une tâche de scraping par son ID.
    """
    task = queries.get_scrape_task_by_id(task_id)
    
    if not task:
        raise HTTPException(status_code=404, detail="Tâche non trouvée")
    
    # Parser les erreurs si présentes
    if task.get('errors_detail'):
        try:
            task['errors_list'] = json_lib.loads(task['errors_detail'])
        except:
            task['errors_list'] = []
    else:
        task['errors_list'] = []
    
    return task


@app.post("/api/scrape/cancel", tags=["Scraping"])
async def cancel_scrape():
    """
    Annule la tâche de scraping en cours.
    """
    current = queries.get_current_scrape_task()
    
    if not current:
        raise HTTPException(status_code=404, detail="Aucun scraping en cours")
    
    queries.update_scrape_task(current['id'], status='cancelled')
    
    return {
        "status": "cancelled",
        "task_id": current['id'],
        "message": "Scraping annulé"
    }


@app.post("/api/scrape/refresh-clubs", tags=["Scraping"])
async def refresh_clubs_names():
    """
    Rafraîchit les noms des clubs depuis l'AFTT.
    Utile pour corriger les clubs avec un nom manquant (N/A).
    """
    try:
        # Récupérer tous les clubs depuis l'AFTT
        all_clubs_from_web = get_all_clubs()
        
        updated_count = 0
        for club_obj in all_clubs_from_web:
            club_dict = club_obj.to_dict() if hasattr(club_obj, 'to_dict') else {
                'code': club_obj.code,
                'name': club_obj.name,
                'province': club_obj.province
            }
            
            # Insérer/mettre à jour le club dans la base
            if club_dict.get('name'):
                queries.insert_club(club_dict)
                updated_count += 1
        
        return {
            "status": "success",
            "message": f"{updated_count} clubs mis à jour",
            "total_clubs": len(all_clubs_from_web)
        }
    except Exception as e:
        logger.error(f"Erreur lors du rafraîchissement des clubs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# ROUTES: Tournaments
# =============================================================================

@app.get("/api/tournaments", tags=["Tournaments"])
async def list_tournaments(
    level: Optional[str] = Query(None, description="Filtrer par niveau"),
    date_from: Optional[str] = Query(None, description="Date de début (DD/MM/YYYY)"),
    date_to: Optional[str] = Query(None, description="Date de fin (DD/MM/YYYY)"),
    search: Optional[str] = Query(None, description="Recherche par nom ou référence"),
    limit: Optional[int] = Query(None, ge=1, le=1000, description="Nombre max de résultats"),
    offset: int = Query(0, ge=0, description="Offset pour pagination")
):
    """Liste tous les tournois avec filtres optionnels."""
    tournaments = queries.get_all_tournaments(
        level=level,
        date_from=date_from,
        date_to=date_to,
        search=search,
        limit=limit,
        offset=offset
    )
    return {
        "count": len(tournaments),
        "tournaments": tournaments
    }


@app.get("/api/tournaments/levels", tags=["Tournaments"])
async def list_tournament_levels():
    """Liste tous les niveaux de tournois disponibles."""
    levels = queries.get_tournament_levels()
    return {"levels": levels}


@app.get("/api/tournaments/{t_id}", tags=["Tournaments"])
async def get_tournament(t_id: int):
    """Récupère un tournoi par son ID."""
    tournament = queries.get_tournament(t_id)
    if not tournament:
        raise HTTPException(status_code=404, detail=f"Tournoi {t_id} non trouvé")
    return tournament


@app.get("/api/tournaments/{t_id}/series", tags=["Tournaments"])
async def get_tournament_series(t_id: int):
    """Récupère les séries d'un tournoi."""
    tournament = queries.get_tournament(t_id)
    if not tournament:
        raise HTTPException(status_code=404, detail=f"Tournoi {t_id} non trouvé")
    
    series = queries.get_tournament_series(t_id)
    return {
        "tournament": tournament,
        "count": len(series),
        "series": series
    }


@app.get("/api/tournaments/{t_id}/inscriptions", tags=["Tournaments"])
async def get_tournament_inscriptions(
    t_id: int,
    series_name: Optional[str] = Query(None, description="Filtrer par série")
):
    """Récupère les inscriptions d'un tournoi."""
    tournament = queries.get_tournament(t_id)
    if not tournament:
        raise HTTPException(status_code=404, detail=f"Tournoi {t_id} non trouvé")
    
    inscriptions = queries.get_tournament_inscriptions(t_id, series_name)
    return {
        "tournament": tournament,
        "count": len(inscriptions),
        "inscriptions": inscriptions
    }


@app.get("/api/tournaments/{t_id}/results", tags=["Tournaments"])
async def get_tournament_results(
    t_id: int,
    series_name: Optional[str] = Query(None, description="Filtrer par série")
):
    """Récupère les résultats d'un tournoi."""
    tournament = queries.get_tournament(t_id)
    if not tournament:
        raise HTTPException(status_code=404, detail=f"Tournoi {t_id} non trouvé")
    
    results = queries.get_tournament_results(t_id, series_name)
    return {
        "tournament": tournament,
        "count": len(results),
        "results": results
    }


# =============================================================================
# ROUTES: Tournament Scraping
# =============================================================================

# Variable globale pour suivre la tâche de scraping de tournois en cours
_current_tournament_scrape = None
_tournament_scrape_logs = {}


async def run_tournament_scrape(task_id: str):
    """Exécute le scraping des tournois en arrière-plan."""
    global _current_tournament_scrape
    
    from src.scraper.tournament_scraper import (
        get_all_tournaments, get_tournament_series, 
        get_tournament_inscriptions, get_tournament_results
    )
    import time
    
    _tournament_scrape_logs[task_id] = []
    
    def add_log(msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        _tournament_scrape_logs[task_id].append({
            "timestamp": timestamp,
            "message": msg
        })
        print(msg)
        # Garder seulement les 1000 derniers logs
        if len(_tournament_scrape_logs[task_id]) > 1000:
            _tournament_scrape_logs[task_id] = _tournament_scrape_logs[task_id][-1000:]
    
    _current_tournament_scrape = {
        'task_id': task_id,
        'status': 'running',
        'started_at': datetime.now().isoformat(),
        'total_tournaments': 0,
        'completed_tournaments': 0,
        'total_series': 0,
        'total_inscriptions': 0,
        'total_results': 0,
        'current_tournament': None,
        'errors': []
    }
    
    try:
        add_log("[TOURNAMENTS] Récupération de la liste des tournois...")
        
        # Récupérer tous les tournois
        tournaments = get_all_tournaments()
        _current_tournament_scrape['total_tournaments'] = len(tournaments)
        
        add_log(f"[TOURNAMENTS] {len(tournaments)} tournois trouvés")
        
        # Sauvegarder les tournois dans la base
        for tournament in tournaments:
            queries.insert_tournament(tournament.to_dict())
        
        add_log(f"[TOURNAMENTS] Tournois sauvegardés dans la base")
        
        # Scraper les détails de chaque tournoi
        for i, tournament in enumerate(tournaments, 1):
            _current_tournament_scrape['current_tournament'] = tournament.name
            _current_tournament_scrape['completed_tournaments'] = i - 1
            
            add_log(f"[TOURNAMENTS] {i}/{len(tournaments)} - {tournament.name}...")
            
            try:
                # Séries
                series = get_tournament_series(tournament.t_id)
                for s in series:
                    queries.insert_tournament_series(s.to_dict())
                _current_tournament_scrape['total_series'] += len(series)
                
                await asyncio.sleep(0.2)
                
                # Inscriptions
                inscriptions = get_tournament_inscriptions(tournament.t_id)
                for insc in inscriptions:
                    queries.insert_tournament_inscription(insc.to_dict())
                _current_tournament_scrape['total_inscriptions'] += len(inscriptions)
                
                await asyncio.sleep(0.2)
                
                # Résultats
                results = get_tournament_results(tournament.t_id)
                for res in results:
                    queries.insert_tournament_result(res.to_dict())
                _current_tournament_scrape['total_results'] += len(results)
                
                add_log(f"[TOURNAMENTS]   -> {len(series)} séries, {len(inscriptions)} inscriptions, {len(results)} résultats")
                
            except Exception as e:
                error_msg = f"Erreur pour {tournament.name}: {str(e)}"
                _current_tournament_scrape['errors'].append(error_msg)
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
    
    finally:
        # Ne pas réinitialiser immédiatement pour permettre de consulter le statut
        pass


@app.post("/api/scrape/tournaments", tags=["Tournament Scraping"])
async def start_tournament_scrape():
    """
    Lance un scraping complet de tous les tournois.
    Le scraping s'exécute en arrière-plan et retourne immédiatement.
    """
    global _current_tournament_scrape
    
    # Vérifier si une tâche est déjà en cours
    if _current_tournament_scrape and _current_tournament_scrape.get('status') == 'running':
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Tournament scraping already in progress",
                "task_id": _current_tournament_scrape['task_id'],
                "started_at": _current_tournament_scrape['started_at'],
                "progress": f"{_current_tournament_scrape['completed_tournaments']}/{_current_tournament_scrape['total_tournaments']} tournois"
            }
        )
    
    # Créer un ID de tâche unique
    task_id = f"tournaments_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Lancer en arrière-plan
    asyncio.create_task(run_tournament_scrape(task_id))
    
    return {
        "status": "started",
        "task_id": task_id,
        "message": "Scraping des tournois démarré en arrière-plan"
    }


@app.get("/api/scrape/tournaments/status", tags=["Tournament Scraping"])
async def get_tournament_scrape_status():
    """
    Récupère le statut du scraping des tournois en cours.
    """
    global _current_tournament_scrape
    
    if not _current_tournament_scrape:
        return {
            "running": False,
            "message": "Aucun scraping de tournois en cours ou récent"
        }
    
    elapsed = None
    if _current_tournament_scrape.get('started_at'):
        try:
            start = datetime.fromisoformat(_current_tournament_scrape['started_at'])
            elapsed = (datetime.now() - start).total_seconds()
        except:
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


@app.get("/api/scrape/tournaments/logs/{task_id}", tags=["Tournament Scraping"])
async def get_tournament_scrape_logs(task_id: str):
    """
    Récupère les logs d'une tâche de scraping de tournois.
    """
    if task_id not in _tournament_scrape_logs:
        return {
            "task_id": task_id,
            "logs": []
        }
    
    return {
        "task_id": task_id,
        "logs": _tournament_scrape_logs[task_id]
    }


@app.post("/api/tournaments/{t_id}/scrape", tags=["Tournament Scraping"])
async def scrape_single_tournament(t_id: int):
    """
    Scrape les détails d'un seul tournoi (séries, inscriptions, résultats).
    """
    from src.scraper.tournament_scraper import (
        get_tournament_series, get_tournament_inscriptions, 
        get_tournament_results, get_tournaments_page
    )
    
    try:
        # Vérifier si le tournoi existe dans la base
        tournament = queries.get_tournament(t_id)
        
        if not tournament:
            # Essayer de le scraper depuis la liste
            # Pour l'instant, retourner une erreur
            raise HTTPException(status_code=404, detail=f"Tournoi {t_id} non trouvé. Lancez d'abord /api/scrape/tournaments")
        
        # Supprimer les anciennes données
        queries.delete_tournament_data(t_id)
        
        # Scraper les nouvelles données
        series = get_tournament_series(t_id)
        for s in series:
            queries.insert_tournament_series(s.to_dict())
        
        inscriptions = get_tournament_inscriptions(t_id)
        for insc in inscriptions:
            queries.insert_tournament_inscription(insc.to_dict())
        
        results = get_tournament_results(t_id)
        for res in results:
            queries.insert_tournament_result(res.to_dict())
        
        return {
            "success": True,
            "tournament_id": t_id,
            "tournament_name": tournament['name'],
            "series_count": len(series),
            "inscriptions_count": len(inscriptions),
            "results_count": len(results),
            "message": f"Tournoi {tournament['name']} scrapé avec succès"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erreur lors du scraping: {str(e)}")


# =============================================================================
# ROUTES: Interclubs Rankings
# =============================================================================

@app.get("/api/interclubs/divisions", tags=["Interclubs"])
async def list_interclubs_divisions(
    category: Optional[str] = Query(None, description="Filtrer par categorie (ex: National, Prov. Hainaut)"),
    gender: Optional[str] = Query(None, description="Filtrer par genre (Hommes, Dames)")
):
    """Liste les divisions interclubs avec filtres optionnels."""
    divisions = queries.get_interclubs_divisions(category=category, gender=gender)
    return {
        "count": len(divisions),
        "divisions": divisions
    }


@app.get("/api/interclubs/rankings", tags=["Interclubs"])
async def get_interclubs_ranking(
    division_index: int = Query(..., description="Index de la division"),
    week: int = Query(..., ge=1, le=22, description="Numero de semaine (1-22)")
):
    """Récupère le classement d'une division pour une semaine donnée."""
    rankings = queries.get_interclubs_ranking(division_index, week)
    return {
        "division_index": division_index,
        "week": week,
        "count": len(rankings),
        "rankings": rankings
    }


@app.get("/api/interclubs/team/{team_name}/history", tags=["Interclubs"])
async def get_interclubs_team_history(
    team_name: str,
    division_index: Optional[int] = Query(None, description="Filtrer par division")
):
    """Récupère l'historique de classement d'une équipe semaine par semaine."""
    history = queries.get_interclubs_team_history(team_name, division_index=division_index)
    if not history:
        raise HTTPException(status_code=404, detail=f"Equipe '{team_name}' non trouvee")
    return {
        "team_name": team_name,
        "count": len(history),
        "history": history
    }


@app.get("/api/interclubs/search", tags=["Interclubs"])
async def search_interclubs_teams(
    q: str = Query(..., min_length=2, description="Terme de recherche"),
    limit: int = Query(50, ge=1, le=200, description="Nombre max de resultats")
):
    """Recherche d'équipes interclubs par nom."""
    teams = queries.search_interclubs_teams(q, limit=limit)
    return {
        "query": q,
        "count": len(teams),
        "teams": teams
    }


@app.get("/api/interclubs/stats", tags=["Interclubs"])
async def get_interclubs_stats():
    """Récupère des statistiques sur les données interclubs."""
    return queries.get_interclubs_stats()


# =============================================================================
# ROUTES: Interclubs Scraping
# =============================================================================

_current_interclubs_scrape = None
_interclubs_scrape_logs = {}


async def run_interclubs_scrape(task_id: str, weeks: Optional[List[int]], division_indices: Optional[List[int]], resume_from: Optional[dict]):
    """Exécute le scraping interclubs en arrière-plan."""
    global _current_interclubs_scrape

    from src.scraper.interclubs_scraper import scrape_all_interclubs_rankings_async

    _interclubs_scrape_logs[task_id] = []

    def add_log(msg):
        timestamp = datetime.now().strftime("%H:%M:%S")
        _interclubs_scrape_logs[task_id].append({
            "timestamp": timestamp,
            "message": msg
        })
        print(msg)
        if len(_interclubs_scrape_logs[task_id]) > 2000:
            _interclubs_scrape_logs[task_id] = _interclubs_scrape_logs[task_id][-2000:]

    _current_interclubs_scrape = {
        'task_id': task_id,
        'status': 'running',
        'started_at': datetime.now().isoformat(),
        'total_rankings': 0,
        'errors_count': 0,
        'last_success': None,
    }

    try:
        add_log(f"[INTERCLUBS] Demarrage tache {task_id}")

        stats = await scrape_all_interclubs_rankings_async(
            callback=add_log,
            weeks=weeks,
            division_indices=division_indices,
            resume_from=resume_from,
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


@app.post("/api/scrape/interclubs", tags=["Interclubs Scraping"])
async def start_interclubs_scrape(
    weeks: Optional[str] = Query(None, description="Semaines a scraper (ex: 1,2,3 ou 1-5). Defaut: 1-22"),
    divisions: Optional[str] = Query(None, description="Indices de divisions (ex: 1,5,10). Defaut: toutes"),
    resume_division: Optional[int] = Query(None, description="Reprendre depuis cette division"),
    resume_week: Optional[int] = Query(None, description="Reprendre depuis cette semaine"),
):
    """
    Lance le scraping des classements interclubs.
    Le scraping s'execute en arriere-plan et retourne immediatement.
    """
    global _current_interclubs_scrape

    if _current_interclubs_scrape and _current_interclubs_scrape.get('status') == 'running':
        raise HTTPException(
            status_code=409,
            detail={
                "error": "Interclubs scraping already in progress",
                "task_id": _current_interclubs_scrape['task_id'],
            }
        )

    # Parser les semaines
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

    # Parser les divisions
    div_list = None
    if divisions:
        div_list = [int(d.strip()) for d in divisions.split(',')]

    # Resume
    resume_from = None
    if resume_division is not None and resume_week is not None:
        resume_from = {'division_index': resume_division, 'week': resume_week}

    task_id = f"interclubs_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    asyncio.create_task(run_interclubs_scrape(task_id, week_list, div_list, resume_from))

    return {
        "status": "started",
        "task_id": task_id,
        "weeks": week_list or list(range(1, 23)),
        "divisions": div_list or "all",
        "message": "Scraping interclubs demarre en arriere-plan"
    }


@app.get("/api/scrape/interclubs/status", tags=["Interclubs Scraping"])
async def get_interclubs_scrape_status():
    """Récupère le statut du scraping interclubs en cours."""
    global _current_interclubs_scrape

    if not _current_interclubs_scrape:
        return {
            "running": False,
            "message": "Aucun scraping interclubs en cours ou recent"
        }

    elapsed = None
    if _current_interclubs_scrape.get('started_at'):
        try:
            start = datetime.fromisoformat(_current_interclubs_scrape['started_at'])
            elapsed = (datetime.now() - start).total_seconds()
        except:
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


@app.get("/api/scrape/interclubs/logs/{task_id}", tags=["Interclubs Scraping"])
async def get_interclubs_scrape_logs(task_id: str):
    """Récupère les logs d'une tache de scraping interclubs."""
    if task_id not in _interclubs_scrape_logs:
        return {
            "task_id": task_id,
            "logs": []
        }
    return {
        "task_id": task_id,
        "logs": _interclubs_scrape_logs[task_id]
    }


@app.post("/api/scrape/interclubs/cancel", tags=["Interclubs Scraping"])
async def cancel_interclubs_scrape():
    """Annule le scraping interclubs en cours."""
    global _current_interclubs_scrape

    if not _current_interclubs_scrape or _current_interclubs_scrape.get('status') != 'running':
        raise HTTPException(status_code=404, detail="Aucun scraping interclubs en cours")

    _current_interclubs_scrape['status'] = 'cancelled'
    _current_interclubs_scrape['finished_at'] = datetime.now().isoformat()

    return {
        "status": "cancelled",
        "task_id": _current_interclubs_scrape['task_id'],
        "message": "Scraping interclubs annule"
    }


# =============================================================================
# Point d'entrée
# =============================================================================

def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Lance le serveur API."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()

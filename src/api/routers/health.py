"""
Routes: Health, API info, Stats
"""
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
import os

from src.database.connection import get_stats, get_db
from src.database import queries
from src.api.cache import cache

router = APIRouter()

WEB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'web')


@router.get("/", tags=["Health"], include_in_schema=False)
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


@router.get("/api-docs.html", include_in_schema=False)
async def api_docs_page():
    """Sert la page de documentation API."""
    docs_path = os.path.join(WEB_DIR, 'api-docs.html')
    if os.path.exists(docs_path):
        return FileResponse(docs_path, media_type='text/html')
    raise HTTPException(status_code=404, detail="Documentation not found")


@router.get("/api", tags=["Health"])
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


@router.get("/health", tags=["Health"])
async def health():
    """Vérification de l'état de l'API."""
    return {"status": "ok"}


@router.get("/api/stats", tags=["Stats"])
async def get_database_stats():
    """Statistiques generales : nombre de clubs, joueurs, matchs en base."""
    cached = cache.get("stats")
    if cached is not None:
        return cached
    result = get_stats()
    cache.set("stats", result, ttl=60)
    return result


@router.get("/api/stats/last-scrape-date", tags=["Stats"])
async def get_last_scrape_date():
    """Retourne la date du dernier scrap réussi."""
    last_date = queries.get_last_scrape_date()
    if not last_date:
        return {
            "last_scrape_date": None,
            "message": "Aucun scraping n'a encore été effectué"
        }
    return {
        "last_scrape_date": last_date
    }


@router.get("/api/stats/clubs-count", tags=["Stats"])
async def get_clubs_count():
    """Retourne le nombre de clubs."""
    count = queries.get_clubs_count()
    return {"clubs_count": count}


@router.get("/api/stats/active-players-count", tags=["Stats"])
async def get_active_players_count():
    """Retourne le nombre de joueurs actifs."""
    count = queries.get_active_players_count()
    return {"active_players_count": count}


@router.get("/api/stats/detailed", tags=["Stats"])
async def get_detailed_stats():
    """Diagnostics detailles : stats par type de match, dates recentes, top joueurs par nombre de matchs."""
    cached = cache.get("stats_detailed")
    if cached is not None:
        return cached
    stats = get_stats()

    with get_db() as db:
        cursor = db.execute("SELECT fiche_type, COUNT(*) FROM matches GROUP BY fiche_type")
        matches_by_type = {row[0]: row[1] for row in cursor.fetchall()}

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

        cursor = db.execute("SELECT MAX(last_update) FROM players WHERE last_update IS NOT NULL")
        last_player_update = cursor.fetchone()[0]

    result = {
        **stats,
        "matches_by_type": matches_by_type,
        "recent_match_dates": recent_match_dates,
        "top_players_by_matches": top_players_by_matches,
        "last_player_update": last_player_update
    }
    cache.set("stats_detailed", result, ttl=120)
    return result

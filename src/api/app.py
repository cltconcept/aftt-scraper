"""
API FastAPI pour les données AFFT
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import sys
import os
import logging

# Ajouter le chemin parent pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from src.config import CORS_ORIGINS, HOST, PORT
from src.logging_config import setup_logging
from src.database.connection import init_database, get_stats
from src.database import queries

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gestion du cycle de vie de l'application."""
    # Startup
    init_database()
    _init_clubs_if_empty()
    logger.info("[INIT] Application démarrée")
    yield
    # Shutdown
    logger.info("[INIT] Application arrêtée")


def _init_clubs_if_empty():
    """Charge la liste des clubs depuis le site AFTT si la base est vide."""
    try:
        stats = get_stats()
        if stats.get('clubs', 0) == 0:
            logger.info("[INIT] Base de données vide, chargement des clubs depuis AFTT...")
            from src.scraper.clubs_scraper import get_all_clubs
            clubs = get_all_clubs()
            for club in clubs:
                club_dict = {
                    'code': club.code,
                    'name': club.name,
                    'province': club.province
                }
                queries.insert_club(club_dict)
            logger.info(f"[INIT] {len(clubs)} clubs chargés")
    except Exception as e:
        logger.error(f"[INIT] Erreur lors du chargement initial des clubs: {e}")


# Créer l'application FastAPI avec lifespan
app = FastAPI(
    title="AFTT Data API",
    description=(
        "API REST pour les donnees du tennis de table belge (AFTT).\n\n"
        "Fournit l'acces aux clubs, joueurs, classements, matchs, tournois et interclubs.\n"
        "Les donnees sont collectees par scraping du site AFTT et stockees dans une base SQLite.\n\n"
        "**Fonctionnalites principales :**\n"
        "- Consultation des clubs et de leurs joueurs\n"
        "- Fiches joueurs avec matchs, stats par classement, fiche masculine et feminine\n"
        "- Classements et progressions\n"
        "- Tournois (series, inscriptions, resultats)\n"
        "- Interclubs (divisions et classements par semaine)\n"
        "- Scraping a la demande (club individuel, global, tournois, interclubs)\n"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configuration CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inclure les routers
from src.api.routers.health import router as health_router
from src.api.routers.clubs import router as clubs_router
from src.api.routers.players import router as players_router
from src.api.routers.scraping import router as scraping_router
from src.api.routers.tournaments import router as tournaments_router
from src.api.routers.interclubs import router as interclubs_router

app.include_router(health_router)
app.include_router(clubs_router)
app.include_router(players_router)
app.include_router(scraping_router)
app.include_router(tournaments_router)
app.include_router(interclubs_router)


# =============================================================================
# Point d'entrée
# =============================================================================

def run_server(host: str = None, port: int = None):
    """Lance le serveur API."""
    import uvicorn
    uvicorn.run(app, host=host or HOST, port=port or PORT)


if __name__ == "__main__":
    run_server()

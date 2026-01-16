"""
Gestion de la connexion à la base de données SQLite
"""
import sqlite3
import os
from contextlib import contextmanager
from typing import Generator
import logging

from .models import CREATE_TABLES_SQL

logger = logging.getLogger(__name__)

# Chemin par défaut de la base de données
DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'aftt.db')


def get_db_path() -> str:
    """Retourne le chemin de la base de données."""
    return os.environ.get('AFTT_DB_PATH', DEFAULT_DB_PATH)


def get_connection(db_path: str = None) -> sqlite3.Connection:
    """
    Crée une connexion à la base de données.
    
    Args:
        db_path: Chemin vers le fichier SQLite (optionnel)
    
    Returns:
        Connection SQLite configurée
    """
    if db_path is None:
        db_path = get_db_path()
    
    # Créer le dossier si nécessaire
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row  # Permet d'accéder aux colonnes par nom
    conn.execute("PRAGMA foreign_keys = ON")  # Activer les clés étrangères
    
    return conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager pour obtenir une connexion à la base.
    
    Usage:
        with get_db() as db:
            cursor = db.execute("SELECT * FROM clubs")
    """
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()


def init_database(db_path: str = None) -> None:
    """
    Initialise la base de données avec les tables nécessaires.
    
    Args:
        db_path: Chemin vers le fichier SQLite (optionnel)
    """
    if db_path is None:
        db_path = get_db_path()
    
    logger.info(f"Initialisation de la base de données: {db_path}")
    
    conn = get_connection(db_path)
    try:
        conn.executescript(CREATE_TABLES_SQL)
        conn.commit()
        logger.info("Tables créées avec succès")
    finally:
        conn.close()


def reset_database(db_path: str = None) -> None:
    """
    Réinitialise complètement la base de données.
    ATTENTION: Supprime toutes les données!
    """
    if db_path is None:
        db_path = get_db_path()
    
    if os.path.exists(db_path):
        os.remove(db_path)
        logger.info(f"Base de données supprimée: {db_path}")
    
    init_database(db_path)


def get_stats() -> dict:
    """Retourne des statistiques sur la base de données."""
    with get_db() as db:
        stats = {}
        
        # Nombre de clubs
        cursor = db.execute("SELECT COUNT(*) FROM clubs")
        stats['clubs'] = cursor.fetchone()[0]
        
        # Nombre de joueurs
        cursor = db.execute("SELECT COUNT(*) FROM players")
        stats['players'] = cursor.fetchone()[0]
        
        # Nombre de matchs
        cursor = db.execute("SELECT COUNT(*) FROM matches")
        stats['matches'] = cursor.fetchone()[0]
        
        # Joueurs avec fiche complète
        cursor = db.execute("SELECT COUNT(DISTINCT player_licence) FROM matches")
        stats['players_with_matches'] = cursor.fetchone()[0]
        
        return stats

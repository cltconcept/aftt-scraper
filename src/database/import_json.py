"""
Script d'import des fichiers JSON vers la base SQLite
"""
import json
import os
import glob
import logging
import sys

from .connection import init_database, get_db, get_stats
from .queries import insert_club, insert_player, insert_match, insert_player_stat

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

logger = logging.getLogger(__name__)


def import_clubs(json_path: str) -> int:
    """
    Importe les clubs depuis clubs.json
    
    Args:
        json_path: Chemin vers clubs.json
        
    Returns:
        Nombre de clubs importés
    """
    logger.info(f"Import des clubs depuis {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        clubs = json.load(f)
    
    with get_db() as db:
        for club in clubs:
            insert_club(club, db)
    
    logger.info(f"{len(clubs)} clubs importés")
    return len(clubs)


def import_members(json_path: str) -> tuple:
    """
    Importe les membres d'un club depuis members_*.json
    
    Args:
        json_path: Chemin vers members_XXXX.json
        
    Returns:
        Tuple (nombre de membres, code du club)
    """
    logger.info(f"Import des membres depuis {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    club_code = data.get('club_code')
    members = data.get('members', [])
    club_info = data.get('club_info', {})
    
    with get_db() as db:
        # Mettre à jour les infos du club
        if club_info:
            # Récupérer la province existante ou la détecter depuis le code
            from src.scraper.clubs_scraper import extract_province_from_code
            existing_club = None
            cursor = db.execute("SELECT province FROM clubs WHERE code = ?", (club_code,))
            row = cursor.fetchone()
            if row and row[0]:
                province = row[0]
            else:
                province = extract_province_from_code(club_code)
            
            club_data = {
                'code': club_code,
                'name': data.get('club_name'),
                'province': province,  # Toujours inclure la province
                **club_info
            }
            insert_club(club_data, db)
        
        # Importer les membres
        for member in members:
            player_data = {
                'licence': member.get('licence'),
                'name': member.get('name'),
                'club_code': club_code,
                'ranking': member.get('ranking'),
                'category': member.get('category'),
            }
            insert_player(player_data, db)
    
    logger.info(f"{len(members)} membres importés pour le club {club_code}")
    return len(members), club_code


def import_player(json_path: str) -> str:
    """
    Importe une fiche joueur depuis player_*.json
    
    Args:
        json_path: Chemin vers player_XXXXXX.json
        
    Returns:
        Licence du joueur importé
    """
    logger.info(f"Import du joueur depuis {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    licence = data.get('licence')
    
    with get_db() as db:
        # Données du joueur (fiche masculine)
        player_data = {
            'licence': licence,
            'name': data.get('name'),
            'ranking': data.get('ranking'),
            'points_start': data.get('points_start'),
            'points_current': data.get('points_current'),
            'ranking_position': data.get('ranking_position'),
            'total_wins': data.get('total_wins', 0),
            'total_losses': data.get('total_losses', 0),
            'last_update': data.get('last_update'),
        }
        
        # Données féminines si présentes
        women = data.get('women_stats')
        if women:
            player_data['women_points_start'] = women.get('points_start')
            player_data['women_points_current'] = women.get('points_current')
            player_data['women_total_wins'] = women.get('total_wins', 0)
            player_data['women_total_losses'] = women.get('total_losses', 0)
        
        insert_player(player_data, db)
        
        # Statistiques par classement (masculine)
        for stat in data.get('stats_by_ranking', []):
            stat_data = {
                'player_licence': licence,
                'fiche_type': 'masculine',
                **stat
            }
            insert_player_stat(stat_data, db)
        
        # Statistiques par classement (féminine)
        if women:
            for stat in women.get('stats_by_ranking', []):
                stat_data = {
                    'player_licence': licence,
                    'fiche_type': 'feminine',
                    **stat
                }
                insert_player_stat(stat_data, db)
        
        # Matchs masculins
        for match in data.get('matches', []):
            match_data = {
                'player_licence': licence,
                'fiche_type': 'masculine',
                **match
            }
            insert_match(match_data, db)
        
        # Matchs féminins
        if women:
            for match in women.get('matches', []):
                match_data = {
                    'player_licence': licence,
                    'fiche_type': 'feminine',
                    **match
                }
                insert_match(match_data, db)
    
    matches_count = len(data.get('matches', []))
    if women:
        matches_count += len(women.get('matches', []))
    
    logger.info(f"Joueur {licence} importé avec {matches_count} matchs")
    return licence


def import_all(data_dir: str = "data") -> dict:
    """
    Importe tous les fichiers JSON du dossier data.
    
    Args:
        data_dir: Chemin vers le dossier data
        
    Returns:
        Statistiques d'import
    """
    logger.info(f"Import de tous les fichiers JSON depuis {data_dir}")
    
    # Initialiser la base
    init_database()
    
    stats = {
        'clubs': 0,
        'members': 0,
        'players': 0,
        'errors': []
    }
    
    # 1. Importer clubs.json
    clubs_path = os.path.join(data_dir, 'clubs.json')
    if os.path.exists(clubs_path):
        try:
            stats['clubs'] = import_clubs(clubs_path)
        except Exception as e:
            logger.error(f"Erreur import clubs: {e}")
            stats['errors'].append(f"clubs.json: {e}")
    
    # 2. Importer les fichiers members_*.json
    members_files = glob.glob(os.path.join(data_dir, 'members_*.json'))
    for members_path in members_files:
        try:
            count, _ = import_members(members_path)
            stats['members'] += count
        except Exception as e:
            logger.error(f"Erreur import {members_path}: {e}")
            stats['errors'].append(f"{os.path.basename(members_path)}: {e}")
    
    # 3. Importer les fichiers player_*.json
    player_files = glob.glob(os.path.join(data_dir, 'player_*.json'))
    for player_path in player_files:
        try:
            import_player(player_path)
            stats['players'] += 1
        except Exception as e:
            logger.error(f"Erreur import {player_path}: {e}")
            stats['errors'].append(f"{os.path.basename(player_path)}: {e}")
    
    # Afficher les stats finales
    db_stats = get_stats()
    logger.info("=" * 50)
    logger.info("IMPORT TERMINE")
    logger.info("=" * 50)
    logger.info(f"Clubs en base    : {db_stats['clubs']}")
    logger.info(f"Joueurs en base  : {db_stats['players']}")
    logger.info(f"Matchs en base   : {db_stats['matches']}")
    logger.info(f"Erreurs          : {len(stats['errors'])}")
    
    return stats


def main():
    """Point d'entrée principal."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Import JSON vers SQLite')
    parser.add_argument('--data-dir', default='data', help='Dossier des fichiers JSON')
    parser.add_argument('--reset', action='store_true', help='Réinitialiser la base avant import')
    
    args = parser.parse_args()
    
    if args.reset:
        from .connection import reset_database
        reset_database()
    
    import_all(args.data_dir)


if __name__ == "__main__":
    main()

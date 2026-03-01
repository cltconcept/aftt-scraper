"""
Fixtures partagées pour les tests AFFT.
"""
import pytest
import sqlite3
import sys
import os

# Ajouter le répertoire racine au path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from src.database.models import CREATE_TABLES_SQL


@pytest.fixture
def db():
    """Base de données SQLite en mémoire pour les tests."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(CREATE_TABLES_SQL)
    yield conn
    conn.close()


@pytest.fixture
def sample_club():
    """Données d'un club de test."""
    return {
        'code': 'H004',
        'name': 'CTT Hainaut',
        'province': 'Hainaut',
        'full_name': 'Club de Tennis de Table du Hainaut',
        'email': 'contact@ctth.be',
        'phone': '065/123456',
        'status': 'Actif',
        'website': 'https://ctth.be',
        'has_shower': True,
        'venue_name': 'Salle Omnisports',
        'venue_address': 'Rue du Sport 1, 7000 Mons',
        'venue_phone': '065/789012',
        'venue_pmr': True,
        'venue_remarks': None,
        'teams_men': 5,
        'teams_women': 2,
        'teams_youth': 3,
        'teams_veterans': 1,
        'label': None,
        'palette': None,
    }


@pytest.fixture
def sample_player():
    """Données d'un joueur de test."""
    return {
        'licence': '152174',
        'name': 'DUPONT Jean',
        'club_code': 'H004',
        'ranking': 'C2',
        'category': 'S',
        'points_start': 1500.0,
        'points_current': 1550.0,
        'ranking_position': 42,
        'total_wins': 30,
        'total_losses': 10,
        'women_ranking': None,
        'women_points_start': None,
        'women_points_current': None,
        'women_total_wins': 0,
        'women_total_losses': 0,
        'last_update': '2025-01-15',
    }


@pytest.fixture
def sample_match():
    """Données d'un match de test."""
    return {
        'player_licence': '152174',
        'fiche_type': 'masculine',
        'date': '2025-01-10',
        'division': 'Prov. 1A',
        'opponent_club': 'BW023',
        'opponent_name': 'MARTIN Pierre',
        'opponent_licence': '167890',
        'opponent_ranking': 'C4',
        'opponent_points': 1300.0,
        'score': '3-1',
        'won': True,
        'points_change': 5.5,
    }


@pytest.fixture
def sample_tournament():
    """Données d'un tournoi de test."""
    return {
        't_id': 1234,
        'name': 'Tournoi de Mons',
        'level': 'Provincial',
        'date_start': '2025-02-01',
        'date_end': '2025-02-02',
        'reference': 'REF-2025-001',
        'series_count': 4,
    }


@pytest.fixture
def db_with_data(db, sample_club, sample_player, sample_match):
    """Base de données avec des données de test pré-insérées."""
    # Insérer le club
    db.execute("""
        INSERT INTO clubs (code, name, province) VALUES (?, ?, ?)
    """, (sample_club['code'], sample_club['name'], sample_club['province']))

    # Insérer le joueur
    db.execute("""
        INSERT INTO players (licence, name, club_code, ranking, category,
                           points_start, points_current, ranking_position,
                           total_wins, total_losses)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sample_player['licence'], sample_player['name'], sample_player['club_code'],
        sample_player['ranking'], sample_player['category'],
        sample_player['points_start'], sample_player['points_current'],
        sample_player['ranking_position'], sample_player['total_wins'],
        sample_player['total_losses']
    ))

    # Insérer le match
    db.execute("""
        INSERT INTO matches (player_licence, fiche_type, date, division,
                           opponent_club, opponent_name, opponent_licence,
                           opponent_ranking, opponent_points, score, won, points_change)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        sample_match['player_licence'], sample_match['fiche_type'],
        sample_match['date'], sample_match['division'],
        sample_match['opponent_club'], sample_match['opponent_name'],
        sample_match['opponent_licence'], sample_match['opponent_ranking'],
        sample_match['opponent_points'], sample_match['score'],
        sample_match['won'], sample_match['points_change']
    ))

    db.commit()
    yield db

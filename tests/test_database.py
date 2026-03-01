"""
Tests unitaires pour la couche database (queries.py).
Utilise SQLite en mémoire via la fixture db.
"""
import pytest
import sqlite3
from unittest.mock import patch
from src.database import queries
from src.database.connection import get_db


# =============================================================================
# Helper: exécuter les queries avec une DB injectée
# =============================================================================

class FakeDbContext:
    """Simule le context manager get_db() avec une connexion injectée."""
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self.conn

    def __exit__(self, *args):
        pass


def patch_db(db):
    """Retourne un patch de get_db() qui injecte la connexion de test."""
    return patch('src.database.queries.get_db', return_value=FakeDbContext(db))


# =============================================================================
# TESTS: Clubs
# =============================================================================

class TestClubs:
    def test_insert_club(self, db, sample_club):
        with patch_db(db):
            queries.insert_club(sample_club)
            result = queries.get_club('H004')
            assert result is not None
            assert result['code'] == 'H004'
            assert result['name'] == 'CTT Hainaut'
            assert result['province'] == 'Hainaut'

    def test_insert_club_upsert(self, db, sample_club):
        with patch_db(db):
            queries.insert_club(sample_club)
            # Mettre à jour le nom
            sample_club['name'] = 'CTT Hainaut Updated'
            queries.insert_club(sample_club)
            result = queries.get_club('H004')
            assert result['name'] == 'CTT Hainaut Updated'

    def test_get_club_not_found(self, db):
        with patch_db(db):
            result = queries.get_club('XXXX')
            assert result is None

    def test_get_all_clubs(self, db, sample_club):
        with patch_db(db):
            queries.insert_club(sample_club)
            queries.insert_club({**sample_club, 'code': 'BW023', 'name': 'Club BW', 'province': 'Brabant Wallon'})
            clubs = queries.get_all_clubs()
            assert len(clubs) == 2

    def test_get_all_clubs_filter_province(self, db, sample_club):
        with patch_db(db):
            queries.insert_club(sample_club)
            queries.insert_club({**sample_club, 'code': 'BW023', 'name': 'Club BW', 'province': 'Brabant Wallon'})
            clubs = queries.get_all_clubs(province='Hainaut')
            assert len(clubs) == 1
            assert clubs[0]['code'] == 'H004'

    def test_get_provinces(self, db, sample_club):
        with patch_db(db):
            queries.insert_club(sample_club)
            queries.insert_club({**sample_club, 'code': 'BW023', 'name': 'Club BW', 'province': 'Brabant Wallon'})
            provinces = queries.get_provinces()
            assert 'Hainaut' in provinces
            assert 'Brabant Wallon' in provinces


# =============================================================================
# TESTS: Players
# =============================================================================

class TestPlayers:
    def _insert_club(self, db, code='H004'):
        db.execute("INSERT OR IGNORE INTO clubs (code, name) VALUES (?, ?)", (code, f'Club {code}'))
        db.commit()

    def test_insert_player(self, db, sample_player):
        self._insert_club(db)
        with patch_db(db):
            queries.insert_player(sample_player)
            result = queries.get_player('152174')
            assert result is not None
            assert result['name'] == 'DUPONT Jean'
            assert result['ranking'] == 'C2'
            assert result['points_current'] == 1550.0

    def test_insert_player_upsert(self, db, sample_player):
        self._insert_club(db)
        with patch_db(db):
            queries.insert_player(sample_player)
            sample_player['points_current'] = 1600.0
            queries.insert_player(sample_player)
            result = queries.get_player('152174')
            assert result['points_current'] == 1600.0

    def test_get_player_not_found(self, db):
        with patch_db(db):
            result = queries.get_player('999999')
            assert result is None

    def test_get_all_players_with_search(self, db, sample_player):
        self._insert_club(db)
        with patch_db(db):
            queries.insert_player(sample_player)
            results = queries.get_all_players(search='DUPONT')
            assert len(results) == 1
            assert results[0]['licence'] == '152174'

    def test_get_all_players_filter_club(self, db, sample_player):
        self._insert_club(db)
        with patch_db(db):
            queries.insert_player(sample_player)
            results = queries.get_all_players(club_code='H004')
            assert len(results) == 1
            no_results = queries.get_all_players(club_code='ZZZZ')
            assert len(no_results) == 0

    def test_get_all_players_filter_points(self, db, sample_player):
        self._insert_club(db)
        with patch_db(db):
            queries.insert_player(sample_player)
            results = queries.get_all_players(min_points=1500.0, max_points=1600.0)
            assert len(results) == 1
            no_results = queries.get_all_players(min_points=2000.0)
            assert len(no_results) == 0

    def test_get_club_players(self, db, sample_player):
        self._insert_club(db)
        with patch_db(db):
            queries.insert_player(sample_player)
            results = queries.get_club_players('H004')
            assert len(results) == 1

    def test_search_players(self, db, sample_player):
        self._insert_club(db)
        with patch_db(db):
            queries.insert_player(sample_player)
            results = queries.search_players('DUPONT')
            assert len(results) == 1
            results = queries.search_players('152174')
            assert len(results) == 1
            results = queries.search_players('ZZZZZ')
            assert len(results) == 0


# =============================================================================
# TESTS: Matches
# =============================================================================

class TestMatches:
    def _setup(self, db):
        db.execute("INSERT INTO clubs (code, name) VALUES ('H004', 'Club H004')")
        db.execute("""
            INSERT INTO players (licence, name, club_code) VALUES ('152174', 'DUPONT Jean', 'H004')
        """)
        db.execute("""
            INSERT INTO players (licence, name, club_code) VALUES ('167890', 'MARTIN Pierre', 'H004')
        """)
        db.commit()

    def test_insert_match(self, db, sample_match):
        self._setup(db)
        with patch_db(db):
            queries.insert_match(sample_match)
            matches = queries.get_player_matches('152174')
            assert len(matches) == 1
            assert matches[0]['opponent_name'] == 'MARTIN Pierre'
            assert matches[0]['won'] == 1  # SQLite stores bool as int

    def test_insert_match_ignore_duplicate(self, db, sample_match):
        self._setup(db)
        with patch_db(db):
            queries.insert_match(sample_match)
            queries.insert_match(sample_match)  # Doublon
            matches = queries.get_player_matches('152174')
            assert len(matches) == 1

    def test_get_player_matches_filter_fiche_type(self, db, sample_match):
        self._setup(db)
        with patch_db(db):
            queries.insert_match(sample_match)
            queries.insert_match({**sample_match, 'fiche_type': 'feminine', 'date': '2025-01-11'})
            masc = queries.get_player_matches('152174', fiche_type='masculine')
            fem = queries.get_player_matches('152174', fiche_type='feminine')
            assert len(masc) == 1
            assert len(fem) == 1

    def test_delete_player_matches_and_stats(self, db, sample_match):
        self._setup(db)
        with patch_db(db):
            queries.insert_match(sample_match)
            queries.insert_player_stat({
                'player_licence': '152174',
                'fiche_type': 'masculine',
                'opponent_ranking': 'C4',
                'wins': 5,
                'losses': 2,
                'ratio': 71.4,
            })
            queries.delete_player_matches_and_stats('152174')
            assert len(queries.get_player_matches('152174')) == 0
            assert len(queries.get_player_stats('152174')) == 0

    def test_head_to_head(self, db, sample_match):
        self._setup(db)
        with patch_db(db):
            queries.insert_match(sample_match)
            # Match inverse
            queries.insert_match({
                **sample_match,
                'player_licence': '167890',
                'opponent_licence': '152174',
                'opponent_name': 'DUPONT Jean',
                'won': False,
                'date': '2025-01-11',
            })
            h2h = queries.get_head_to_head('152174', '167890')
            assert h2h['total_matches'] == 2
            assert h2h['player1_wins'] == 1


# =============================================================================
# TESTS: Player Stats
# =============================================================================

class TestPlayerStats:
    def _setup(self, db):
        db.execute("INSERT INTO clubs (code, name) VALUES ('H004', 'Club H004')")
        db.execute("INSERT INTO players (licence, name, club_code) VALUES ('152174', 'DUPONT', 'H004')")
        db.commit()

    def test_insert_and_get_stats(self, db):
        self._setup(db)
        with patch_db(db):
            queries.insert_player_stat({
                'player_licence': '152174',
                'fiche_type': 'masculine',
                'opponent_ranking': 'C4',
                'wins': 10,
                'losses': 3,
                'ratio': 76.9,
            })
            stats = queries.get_player_stats('152174', 'masculine')
            assert len(stats) == 1
            assert stats[0]['wins'] == 10
            assert stats[0]['losses'] == 3

    def test_insert_stat_upsert(self, db):
        self._setup(db)
        with patch_db(db):
            queries.insert_player_stat({
                'player_licence': '152174',
                'fiche_type': 'masculine',
                'opponent_ranking': 'C4',
                'wins': 10,
                'losses': 3,
                'ratio': 76.9,
            })
            queries.insert_player_stat({
                'player_licence': '152174',
                'fiche_type': 'masculine',
                'opponent_ranking': 'C4',
                'wins': 15,
                'losses': 5,
                'ratio': 75.0,
            })
            stats = queries.get_player_stats('152174', 'masculine')
            assert len(stats) == 1
            assert stats[0]['wins'] == 15


# =============================================================================
# TESTS: Tournaments
# =============================================================================

class TestTournaments:
    def test_insert_and_get_tournament(self, db, sample_tournament):
        with patch_db(db):
            queries.insert_tournament(sample_tournament)
            result = queries.get_tournament(1234)
            assert result is not None
            assert result['name'] == 'Tournoi de Mons'
            assert result['level'] == 'Provincial'

    def test_get_tournament_not_found(self, db):
        with patch_db(db):
            assert queries.get_tournament(9999) is None

    def test_get_all_tournaments(self, db, sample_tournament):
        with patch_db(db):
            queries.insert_tournament(sample_tournament)
            queries.insert_tournament({**sample_tournament, 't_id': 5678, 'name': 'Tournoi de Liège'})
            tournaments = queries.get_all_tournaments()
            assert len(tournaments) == 2

    def test_get_all_tournaments_filter_level(self, db, sample_tournament):
        with patch_db(db):
            queries.insert_tournament(sample_tournament)
            queries.insert_tournament({**sample_tournament, 't_id': 5678, 'name': 'Tournoi National', 'level': 'National'})
            results = queries.get_all_tournaments(level='Provincial')
            assert len(results) == 1
            assert results[0]['t_id'] == 1234

    def test_tournament_series(self, db, sample_tournament):
        with patch_db(db):
            queries.insert_tournament(sample_tournament)
            queries.insert_tournament_series({
                'tournament_id': 1234,
                'series_name': 'E6-D6',
                'date': '2025-02-01',
                'time': '09:00',
                'inscriptions_count': 16,
                'inscriptions_max': 32,
            })
            series = queries.get_tournament_series(1234)
            assert len(series) == 1
            assert series[0]['series_name'] == 'E6-D6'

    def test_delete_tournament_data(self, db, sample_tournament):
        with patch_db(db):
            queries.insert_tournament(sample_tournament)
            queries.insert_tournament_series({
                'tournament_id': 1234,
                'series_name': 'E6-D6',
                'date': '2025-02-01',
                'time': '09:00',
                'inscriptions_count': 0,
                'inscriptions_max': 0,
            })
            queries.delete_tournament_data(1234)
            assert len(queries.get_tournament_series(1234)) == 0


# =============================================================================
# TESTS: Scrape Tasks
# =============================================================================

class TestScrapeTasks:
    def test_create_scrape_task(self, db):
        with patch_db(db):
            task_id = queries.create_scrape_task('manual', 10)
            assert task_id is not None
            assert task_id > 0

    def test_get_current_scrape_task(self, db):
        with patch_db(db):
            task_id = queries.create_scrape_task('manual', 10)
            current = queries.get_current_scrape_task()
            assert current is not None
            assert current['status'] == 'running'

    def test_update_scrape_task(self, db):
        with patch_db(db):
            task_id = queries.create_scrape_task('manual', 10)
            queries.update_scrape_task(task_id, completed_clubs=5, status='success')
            task = queries.get_scrape_task_by_id(task_id)
            assert task['completed_clubs'] == 5
            assert task['status'] == 'success'
            assert task['finished_at'] is not None

    def test_get_scrape_task_history(self, db):
        with patch_db(db):
            queries.create_scrape_task('manual', 10)
            queries.create_scrape_task('cron', 20)
            history = queries.get_scrape_task_history(limit=5)
            assert len(history) == 2

    def test_cancel_running_tasks(self, db):
        with patch_db(db):
            queries.create_scrape_task('manual', 10)
            queries.cancel_running_tasks()
            current = queries.get_current_scrape_task()
            assert current is None


# =============================================================================
# TESTS: Interclubs
# =============================================================================

class TestInterclubs:
    def test_insert_division(self, db):
        with patch_db(db):
            queries.insert_interclubs_division({
                'division_index': 1,
                'division_id': '8662',
                'division_name': 'National - Hommes',
                'division_category': 'National',
                'division_gender': 'Hommes',
            })
            divisions = queries.get_interclubs_divisions()
            assert len(divisions) == 1
            assert divisions[0]['division_name'] == 'National - Hommes'

    def test_insert_ranking(self, db):
        with patch_db(db):
            queries.insert_interclubs_ranking({
                'division_index': 1,
                'division_name': 'National',
                'week': 5,
                'rank': 1,
                'team_name': 'CTT Hainaut A',
                'played': 4,
                'wins': 3,
                'losses': 1,
                'draws': 0,
                'forfeits': 0,
                'points': 9,
            })
            rankings = queries.get_interclubs_ranking(1, 5)
            assert len(rankings) == 1
            assert rankings[0]['team_name'] == 'CTT Hainaut A'
            assert rankings[0]['points'] == 9

    def test_insert_rankings_batch(self, db):
        with patch_db(db):
            batch = [
                {'division_index': 1, 'division_name': 'Nat', 'week': 1, 'rank': i,
                 'team_name': f'Team {i}', 'played': 0, 'wins': 0, 'losses': 0,
                 'draws': 0, 'forfeits': 0, 'points': 0}
                for i in range(1, 6)
            ]
            queries.insert_interclubs_rankings_batch(batch)
            rankings = queries.get_interclubs_ranking(1, 1)
            assert len(rankings) == 5

    def test_get_interclubs_stats(self, db):
        with patch_db(db):
            queries.insert_interclubs_division({
                'division_index': 1, 'division_id': '1', 'division_name': 'Nat',
                'division_category': None, 'division_gender': None,
            })
            queries.insert_interclubs_ranking({
                'division_index': 1, 'division_name': 'Nat', 'week': 1,
                'rank': 1, 'team_name': 'Team A',
                'played': 0, 'wins': 0, 'losses': 0, 'draws': 0, 'forfeits': 0, 'points': 0,
            })
            stats = queries.get_interclubs_stats()
            assert stats['divisions_count'] == 1
            assert stats['rankings_count'] == 1
            assert stats['teams_count'] == 1

    def test_search_interclubs_teams(self, db):
        with patch_db(db):
            queries.insert_interclubs_ranking({
                'division_index': 1, 'division_name': 'Nat', 'week': 1,
                'rank': 1, 'team_name': 'CTT Hainaut A',
                'played': 0, 'wins': 0, 'losses': 0, 'draws': 0, 'forfeits': 0, 'points': 0,
            })
            results = queries.search_interclubs_teams('Hainaut')
            assert len(results) == 1
            results = queries.search_interclubs_teams('ZZZZZ')
            assert len(results) == 0


# =============================================================================
# TESTS: Statistics helpers
# =============================================================================

class TestStatistics:
    def _setup(self, db):
        db.execute("INSERT INTO clubs (code, name, province) VALUES ('H004', 'Club H', 'Hainaut')")
        db.execute("""
            INSERT INTO players (licence, name, club_code, ranking, points_start, points_current, ranking_position)
            VALUES ('152174', 'DUPONT Jean', 'H004', 'C2', 1500.0, 1550.0, 42)
        """)
        db.execute("""
            INSERT INTO players (licence, name, club_code, ranking, points_start, points_current, ranking_position)
            VALUES ('167890', 'MARTIN Pierre', 'H004', 'C4', 1200.0, 1350.0, 100)
        """)
        db.commit()

    def test_get_top_players(self, db):
        self._setup(db)
        with patch_db(db):
            top = queries.get_top_players(limit=10)
            assert len(top) == 2
            assert top[0]['licence'] == '152174'  # Plus de points

    def test_get_top_progressions(self, db):
        self._setup(db)
        with patch_db(db):
            top = queries.get_top_progressions(limit=10)
            assert len(top) == 2
            # MARTIN a une progression de 150 vs DUPONT 50
            assert top[0]['licence'] == '167890'

    def test_get_clubs_count(self, db):
        self._setup(db)
        with patch_db(db):
            assert queries.get_clubs_count() == 1

    def test_get_active_players_count(self, db):
        self._setup(db)
        with patch_db(db):
            assert queries.get_active_players_count() == 2

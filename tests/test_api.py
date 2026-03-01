"""
Tests d'intégration pour l'API FastAPI.
Utilise httpx TestClient avec une DB de test.
"""
import pytest
import sqlite3
import os
import sys
from unittest.mock import patch, MagicMock

# Préparer l'environnement AVANT d'importer l'app
# Utiliser une DB de test temporaire
TEST_DB_PATH = os.path.join(os.path.dirname(__file__), 'test_api.db')


@pytest.fixture(autouse=True)
def setup_test_db():
    """Crée une DB de test propre avant chaque test."""
    # Supprimer la DB de test si elle existe
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)

    # Configurer la variable d'environnement
    os.environ['AFTT_DB_PATH'] = TEST_DB_PATH

    # Patcher le scraping d'init pour ne pas appeler le réseau
    with patch('src.scraper.clubs_scraper.get_all_clubs', return_value=[]):
        # Importer l'app (la première fois, cela initialise la DB)
        # Re-import pour reset
        if 'src.api.app' in sys.modules:
            # Réinitialiser la DB
            from src.database.connection import init_database
            init_database(TEST_DB_PATH)
        else:
            import src.api.app  # noqa

        from src.api.app import app
        from src.database.connection import init_database
        init_database(TEST_DB_PATH)

        yield app

    # Cleanup
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    # Supprimer aussi les fichiers WAL/SHM
    for ext in ['-wal', '-shm']:
        path = TEST_DB_PATH + ext
        if os.path.exists(path):
            os.remove(path)


@pytest.fixture
def client(setup_test_db):
    """Client HTTP de test."""
    from httpx import ASGITransport, AsyncClient
    transport = ASGITransport(app=setup_test_db)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def seed_data():
    """Insère des données de test dans la DB."""
    from src.database import queries
    queries.insert_club({
        'code': 'H004', 'name': 'CTT Hainaut', 'province': 'Hainaut',
        'full_name': None, 'email': None, 'phone': None, 'status': None,
        'website': None, 'has_shower': None, 'venue_name': None,
        'venue_address': None, 'venue_phone': None, 'venue_pmr': None,
        'venue_remarks': None, 'teams_men': 0, 'teams_women': 0,
        'teams_youth': 0, 'teams_veterans': 0, 'label': None, 'palette': None,
    })
    queries.insert_club({
        'code': 'BW023', 'name': 'Club BW', 'province': 'Brabant Wallon',
        'full_name': None, 'email': None, 'phone': None, 'status': None,
        'website': None, 'has_shower': None, 'venue_name': None,
        'venue_address': None, 'venue_phone': None, 'venue_pmr': None,
        'venue_remarks': None, 'teams_men': 0, 'teams_women': 0,
        'teams_youth': 0, 'teams_veterans': 0, 'label': None, 'palette': None,
    })
    queries.insert_player({
        'licence': '152174', 'name': 'DUPONT Jean', 'club_code': 'H004',
        'ranking': 'C2', 'category': 'S', 'points_start': 1500.0,
        'points_current': 1550.0, 'ranking_position': 42,
        'total_wins': 30, 'total_losses': 10,
        'women_ranking': None, 'women_points_start': None,
        'women_points_current': None, 'women_total_wins': 0,
        'women_total_losses': 0, 'last_update': '2025-01-15',
    })
    queries.insert_match({
        'player_licence': '152174', 'fiche_type': 'masculine',
        'date': '2025-01-10', 'division': 'Prov. 1A',
        'opponent_club': 'BW023', 'opponent_name': 'MARTIN Pierre',
        'opponent_licence': '167890', 'opponent_ranking': 'C4',
        'opponent_points': 1300.0, 'score': '3-1',
        'won': True, 'points_change': 5.5,
    })


# =============================================================================
# TESTS: Health & Info
# =============================================================================

class TestHealth:
    @pytest.mark.asyncio
    async def test_health(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_api_info(self, client):
        resp = await client.get("/api")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "AFTT Data API"
        assert "endpoints" in data

    @pytest.mark.asyncio
    async def test_stats(self, client):
        resp = await client.get("/api/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "clubs" in data
        assert "players" in data


# =============================================================================
# TESTS: Clubs endpoints
# =============================================================================

class TestClubsAPI:
    @pytest.mark.asyncio
    async def test_list_clubs(self, client, seed_data):
        resp = await client.get("/api/clubs")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2

    @pytest.mark.asyncio
    async def test_get_club(self, client, seed_data):
        resp = await client.get("/api/clubs/H004")
        assert resp.status_code == 200
        data = resp.json()
        assert data["code"] == "H004"
        assert data["name"] == "CTT Hainaut"

    @pytest.mark.asyncio
    async def test_get_club_not_found(self, client):
        resp = await client.get("/api/clubs/ZZ99")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_club_invalid_code(self, client):
        resp = await client.get("/api/clubs/invalid!")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_get_club_players(self, client, seed_data):
        resp = await client.get("/api/clubs/H004/players")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["players"][0]["licence"] == "152174"

    @pytest.mark.asyncio
    async def test_get_provinces(self, client, seed_data):
        resp = await client.get("/api/clubs/provinces")
        assert resp.status_code == 200
        data = resp.json()
        assert "Hainaut" in data["provinces"]


# =============================================================================
# TESTS: Players endpoints
# =============================================================================

class TestPlayersAPI:
    @pytest.mark.asyncio
    async def test_get_player(self, client, seed_data):
        resp = await client.get("/api/players/152174")
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "DUPONT Jean"
        assert data["ranking"] == "C2"
        assert "stats_masculine" in data
        assert "matches_masculine" in data

    @pytest.mark.asyncio
    async def test_get_player_not_found(self, client):
        resp = await client.get("/api/players/999999")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_player_matches(self, client, seed_data):
        resp = await client.get("/api/players/152174/matches")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1
        assert data["matches"][0]["opponent_name"] == "MARTIN Pierre"

    @pytest.mark.asyncio
    async def test_list_players(self, client, seed_data):
        resp = await client.get("/api/players", params={"club_code": "H004"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1


# =============================================================================
# TESTS: Input Validation
# =============================================================================

class TestValidation:
    @pytest.mark.asyncio
    async def test_invalid_licence_format(self, client):
        resp = await client.get("/api/players/abc")
        assert resp.status_code == 400
        assert "invalide" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_invalid_licence_too_short(self, client):
        resp = await client.get("/api/players/123")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_invalid_licence_special_chars(self, client):
        resp = await client.get("/api/players/12345'OR 1=1")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_valid_licence_format(self, client):
        # Format valide mais joueur n'existe pas => 404 pas 400
        resp = await client.get("/api/players/123456")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_club_code(self, client):
        resp = await client.get("/api/clubs/INVALID!")
        assert resp.status_code == 400
        assert "invalide" in resp.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_invalid_club_code_injection(self, client):
        resp = await client.get("/api/clubs/H004';DROP TABLE clubs;--")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_valid_club_code_format(self, client):
        # Format valide mais club n'existe pas => 404 pas 400
        resp = await client.get("/api/clubs/ZZ99")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_scrape_player_invalid_licence(self, client):
        resp = await client.post("/api/players/abc/scrape")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_scrape_club_invalid_code(self, client):
        resp = await client.post("/api/clubs/INVALID!/scrape")
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_player_matches_invalid_licence(self, client):
        resp = await client.get("/api/players/abc/matches")
        assert resp.status_code == 400

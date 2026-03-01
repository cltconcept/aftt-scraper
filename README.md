# AFTT Data API

Application de scraping et API REST pour les donnees du tennis de table belge (AFTT - Association Francophone de Tennis de Table).

Collecte automatiquement les clubs, joueurs, classements, matchs, tournois et interclubs depuis le site AFTT, les stocke dans une base SQLite et les expose via une API FastAPI.

## Prerequis

- Python 3.11+
- pip

## Installation

```bash
# Cloner le projet
git clone <repo-url>
cd AFFT

# Installer les dependances
pip install -r requirements.txt

# (Optionnel) Installer les dependances de test
pip install -r requirements-dev.txt

# (Optionnel) Installer Playwright pour le scraping des classements numeriques
playwright install chromium
```

## Configuration

Copier `.env.example` en `.env` et adapter si necessaire :

```bash
cp .env.example .env
```

Variables disponibles :

| Variable | Default | Description |
|----------|---------|-------------|
| `AFTT_DB_PATH` | `data/aftt.db` | Chemin de la base SQLite |
| `AFTT_HOST` | `0.0.0.0` | Host du serveur API |
| `AFTT_PORT` | `8000` | Port du serveur API |
| `AFTT_CORS_ORIGINS` | `*` | Origins CORS (separees par virgules) |
| `AFTT_LOG_LEVEL` | `INFO` | Niveau de log (DEBUG, INFO, WARNING, ERROR) |
| `AFTT_SCRAPE_DELAY` | `0.3` | Delai entre les requetes de scraping (secondes) |
| `AFTT_RETRY_DELAY` | `2.0` | Delai avant retry en cas d'erreur (secondes) |
| `AFTT_MAX_RETRIES` | `3` | Nombre max de tentatives |
| `AFTT_SCRAPE_TIMEOUT` | `30` | Timeout des requetes de scraping (secondes) |

## Lancement

### API (mode principal)

```bash
python main.py api
```

L'API demarre sur `http://localhost:8000`. Documentation interactive disponible sur :
- Swagger UI : `http://localhost:8000/docs`
- ReDoc : `http://localhost:8000/redoc`

Au premier demarrage, la liste des clubs est automatiquement chargee depuis le site AFTT.

### CLI (scraping manuel)

```bash
python main.py                     # Scrape tous les clubs
python main.py clubs               # Scrape la liste des clubs
python main.py members H004        # Scrape les membres du club H004
python main.py members all         # Scrape les membres de tous les clubs
python main.py player 152174       # Scrape la fiche d'un joueur
python main.py tournaments         # Scrape tous les tournois
python main.py tournament 6310     # Scrape les details d'un tournoi
python main.py import              # Importe les fichiers JSON dans SQLite
```

## Structure du projet

```
AFFT/
├── main.py                    # Point d'entree CLI
├── requirements.txt           # Dependances production
├── requirements-dev.txt       # Dependances de test
├── .env.example               # Template de configuration
├── pytest.ini                 # Configuration pytest
│
├── src/
│   ├── config.py              # Configuration centralisee (env vars)
│   ├── logging_config.py      # Configuration du logging
│   │
│   ├── api/
│   │   ├── app.py             # Application FastAPI (lifespan, CORS, routers)
│   │   ├── cache.py           # Cache TTL en memoire
│   │   ├── validators.py      # Validation des entrees (licence, club code)
│   │   └── routers/
│   │       ├── health.py      # Sante, stats, diagnostics
│   │       ├── clubs.py       # CRUD clubs + scraping club/province
│   │       ├── players.py     # CRUD joueurs, matchs, rankings, search
│   │       ├── scraping.py    # Scraping global (tous les clubs)
│   │       ├── tournaments.py # CRUD tournois + scraping
│   │       └── interclubs.py  # Interclubs divisions et classements
│   │
│   ├── database/
│   │   ├── connection.py      # Connexion SQLite, init, migrations
│   │   ├── models.py          # Schema SQL (CREATE TABLE) et dataclasses
│   │   ├── queries.py         # Toutes les requetes SQL (CRUD)
│   │   └── import_json.py     # Import de fichiers JSON en base
│   │
│   └── scraper/
│       ├── clubs_scraper.py       # Scraper liste des clubs
│       ├── members_scraper.py     # Scraper membres d'un club
│       ├── player_scraper.py      # Scraper fiche joueur individuelle
│       ├── ranking_scraper.py     # Scraper classement numerique (Playwright)
│       ├── tournament_scraper.py  # Scraper tournois
│       └── interclubs_scraper.py  # Scraper interclubs
│
├── tests/
│   ├── conftest.py            # Fixtures pytest (base de test, client HTTP)
│   ├── test_api.py            # Tests d'integration API
│   └── test_database.py       # Tests des operations base de donnees
│
├── data/                      # Base de donnees SQLite (genere)
├── web/                       # Frontend web
└── documentation/             # Documentation detaillee
```

## Endpoints API (resume)

| Methode | Endpoint | Description |
|---------|----------|-------------|
| **Sante** | | |
| `GET` | `/health` | Verification de sante |
| `GET` | `/api/stats` | Statistiques generales |
| `GET` | `/api/stats/detailed` | Diagnostics detailles |
| **Clubs** | | |
| `GET` | `/api/clubs` | Lister les clubs |
| `GET` | `/api/clubs/{code}` | Detail d'un club |
| `GET` | `/api/clubs/{code}/players` | Joueurs d'un club |
| `POST` | `/api/clubs/{code}/scrape` | Scraper un club |
| **Joueurs** | | |
| `GET` | `/api/players` | Lister les joueurs (filtres) |
| `GET` | `/api/players/{licence}` | Detail d'un joueur |
| `GET` | `/api/players/{licence}/matches` | Matchs d'un joueur |
| `GET` | `/api/players/{l1}/vs/{l2}` | Confrontations directes |
| `POST` | `/api/players/{licence}/scrape` | Rescraper un joueur |
| `GET` | `/api/search?q=` | Recherche joueurs |
| **Rankings** | | |
| `GET` | `/api/rankings/top` | Top joueurs |
| `GET` | `/api/rankings/progressions` | Meilleures progressions |
| **Tournois** | | |
| `GET` | `/api/tournaments` | Lister les tournois |
| `GET` | `/api/tournaments/{id}` | Detail d'un tournoi |
| `GET` | `/api/tournaments/{id}/series` | Series d'un tournoi |
| `GET` | `/api/tournaments/{id}/inscriptions` | Inscriptions |
| `GET` | `/api/tournaments/{id}/results` | Resultats |
| **Interclubs** | | |
| `GET` | `/api/interclubs/divisions` | Divisions |
| `GET` | `/api/interclubs/rankings` | Classements |
| **Scraping** | | |
| `POST` | `/api/scrape/all` | Scraping global |
| `GET` | `/api/scrape/status` | Statut du scraping |
| `POST` | `/api/scrape/cancel` | Annuler le scraping |
| `POST` | `/api/scrape/tournaments` | Scraper les tournois |
| `POST` | `/api/scrape/interclubs` | Scraper les interclubs |

Documentation complete : voir `/docs` (Swagger) ou `/redoc` une fois l'API lancee.

## Tests

```bash
# Lancer tous les tests
pytest

# Avec couverture
pytest --cov=src --cov-report=term-missing

# Un fichier specifique
pytest tests/test_api.py -v
```

## Base de donnees

SQLite avec les tables principales :
- `clubs` - Liste des clubs AFTT
- `players` - Joueurs avec classements et points
- `matches` - Historique des matchs individuels
- `player_stats` - Stats par classement adverse
- `tournaments` - Tournois
- `tournament_series`, `tournament_inscriptions`, `tournament_results` - Details tournois
- `interclubs_divisions`, `interclubs_rankings` - Interclubs
- `scrape_tasks` - Historique des taches de scraping
- `schema_version` - Versioning des migrations

Les migrations sont gerees automatiquement au demarrage via un systeme de versioning incremental.

## Licence

Projet prive - Donnees AFTT.

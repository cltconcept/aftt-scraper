# Documentation API AFTT

## Résumé

API REST FastAPI pour accéder aux données du tennis de table belge (AFTT).

## Endpoints

### Base URL
- **Local** : `http://localhost:8000`
- **Documentation Swagger** : `http://localhost:8000/docs`

### Santé & Stats

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/` | Page d'accueil avec liste des endpoints |
| GET | `/health` | Vérification de l'état de l'API |
| GET | `/api/stats` | Statistiques de la base de données |

### Clubs

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/clubs` | Liste tous les clubs |
| GET | `/api/clubs/provinces` | Liste les provinces |
| GET | `/api/clubs/{code}` | Détails d'un club |
| GET | `/api/clubs/{code}/players` | Joueurs d'un club |

**Paramètres de `/api/clubs`** :
- `province` : Filtrer par province
- `limit` : Nombre max de résultats (1-1000)
- `offset` : Pagination

### Joueurs

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/players` | Liste des joueurs |
| GET | `/api/players/{licence}` | Fiche complète d'un joueur |
| GET | `/api/players/{licence}/matches` | Matchs d'un joueur |
| GET | `/api/players/{l1}/vs/{l2}` | Head-to-head entre 2 joueurs |

**Paramètres de `/api/players`** :
- `club_code` : Filtrer par club
- `ranking` : Filtrer par classement
- `min_points` / `max_points` : Filtrer par points
- `search` : Recherche par nom/licence
- `order_by` : Tri (points_current DESC, name ASC, etc.)
- `limit` / `offset` : Pagination

### Classements

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/rankings/top` | Top joueurs |
| GET | `/api/rankings/progressions` | Meilleures progressions |

### Recherche

| Méthode | Endpoint | Description |
|---------|----------|-------------|
| GET | `/api/search?q=...` | Recherche joueurs |

## Exemples d'utilisation

### Liste des clubs du Hainaut

```bash
curl "http://localhost:8000/api/clubs?province=Hainaut"
```

### Fiche complète d'un joueur

```bash
curl "http://localhost:8000/api/players/152174"
```

**Réponse** :
```json
{
  "licence": "152174",
  "name": "KEVIN BRULEZ",
  "club_code": "H004",
  "ranking": "C2",
  "points_start": 1543.0,
  "points_current": 1485.2,
  "total_wins": 24,
  "total_losses": 15,
  "stats_masculine": [...],
  "matches_masculine": [...],
  "stats_feminine": [],
  "matches_feminine": []
}
```

### Confrontations entre 2 joueurs

```bash
curl "http://localhost:8000/api/players/152174/vs/101452"
```

### Top 10 des joueurs du Hainaut

```bash
curl "http://localhost:8000/api/rankings/top?limit=10&province=Hainaut"
```

### Recherche

```bash
curl "http://localhost:8000/api/search?q=BRULEZ"
```

## Lancement

### Local

```bash
# 1. Importer les données
python main.py import

# 2. Lancer l'API
python main.py api
```

### Docker

```bash
# Construction et lancement
docker-compose up -d

# Ou avec le scraper
docker-compose --profile scraper up
```

### Coolify

Le projet est prêt pour déploiement via Coolify :
1. Connecter le repository Git
2. Coolify détectera automatiquement le Dockerfile
3. L'API sera disponible sur le port 8000

## Architecture

```
AFTT/
├── data/
│   ├── aftt.db              # Base SQLite
│   └── *.json               # Fichiers JSON (optionnels)
├── src/
│   ├── api/
│   │   └── app.py           # Application FastAPI
│   ├── database/
│   │   ├── models.py        # Modèles de données
│   │   ├── connection.py    # Connexion SQLite
│   │   ├── queries.py       # Requêtes SQL
│   │   └── import_json.py   # Import JSON → SQLite
│   └── scraper/             # Scrapers existants
├── main.py                  # Point d'entrée
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Base de données

### Tables

- **clubs** : Informations des clubs
- **players** : Informations des joueurs
- **matches** : Historique des matchs
- **player_stats** : Statistiques par classement adverse

### Relations

```
clubs (1) ←→ (N) players
players (1) ←→ (N) matches
players (1) ←→ (N) player_stats
```

## Performance

- SQLite est suffisant pour ~15000 joueurs
- Index sur les colonnes fréquemment recherchées
- Pagination obligatoire pour les grandes listes

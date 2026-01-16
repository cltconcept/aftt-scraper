# Documentation API AFTT

## URL de Base

- **Production** : `https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com`
- **Local** : `http://localhost:8000`
- **Swagger UI** : `/docs`

---

## Endpoints Disponibles

### 🏥 Health & Stats

#### Vérifier l'état de l'API
```http
GET /health
```
**Réponse :**
```json
{ "status": "ok" }
```

#### Statistiques de la base
```http
GET /api/stats
```
**Réponse :**
```json
{
  "clubs": 823,
  "players": 1250,
  "matches": 15420,
  "players_with_matches": 1100
}
```

---

### 🏢 Clubs

#### Liste des clubs
```http
GET /api/clubs
GET /api/clubs?province=Hainaut
GET /api/clubs?limit=100&offset=0
```
**Paramètres :**
| Param | Type | Description |
|-------|------|-------------|
| `province` | string | Filtrer par province |
| `limit` | int | Nombre max de résultats (1-10000) |
| `offset` | int | Pagination |

**Réponse :**
```json
{
  "count": 823,
  "clubs": [
    {
      "code": "H004",
      "name": "ETT MANAGE",
      "province": "Hainaut"
    }
  ]
}
```

#### Liste des provinces
```http
GET /api/clubs/provinces
```
**Réponse :**
```json
{
  "provinces": ["Hainaut", "Brabant", "Liège", "Namur", ...]
}
```

#### Détail d'un club
```http
GET /api/clubs/{code}
```
**Exemple :** `GET /api/clubs/H004`

**Réponse :**
```json
{
  "code": "H004",
  "name": "ETT MANAGE",
  "province": "Hainaut",
  "address": "...",
  "venue": "..."
}
```

#### Joueurs d'un club
```http
GET /api/clubs/{code}/players
```
**Exemple :** `GET /api/clubs/H004/players`

**Réponse :**
```json
{
  "club": { "code": "H004", "name": "ETT MANAGE" },
  "count": 45,
  "players": [
    {
      "licence": "176506",
      "name": "DEBESSEL CHRISTOPHER",
      "ranking": "C2",
      "points_current": 1250,
      "category": "SEN"
    }
  ]
}
```

#### Scraper un club (rafraîchir les données)
```http
POST /api/clubs/{code}/scrape
```
**Exemple :** `POST /api/clubs/H004/scrape`

**Réponse :**
```json
{
  "success": true,
  "club_code": "H004",
  "total_players": 52,
  "players_scraped": 52,
  "message": "Scraping terminé: 52 joueurs, 52 fiches"
}
```

---

### 👤 Joueurs

#### Liste des joueurs
```http
GET /api/players
GET /api/players?club_code=H004
GET /api/players?ranking=B2
GET /api/players?min_points=1000&max_points=2000
GET /api/players?search=DEBESSEL
```
**Paramètres :**
| Param | Type | Description |
|-------|------|-------------|
| `club_code` | string | Filtrer par club |
| `ranking` | string | Filtrer par classement (NC, E6, D6, C6, B6, etc.) |
| `min_points` | float | Points minimum |
| `max_points` | float | Points maximum |
| `search` | string | Recherche par nom ou licence |
| `order_by` | string | Tri (ex: "points_current DESC") |
| `limit` | int | Max résultats (1-1000) |
| `offset` | int | Pagination |

**Réponse :**
```json
{
  "count": 45,
  "players": [
    {
      "licence": "176506",
      "name": "DEBESSEL CHRISTOPHER",
      "club_code": "H004",
      "ranking": "C2",
      "points_start": 1200,
      "points_current": 1285,
      "total_wins": 25,
      "total_losses": 12
    }
  ]
}
```

#### Détail d'un joueur
```http
GET /api/players/{licence}
```
**Exemple :** `GET /api/players/176506`

**Réponse :**
```json
{
  "licence": "176506",
  "name": "DEBESSEL CHRISTOPHER",
  "club_code": "H004",
  "ranking": "C2",
  "points_start": 1200,
  "points_current": 1285,
  "total_wins": 25,
  "total_losses": 12,
  "stats_masculine": [
    { "opponent_ranking": "C4", "wins": 5, "losses": 2 }
  ],
  "matches_masculine": [
    {
      "date": "2024-09-15",
      "opponent_name": "DUPONT JEAN",
      "opponent_ranking": "C4",
      "result": "V",
      "score": "3-1"
    }
  ]
}
```

#### Matchs d'un joueur
```http
GET /api/players/{licence}/matches
GET /api/players/{licence}/matches?fiche_type=masculine
GET /api/players/{licence}/matches?opponent=152174
```
**Paramètres :**
| Param | Type | Description |
|-------|------|-------------|
| `fiche_type` | string | "masculine" ou "feminine" |
| `opponent` | string | Licence de l'adversaire |
| `limit` | int | Max résultats |

#### Confrontation entre deux joueurs
```http
GET /api/players/{licence1}/vs/{licence2}
```
**Exemple :** `GET /api/players/176506/vs/152174`

**Réponse :**
```json
{
  "player1": { "licence": "176506", "name": "DEBESSEL CHRISTOPHER" },
  "player2": { "licence": "152174", "name": "DUPONT JEAN" },
  "player1_wins": 3,
  "player2_wins": 2,
  "matches": [...]
}
```

---

### 🏆 Rankings

#### Top joueurs
```http
GET /api/rankings/top
GET /api/rankings/top?limit=50
GET /api/rankings/top?province=Hainaut
GET /api/rankings/top?club_code=H004
```
**Paramètres :**
| Param | Type | Description |
|-------|------|-------------|
| `limit` | int | Nombre de joueurs (1-500) |
| `province` | string | Filtrer par province |
| `club_code` | string | Filtrer par club |
| `ranking` | string | Filtrer par classement |

#### Meilleures progressions
```http
GET /api/rankings/progressions
GET /api/rankings/progressions?limit=50
```

---

### 🔍 Recherche

#### Recherche de joueurs
```http
GET /api/search?q=DEBESSEL
GET /api/search?q=176506&limit=20
```
**Paramètres :**
| Param | Type | Description |
|-------|------|-------------|
| `q` | string | Terme de recherche (min 2 caractères) |
| `limit` | int | Max résultats (1-200) |

---

## Exemples d'Utilisation

### JavaScript (Fetch)
```javascript
const API_URL = 'https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com';

// Liste des clubs du Hainaut
const response = await fetch(`${API_URL}/api/clubs?province=Hainaut`);
const data = await response.json();
console.log(data.clubs);

// Détail d'un joueur
const player = await fetch(`${API_URL}/api/players/176506`).then(r => r.json());
console.log(player.name, player.ranking);
```

### Python (Requests)
```python
import requests

API_URL = 'https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com'

# Liste des clubs
response = requests.get(f'{API_URL}/api/clubs?province=Hainaut')
clubs = response.json()['clubs']

# Joueurs d'un club
response = requests.get(f'{API_URL}/api/clubs/H004/players')
players = response.json()['players']

# Recherche
response = requests.get(f'{API_URL}/api/search', params={'q': 'DEBESSEL'})
results = response.json()['players']
```

### cURL
```bash
# Stats
curl https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/stats

# Clubs du Hainaut
curl "https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/clubs?province=Hainaut"

# Scraper un club
curl -X POST https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/clubs/H004/scrape
```

---

## Codes d'Erreur

| Code | Description |
|------|-------------|
| 200 | Succès |
| 404 | Ressource non trouvée (club, joueur) |
| 422 | Paramètres invalides |
| 500 | Erreur serveur |

---

## Notes

- **CORS** : L'API accepte les requêtes depuis n'importe quelle origine
- **Rate Limiting** : Pas de limite actuellement
- **Scraping** : Le scraping des joueurs peut prendre 30-60 secondes par club
- **Données** : Les données sont scrappées depuis le site officiel AFTT (aftt.be)

# Documentation API AFTT

## URL de Base

- **Production** : `https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com`
- **Swagger UI** : `https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/docs`
- **Local** : `http://localhost:8000`

---

## Lexique & Codes

### Codes des Provinces/Régions

| Code | Province | Exemple Club |
|------|----------|--------------|
| `A` | Antwerpen (Anvers) | A001, A125 |
| `B` | Brabant | B001, B042 |
| `E` | Oost-Vlaanderen (Flandre Orientale) | E001, E089 |
| `H` | Hainaut | H004, H156 |
| `K` | Brussels Hoofdstedelijk (Bruxelles) | K001 |
| `L` | Limburg (Limbourg) | L001, L078 |
| `Li` | Liège | Li001, Li234 |
| `Lu` | Luxembourg | Lu001, Lu045 |
| `N` | Namur | N001, N067 |
| `O` | West-Vlaanderen (Flandre Occidentale) | O001, O112 |
| `V` | Vlaams-Brabant (Brabant Flamand) | V001, V089 |
| `W` | Brabant Wallon | W001, W034 |

### Classements (du plus bas au plus haut)

| Classement | Points approximatifs | Niveau |
|------------|---------------------|--------|
| `NC` | 0-100 | Non classé |
| `E6` | 100-150 | Débutant |
| `E4` | 150-200 | Débutant+ |
| `E2` | 200-250 | Initié |
| `E0` | 250-300 | Initié+ |
| `D6` | 300-400 | Intermédiaire |
| `D4` | 400-500 | Intermédiaire |
| `D2` | 500-600 | Intermédiaire+ |
| `D0` | 600-700 | Confirmé |
| `C6` | 700-900 | Confirmé |
| `C4` | 900-1100 | Confirmé+ |
| `C2` | 1100-1400 | Bon joueur |
| `C0` | 1400-1700 | Très bon |
| `B6` | 1700-2000 | Excellent |
| `B4` | 2000-2300 | Régional |
| `B2` | 2300-2600 | National |
| `B0` | 2600-2900 | Elite |
| `A` | 2900+ | Top national |

### Catégories d'âge

| Code | Catégorie | Âge |
|------|-----------|-----|
| `PRE` | Pré-minimes | -9 ans |
| `MIN` | Minimes | 9-10 ans |
| `CAD` | Cadets | 11-12 ans |
| `JUN` | Juniors | 13-14 ans |
| `J21` | -21 ans | 15-20 ans |
| `SEN` | Seniors | 21-39 ans |
| `V40` | Vétérans 40 | 40-49 ans |
| `V50` | Vétérans 50 | 50-59 ans |
| `V60` | Vétérans 60 | 60-69 ans |
| `V70` | Vétérans 70 | 70+ ans |

### Résultats de match

| Code | Signification |
|------|---------------|
| `V` | Victoire |
| `D` | Défaite |
| `WO` | Walk-over (forfait) |

---

## Endpoints avec Exemples

### 🏥 Health & Stats

#### GET /health
Vérifie que l'API fonctionne.

**Requête :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/health
```

**Réponse :**
```json
{
  "status": "ok"
}
```

---

#### GET /api/stats
Statistiques de la base de données.

**Requête :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/stats
```

**Réponse :**
```json
{
  "clubs": 823,
  "players": 45210,
  "matches": 156420,
  "players_with_matches": 12500
}
```

---

### 🏢 Clubs

#### GET /api/clubs
Liste tous les clubs.

**Requête - Tous les clubs :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/clubs
```

**Requête - Clubs du Hainaut :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/clubs?province=Hainaut
```

**Requête - Avec pagination :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/clubs?limit=50&offset=0
```

**Réponse :**
```json
{
  "count": 156,
  "clubs": [
    {
      "code": "H004",
      "name": "ETT MANAGE",
      "province": "Hainaut"
    },
    {
      "code": "H005",
      "name": "CTT GODARVILLE",
      "province": "Hainaut"
    }
  ]
}
```

---

#### GET /api/clubs/provinces
Liste toutes les provinces.

**Requête :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/clubs/provinces
```

**Réponse :**
```json
{
  "provinces": [
    "Antwerpen",
    "Brabant Wallon", 
    "Brussels Hoofdstedelijk",
    "Hainaut",
    "Liège",
    "Limburg",
    "Luxembourg",
    "Namur",
    "Oost-Vlaanderen",
    "Vlaams-Brabant",
    "West-Vlaanderen"
  ]
}
```

---

#### GET /api/clubs/{code}
Détail d'un club spécifique.

**Requête :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/clubs/H004
```

**Réponse :**
```json
{
  "code": "H004",
  "name": "ETT MANAGE",
  "province": "Hainaut",
  "address": "Rue de la Salle 12",
  "postal_code": "7170",
  "city": "Manage",
  "venue": "Salle omnisports de Manage"
}
```

---

#### GET /api/clubs/{code}/players
Tous les joueurs d'un club.

**Requête :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/clubs/H004/players
```

**Réponse :**
```json
{
  "club": {
    "code": "H004",
    "name": "ETT MANAGE"
  },
  "count": 52,
  "players": [
    {
      "licence": "176506",
      "name": "DEBESSEL CHRISTOPHER",
      "ranking": "C2",
      "points_current": 1285,
      "points_start": 1200,
      "category": "SEN",
      "total_wins": 25,
      "total_losses": 12
    },
    {
      "licence": "145892",
      "name": "DUPONT JEAN",
      "ranking": "D4",
      "points_current": 456,
      "points_start": 420,
      "category": "V50",
      "total_wins": 18,
      "total_losses": 22
    }
  ]
}
```

---

#### POST /api/clubs/{code}/scrape
Scrape les données d'un club depuis le site AFTT (rafraîchit la base).

**Requête :**
```
POST https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/clubs/H004/scrape
```

**Réponse :**
```json
{
  "success": true,
  "club_code": "H004",
  "members_from_annuaire": 45,
  "members_from_ranking": 52,
  "total_players": 52,
  "players_scraped": 52,
  "players_errors": [],
  "message": "Scraping terminé: 52 joueurs (45 annuaire + 52 ranking), 52 fiches"
}
```

---

### 👤 Joueurs

#### GET /api/players
Liste les joueurs avec filtres.

**Requête - Tous les joueurs d'un club :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/players?club_code=H004
```

**Requête - Joueurs B2 et plus :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/players?ranking=B2
```

**Requête - Joueurs entre 1000 et 1500 points :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/players?min_points=1000&max_points=1500
```

**Requête - Recherche par nom :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/players?search=DEBESSEL
```

**Requête - Trié par points décroissants :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/players?order_by=points_current%20DESC&limit=100
```

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
      "total_losses": 12,
      "category": "SEN"
    }
  ]
}
```

---

#### GET /api/players/{licence}
Fiche complète d'un joueur avec stats et matchs.

**Requête :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/players/176506
```

**Réponse :**
```json
{
  "licence": "176506",
  "name": "DEBESSEL CHRISTOPHER",
  "club_code": "H004",
  "ranking": "C2",
  "points_start": 1200,
  "points_current": 1285,
  "ranking_position": 1542,
  "total_wins": 25,
  "total_losses": 12,
  "category": "SEN",
  "last_update": "2024-12-15",
  "stats_masculine": [
    {
      "opponent_ranking": "C4",
      "wins": 8,
      "losses": 2,
      "win_percentage": 80.0
    },
    {
      "opponent_ranking": "C2",
      "wins": 5,
      "losses": 4,
      "win_percentage": 55.5
    },
    {
      "opponent_ranking": "C0",
      "wins": 2,
      "losses": 6,
      "win_percentage": 25.0
    }
  ],
  "stats_feminine": [],
  "matches_masculine": [
    {
      "date": "2024-12-10",
      "competition": "Championnat",
      "opponent_name": "MARTIN PIERRE",
      "opponent_licence": "152478",
      "opponent_ranking": "C4",
      "opponent_club": "H012",
      "result": "V",
      "score": "3-1",
      "sets_won": 3,
      "sets_lost": 1
    },
    {
      "date": "2024-12-03",
      "competition": "Championnat",
      "opponent_name": "DURAND MARC",
      "opponent_licence": "148956",
      "opponent_ranking": "C2",
      "opponent_club": "H025",
      "result": "D",
      "score": "1-3",
      "sets_won": 1,
      "sets_lost": 3
    }
  ],
  "matches_feminine": []
}
```

---

#### GET /api/players/{licence}/matches
Matchs d'un joueur avec filtres.

**Requête - Tous les matchs :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/players/176506/matches
```

**Requête - Matchs masculins uniquement :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/players/176506/matches?fiche_type=masculine
```

**Requête - Matchs contre un adversaire spécifique :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/players/176506/matches?opponent=152478
```

**Réponse :**
```json
{
  "player": {
    "licence": "176506",
    "name": "DEBESSEL CHRISTOPHER"
  },
  "count": 37,
  "matches": [
    {
      "date": "2024-12-10",
      "opponent_name": "MARTIN PIERRE",
      "opponent_licence": "152478",
      "opponent_ranking": "C4",
      "result": "V",
      "score": "3-1"
    }
  ]
}
```

---

#### GET /api/players/{licence1}/vs/{licence2}
Historique des confrontations entre deux joueurs.

**Requête :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/players/176506/vs/152478
```

**Réponse :**
```json
{
  "player1": {
    "licence": "176506",
    "name": "DEBESSEL CHRISTOPHER"
  },
  "player2": {
    "licence": "152478",
    "name": "MARTIN PIERRE"
  },
  "player1_wins": 5,
  "player2_wins": 2,
  "total_matches": 7,
  "matches": [
    {
      "date": "2024-12-10",
      "winner": "176506",
      "score": "3-1"
    },
    {
      "date": "2024-11-05",
      "winner": "176506",
      "score": "3-2"
    },
    {
      "date": "2024-09-20",
      "winner": "152478",
      "score": "3-0"
    }
  ]
}
```

---

### 🏆 Rankings

#### GET /api/rankings/top
Classement des meilleurs joueurs.

**Requête - Top 100 :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/rankings/top?limit=100
```

**Requête - Top 50 du Hainaut :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/rankings/top?province=Hainaut&limit=50
```

**Requête - Top 20 d'un club :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/rankings/top?club_code=H004&limit=20
```

**Requête - Tous les B2 :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/rankings/top?ranking=B2&limit=500
```

**Réponse :**
```json
{
  "count": 50,
  "players": [
    {
      "rank": 1,
      "licence": "100234",
      "name": "CHAMPION ELITE",
      "club_code": "H001",
      "ranking": "A",
      "points_current": 3250
    },
    {
      "rank": 2,
      "licence": "100567",
      "name": "TOPPLAYER JEAN",
      "club_code": "H012",
      "ranking": "B0",
      "points_current": 2890
    }
  ]
}
```

---

#### GET /api/rankings/progressions
Meilleures progressions de la saison.

**Requête :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/rankings/progressions?limit=50
```

**Réponse :**
```json
{
  "count": 50,
  "players": [
    {
      "licence": "198765",
      "name": "PROGRESSION RAPIDE",
      "club_code": "H004",
      "points_start": 450,
      "points_current": 720,
      "progression": 270,
      "ranking_start": "D4",
      "ranking_current": "D0"
    },
    {
      "licence": "187654",
      "name": "AMELIORATION MARIE",
      "club_code": "Li025",
      "points_start": 800,
      "points_current": 1050,
      "progression": 250,
      "ranking_start": "C6",
      "ranking_current": "C4"
    }
  ]
}
```

---

### 🔍 Recherche

#### GET /api/search
Recherche de joueurs par nom ou licence.

**Requête - Recherche par nom :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/search?q=DEBESSEL
```

**Requête - Recherche par licence :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/search?q=176506
```

**Requête - Recherche partielle :**
```
GET https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/search?q=DEB&limit=20
```

**Réponse :**
```json
{
  "query": "DEBESSEL",
  "count": 2,
  "players": [
    {
      "licence": "176506",
      "name": "DEBESSEL CHRISTOPHER",
      "club_code": "H004",
      "ranking": "C2",
      "points_current": 1285
    },
    {
      "licence": "176507",
      "name": "DEBESSEL MARIE",
      "club_code": "H004",
      "ranking": "D2",
      "points_current": 580
    }
  ]
}
```

---

### 🏓 Tournois

#### GET /api/tournaments
Liste les tournois avec filtres.

**Requete - Tous les tournois :**
```
GET /api/tournaments
```

**Requete - Filtrer par niveau :**
```
GET /api/tournaments?level=Provincial
```

**Requete - Filtrer par dates :**
```
GET /api/tournaments?date_from=01/01/2025&date_to=31/03/2025
```

**Requete - Recherche :**
```
GET /api/tournaments?search=manage&limit=50
```

**Reponse :**
```json
{
  "count": 15,
  "tournaments": [
    {
      "t_id": 6310,
      "name": "TOURNOI DE MANAGE",
      "level": "Provincial",
      "date": "15/02/2025",
      "venue": "Salle omnisports"
    }
  ]
}
```

---

#### GET /api/tournaments/levels
Liste les niveaux de tournois disponibles.

```
GET /api/tournaments/levels
```

**Reponse :**
```json
{
  "levels": ["National", "Provincial", "Regional"]
}
```

---

#### GET /api/tournaments/{id}
Detail d'un tournoi.

```
GET /api/tournaments/6310
```

---

#### GET /api/tournaments/{id}/series
Series d'un tournoi.

```
GET /api/tournaments/6310/series
```

**Reponse :**
```json
{
  "tournament": {"t_id": 6310, "name": "TOURNOI DE MANAGE"},
  "count": 4,
  "series": [
    {"series_name": "Serie A (E0-D0)", "series_type": "Individuel"},
    {"series_name": "Serie B (D2-E6)", "series_type": "Individuel"}
  ]
}
```

---

#### GET /api/tournaments/{id}/inscriptions
Inscriptions a un tournoi (filtrable par serie).

```
GET /api/tournaments/6310/inscriptions?series_name=Serie+A
```

---

#### GET /api/tournaments/{id}/results
Resultats d'un tournoi (filtrable par serie).

```
GET /api/tournaments/6310/results?series_name=Serie+A
```

---

#### POST /api/tournaments/{id}/scrape
Rescrape un tournoi (series, inscriptions, resultats).

```
POST /api/tournaments/6310/scrape
```

---

### ⚔ Interclubs

#### GET /api/interclubs/divisions
Liste les divisions interclubs.

**Requete - Filtrer par categorie :**
```
GET /api/interclubs/divisions?category=National
```

**Requete - Filtrer par genre :**
```
GET /api/interclubs/divisions?gender=Hommes
```

**Reponse :**
```json
{
  "count": 45,
  "divisions": [
    {
      "division_index": 1,
      "division_name": "Super Division Hommes",
      "division_category": "National",
      "division_gender": "Hommes"
    }
  ]
}
```

---

#### GET /api/interclubs/rankings
Classement d'une division pour une semaine.

```
GET /api/interclubs/rankings?division_index=1&week=10
```

**Reponse :**
```json
{
  "division_index": 1,
  "week": 10,
  "count": 8,
  "rankings": [
    {
      "rank": 1,
      "team_name": "ETT MANAGE A",
      "played": 10,
      "wins": 8,
      "losses": 2,
      "points": 26
    }
  ]
}
```

---

#### GET /api/interclubs/team/{team_name}/history
Evolution d'une equipe semaine par semaine.

```
GET /api/interclubs/team/ETT%20MANAGE%20A/history
```

---

#### GET /api/interclubs/search
Recherche d'equipes par nom.

```
GET /api/interclubs/search?q=MANAGE&limit=20
```

---

#### GET /api/interclubs/stats
Statistiques interclubs (divisions, equipes, semaines).

```
GET /api/interclubs/stats
```

---

### ⚙ Scraping Management

#### POST /api/scrape/all
Lance un scraping complet de tous les clubs et joueurs en arriere-plan.

```
POST /api/scrape/all?trigger=manual
```

**Reponse :**
```json
{
  "status": "started",
  "task_id": 42,
  "total_clubs": 823,
  "message": "Scraping de 823 clubs demarre en arriere-plan"
}
```

---

#### GET /api/scrape/status
Statut du scraping en cours.

```
GET /api/scrape/status
```

**Reponse :**
```json
{
  "running": true,
  "task_id": 42,
  "total_clubs": 823,
  "completed_clubs": 150,
  "total_players": 5200,
  "current_club": "H004",
  "current_province": "Hainaut",
  "progress_percent": 18.2
}
```

---

#### POST /api/scrape/cancel
Annule le scraping en cours.

```
POST /api/scrape/cancel
```

---

#### GET /api/scrape/logs/{task_id}
Logs en temps reel d'une tache de scraping.

```
GET /api/scrape/logs/42
```

---

#### GET /api/scrape/history
Historique des taches de scraping.

```
GET /api/scrape/history?limit=10
```

---

#### POST /api/scrape/tournaments
Lance le scraping de tous les tournois.

```
POST /api/scrape/tournaments
```

---

#### GET /api/scrape/tournaments/status
Statut du scraping des tournois.

```
GET /api/scrape/tournaments/status
```

---

#### POST /api/scrape/tournaments/cancel
Annule le scraping des tournois en cours.

```
POST /api/scrape/tournaments/cancel
```

---

#### POST /api/scrape/interclubs
Lance le scraping des classements interclubs.

```
POST /api/scrape/interclubs?weeks=1-5&divisions=1,2,3
```

**Parametres optionnels :**
- `weeks` : Semaines a scraper (ex: `1,2,3` ou `1-5`). Defaut: 1-22
- `divisions` : Indices de divisions (ex: `1,5,10`). Defaut: toutes
- `resume_division` + `resume_week` : Reprendre depuis un point donne

---

#### POST /api/scrape/interclubs/cancel
Annule le scraping interclubs en cours.

```
POST /api/scrape/interclubs/cancel
```

---

#### POST /api/players/{licence}/scrape
Rescrape la fiche d'un joueur individuel.

```
POST /api/players/176506/scrape
```

---

#### POST /api/scrape/refresh-clubs
Rafraichit la liste des clubs depuis le site AFTT sans scraper les joueurs.

```
POST /api/scrape/refresh-clubs
```

---

### 📊 Stats additionnelles

#### GET /api/stats/last-scrape-date
Date du dernier scraping reussi.

```
GET /api/stats/last-scrape-date
```

---

#### GET /api/stats/clubs-count
Nombre de clubs en base.

```
GET /api/stats/clubs-count
```

---

#### GET /api/stats/active-players-count
Nombre de joueurs ayant au moins un match enregistre.

```
GET /api/stats/active-players-count
```

---

#### GET /api/stats/detailed
Diagnostics detailles : matchs par type, dates recentes, top joueurs.

```
GET /api/stats/detailed
```

---

## Exemples de Code

### JavaScript (Fetch)
```javascript
const API = 'https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com';

// Stats de la base
const stats = await fetch(`${API}/api/stats`).then(r => r.json());
console.log(`${stats.clubs} clubs, ${stats.players} joueurs`);

// Clubs du Hainaut
const hainaut = await fetch(`${API}/api/clubs?province=Hainaut`).then(r => r.json());
console.log(`${hainaut.count} clubs dans le Hainaut`);

// Joueurs d'un club
const club = await fetch(`${API}/api/clubs/H004/players`).then(r => r.json());
club.players.forEach(p => console.log(`${p.name} - ${p.ranking}`));

// Recherche
const results = await fetch(`${API}/api/search?q=DEBESSEL`).then(r => r.json());

// Fiche joueur complète
const player = await fetch(`${API}/api/players/176506`).then(r => r.json());
console.log(`${player.name}: ${player.total_wins}V - ${player.total_losses}D`);

// Confrontation
const h2h = await fetch(`${API}/api/players/176506/vs/152478`).then(r => r.json());
console.log(`${h2h.player1.name} ${h2h.player1_wins} - ${h2h.player2_wins} ${h2h.player2.name}`);
```

### Python
```python
import requests

API = 'https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com'

# Stats
stats = requests.get(f'{API}/api/stats').json()
print(f"{stats['clubs']} clubs, {stats['players']} joueurs")

# Clubs du Hainaut
hainaut = requests.get(f'{API}/api/clubs', params={'province': 'Hainaut'}).json()
print(f"{hainaut['count']} clubs dans le Hainaut")

# Joueurs d'un club
club = requests.get(f'{API}/api/clubs/H004/players').json()
for p in club['players']:
    print(f"{p['name']} - {p['ranking']}")

# Recherche
results = requests.get(f'{API}/api/search', params={'q': 'DEBESSEL'}).json()

# Fiche joueur
player = requests.get(f'{API}/api/players/176506').json()
print(f"{player['name']}: {player['total_wins']}V - {player['total_losses']}D")

# Top 50 Hainaut
top = requests.get(f'{API}/api/rankings/top', params={'province': 'Hainaut', 'limit': 50}).json()
```

### cURL
```bash
# Stats
curl https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/stats

# Clubs du Hainaut
curl "https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/clubs?province=Hainaut"

# Joueurs d'un club
curl https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/clubs/H004/players

# Recherche
curl "https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/search?q=DEBESSEL"

# Fiche joueur
curl https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/players/176506

# Scraper un club (POST)
curl -X POST https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/clubs/H004/scrape

# Top 100
curl "https://lkkkwcg88c04c4g8kgw884ko.chris-ia.com/api/rankings/top?limit=100"
```

---

## Codes HTTP

| Code | Description |
|------|-------------|
| `200` | Succes |
| `400` | Parametre invalide (licence, code club) |
| `404` | Ressource non trouvee (club/joueur/tournoi inexistant) |
| `409` | Conflit (scraping deja en cours) |
| `422` | Parametres de validation invalides |
| `500` | Erreur serveur |

---

## Notes Importantes

- **CORS** : Configurable via `AFTT_CORS_ORIGINS` (defaut: `*`)
- **Scraping club** : Le POST `/api/clubs/{code}/scrape` peut prendre 30-60 secondes
- **Scraping global** : Le POST `/api/scrape/all` tourne en arriere-plan, suivre via `/api/scrape/status`
- **Annulation** : Tous les scrapings (global, tournois, interclubs) supportent l'annulation via `/cancel`
- **Cache** : Certains endpoints sont mis en cache (stats 60s, provinces 600s, niveaux tournois 600s)
- **Donnees** : Proviennent du site officiel AFTT (aftt.be et data.aftt.be)
- **Documentation interactive** : Swagger UI sur `/docs`, ReDoc sur `/redoc`

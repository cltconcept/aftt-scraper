# Documentation : Scraper Fiche Joueur AFTT

## Résumé de la demande

Étape 4-5 du projet : récupérer la fiche détaillée d'un joueur depuis :
- https://data.aftt.be/tools/fiche.php (fiche masculine)
- https://data.aftt.be/tools/fiche_women.php (fiche féminine)

**Important** : Une joueuse peut jouer en interclubs hommes ET dames, avec des points/stats différents dans chaque catégorie.

**Mise à jour** : Les matchs sont maintenant groupés par journée avec :
- Date de la rencontre
- Division (code)
- Club adverse

Tests effectués avec :
- **KEVIN BRULEZ** (152174) - Homme, fiche masculine uniquement
- **DEBORA FAUCHE** (177378) - Femme, fiches masculine ET féminine

## Solution implémentée

### Source des données

Les pages utilisent un paramètre **GET** `licenceID` :

```python
# Fiche masculine
response = requests.get("https://data.aftt.be/tools/fiche.php?licenceID=177378")

# Fiche féminine
response = requests.get("https://data.aftt.be/tools/fiche_women.php?licenceID=177378")
```

### Données extraites

| Section | Champs |
|---------|--------|
| **Identité** | licence, name, ranking |
| **Points** | points_start, points_current, points_evolution (array) |
| **Ranking** | ranking_position, ranking_position_active |
| **Stats** | stats_by_ranking (wins, losses, ratio par classement adverse) |
| **Matchs** | date, division, opponent_club, opponent_name, opponent_ranking, opponent_licence, opponent_points, score, won, points_change |
| **Méta** | last_update |

### Structure JSON

```json
{
  "licence": "177378",
  "name": "DEBORA FAUCHE",
  "ranking": "NC",
  "club_code": null,
  "fiche_type": "masculine",
  
  // Fiche masculine (interclubs hommes)
  "points_start": 100.0,
  "points_current": 34.72,
  "points_evolution": [],
  "ranking_position": 15452,
  "stats_by_ranking": [
    {"ranking": "E2", "wins": 0, "losses": 6, "ratio": 0.0},
    {"ranking": "NC", "wins": 3, "losses": 6, "ratio": 33.0}
  ],
  "total_wins": 3,
  "total_losses": 21,
  "matches": [
    {
      "date": "10/01/2026",
      "division": "PHM12/475",
      "opponent_club": "Maurage",
      "opponent_name": "SIMON MARCHIONI",
      "opponent_ranking": "NC",
      "opponent_licence": "123456",
      "opponent_points": 31.0,
      "score": "3-0",
      "won": true,
      "points_change": 7.7
    }
  ],
  
  // Fiche féminine (interclubs dames) - si applicable
  "women_stats": {
    "points_start": 100.0,
    "points_current": 90.48,
    "ranking_position": null,
    "stats_by_ranking": [...],
    "total_wins": 0,
    "total_losses": 2,
    "matches": [...]
  },
  
  "last_update": "01/01/26"
}
```

**Note** : `women_stats` n'est présent que si le joueur a des matchs en interclubs dames.

## Exemple de sortie console

```
[MATCHS] (39 total: 24V - 15D)
================================================================================

  [10/01/2026] PHM12/045 vs Palette Verte Ecaus. (4V-0D = +31.4 pts)
--------------------------------------------------------------------------------
    Score  Adversaire                Clt   Pts Adv    Gain      
--------------------------------------------------------------------------------
    3-0    SAVINO CICORIA            C4    1304       +3.4       ✓
    3-1    ROMUALD DESHAYES          C4    1321       +3.4       ✓
    3-0    DAVID BUZIN               C0    1682       +17.0      ✓
    3-1    MICHEL LARCIN             C2    1471       +7.7       ✓

  [29/11/2025] PHM10/045 vs La Villette (2V-2D = -19.6 pts)
--------------------------------------------------------------------------------
    Score  Adversaire                Clt   Pts Adv    Gain      
--------------------------------------------------------------------------------
    3-0    ANTOINE BERNARD           C6    1251       +2.5       ✓
    2-3    FREDERIC SCHMIDT          C6    1264       -13.6      ✗
    ...
```

## Résultats des tests

### Test 1 : KEVIN BRULEZ (152174) - Homme

| Champ | Fiche Masculine |
|-------|-----------------|
| Classement | C2 |
| Points départ | 1543 pts |
| Points actuels | 1485.2 pts |
| Évolution | -57.8 pts |
| Ranking | 1866e |
| Bilan | 24V - 15D (62%) |
| Journées | 10 rencontres |

*Pas de fiche féminine (aucun match en dames)*

### Test 2 : DEBORA FAUCHE (177378) - Femme

| Champ | Fiche Masculine | Fiche Féminine |
|-------|-----------------|----------------|
| Classement | NC | NC |
| Points départ | 100 pts | 100 pts |
| Points actuels | 34.72 pts | 90.48 pts |
| Évolution | -65.3 pts | -9.5 pts |
| Ranking | 15452e | - |
| Bilan | 3V - 21D (12.5%) | 0V - 2D (0%) |
| Journées | 8 rencontres | 1 rencontre |

**Observation** : Une joueuse peut avoir des points très différents entre les deux catégories car les adversaires ne sont pas les mêmes.

## Utilisation

```bash
# Via main.py
python main.py player 152174

# Directement
python -m src.scraper.player_scraper 152174
```

## Fichiers générés

- `data/player_{licence}.json` - Fiche complète du joueur

## Points techniques

### Parsing du HTML

1. **Titre (h2)** : Format `LICENCE - NOM - CLASSEMENT`
2. **Points (h3)** : Valeurs avec "pts", précédées d'un h5 label
3. **Tableau stats** : Victoires/Défaites/Ratio par classement
4. **Card headers** : Format `DATE - DIVISION - CLUB_ADVERSE`
5. **Match cards** : Nom (h6), classement (small), points (small), score (h5), gain (badge), licence (input hidden)
6. **Graphique** : Données dans un script JavaScript

### Structure HTML des matchs

```html
<div class="card-header">
  10/01/2026 - PHM12/045 - Palette Verte Ecaus.Total : +31.45 pts
</div>
<div class="match-card">
  <h6><form><input name="licence" value="101452"/><button>SAVINO CICORIA</button></form></h6>
  <small>C4</small>
  <small>1303.76 pts</small>
  <h5 class="fw-bold">3-0</h5>
  <span class="badge">+3.4 pts</span>
</div>
```

### Gestion des erreurs

- La page retourne des erreurs PHP si la licence est invalide
- Vérification de la présence du nom pour valider les données

## Prochaines étapes

1. ✅ Scraper la liste des clubs (663 clubs)
2. ✅ Scraper les membres d'un club
3. ✅ Scraper les informations détaillées du club
4. ✅ Scraper la fiche d'un joueur (masculine)
5. ✅ Scraper la fiche féminine (si applicable)
6. ✅ Matchs groupés par journée (date, division, club)
7. ✅ Interface web pour visualiser les données
8. ⬜ Scraper tous les joueurs d'un club
9. ⬜ Stocker dans une base de données (PostgreSQL/SQLite)
10. ⬜ Créer une API pour exposer les données

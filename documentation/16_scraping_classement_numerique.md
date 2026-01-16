# Scraping du classement numérique

## Résumé de la demande

L'utilisateur a signalé que des joueurs manquaient dans la liste des membres d'un club, notamment DEBESSEL CHRISTOPHER (176506) qui apparaissait sur le site AFTT mais pas dans les données scrapées.

## Problème identifié

### Deux sources de données différentes

| Source | URL | Contenu |
|--------|-----|---------|
| **Annuaire** | `data.aftt.be/annuaire/membres.php` | Joueurs **actifs** uniquement |
| **Classement numérique** | `data.aftt.be/ranking/clubs.php` | **Tous** les joueurs (actifs + inactifs) |

Le scraper original utilisait uniquement l'annuaire, qui ne contient que les joueurs actifs. Les joueurs inactifs (comme DEBESSEL CHRISTOPHER) n'apparaissaient pas.

### Difficulté technique

La page de classement numérique charge ses données via **JavaScript** (MDB Datatables). Un simple `requests.get()` ne récupère pas les données - il faut rendre le JavaScript.

## Solution implémentée

### 1. Nouveau scraper `ranking_scraper.py`

**Fichier** : `src/scraper/ranking_scraper.py`

Utilise **Playwright** pour :
1. Charger la page de classement
2. Sélectionner le club via JavaScript
3. Attendre le rendu des données
4. Parser le HTML généré

**Fonction principale** :
```python
def get_club_ranking_players(club_code: str, timeout: int = 30000) -> Dict:
    """
    Récupère tous les joueurs d'un club depuis le classement numérique.
    
    Returns:
        Dict avec 'players_men' et 'players_women'
    """
```

**Données extraites par joueur** :
- `licence` : Numéro de licence
- `name` : Nom du joueur
- `ranking` : Classement (NC, E6, C2, etc.)
- `points` : Points actuels
- `matches` : Nombre de matchs joués
- `position` : Position dans le classement (avec inactifs)
- `position_active` : Position sans les inactifs (None si inactif)
- `is_active` : Si le joueur est actif

### 2. Intégration dans l'API

**Endpoint modifié** : `POST /api/clubs/{code}/scrape`

**Nouveau paramètre** : `include_ranking` (défaut: `true`)

**Comportement** :
1. Scrape l'annuaire (pour les infos du club et les catégories)
2. Scrape le classement numérique (pour tous les joueurs)
3. Fusionne les deux sources
4. Scrape les fiches individuelles de tous les joueurs

**Réponse enrichie** :
```json
{
    "success": true,
    "club_code": "H004",
    "members_from_annuaire": 99,
    "members_from_ranking": 99,
    "total_players": 99,
    "players_scraped": 95,
    "players_errors": [...],
    "message": "Scraping terminé: 99 joueurs (99 annuaire + 99 ranking), 95 fiches"
}
```

## Points techniques importants

### Utilisation de Playwright

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # Charger la page
    page.goto(url)
    page.wait_for_load_state('networkidle')
    
    # Sélectionner le club via JavaScript
    page.evaluate("""
        () => {
            const select = document.getElementById('clubSelect');
            select.value = 'H004';
            select.dispatchEvent(new Event('change', { bubbles: true }));
            select.form.submit();
        }
    """)
    
    # Attendre le rechargement
    page.wait_for_load_state('networkidle')
    
    # Récupérer le HTML rendu
    html = page.content()
```

### Parsing des datatables

La page utilise MDB Datatables avec cette structure :
- `#datatable-messieurs` : Tableau des joueurs messieurs
- `#datatable-dames` : Tableau des joueuses

Colonnes :
| Index | Contenu |
|-------|---------|
| 0 | Position (avec inactifs) |
| 1 | Position sans inactifs ou "Inactive" |
| 2 | Nom |
| 3 | Classement |
| 4 | Club |
| 5 | Matchs |
| 6 | Points |
| 7 | Action (lien avec licence) |

### Extraction de la licence

La licence est dans le lien "Voir fiche" :
```html
<a href="../tools/fiche.php?licenceID=152174">Voir fiche</a>
```

## Résultats

### Test H004

| Source | Joueurs |
|--------|---------|
| Annuaire seul | 99 |
| Classement numérique | 83 messieurs + 16 dames = 99 |
| **Dont DEBESSEL** | ✅ Trouvé (176506) |

### Joueurs inactifs détectés

Sur 83 joueurs messieurs :
- 62 actifs
- 21 inactifs (dont DEBESSEL THEO)

## Dépendances ajoutées

- `playwright` : Pour le rendu JavaScript
- Installation : `pip install playwright && playwright install chromium`

## Fichiers modifiés/créés

- `src/scraper/ranking_scraper.py` : Nouveau scraper pour le classement numérique
- `src/api/app.py` : Intégration du nouveau scraper dans l'endpoint `/api/clubs/{code}/scrape`

## Notes

- Le scraping du classement prend environ 6-7 secondes (chargement de la page + rendu JS)
- Playwright nécessite un navigateur Chromium installé
- Le paramètre `include_ranking=false` permet de désactiver le scraping du classement si nécessaire

# Documentation : Scraper des Membres et Infos Club AFTT

## Résumé de la demande

Étapes 2 et 3 du projet :
- Récupérer la liste des membres d'un club de tennis de table
- Récupérer les informations détaillées du club (contact, local, équipes, labels)

Test effectué avec le club H004 - Le Centre.

## Solution implémentée

### Source des données

La page `https://data.aftt.be/annuaire/membres.php` utilise un formulaire **POST** avec le paramètre `indice`.

**Important** : Ce n'est PAS une requête GET avec `?club=` mais un POST avec `indice=`

```python
# Correct
response = requests.post(url, data={'indice': 'H004'})

# Incorrect (ne fonctionne pas)
response = requests.get(url + '?club=H004')
```

### Architecture mise à jour

```
AFFT/
├── src/
│   ├── __init__.py
│   └── scraper/
│       ├── __init__.py
│       ├── clubs_scraper.py      # Scraping des clubs
│       └── members_scraper.py    # Scraping des membres (NEW)
├── data/
│   ├── clubs.json
│   └── members_H004.json         # Membres du club H004
├── documentation/
│   ├── 01_clubs_scraper.md
│   └── 02_members_scraper.md     # Cette documentation
├── main.py                        # Point d'entrée mis à jour
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

### Structure des données extraites

Le fichier JSON contient maintenant :

```json
{
  "club_code": "H004",
  "club_name": "Le Centre",
  "club_info": {
    "code": "H004",
    "name": "Le Centre",
    "full_name": "H004 - ETT CENTRE MANAGE",
    "email": "vincent.tondeur1970@gmail.com",
    "phone": "0494-578013",
    "status": "ASBL",
    "website": null,
    "has_shower": true,
    "venue_name": "CENTRE CULTUREL ET SPORTIF DU SCAILMONT",
    "venue_address": "Avenue du Scailmont, 96 - 7170 Manage",
    "venue_phone": "0494/578013",
    "venue_pmr_access": true,
    "venue_remarks": "Sortie Manage sur autoroute E42",
    "teams_men": 12,
    "teams_women": 3,
    "teams_youth": 0,
    "teams_veterans": 0,
    "label": null,
    "palette": null
  },
  "members": [
    {
      "licence": "152174",
      "name": "KEVIN BRULEZ",
      "category": "SEN",
      "ranking": "C2",
      "club_code": "H004",
      "gender": null
    },
    ...
  ]
}
```

### Informations du club extraites

| Section | Champs |
|---------|--------|
| **Général** | full_name, email, phone, status, website, has_shower |
| **Local** | venue_name, venue_address, venue_phone, venue_pmr_access, venue_remarks |
| **Équipes** | teams_men, teams_women, teams_youth, teams_veterans |
| **Labels** | label, palette |

### Catégories de joueurs

| Code | Description |
|------|-------------|
| SEN | Senior |
| V40 | Vétéran 40+ |
| V50 | Vétéran 50+ |
| V60 | Vétéran 60+ |
| V65 | Vétéran 65+ |
| V70 | Vétéran 70+ |
| V75 | Vétéran 75+ |
| JUN | Junior |
| J19 | Junior U19 |
| CAD | Cadet |
| MIN | Minime |
| PRE | Préminime |
| BEN | Benjamin |

### Classements

Les classements vont de A0 (meilleur) à NC (non classé) :
- **Série A** : A0, A2, A4, A6
- **Série B** : B0, B2, B4, B6
- **Série C** : C0, C2, C4, C6
- **Série D** : D0, D2, D4, D6
- **Série E** : E0, E2, E4, E6
- **NC** : Non classé

## Utilisation

### Commandes disponibles

```bash
# Scraper un club spécifique
python main.py members H004

# Scraper tous les clubs (à venir)
python main.py members all

# Scraper uniquement la liste des clubs
python main.py clubs
```

### Exécution directe du module

```bash
python -m src.scraper.members_scraper H004
```

## Résultats du test avec H004 - Le Centre

### Informations du club

| Champ | Valeur |
|-------|--------|
| Nom complet | ETT CENTRE MANAGE |
| Email | vincent.tondeur1970@gmail.com |
| Téléphone | 0494-578013 |
| Statut | ASBL |
| Douche | Oui |
| Local | CENTRE CULTUREL ET SPORTIF DU SCAILMONT |
| Adresse | Avenue du Scailmont, 96 - 7170 Manage |
| Accès PMR | Oui |
| Remarques | Sortie Manage sur autoroute E42 |

### Équipes

| Type | Nombre |
|------|--------|
| Messieurs | 12 |
| Dames | 3 |
| Jeunes | 0 |
| Vétérans | 0 |
| **TOTAL** | **15 équipes** |

### Membres par catégorie

| Catégorie | Nombre |
|-----------|--------|
| SEN (Senior) | 24 |
| V50 | 18 |
| V40 | 11 |
| BEN | 3 |
| JUN | 3 |
| MIN | 3 |
| PRE | 3 |
| V60 | 3 |
| CAD | 2 |
| V65 | 2 |
| V70 | 2 |
| V80 | 1 |
| **TOTAL** | **75 membres** |

## Points techniques importants

### Parsing du tableau

1. La page contient un seul tableau HTML avec les colonnes :
   - Position | Licence | Nom | Catégorie | Classement

2. Le scraper détecte automatiquement le format (avec ou sans colonne Position)

3. Validation des données :
   - La licence doit contenir au moins un chiffre
   - Le nom ne doit pas être vide

### Gestion des erreurs

- Timeout de 30 secondes
- Si aucun membre trouvé, sauvegarde du HTML pour debug
- Logging détaillé des étapes

## Prochaines étapes

1. ✅ Scraper la liste des clubs (531 clubs)
2. ✅ Scraper les membres d'un club
3. ✅ Scraper les informations détaillées du club
4. ⬜ Scraper tous les clubs automatiquement
5. ⬜ Stocker dans une base de données (PostgreSQL/SQLite)
6. ⬜ Créer une API pour exposer les données

# Documentation : Scraper des Clubs AFTT

## Résumé de la demande

L'utilisateur souhaite créer un script Python pour construire une base de données des clubs de tennis de table belges. La première étape consiste à récupérer la liste de tous les clubs depuis la page https://data.aftt.be/interclubs/rankings.php.

Le script doit être exécutable via Coolify sur un VPS.

## Solution implémentée

### Architecture

```
AFFT/
├── src/
│   ├── __init__.py
│   └── scraper/
│       ├── __init__.py
│       └── clubs_scraper.py    # Script principal de scraping
├── data/                        # Données extraites (JSON)
├── documentation/               # Documentation du projet
├── main.py                      # Point d'entrée
├── requirements.txt             # Dépendances Python
├── Dockerfile                   # Image Docker pour Coolify
├── docker-compose.yml           # Configuration Docker Compose
└── .gitignore
```

### Fonctionnalités du scraper

1. **Récupération HTTP** : Utilise `requests` avec des headers appropriés pour éviter le blocage
2. **Parsing HTML** : Utilise `BeautifulSoup` pour parser le HTML et extraire les options du `<select>`
3. **Extraction des données** :
   - Code du club (ex: `A003`)
   - Nom du club (ex: `Salamander`)
   - Province déduite du code (ex: `Antwerpen`)
4. **Export JSON** : Sauvegarde des données dans `data/clubs.json`

### Structure des données extraites

Chaque club est représenté par :

```json
{
  "code": "A003",
  "name": "Salamander",
  "province": "Antwerpen"
}
```

### Provinces/Régions identifiées

| Préfixe | Province/Région |
|---------|-----------------|
| A | Antwerpen (Anvers) |
| BBW | Brabant Wallon / Bruxelles |
| H | Hainaut |
| L | Liège |
| Lx | Luxembourg |
| N | Namur |
| OVL | Oost-Vlaanderen |
| Vl-B | Vlaams-Brabant |
| WVL | West-Vlaanderen |

## Points techniques importants

### Dépendances

- `requests==2.31.0` : Requêtes HTTP
- `beautifulsoup4==4.12.3` : Parsing HTML
- `lxml==5.1.0` : Parser rapide pour BeautifulSoup

### Exécution

**Localement :**
```bash
pip install -r requirements.txt
python main.py
```

**Via Docker :**
```bash
docker-compose up --build
```

**Via Coolify :**
1. Connecter le repository Git
2. Coolify détectera automatiquement le `Dockerfile`
3. Le conteneur s'exécutera et sauvegardera les données dans `/app/data`

### Gestion des erreurs

- Timeout de 30 secondes pour les requêtes HTTP
- Logging détaillé des étapes
- Gestion des exceptions avec messages explicites

### Output

Le script génère :
1. Un fichier `data/clubs.json` contenant tous les clubs
2. Un résumé dans la console avec le nombre de clubs par province

## Prochaines étapes possibles

1. Stocker les données dans une vraie base de données (PostgreSQL, SQLite)
2. Récupérer les équipes de chaque club
3. Récupérer les classements des joueurs
4. Créer une API pour exposer les données

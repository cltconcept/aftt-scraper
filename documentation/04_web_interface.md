# AFTT Data Explorer - Interface Web

## Résumé de la demande
Création d'une page HTML permettant d'afficher et naviguer dans les données JSON générées par les scrapers AFTT.

## Solution implémentée

### Architecture
- **`web/index.html`** : Interface utilisateur complète en HTML/CSS/JavaScript vanilla
- **`web/server.py`** : Serveur HTTP Python pour servir les fichiers et exposer une API

### Fonctionnalités

#### 1. Navigation par sections
- **Clubs** : Liste de tous les clubs avec recherche
- **Membres** : Liste des membres d'un club
- **Joueurs** : Fiches détaillées des joueurs
- **Importer** : Zone de drag & drop pour charger les JSON

#### 2. Recherche et filtres
- Recherche instantanée dans chaque section
- Filtrage par nom, code, licence, classement, etc.

#### 3. Panneau de détails
- Vue détaillée de chaque élément (club, joueur)
- Statistiques, matchs, évolution des points
- Visualisation JSON brute avec coloration syntaxique

#### 4. Chargement des données
**Méthode 1 - Import manuel :**
- Glisser-déposer des fichiers JSON
- Support de `clubs.json`, `members_*.json`, `player_*.json`

**Méthode 2 - Chargement automatique via API :**
- Le serveur Python expose une API REST
- Les données sont chargées automatiquement au démarrage

### Points techniques

#### Design
- Interface moderne avec thème sombre
- Animations fluides et micro-interactions
- Responsive design (mobile-friendly)
- Coloration syntaxique JSON avec `JetBrains Mono`

#### API REST (server.py)
```
GET /api/list           → Liste les fichiers disponibles
GET /api/clubs          → Retourne clubs.json
GET /api/members/{code} → Retourne members_{code}.json
GET /api/player/{id}    → Retourne player_{id}.json
```

#### Structure des données attendues
```javascript
// clubs.json
[{ code: "H004", name: "Le Centre", province: "Hainaut" }, ...]

// members_H004.json
{
    club_code: "H004",
    club_name: "Le Centre",
    members: [{ licence: "152174", name: "BRULEZ KEVIN", ranking: "B2", category: "S" }, ...],
    club_info: { /* détails du club */ }
}

// player_152174.json
{
    licence: "152174",
    name: "BRULEZ KEVIN",
    ranking: "B2",
    points_start: 1234.5,
    points_current: 1345.6,
    matches: [...],
    women_stats: { /* si applicable */ }
}
```

## Utilisation

### Lancement du serveur
```bash
cd web
python server.py
```
Puis ouvrir http://localhost:8080

### Ouverture directe du fichier HTML
Ouvrir `web/index.html` dans un navigateur et utiliser l'import manuel pour charger les fichiers JSON.

## Dépendances
- Aucune dépendance externe
- HTML/CSS/JavaScript vanilla
- Python standard library (http.server, json, os)

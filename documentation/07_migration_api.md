# Migration vers l'API FastAPI

## Résumé de la demande

L'utilisateur a demandé de :
1. Supprimer la section "Importer" de l'interface web car les données sont maintenant dans la base de données
2. Vérifier que les données sont bien dans la base de données
3. Supprimer les fichiers JSON qui ne sont plus utilisés

## Solution implémentée

### 1. Suppression de la section "Importer"

**Fichier modifié** : `web/index.html`

**Modifications** :
- Suppression du bouton "Importer" dans le menu de navigation
- Suppression de la section HTML `<section id="upload-section">` avec le formulaire d'upload
- Suppression du code JavaScript de gestion des fichiers uploadés :
  - Fonction `handleFiles()`
  - Fonction `processFile()`
  - Event listener sur `file-input`

### 2. Migration vers l'API FastAPI

**Fichier modifié** : `web/index.html`

**Modifications** :
- Ajout de la constante `API_BASE_URL = 'http://localhost:8000'`
- Modification de la fonction `loadFromAPI()` pour utiliser l'API FastAPI :
  - `/api/clubs` pour charger les clubs (retourne `{count, clubs}`)
  - `/api/players` pour charger les joueurs (retourne `{count, players}`)
  - `/api/clubs/{code}/players` pour charger les joueurs d'un club
- Adaptation du code pour gérer le format de réponse de l'API :
  - Les clubs sont dans `clubsData.clubs`
  - Les joueurs sont dans `playersData.players`
- Modification de `showClubDetail()` pour charger les joueurs depuis l'API
- Modification de `renderMembers()` pour charger depuis l'API au lieu des fichiers JSON
- Modification de `showPlayerDetail()` pour charger les données complètes depuis l'API si nécessaire
- Adaptation pour utiliser les champs de l'API :
  - `stats_masculine` au lieu de `stats_by_ranking`
  - `matches_masculine` au lieu de `matches`
  - `stats_feminine` et `matches_feminine` pour les données féminines

### 3. Suppression des fichiers JSON

**Fichiers supprimés** :
- `data/clubs.json`
- `data/members_H004.json`
- `data/player_152174.json`
- `data/player_177378.json`

**Note** : Les fichiers de debug HTML (`debug_*.html`) ont été conservés car ils peuvent être utiles pour le développement.

## Points techniques importants

### Structure des données de l'API

1. **Clubs** :
   ```json
   {
     "count": 123,
     "clubs": [...]
   }
   ```

2. **Joueurs** :
   ```json
   {
     "count": 456,
     "players": [...]
   }
   ```

3. **Joueur complet** :
   ```json
   {
     "licence": "152174",
     "name": "...",
     "stats_masculine": [...],
     "matches_masculine": [...],
     "stats_feminine": [...],
     "matches_feminine": [...]
   }
   ```

### Chargement des données

- **Au démarrage** : Les clubs et les premiers 500 joueurs sont chargés automatiquement
- **À la demande** : Les données complètes d'un joueur sont chargées quand on ouvre sa fiche
- **Par club** : Les joueurs d'un club sont chargés quand on consulte les membres

### Gestion des erreurs

- Messages d'erreur adaptés pour indiquer que l'API doit être démarrée
- Gestion gracieuse des erreurs de connexion
- Messages informatifs dans la console

## Prérequis

Pour que l'interface fonctionne correctement :

1. **Base de données** : Les données doivent être importées dans la base SQLite
   ```bash
   python main.py import
   ```

2. **API FastAPI** : L'API doit être démarrée
   ```bash
   python main.py api
   ```

3. **Interface web** : Le serveur web doit être démarré
   ```bash
   python web/server.py
   ```

## Fichiers modifiés

- `web/index.html` : Migration complète vers l'API FastAPI
- `data/*.json` : Fichiers JSON supprimés (sauf fichiers de debug)

## Compatibilité

- L'interface nécessite maintenant que l'API FastAPI soit démarrée
- Les données sont chargées dynamiquement depuis la base de données via l'API
- Plus besoin de fichiers JSON locaux
- Meilleure performance grâce à la pagination et au chargement à la demande

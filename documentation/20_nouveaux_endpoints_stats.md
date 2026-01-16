# Nouveaux Endpoints de Statistiques

## Résumé de la demande

L'utilisateur a demandé la création de 3 nouveaux endpoints pour récupérer des statistiques importantes :
1. Date du dernier scrap réussi
2. Nombre total de clubs
3. Nombre total de joueurs actifs

## Solution implémentée

### 1. Fonctions de requêtes (`src/database/queries.py`)

Trois nouvelles fonctions ont été ajoutées dans le module `queries.py` :

#### `get_last_scrape_date()`
- **Description** : Récupère la date du dernier scrap réussi depuis la table `scrape_tasks`
- **Logique** : 
  - Recherche la dernière tâche avec `status = 'success'`
  - Retourne `finished_at` si disponible, sinon `started_at`
  - Retourne `None` si aucun scrap réussi n'existe
- **Retour** : `Optional[str]` - Date au format ISO ou None

#### `get_clubs_count()`
- **Description** : Compte le nombre total de clubs dans la base de données
- **Logique** : Simple `COUNT(*)` sur la table `clubs`
- **Retour** : `int` - Nombre de clubs

#### `get_active_players_count()`
- **Description** : Compte le nombre de joueurs actifs
- **Logique** : 
  - Un joueur est considéré comme actif s'il a des points actuels (`points_current IS NOT NULL`) OU un classement (`ranking IS NOT NULL`)
  - Cela permet d'inclure tous les joueurs qui ont des données de performance
- **Retour** : `int` - Nombre de joueurs actifs

### 2. Endpoints API (`src/api/app.py`)

Trois nouveaux endpoints ont été ajoutés dans la section "Stats" :

#### `GET /api/stats/last-scrape-date`
- **Description** : Retourne la date du dernier scrap réussi
- **Réponse** :
  ```json
  {
    "last_scrape_date": "2024-01-15 10:30:00"
  }
  ```
  Ou si aucun scrap n'existe :
  ```json
  {
    "last_scrape_date": null,
    "message": "Aucun scrap réussi trouvé"
  }
  ```

#### `GET /api/stats/clubs-count`
- **Description** : Retourne le nombre total de clubs
- **Réponse** :
  ```json
  {
    "clubs_count": 250
  }
  ```

#### `GET /api/stats/active-players-count`
- **Description** : Retourne le nombre total de joueurs actifs
- **Réponse** :
  ```json
  {
    "active_players_count": 5000
  }
  ```

## Points techniques importants

### Définition d'un joueur actif

Un joueur est considéré comme actif s'il répond à au moins un de ces critères :
- A des points actuels (`points_current IS NOT NULL`)
- A un classement (`ranking IS NOT NULL`)

Cette définition permet d'inclure tous les joueurs qui ont des données de performance, même s'ils n'ont pas encore de points calculés mais ont un classement.

### Gestion de la date du dernier scrap

La fonction `get_last_scrape_date()` utilise une logique robuste :
- Priorise `finished_at` (date de fin) si disponible
- Utilise `started_at` (date de début) en fallback
- Trie par date décroissante pour obtenir le plus récent
- Filtre uniquement les tâches avec `status = 'success'`

### Performance

Toutes les requêtes sont optimisées :
- Utilisation d'index existants sur les tables
- Requêtes simples avec `COUNT(*)` pour les comptages
- Requête avec `LIMIT 1` pour la date du dernier scrap

## Utilisation

### Exemples de requêtes

```bash
# Récupérer la date du dernier scrap
curl http://localhost:8000/api/stats/last-scrape-date

# Récupérer le nombre de clubs
curl http://localhost:8000/api/stats/clubs-count

# Récupérer le nombre de joueurs actifs
curl http://localhost:8000/api/stats/active-players-count
```

### Intégration dans le frontend

Ces endpoints peuvent être utilisés pour afficher des statistiques sur un tableau de bord :

```javascript
// Exemple d'utilisation avec fetch
const stats = await Promise.all([
  fetch('/api/stats/last-scrape-date').then(r => r.json()),
  fetch('/api/stats/clubs-count').then(r => r.json()),
  fetch('/api/stats/active-players-count').then(r => r.json())
]);

console.log('Dernier scrap:', stats[0].last_scrape_date);
console.log('Clubs:', stats[1].clubs_count);
console.log('Joueurs actifs:', stats[2].active_players_count);
```

## Fichiers modifiés

1. **src/database/queries.py**
   - Ajout de `get_last_scrape_date()`
   - Ajout de `get_clubs_count()`
   - Ajout de `get_active_players_count()`

2. **src/api/app.py**
   - Ajout de `GET /api/stats/last-scrape-date`
   - Ajout de `GET /api/stats/clubs-count`
   - Ajout de `GET /api/stats/active-players-count`

## Tests recommandés

1. Vérifier que les endpoints retournent les bonnes valeurs
2. Tester le cas où aucun scrap n'existe encore
3. Vérifier que le comptage des joueurs actifs correspond aux attentes
4. Tester avec une base de données vide

## Notes

- Tous les endpoints sont dans le tag "Stats" pour une organisation cohérente
- Les endpoints suivent le même format de réponse que les autres endpoints de l'API
- La documentation Swagger/OpenAPI sera automatiquement mise à jour grâce aux docstrings FastAPI

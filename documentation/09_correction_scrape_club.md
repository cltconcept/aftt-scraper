# Correction de l'endpoint de scraping d'un club

## Résumé de la demande

L'utilisateur a signalé une erreur 500 lors du clic sur un club. L'erreur se produisait dans l'endpoint `/api/clubs/{code}/scrape` qui tentait d'utiliser des fichiers JSON intermédiaires qui n'étaient plus nécessaires.

## Problème identifié

L'endpoint `/api/clubs/{code}/scrape` utilisait encore l'ancienne méthode avec fichiers JSON :
- `save_members_to_json()` pour sauvegarder les membres
- `import_members()` pour importer depuis le JSON
- `save_player_to_json()` pour sauvegarder chaque joueur
- `import_player()` pour importer depuis le JSON

Cette approche était :
- Plus lente (écriture/lecture de fichiers)
- Plus fragile (gestion des fichiers temporaires)
- Incohérente avec l'endpoint de scraping de province qui importe directement

## Solution implémentée

### Modification de l'endpoint `/api/clubs/{code}/scrape`

**Fichier modifié** : `src/api/app.py`

**Modifications** :
1. **Import direct des membres** : Les membres sont maintenant insérés directement dans la base avec `queries.insert_player()`
2. **Import direct des joueurs** : Les données des joueurs sont insérées directement avec `queries.insert_player()`
3. **Import direct des matchs** : Les matchs sont insérés directement avec `queries.insert_match()`
4. **Import direct des statistiques** : Les statistiques sont insérées directement avec `queries.insert_player_stat()`

### Code modifié

**Avant** :
```python
# Sauvegarder en JSON
members_json_path = save_members_to_json(members_data, code, data_dir)
# Importer dans la base
import_members(members_json_path)
```

**Après** :
```python
# Importer les membres directement dans la base
for member in members_data.get('members', []):
    player_data = {
        'licence': member.get('licence'),
        'name': member.get('name'),
        'club_code': code,
        'ranking': member.get('ranking'),
        'category': member.get('category'),
    }
    queries.insert_player(player_data)
```

**Avant** :
```python
# Scraper la fiche du joueur
player_data = get_player_info(licence)
# Sauvegarder en JSON
player_json_path = os.path.join(data_dir, f'player_{licence}.json')
with open(player_json_path, 'w', encoding='utf-8') as f:
    json.dump(player_data, f, ensure_ascii=False, indent=2)
# Importer dans la base
import_player(player_json_path)
```

**Après** :
```python
# Scraper la fiche du joueur
player_info = get_player_info(licence)
# Préparer les données du joueur
player_data = {
    'licence': licence,
    'name': player_info.get('name'),
    'club_code': code,
    'ranking': player_info.get('ranking'),
    # ... autres champs
}
# Insérer/mettre à jour le joueur
queries.insert_player(player_data)
# Insérer les matchs
for match in player_info.get('matches', []):
    queries.insert_match({
        **match,
        'player_licence': licence,
        'fiche_type': 'masculine'
    })
# Insérer les statistiques
for stat in player_info.get('stats_by_ranking', []):
    queries.insert_player_stat({
        **stat,
        'player_licence': licence,
        'fiche_type': 'masculine'
    })
```

## Points techniques importants

### Structure des données retournées par `get_player_info()`

La fonction `get_player_info()` retourne un dictionnaire avec :
- **Données masculines** :
  - `matches` : Liste des matchs masculins
  - `stats_by_ranking` : Statistiques par classement adverse
  - `points_start`, `points_current`, `total_wins`, `total_losses`, etc.

- **Données féminines** (si présentes) :
  - `women_stats` : Dictionnaire contenant :
    - `matches` : Liste des matchs féminins
    - `stats_by_ranking` : Statistiques par classement adverse
    - `points_start`, `points_current`, `total_wins`, `total_losses`, etc.

### Gestion des erreurs

- Les erreurs de scraping d'un joueur individuel sont capturées et ajoutées à `players_errors`
- Le processus continue pour les autres joueurs même si un échoue
- Les erreurs sont retournées dans la réponse pour information

### Mise à jour du club

L'endpoint met également à jour les informations du club dans la base de données si `club_info` est présent dans les données scrapées.

## Avantages de la nouvelle approche

1. **Performance** : Plus rapide car pas d'écriture/lecture de fichiers
2. **Simplicité** : Moins de code, moins de dépendances
3. **Cohérence** : Même approche que l'endpoint de scraping de province
4. **Fiabilité** : Moins de points de défaillance (pas de gestion de fichiers)

## Fichiers modifiés

- `src/api/app.py` : Modification de l'endpoint `/api/clubs/{code}/scrape`

## Prérequis

- Les fonctions `queries.insert_player()`, `queries.insert_match()`, et `queries.insert_player_stat()` doivent être disponibles
- La fonction `get_club_members()` doit retourner les données au format attendu
- La fonction `get_player_info()` doit retourner les données au format attendu

## Notes

- Les fichiers JSON temporaires ne sont plus créés lors du scraping d'un club
- L'endpoint est maintenant cohérent avec l'endpoint de scraping de province
- Les erreurs sont mieux gérées et rapportées

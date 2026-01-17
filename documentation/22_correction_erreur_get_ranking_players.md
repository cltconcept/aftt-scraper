# Correction de l'erreur 'str' object has no attribute 'get' dans le scraping

## Résumé du problème

Lors du scraping automatique des clubs, 608 erreurs étaient générées avec le message `'str' object has no attribute 'get'`. Toutes les erreurs provenaient du traitement des données du classement numérique (`ranking_scraper`).

## Cause du problème

Dans `src/api/app.py`, la fonction `run_full_scrape` appelait `get_club_ranking_players_async()` qui retourne un **dictionnaire** avec la structure suivante :

```python
{
    'club_code': 'H004',
    'players_men': [...],  # Liste de dictionnaires
    'players_women': [...]  # Liste de dictionnaires
}
```

Mais le code itérait directement sur ce dictionnaire :

```python
ranking_players = await get_club_ranking_players_async(code)

if ranking_players:
    for player in ranking_players:  # ❌ Ici, on itère sur les clés du dict !
        player_data = {
            'licence': player.get('licence'),  # ❌ player est une string ('players_men', 'club_code', etc.)
            ...
        }
```

Quand on itère sur un dictionnaire en Python avec `for player in ranking_players`, on itère sur les **clés** (qui sont des strings), pas sur les valeurs. Donc `player` devenait `'players_men'`, `'club_code'`, etc., et appeler `.get()` sur une string générait l'erreur `'str' object has no attribute 'get'`.

## Solution implémentée

### Correction dans `src/api/app.py`

1. **Combiner les listes de joueurs** : Extraire et combiner les listes `players_men` et `players_women` du dictionnaire retourné.

2. **Vérification de type** : Ajouter une vérification pour s'assurer que chaque élément est bien un dictionnaire avant d'appeler `.get()`.

```python
# Scraper depuis la page ranking
ranking_data = await get_club_ranking_players_async(code)

if ranking_data:
    # Combiner les joueurs messieurs et dames
    all_ranking_players = []
    if isinstance(ranking_data, dict):
        all_ranking_players.extend(ranking_data.get('players_men', []))
        all_ranking_players.extend(ranking_data.get('players_women', []))
    
    for player in all_ranking_players:
        if isinstance(player, dict):  # ✅ Vérification de type
            player_data = {
                'licence': player.get('licence'),
                'name': player.get('name', ''),
                'club_code': code,
                'ranking': player.get('ranking'),
                'points_current': player.get('points')
            }
            if player_data['licence']:
                queries.insert_player(player_data)
    total_players += len(all_ranking_players)
```

### Amélioration pour les membres

Ajout d'une vérification similaire pour les membres pour éviter des erreurs similaires :

```python
if members_list:
    for member in members_list:
        # Vérifier que member est un dictionnaire
        if not isinstance(member, dict):
            continue
        player_data = {
            'licence': member.get('licence'),
            ...
        }
```

## Impact

- **Avant** : 608 erreurs sur 608 clubs (100% d'erreurs)
- **Après** : Les joueurs du classement numérique sont correctement traités et insérés en base de données

## Fichiers modifiés

- `src/api/app.py` : Correction de la boucle de traitement des joueurs du classement numérique

## Tests recommandés

1. Lancer un scraping complet sur quelques clubs pour vérifier que les erreurs ont disparu
2. Vérifier que les joueurs du classement numérique sont bien insérés en base de données
3. Vérifier que le compteur `total_players` est correct

## Notes techniques

- La fonction `get_club_ranking_players_async()` retourne toujours un dictionnaire avec `players_men` et `players_women`
- Les listes peuvent être vides si aucun joueur n'est trouvé pour un club
- La vérification `isinstance(player, dict)` protège contre les cas où la structure des données serait inattendue

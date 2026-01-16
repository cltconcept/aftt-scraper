# Correction des joueurs sans nom

## Résumé de la demande

L'utilisateur a signalé que des joueurs apparaissaient sans nom dans la liste des membres d'un club, et que certains joueurs manquaient.

## Problèmes identifiés

### Problème 1 : Regex ne gérant pas les joueurs sans classement

La page fiche d'un joueur sur le site AFTT affiche le format :
- Avec classement : `152174 - KEVIN BRULEZ - C2`
- Sans classement : `151410 - LUCAS MENIER -` (notez le tiret final sans valeur)

Le regex original :
```python
match = re.match(r'(\d+)\s+-\s+(.+)\s+-\s+(\w+)$', h2_text)
```

Ce regex exigeait un mot (`\w+`) après le dernier tiret, ce qui excluait les joueurs sans classement (nouveaux joueurs ou joueurs n'ayant pas encore joué de matchs officiels).

### Problème 2 : Écrasement du nom valide par une chaîne vide

La fonction `insert_player()` dans `queries.py` écrasait le nom existant même si le nouveau nom était une chaîne vide :
```sql
name = excluded.name,  -- Écrase même avec ''
```

## Solutions implémentées

### 1. Correction du regex dans `player_scraper.py`

**Fichier** : `src/scraper/player_scraper.py`

**Avant** :
```python
match = re.match(r'(\d+)\s+-\s+(.+)\s+-\s+(\w+)$', h2_text)
if match:
    player.licence = match.group(1)
    player.name = match.group(2).strip()
    player.ranking = match.group(3)
```

**Après** :
```python
# Essayer d'abord le format avec classement
match = re.match(r'(\d+)\s+-\s+(.+)\s+-\s+(\w+)$', h2_text)
if match:
    player.licence = match.group(1)
    player.name = match.group(2).strip()
    player.ranking = match.group(3)
else:
    # Essayer le format sans classement (ex: "151410 - LUCAS MENIER -")
    match_no_ranking = re.match(r'(\d+)\s+-\s+(.+?)\s*-?\s*$', h2_text)
    if match_no_ranking:
        player.licence = match_no_ranking.group(1)
        player.name = match_no_ranking.group(2).strip()
        player.ranking = ''  # Pas de classement
```

### 2. Protection avec COALESCE et NULLIF dans `insert_player()`

**Fichier** : `src/database/queries.py`

**Avant** :
```sql
ON CONFLICT(licence) DO UPDATE SET
    name = excluded.name,
    ranking = COALESCE(excluded.ranking, players.ranking),
```

**Après** :
```sql
ON CONFLICT(licence) DO UPDATE SET
    name = COALESCE(NULLIF(excluded.name, ''), players.name),
    ranking = COALESCE(NULLIF(excluded.ranking, ''), players.ranking),
```

**Explication** :
- `NULLIF(excluded.name, '')` : Retourne NULL si `excluded.name` est une chaîne vide
- `COALESCE(NULL, players.name)` : Retourne l'ancien nom si le nouveau est NULL
- Résultat : Le nom n'est mis à jour que si le nouveau nom n'est pas vide

### 3. Correction des données existantes

Un script a été exécuté pour corriger les 6 joueurs sans nom :
- 151410 : LUCAS MENIER
- 150147 : GIACOMINO PARDO
- 164472 : GAETANO DE LISO
- 173885 : AURELIE GRANATA
- 158247 : CINDY LIMAN
- 170448 : ALISSON VAUSORT

Ces joueurs n'avaient pas de classement affiché sur leur fiche car ils n'ont pas encore joué de matchs officiels.

## Points techniques importants

### Gestion des joueurs sans classement

Le site AFTT affiche :
- Joueurs actifs avec matchs : `licence - NOM - classement`
- Joueurs sans matchs : `licence - NOM -` (tiret final sans classement)

Les deux formats sont maintenant gérés correctement.

### Stratégie de préservation des données

1. **Regex multiple** : Essayer d'abord le format complet, puis le format réduit
2. **NULLIF + COALESCE** : Ne jamais écraser une valeur valide par une chaîne vide
3. **Fallback** : Si `player_scraper` ne trouve pas le nom, utiliser `members_scraper`

## Fichiers modifiés

- `src/scraper/player_scraper.py` : Regex pour gérer les joueurs sans classement
- `src/database/queries.py` : COALESCE + NULLIF pour protéger nom et ranking

## Tests effectués

1. Scraping du joueur 151410 (LUCAS MENIER) : ✅ Nom extrait correctement
2. Scraping du joueur 150147 (GIACOMINO PARDO) : ✅ Nom extrait correctement
3. Scraping du joueur 164472 (GAETANO DE LISO) : ✅ Nom extrait correctement
4. Vérification base de données : 0 joueurs sans nom restants

## Résultat

- 6 joueurs corrigés
- 0 joueurs sans nom restants
- Le problème ne devrait plus se reproduire grâce aux protections SQL

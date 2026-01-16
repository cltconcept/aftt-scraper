# Correction définitive de la perte des provinces

## Résumé de la demande

L'utilisateur a signalé que le club H004 disparaissait régulièrement de la liste du Hainaut. Le problème était que la province était écrasée par NULL lors des opérations de scraping.

## Problème identifié

### Cause racine

La fonction `insert_club()` dans `src/database/queries.py` écrasait systématiquement toutes les colonnes lors d'une mise à jour, y compris la province. Si le scraping ne fournissait pas de province (ce qui est le cas car le scraping des membres ne récupère pas cette information), la province existante était remplacée par NULL.

**Code problématique** :
```sql
ON CONFLICT(code) DO UPDATE SET
    province = excluded.province,  -- Écrase avec NULL si non fourni
    ...
```

### Scénario du bug

1. Le club H004 existe avec `province = 'Hainaut'`
2. L'utilisateur clique sur "Recharger" pour scraper le club
3. Le scraping récupère les membres mais pas la province
4. `insert_club()` est appelé avec `province = NULL`
5. La province existante est écrasée par NULL
6. H004 disparaît de la liste du Hainaut

## Solution implémentée

### 1. Modification de `insert_club()` avec COALESCE

**Fichier modifié** : `src/database/queries.py`

**Avant** :
```sql
ON CONFLICT(code) DO UPDATE SET
    province = excluded.province,
    ...
```

**Après** :
```sql
ON CONFLICT(code) DO UPDATE SET
    province = COALESCE(excluded.province, clubs.province),
    ...
```

`COALESCE` retourne la première valeur non-NULL. Ainsi :
- Si `excluded.province` est fourni → utilise la nouvelle valeur
- Si `excluded.province` est NULL → conserve l'ancienne valeur

Cette modification a été appliquée à **toutes les colonnes** pour éviter des problèmes similaires.

### 2. Détection automatique de la province dans le scraping

**Fichier modifié** : `src/api/app.py` (endpoint `/api/clubs/{code}/scrape`)

**Ajout** :
```python
# Récupérer la province existante ou la détecter depuis le code
existing_club = queries.get_club(code)
province = None
if existing_club and existing_club.get('province'):
    province = existing_club['province']
else:
    province = extract_province_from_code(code)

# Mettre à jour les infos du club dans la base (en préservant la province)
club_data = {
    'code': code,
    'name': club_name,
    'province': province,  # Toujours inclure la province
    **club_info
}
```

### 3. Détection automatique dans `import_members()`

**Fichier modifié** : `src/database/import_json.py`

**Ajout** :
```python
# Récupérer la province existante ou la détecter depuis le code
from src.scraper.clubs_scraper import extract_province_from_code
cursor = db.execute("SELECT province FROM clubs WHERE code = ?", (club_code,))
row = cursor.fetchone()
if row and row[0]:
    province = row[0]
else:
    province = extract_province_from_code(club_code)

club_data = {
    'code': club_code,
    'name': data.get('club_name'),
    'province': province,  # Toujours inclure la province
    **club_info
}
```

## Points techniques importants

### Stratégie de préservation des données

1. **COALESCE dans SQL** : Ne jamais écraser une valeur existante par NULL
2. **Détection automatique** : Si la province n'existe pas, la détecter depuis le code du club
3. **Priorité** : Province existante > Province détectée > NULL

### Détection de la province depuis le code

La fonction `extract_province_from_code()` détecte la province à partir du préfixe du code :
- `H004` → `Hainaut` (préfixe `H`)
- `A003` → `Antwerpen` (préfixe `A`)
- `L001` → `Liège` (préfixe `L`)
- etc.

### Correction des données existantes

Un script a été exécuté pour corriger les clubs avec `province = NULL` :
- H000 (Hainaut) : NULL → Hainaut
- H004 (Le Centre) : NULL → Hainaut

## Avantages de la solution

1. **Robustesse** : La province ne peut plus être écrasée par NULL
2. **Automatique** : Si la province est manquante, elle est détectée automatiquement
3. **Rétrocompatible** : Les données existantes sont préservées
4. **Défensif** : Même si un bug introduit NULL, COALESCE protège les données

## Fichiers modifiés

- `src/database/queries.py` : Ajout de COALESCE dans `insert_club()`
- `src/api/app.py` : Détection automatique de la province dans le scraping
- `src/database/import_json.py` : Détection automatique de la province dans l'import

## Notes

- La correction avec COALESCE a été appliquée à toutes les colonnes, pas seulement la province
- La détection automatique est un filet de sécurité supplémentaire
- Les clubs existants avec `province = NULL` ont été corrigés manuellement
- Le problème ne devrait plus se reproduire grâce à ces multiples protections

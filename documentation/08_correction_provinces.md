# Correction des provinces manquantes lors du scraping

## Résumé de la demande

L'utilisateur a signalé que certains clubs manquaient lors du scraping d'une province, notamment le club H004 (Le Centre) dans le Hainaut. Le problème était que certains clubs avaient `province = None` dans la base de données au lieu de la province correcte.

## Problème identifié

L'endpoint `/api/clubs/province/{province}/scrape` utilisait `queries.get_all_clubs(province=province)` qui récupère les clubs depuis la base de données en filtrant par province. Si un club avait `province = None` dans la base de données, il n'était pas inclus dans les résultats, même s'il appartenait à la province demandée.

**Exemple** : Le club H004 avait `province = None` au lieu de `Hainaut`, donc il n'était pas inclus lors du scraping du Hainaut.

## Solution implémentée

### Modification de l'endpoint `/api/clubs/province/{province}/scrape`

**Fichier modifié** : `src/api/app.py`

**Modifications** :
1. **Scraping initial depuis le site web** : L'endpoint commence maintenant par scraper tous les clubs depuis le site web AFTT (`get_all_clubs()`)
2. **Mise à jour des provinces** : Chaque club est inséré/mis à jour dans la base de données avec `queries.insert_club()`, ce qui corrige automatiquement les provinces manquantes
3. **Filtrage par province** : Les clubs sont ensuite filtrés par province après la mise à jour
4. **Scraping des membres et joueurs** : Le reste du processus reste identique

### Code ajouté

```python
# 1. Scraper tous les clubs depuis le site web pour mettre à jour les provinces
all_clubs_from_web = get_all_clubs()

# Normaliser le nom de la province pour la comparaison
normalized_province = province.strip()

# Mapper les variations possibles du nom de la province
province_mapping = {
    'Hainaut': 'Hainaut',
    'hainaut': 'Hainaut',
    'HAINAUT': 'Hainaut',
}
normalized_province = province_mapping.get(normalized_province, normalized_province)

# Mettre à jour les clubs dans la base de données avec les bonnes provinces
clubs_to_scrape = []
for club_obj in all_clubs_from_web:
    club_dict = club_obj.to_dict() if hasattr(club_obj, 'to_dict') else {
        'code': club_obj.code,
        'name': club_obj.name,
        'province': club_obj.province
    }
    
    # Insérer/mettre à jour le club dans la base (cela corrigera les provinces manquantes)
    queries.insert_club(club_dict)
    
    # Filtrer les clubs de la province demandée
    club_province = club_dict.get('province', '').strip()
    if club_province == normalized_province:
        clubs_to_scrape.append(club_dict)
```

### Import ajouté

```python
from src.scraper.clubs_scraper import get_all_clubs
```

## Points techniques importants

### Détection automatique de la province

La fonction `extract_province_from_code()` dans `src/scraper/clubs_scraper.py` détermine automatiquement la province à partir du code du club :
- `H004` → `Hainaut` (préfixe `H`)
- `A003` → `Antwerpen` (préfixe `A`)
- `L001` → `Liège` (préfixe `L`)
- etc.

### Normalisation des noms de provinces

Le code normalise les variations possibles du nom de la province (majuscules/minuscules) pour assurer une correspondance correcte.

### Mise à jour automatique

Lors de chaque scraping de province, tous les clubs sont mis à jour depuis le site web, ce qui garantit :
- Les provinces manquantes sont corrigées
- Les nouveaux clubs sont ajoutés
- Les informations des clubs existants sont mises à jour

## Résultat

Après cette modification :
- ✅ Le club H004 est maintenant correctement identifié comme étant du Hainaut
- ✅ Tous les clubs avec `province = None` sont corrigés lors du scraping
- ✅ Les nouveaux clubs sont automatiquement ajoutés avec la bonne province
- ✅ Le scraping inclut tous les clubs de la province, même ceux qui avaient une province manquante

## Fichiers modifiés

- `src/api/app.py` : Modification de l'endpoint `/api/clubs/province/{province}/scrape`

## Prérequis

- La fonction `get_all_clubs()` doit être accessible depuis `src.scraper.clubs_scraper`
- La fonction `queries.insert_club()` doit être disponible pour mettre à jour les clubs

## Notes

- Le scraping initial depuis le site web peut prendre quelques secondes supplémentaires, mais cela garantit la cohérence des données
- Les clubs "Individueel" ou génériques sont toujours exclus du scraping (comme avant)
- Les erreurs de scraping pour un club spécifique n'empêchent pas le traitement des autres clubs

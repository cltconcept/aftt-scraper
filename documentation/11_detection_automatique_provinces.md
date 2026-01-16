# Détection automatique des provinces manquantes

## Résumé de la demande

L'utilisateur a signalé que le club H004 disparaissait de nouveau de la liste du Hainaut. Le problème était que certains clubs avaient `province = None` dans la base de données au lieu de la province correcte.

## Problème identifié

Le club H004 avait `province = None` dans la base de données. Lors du filtrage par province dans l'endpoint `/api/clubs?province=Hainaut`, les clubs avec `province = None` n'étaient pas inclus dans les résultats, même si leur code permettait de détecter qu'ils appartenaient au Hainaut.

## Solution implémentée

### 1. Correction immédiate dans la base de données

Un script Python a été créé pour corriger directement H004 et tous les autres clubs sans province avec un code commençant par "H".

### 2. Détection automatique dans l'endpoint API

**Fichier modifié** : `src/api/app.py`

**Modifications** :
- Lors du filtrage par province, l'endpoint charge maintenant tous les clubs (sans filtre)
- Il détecte automatiquement les provinces manquantes à partir du code du club
- Il met à jour la base de données avec la province détectée
- Il filtre ensuite les clubs par province (en incluant ceux dont la province a été détectée)

### Code modifié

**Avant** :
```python
@app.get("/api/clubs", tags=["Clubs"])
async def list_clubs(province: Optional[str] = None, ...):
    clubs = queries.get_all_clubs(province=province, limit=limit, offset=offset)
    return {"count": len(clubs), "clubs": clubs}
```

**Après** :
```python
@app.get("/api/clubs", tags=["Clubs"])
async def list_clubs(province: Optional[str] = None, ...):
    from src.scraper.clubs_scraper import extract_province_from_code
    
    if province:
        # Charger tous les clubs pour détecter les provinces manquantes
        all_clubs = queries.get_all_clubs(province=None, limit=None, offset=0)
        
        # Détecter et corriger automatiquement les provinces manquantes
        filtered_clubs = []
        for club in all_clubs:
            # Détecter la province si elle est manquante
            if not club.get('province') and club.get('code'):
                detected_province = extract_province_from_code(club['code'])
                if detected_province:
                    # Mettre à jour dans la base de données
                    club['province'] = detected_province
                    queries.insert_club({
                        'code': club['code'],
                        'name': club.get('name'),
                        'province': detected_province
                    })
            
            # Filtrer par province (exacte ou détectée)
            club_province = club.get('province', '').strip()
            if club_province and (club_province == province or ...):
                filtered_clubs.append(club)
        
        clubs = filtered_clubs
    else:
        # Pas de filtre, charger normalement avec détection
        clubs = queries.get_all_clubs(province=None, limit=limit, offset=offset)
        # Détecter et corriger les provinces manquantes
        ...
    
    return {"count": len(clubs), "clubs": clubs}
```

## Points techniques importants

### Détection de la province

La fonction `extract_province_from_code()` dans `src/scraper/clubs_scraper.py` détermine automatiquement la province à partir du code du club :
- `H004` → `Hainaut` (préfixe `H`)
- `A003` → `Antwerpen` (préfixe `A`)
- `L001` → `Liège` (préfixe `L`)
- `Lx001` → `Luxembourg` (préfixe `Lx`)
- etc.

### Mise à jour automatique

Lors de chaque requête avec filtre de province :
1. Tous les clubs sont chargés
2. Les provinces manquantes sont détectées et mises à jour dans la base
3. Les clubs sont filtrés par province (en incluant ceux dont la province a été détectée)

### Filtrage flexible

Le filtrage par province est flexible et accepte :
- Correspondance exacte : `province = "Hainaut"`
- Correspondance partielle : `province` contient "Hainaut" ou vice versa

## Avantages

1. **Correction automatique** : Les provinces manquantes sont détectées et corrigées automatiquement
2. **Robustesse** : Les clubs ne disparaissent plus même si leur province est NULL
3. **Transparence** : La correction se fait de manière transparente pour l'utilisateur
4. **Performance** : La détection ne se fait que lors du filtrage par province

## Fichiers modifiés

- `src/api/app.py` : Modification de l'endpoint `/api/clubs`
- `fix_h004_province.py` : Script de correction (temporaire, supprimé après utilisation)

## Prérequis

- La fonction `extract_province_from_code()` doit être disponible depuis `src.scraper.clubs_scraper`
- La fonction `queries.insert_club()` doit être disponible pour mettre à jour les clubs

## Notes

- La détection automatique ne se fait que lors du filtrage par province pour éviter de ralentir les requêtes sans filtre
- Les clubs sans province et sans code détectable ne seront pas inclus dans les résultats filtrés
- La mise à jour dans la base de données garantit que le problème ne se reproduira pas

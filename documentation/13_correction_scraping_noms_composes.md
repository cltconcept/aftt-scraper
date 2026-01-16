# Correction du scraping des noms composés

## Résumé de la demande

L'utilisateur a signalé des problèmes dans le scraping des joueurs :
- Des joueurs sans nom
- Des inversions dans les colonnes (classement contenant des morceaux de noms)

## Problème identifié

Le regex utilisé pour extraire les informations du joueur depuis le HTML ne gérait pas correctement les noms composés avec des tirets.

**Exemple du problème** :
- H2 HTML : `103603 - JEAN-FRANCOIS CULOT - D0`
- Ancien regex : `(\d+)\s*-\s*(.+?)\s*-\s*(\w+)`
- Résultat : Name='JEAN', Ranking='FRANCOIS' ❌

**Cause** :
Le regex utilisait `\s*-\s*` (tiret avec espaces **optionnels**) et `.+?` (non-greedy). Le tiret dans les noms composés "JEAN-FRANCOIS" était donc considéré comme un séparateur.

## Solution implémentée

### Correction du regex

**Fichier modifié** : `src/scraper/player_scraper.py`

**Ancien regex** :
```python
match = re.match(r'(\d+)\s*-\s*(.+?)\s*-\s*(\w+)', h2_text)
```

**Nouveau regex** :
```python
match = re.match(r'(\d+)\s+-\s+(.+)\s+-\s+(\w+)$', h2_text)
```

**Changements** :
1. `\s*` → `\s+` : Les espaces autour du tiret sont maintenant **obligatoires**
2. `.+?` → `.+` : Le regex est maintenant greedy et capture le maximum possible
3. Ajout de `$` à la fin pour ancrer le match

**Logique** :
- Les séparateurs dans le format sont toujours ` - ` (tiret avec espaces)
- Les tirets dans les noms composés n'ont pas d'espaces : `JEAN-FRANCOIS`
- En exigeant des espaces, le regex ne matche que les vrais séparateurs

**Résultat après correction** :
- H2 HTML : `103603 - JEAN-FRANCOIS CULOT - D0`
- Nouveau regex : `(\d+)\s+-\s+(.+)\s+-\s+(\w+)$`
- Résultat : Name='JEAN-FRANCOIS CULOT', Ranking='D0' ✅

### Mise à jour de la fonction de tri

**Fichier modifié** : `web/index.html`

Les classements D et E ont été ajoutés à la fonction de tri :

**Ordre des classements** :
```
NC < E6 < E4 < E2 < E0 < D6 < D4 < D2 < D0 < C6 < C4 < C2 < C0 < B6 < B4 < B2 < B0 < A0
```

**Code mis à jour** :
```javascript
function getRankingValue(ranking) {
    // NC (Non Classé) = 0
    if (r === 'NC' || r === 'N') return 0;
    
    // Extraire la lettre et le chiffre
    const match = r.match(/^([ABCDE])(\d+)$/);
    
    // Base par lettre: E < D < C < B < A
    let base = 0;
    if (letter === 'E') base = 100;
    else if (letter === 'D') base = 200;
    else if (letter === 'C') base = 300;
    else if (letter === 'B') base = 400;
    else if (letter === 'A') base = 500;
    
    // Le chiffre est inversé: 6 est plus faible que 0
    return base + (10 - number);
}
```

## Exemples de corrections

| Licence | Avant (corrompu) | Après (correct) |
|---------|------------------|-----------------|
| 103603 | Name='JEAN', Ranking='FRANCOIS' | Name='JEAN-FRANCOIS CULOT', Ranking='D0' |
| 104714 | Name='JEAN', Ranking='PIERRE' | Name='JEAN-PIERRE BYLOO', Ranking='D4' |
| 111288 | Name='LAURENT PINO', Ranking='VILA' | Name='LAURENT PINO-VILA', Ranking='D2' |
| 158842 | Name='JEAN', Ranking='MARC' | Name='JEAN-MARC LECLERCQ', Ranking='E2' |
| 124462 | Name='JEAN', Ranking='PIERRE' | Name='JEAN-PIERRE HORNY', Ranking='D6' |

## Points techniques importants

### Format du H2 dans la fiche joueur

```
{licence} - {nom complet} - {classement}
```

Exemples :
- `152174 - KEVIN BRULEZ - C2`
- `103603 - JEAN-FRANCOIS CULOT - D0`
- `111288 - LAURENT PINO-VILA - D2`

### Classements du tennis de table belge

Les classements vont de E (débutant) à A (expert) :
- **E** (E6 → E0) : Débutants / Loisirs
- **D** (D6 → D0) : Récréatifs
- **C** (C6 → C0) : Compétition niveau C
- **B** (B6 → B0) : Compétition niveau B
- **A** (A6 → A0) : Compétition niveau A (plus fort)
- **NC** : Non Classé

Le chiffre est inversé : E6 < E4 < E2 < E0

## Actions requises

Pour corriger les données existantes dans la base de données, il faut re-scraper les clubs concernés en cliquant sur le bouton "Recharger" dans la page de détails du club.

## Fichiers modifiés

- `src/scraper/player_scraper.py` : Correction du regex pour les noms composés
- `web/index.html` : Ajout des classements D et E dans la fonction de tri

## Notes

- Les données du site web sont correctes, c'était le parsing qui était défaillant
- Les données corrompues dans la base proviennent d'anciens scrapings
- Il est recommandé de re-scraper les clubs pour corriger les données
- Le scraping des membres (members_scraper.py) n'était pas affecté car il utilise un tableau HTML avec des colonnes séparées

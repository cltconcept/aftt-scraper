# Page complète des membres d'un club triés par classement

## Résumé de la demande

L'utilisateur a demandé que lorsqu'on clique sur un club, une page complète s'affiche avec tous les membres triés par classement, du plus petit (NC) au plus grand (A0).

## Problème identifié

Lorsqu'on cliquait sur un club, seuls les 20 premiers joueurs étaient affichés, et ils n'étaient pas triés par classement. L'utilisateur voulait voir tous les membres dans un tableau complet, triés par classement.

## Solution implémentée

### 1. Fonction de tri par classement

**Fichier modifié** : `web/index.html`

**Nouvelle fonction** : `sortPlayersByRanking(players)`

Cette fonction trie les joueurs selon l'ordre suivant :
- **NC** (Non Classé) = le plus petit
- **C0, C1, C2, ..., C9** (classements C)
- **B0, B1, B2, ..., B9** (classements B)
- **A0, A1, A2, ..., A9** (classements A) = le plus grand

**Logique de tri** :
```javascript
function getRankingValue(ranking) {
    if (!ranking) return -1; // Pas de classement = le plus bas
    const r = ranking.trim().toUpperCase();
    
    // NC (Non Classé) = 0
    if (r === 'NC') return 0;
    
    // Extraire la lettre et le chiffre
    const match = r.match(/^([ABC])(\d+)$/);
    if (!match) return 9999; // Classement inconnu = le plus haut
    
    const letter = match[1];
    const number = parseInt(match[2], 10);
    
    // C = 1000-1999, B = 2000-2999, A = 3000-3999
    let base = 0;
    if (letter === 'C') base = 1000;
    else if (letter === 'B') base = 2000;
    else if (letter === 'A') base = 3000;
    
    return base + number;
}
```

### 2. Modification de `showClubDetail()`

**Modifications** :
1. **Chargement de tous les membres** : L'endpoint `/api/clubs/{code}/players?limit=10000` est appelé pour charger tous les membres (pas seulement 20)
2. **Tri par classement** : Les membres sont triés avec `sortPlayersByRanking()`
3. **Affichage complet** : Tous les membres sont affichés dans un tableau complet avec :
   - Numéro de ligne
   - Licence
   - Nom
   - Catégorie
   - Classement
   - Points actuels
4. **Suppression de la limite** : Plus de limite à 20 membres, tous sont affichés
5. **Suppression du JSON brut** : La section JSON brut a été retirée pour une meilleure lisibilité

### Structure du tableau

Le tableau affiche maintenant :
- **#** : Numéro de ligne (1, 2, 3, ...)
- **Licence** : Numéro de licence du joueur (police monospace)
- **Nom** : Nom complet du joueur (gras)
- **Catégorie** : Catégorie du joueur (SEN, VET, JUN, etc.)
- **Classement** : Classement du joueur (NC, C0, C1, ..., A0, A1, ...) en gras
- **Points** : Points actuels du joueur (format décimal avec 1 décimale)

### Code modifié

**Avant** :
```javascript
// Charger les joueurs (limite implicite)
const res = await fetch(`${API_BASE_URL}/api/clubs/${code}/players`);
// Afficher seulement les 20 premiers
${clubPlayers.slice(0, 20).map(...)}
```

**Après** :
```javascript
// Charger TOUS les joueurs (sans limite)
const res = await fetch(`${API_BASE_URL}/api/clubs/${code}/players?limit=10000`);
// Trier par classement
const sortedPlayers = sortPlayersByRanking(clubPlayers);
// Afficher TOUS les membres
${sortedPlayers.map((p, index) => ...)}
```

### Amélioration de l'interface

1. **Titre amélioré** : Le titre affiche maintenant "CODE - NOM" du club
2. **Tableau complet** : Tous les membres sont visibles dans un tableau scrollable
3. **Tri visuel** : Les membres sont triés du plus petit classement (NC) au plus grand (A0)
4. **Numérotation** : Chaque ligne est numérotée pour faciliter la lecture
5. **Clic sur les lignes** : Cliquer sur une ligne ouvre la fiche du joueur

## Points techniques importants

### Ordre de tri des classements

L'ordre de tri est le suivant (du plus petit au plus grand) :
1. **NC** (Non Classé)
2. **C0, C1, C2, ..., C9** (classements C)
3. **B0, B1, B2, ..., B9** (classements B)
4. **A0, A1, A2, ..., A9** (classements A)

### Gestion des classements manquants

- Si un joueur n'a pas de classement (`ranking = null` ou `ranking = ''`), il est considéré comme NC et placé en premier
- Si un classement est dans un format inconnu, il est placé à la fin (après A9)

### Performance

- Le chargement de tous les membres peut prendre quelques instants pour les grands clubs
- Le tri se fait côté client (JavaScript) pour une meilleure réactivité
- Le tableau est scrollable si nécessaire pour les clubs avec beaucoup de membres

## Avantages

1. **Visibilité complète** : Tous les membres sont visibles d'un coup d'œil
2. **Tri logique** : Les membres sont triés par classement du plus petit au plus grand
3. **Navigation facile** : Cliquer sur une ligne ouvre directement la fiche du joueur
4. **Interface claire** : Tableau bien structuré avec toutes les informations importantes

## Fichiers modifiés

- `web/index.html` : 
  - Ajout de la fonction `sortPlayersByRanking()`
  - Modification de `showClubDetail()` pour afficher tous les membres triés

## Prérequis

- L'endpoint `/api/clubs/{code}/players` doit retourner tous les joueurs (sans limite ou avec une limite élevée)
- Les joueurs doivent avoir un champ `ranking` dans leurs données

## Notes

- Le tri se fait côté client pour une meilleure performance
- Les classements sont normalisés en majuscules pour le tri
- Le tableau est responsive et scrollable pour les grands clubs
- Le bouton "Recharger" reste disponible pour mettre à jour les données

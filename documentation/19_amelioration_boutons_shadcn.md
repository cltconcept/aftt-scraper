# Amélioration des Boutons avec Shadcn UI (Style)

## Résumé
L'interface utilisateur a été améliorée pour adopter le style visuel de **Shadcn UI** pour tous les boutons. Comme le projet utilise une architecture HTML/Python sans framework JS (React/Vue), nous avons implémenté le design system de Shadcn via **Tailwind CSS** en mode CDN.

## Modifications Effectuées

### 1. Intégration de Tailwind CSS
- Ajout du CDN Tailwind CSS (`cdn.tailwindcss.com`) dans `web/index.html` et `web/api-docs.html`.
- Configuration du thème Tailwind pour utiliser les variables CSS existantes du projet (couleurs, bordures, etc.).
- Désactivation du "preflight" (reset CSS) pour ne pas casser les styles existants.

### 2. Styles des Boutons (Shadcn Replica)
Une couche de composants Tailwind personnalisée a été ajoutée pour répliquer exactement les classes de boutons Shadcn :

| Classe | Description |
|--------|-------------|
| `.btn` | Classe de base (padding, rounded-md, focus ring, transition) |
| `.btn-primary` | Couleur d'accentuation, texte blanc, ombre portée (shadow-lg) |
| `.btn-secondary` | *Déprécié pour ce thème sombre* (problème de contraste) |
| `.btn-outline` | Fond transparent, bordure visible. Utilisé pour les actions secondaires. |
| `.btn-ghost` | Transparent, hover effet subtil (utilisé pour la navigation) |
| `.btn-destructive` | Rouge (erreurs, suppressions) |
| `.btn-sm` / `.btn-lg` | Variantes de taille |
| `.btn-icon` | Pour les boutons carrés avec icône seule |

### 3. Modifications Spécifiques
- **Boutons "Scraper tout" (Cartes Régions)** : Remplacés par `.btn-outline` avec un effet hover coloré (`hover:bg-primary/20`) pour une meilleure intégration sur fond sombre.
- **Bouton "Scraper TOUT" (Header)** : Ajout d'une ombre portée (`shadow-lg`) pour le faire ressortir comme action principale.
- **Boutons Admin** : Remplacement des `btn-secondary` par `btn-outline` pour la cohérence.

### 4. Mapping des Classes Existantes
Les classes existantes ont été redéfinies pour utiliser les nouveaux styles :
- `.nav-btn` → Hérite de `.btn .btn-ghost` (Navigation)
- `.close-btn` → Hérite de `.btn .btn-ghost .btn-icon` (Fermeture modale)
- `.copy-btn` → Hérite de `.btn .btn-sm .btn-primary` (Boutons de copie)

## Utilisation Technique

Pour ajouter un nouveau bouton dans le futur :

```html
<!-- Bouton Principal -->
<button class="btn btn-primary shadow-lg">Action Principale</button>

<!-- Bouton Secondaire (Outline préféré sur fond sombre) -->
<button class="btn btn-outline hover:bg-primary/10">Action Secondaire</button>

<!-- Bouton Navigation -->
<button class="btn btn-ghost">Lien</button>
```

## Fichiers Modifiés
- `web/index.html`
- `web/api-docs.html`

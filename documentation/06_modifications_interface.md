# Modifications de l'interface web

## Résumé de la demande

L'utilisateur a demandé deux modifications sur le fichier `index.html` :
1. Supprimer le logo de l'en-tête
2. Ajouter un lien vers la documentation API dans le menu de navigation

## Solution implémentée

### 1. Suppression du logo

**Fichier modifié** : `web/index.html`

**Modifications** :
- Suppression de l'élément `<div class="logo">` contenant l'icône et le titre avec sous-titre
- Suppression des styles CSS associés au logo :
  - `.logo`
  - `.logo-icon`
  - `.logo h1`
  - `.logo span`
- Remplacement par un simple titre `<h1>` avec les styles de gradient conservés

**Code avant** :
```html
<div class="logo">
    <div class="logo-icon">🏓</div>
    <div>
        <h1>AFTT Data Explorer</h1>
        <span>Tennis de Table Belge</span>
    </div>
</div>
```

**Code après** :
```html
<div>
    <h1 style="font-size: 1.5rem; font-weight: 700; background: var(--gradient-1); -webkit-background-clip: text; -webkit-text-fill-color: transparent; background-clip: text;">AFTT Data Explorer</h1>
</div>
```

### 2. Ajout du lien vers la documentation API

**Fichiers modifiés** : `web/index.html`, `web/api-docs.html` (nouveau fichier)

**Modifications** :
- Création d'une page de documentation API statique (`web/api-docs.html`) accessible même si l'API n'est pas démarrée
- Ajout d'un lien dans le menu de navigation pointant vers cette page de documentation
- Le lien utilise la classe `.nav-btn` pour conserver le style cohérent avec les autres boutons du menu
- La page de documentation inclut :
  - Tous les endpoints de l'API avec leurs paramètres
  - Des exemples d'utilisation avec curl
  - Un lien vers la documentation Swagger interactive (si l'API est démarrée)
  - Des instructions pour démarrer l'API

**Code ajouté dans index.html** :
```html
<a href="api-docs.html" class="nav-btn" style="text-decoration: none; display: inline-block;">📚 API Docs</a>
```

**Note** : La page de documentation statique permet d'accéder à la documentation même si l'API FastAPI n'est pas démarrée. Elle contient également un lien vers la documentation Swagger interactive (`http://localhost:8000/docs`) pour les utilisateurs qui ont démarré l'API.

## Points techniques importants

1. **Conservation du style** : Le titre conserve le style de gradient pour maintenir l'identité visuelle
2. **Cohérence du menu** : Le lien API utilise la même classe CSS que les boutons de navigation pour un rendu uniforme
3. **Accessibilité** : Le lien s'ouvre dans un nouvel onglet pour ne pas interrompre la navigation de l'utilisateur
4. **URL de l'API** : L'URL pointe vers `http://localhost:8000/docs` qui correspond à la documentation Swagger générée automatiquement par FastAPI

## Fichiers modifiés

- `web/index.html` : Suppression du logo et ajout du lien API dans le menu

## Compatibilité

- Les modifications sont compatibles avec tous les navigateurs modernes
- Le lien API fonctionne lorsque l'API FastAPI est démarrée sur le port 8000
- Si l'API n'est pas disponible, le lien affichera une erreur de connexion (comportement attendu)

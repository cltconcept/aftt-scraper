# Ajout du bouton "Recharger" pour les clubs

## Résumé de la demande

L'utilisateur a demandé que lorsqu'on clique sur un club, le scraping ne soit pas lancé automatiquement. À la place, les données doivent être affichées directement depuis la base de données, et un bouton "Recharger" doit être ajouté pour déclencher le scraping manuellement.

## Problème identifié

Lorsqu'on cliquait sur un club, la fonction `showClubDetail()` lançait automatiquement le scraping, ce qui :
- Ralentissait l'affichage des données
- Consommait des ressources inutilement si les données étaient déjà à jour
- Empêchait de voir rapidement les données existantes

## Solution implémentée

### Modification de la fonction `showClubDetail()`

**Fichier modifié** : `web/index.html`

**Modifications** :
1. **Affichage direct des données** : La fonction charge maintenant directement les données du club depuis l'API (`/api/clubs/{code}`) sans lancer le scraping
2. **Chargement des joueurs** : Les joueurs sont chargés depuis `/api/clubs/{code}/players`
3. **Bouton "Recharger"** : Un bouton "Recharger" est ajouté dans l'en-tête du panneau de détails
4. **Fonction séparée** : Création d'une fonction `reloadClubData()` dédiée au scraping

### Code modifié

**Avant** :
```javascript
async function showClubDetail(code) {
    // Afficher message de chargement
    // Lancer le scraping automatiquement
    const scrapeRes = await fetch(`${API_BASE_URL}/api/clubs/${code}/scrape`, {
        method: 'POST'
    });
    // Afficher les résultats après le scraping
}
```

**Après** :
```javascript
async function showClubDetail(code) {
    // Charger les données du club depuis l'API
    const res = await fetch(`${API_BASE_URL}/api/clubs/${code}`);
    // Charger les joueurs depuis l'API
    const playersRes = await fetch(`${API_BASE_URL}/api/clubs/${code}/players`);
    // Afficher les données avec un bouton "Recharger"
    // Ajouter l'event listener pour le bouton
    reloadBtn.onclick = () => reloadClubData(code);
}

async function reloadClubData(code) {
    // Afficher message de chargement
    // Lancer le scraping
    const scrapeRes = await fetch(`${API_BASE_URL}/api/clubs/${code}/scrape`, {
        method: 'POST'
    });
    // Recharger les données après le scraping
    await showClubDetail(code);
    // Afficher un message de succès temporaire
}
```

### Structure du bouton "Recharger"

Le bouton est placé dans l'en-tête du panneau de détails, à côté du titre :

```html
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1.5rem;">
    <h3 style="margin: 0;">Informations du club</h3>
    <button id="reload-club-btn" class="nav-btn" style="text-decoration: none; display: inline-block;">
        🔄 Recharger
    </button>
</div>
```

### Gestion des messages

Après le scraping, un message de succès ou d'erreur est affiché temporairement en haut du panneau de détails :
- **Succès** : Affiche le nombre de membres et fiches joueurs scrapés
- **Erreur** : Affiche le message d'erreur
- Les messages disparaissent automatiquement après 5 secondes

### Message informatif

Si aucun joueur n'est trouvé, un message informatif est affiché :

```html
<div style="background: rgba(59, 130, 246, 0.1); border: 1px solid var(--primary); border-radius: 10px; padding: 1rem; margin-top: 1.5rem;">
    <p style="color: var(--text-secondary); margin: 0;">Aucun joueur trouvé. Cliquez sur "Recharger" pour scraper les données du club.</p>
</div>
```

## Points techniques importants

### Chargement des données

1. **Données du club** : Chargées depuis `/api/clubs/{code}`
2. **Joueurs du club** : Chargés depuis `/api/clubs/{code}/players`
3. **Gestion des erreurs** : Les erreurs de chargement sont capturées mais n'empêchent pas l'affichage

### Workflow du scraping

1. L'utilisateur clique sur "Recharger"
2. Un message de chargement est affiché
3. Le scraping est lancé via `POST /api/clubs/{code}/scrape`
4. Après le scraping, les données sont rechargées depuis l'API
5. Un message de succès/erreur est affiché temporairement

### Mise à jour de l'affichage

Après le scraping, `showClubDetail()` est rappelée pour mettre à jour l'affichage avec les nouvelles données.

## Avantages de la nouvelle approche

1. **Performance** : Affichage instantané des données existantes
2. **Contrôle utilisateur** : L'utilisateur décide quand scraper
3. **Efficacité** : Évite les scrapings inutiles
4. **Expérience utilisateur** : Permet de voir rapidement les données disponibles

## Fichiers modifiés

- `web/index.html` : 
  - Modification de `showClubDetail()`
  - Ajout de `reloadClubData()`

## Prérequis

- L'API doit être accessible (`/api/clubs/{code}` et `/api/clubs/{code}/players`)
- L'endpoint de scraping `/api/clubs/{code}/scrape` doit être fonctionnel

## Notes

- Le bouton "Recharger" est uniquement visible dans le panneau de détails d'un club
- Les messages de succès/erreur disparaissent automatiquement après 5 secondes
- Si aucune donnée n'est disponible, un message informatif guide l'utilisateur

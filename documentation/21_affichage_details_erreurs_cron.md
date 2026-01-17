# Affichage des Détails des Erreurs Cron

## Résumé de la demande

L'utilisateur souhaitait pouvoir voir les détails des erreurs des jobs cron depuis l'interface web. Actuellement, seule la liste des tâches avec le nombre d'erreurs était affichée, sans possibilité de consulter les détails de ces erreurs.

## Solution implémentée

### Modifications apportées

1. **Ajout d'une colonne "Actions" dans le tableau de l'historique**
   - Chaque ligne de la table affiche maintenant un bouton "Voir détails" ou "Voir erreurs" selon le nombre d'erreurs
   - Le bouton est plus visible pour les tâches avec des erreurs (texte "🔍 Voir erreurs")

2. **Fonction `showTaskDetails(taskId)`**
   - Charge les détails complets d'une tâche via l'endpoint `/api/scrape/task/{task_id}`
   - Affiche toutes les informations dans une modale existante (`detail-panel`)
   - Présente les erreurs de manière structurée et lisible

### Interface utilisateur

La modale affiche plusieurs sections :

1. **Informations générales**
   - Statut de la tâche
   - Source (Cron ou Manuel)
   - Date de début et de fin
   - Durée totale

2. **Statistiques**
   - Nombre de clubs traités
   - Nombre total de joueurs
   - Nombre d'erreurs (avec code couleur)

3. **Progression** (si disponible)
   - Province actuelle
   - Club actuel

4. **Liste des erreurs**
   - Affichage de toutes les erreurs dans une liste défilante
   - Chaque erreur est numérotée et affichée dans un bloc distinct
   - Style avec bordure gauche rouge pour mettre en évidence les erreurs
   - Zone scrollable si beaucoup d'erreurs (max-height: 400px)

### Endpoint API utilisé

L'endpoint existant `/api/scrape/task/{task_id}` est utilisé pour récupérer les détails :

```http
GET /api/scrape/task/{task_id}
```

Réponse :
```json
{
  "id": 5,
  "started_at": "2026-01-17T02:00:00",
  "finished_at": "2026-01-17T03:17:29",
  "status": "success",
  "total_clubs": 608,
  "completed_clubs": 608,
  "total_players": 30000,
  "errors_count": 0,
  "errors_detail": "[\"erreur1\", \"erreur2\"]",
  "errors_list": ["erreur1", "erreur2"],
  "trigger_type": "cron",
  "current_club": null,
  "current_province": null
}
```

## Points techniques importants

### Structure des erreurs

Les erreurs sont stockées dans la base de données sous forme de JSON dans le champ `errors_detail` de la table `scrape_tasks`. L'API parse automatiquement ce JSON et retourne un champ `errors_list` contenant un tableau d'erreurs.

### Format d'affichage

- Chaque erreur est affichée dans un bloc avec :
  - Numéro d'erreur (#1, #2, etc.)
  - Message d'erreur complet
  - Style visuel distinctif (bordure rouge, fond sombre)
  - Police monospace pour une meilleure lisibilité

### Gestion des cas limites

- Si aucune erreur : affichage d'un message "✅ Aucune erreur"
- Si la tâche est en cours : affichage de la progression actuelle
- Gestion des erreurs de chargement avec message d'alerte

## Utilisation

1. Accéder à la section **Admin** de l'interface web
2. Aller dans l'onglet **Historique des tâches**
3. Cliquer sur le bouton **"🔍 Voir erreurs"** ou **"📋 Détails"** pour une tâche
4. La modale s'ouvre avec tous les détails, y compris la liste complète des erreurs

## Fichiers modifiés

- `web/index.html` : Ajout de la colonne Actions et de la fonction `showTaskDetails()`

## Améliorations futures possibles

- Export des erreurs en CSV ou JSON
- Filtrage des erreurs par type
- Recherche dans les erreurs
- Affichage des erreurs en temps réel pendant l'exécution d'une tâche

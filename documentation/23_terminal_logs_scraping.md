# Terminal de Logs en Temps Réel pour le Scraping

## Résumé de la demande

L'utilisateur souhaitait voir la simulation du terminal dans la page admin pendant un scraping, pour pouvoir suivre en temps réel les logs et messages du processus de scraping.

## Solution implémentée

### Backend (API)

1. **Stockage des logs en mémoire**
   - Création d'un dictionnaire global `_scrape_logs` qui stocke les logs par `task_id`
   - Chaque log contient un timestamp et un message
   - Limite de 1000 logs par tâche pour éviter la surconsommation mémoire

2. **Fonction `_add_log()`**
   - Ajoute un log avec timestamp pour une tâche donnée
   - Affiche aussi le log dans la console Python
   - Gère automatiquement la limitation à 1000 logs

3. **Modification des `print()`**
   - Tous les `print()` dans `run_full_scrape()` ont été remplacés par `_add_log()`
   - Les logs sont maintenant capturés et stockés en mémoire

4. **Nouvel endpoint `/api/scrape/logs/{task_id}`**
   - Retourne tous les logs d'une tâche de scraping
   - Format : `{"task_id": int, "logs": [{"timestamp": "...", "message": "..."}, ...]}`

### Frontend (Interface Web)

1. **Zone terminal dans l'admin**
   - Ajout d'une section "Terminal" sous la tâche en cours
   - Style similaire à un terminal avec police monospace
   - Hauteur maximale de 400px avec scroll automatique
   - Bouton pour réduire/agrandir le terminal

2. **Polling des logs**
   - Fonction `loadScrapeLogs(taskId)` qui récupère les logs toutes les 2 secondes
   - Mise à jour incrémentale (seulement les nouveaux logs)
   - Auto-scroll vers le bas pour voir les derniers logs

3. **Affichage des logs**
   - Formatage avec couleurs selon le type de message :
     - ✅ Succès : vert (`var(--success)`)
     - ❌ Erreur : rouge (`var(--danger)`)
     - ⚠️ Warning : orange (`var(--warning)`)
     - [SCRAPE] : bleu (`var(--accent)`)
   - Timestamp affiché avant chaque message
   - Police monospace pour un rendu terminal

4. **Gestion de l'état**
   - Le terminal s'affiche automatiquement quand un scraping démarre
   - Le terminal se masque quand le scraping se termine
   - Le polling s'arrête automatiquement quand il n'y a plus de scraping

## Structure des logs

Chaque log contient :
```json
{
  "timestamp": "15:30:45",
  "message": "[SCRAPE] ✅ H004 - 150 joueurs, 145 fiches scrapées"
}
```

## Exemples de messages

- `[SCRAPE] Démarrage tâche #7 (trigger: cron)`
- `[SCRAPE] 608 clubs à traiter`
- `[SCRAPE] ✅ H004 - 150 joueurs, 145 fiches scrapées`
- `[SCRAPE] ❌ A000: Erreur timeout`
- `[WARNING] Erreur ranking_scraper pour H004: ...`
- `[SCRAPE] ✅ Tâche #7 terminée: 608 clubs, 30000 joueurs, 0 erreurs`

## Fichiers modifiés

- `src/api/app.py` :
  - Ajout du dictionnaire `_scrape_logs`
  - Fonction `_add_log()`
  - Remplacement des `print()` par `_add_log()`
  - Nouvel endpoint `/api/scrape/logs/{task_id}`

- `web/index.html` :
  - Ajout de la zone terminal dans la section admin
  - Fonctions `loadScrapeLogs()`, `startScrapeLogsPolling()`, `stopScrapeLogsPolling()`
  - Fonction `toggleTerminal()` pour réduire/agrandir
  - Intégration avec `loadScrapeStatus()` et `startFullScrape()`

## Utilisation

1. Aller dans la section **Admin** de l'interface web
2. Lancer un scraping complet
3. Le terminal s'affiche automatiquement sous les statistiques
4. Les logs s'affichent en temps réel avec mise à jour toutes les 2 secondes
5. Utiliser le bouton "Réduire/Agrandir" pour ajuster la taille du terminal

## Notes techniques

- Les logs sont stockés en mémoire et ne persistent pas après le redémarrage du serveur
- Limite de 1000 logs par tâche pour éviter la surconsommation mémoire
- Le polling se fait toutes les 2 secondes pour un bon compromis entre réactivité et charge serveur
- Les logs sont formatés avec des couleurs pour faciliter la lecture
- Auto-scroll vers le bas pour toujours voir les derniers logs

## Améliorations futures possibles

- Persistance des logs dans la base de données
- Export des logs en fichier texte
- Filtrage des logs par type (succès, erreurs, warnings)
- Recherche dans les logs
- Limite configurable du nombre de logs conservés

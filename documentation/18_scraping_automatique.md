# Scraping Automatique - Configuration

## Aperçu

Le système de scraping automatique permet de mettre à jour quotidiennement la base de données avec les dernières données du site AFTT.

## Architecture

- **Table `scrape_tasks`** : Stocke l'historique et le statut des tâches
- **Mode WAL SQLite** : Permet les lectures pendant les écritures
- **BackgroundTasks FastAPI** : Exécution non-bloquante du scraping

## Endpoints API

### Lancer un scraping complet

```http
POST /api/scrape/all?trigger=manual
```

Réponse :
```json
{
    "status": "started",
    "task_id": 1,
    "total_clubs": 531,
    "message": "Scraping de 531 clubs démarré en arrière-plan"
}
```

### Vérifier le statut

```http
GET /api/scrape/status
```

Réponse (en cours) :
```json
{
    "running": true,
    "task_id": 1,
    "started_at": "2026-01-16T02:00:00",
    "elapsed_seconds": 3600,
    "total_clubs": 531,
    "completed_clubs": 265,
    "total_players": 15000,
    "current_club": "H004",
    "current_province": "Hainaut",
    "errors_count": 2,
    "progress_percent": 49.9
}
```

### Historique des tâches

```http
GET /api/scrape/history?limit=20
```

### Annuler le scraping

```http
POST /api/scrape/cancel
```

## Configuration Coolify

### Étape 1 : Accéder aux paramètres Coolify

1. Ouvrir Coolify
2. Aller dans votre application
3. Cliquer sur **"Scheduled Tasks"** ou **"Cron Jobs"**

### Étape 2 : Créer les tâches planifiées

#### Tâche 1 : Scraping des clubs/joueurs (quotidien)

- **Nom** : `daily-scrape-clubs`
- **Schedule** : `0 2 * * *` (tous les jours à 2h du matin)
- **Command** :
  ```bash
  curl -X POST http://localhost:3000/api/scrape/all?trigger=cron
  ```

#### Tâche 2 : Scraping des tournois (hebdomadaire)

- **Nom** : `weekly-scrape-tournaments`
- **Schedule** : `0 3 * * 1` (tous les lundis à 3h du matin)
- **Command** :
  ```bash
  curl -X POST http://localhost:3000/api/scrape/tournaments
  ```

**Option B : Via Docker exec**

Si Coolify ne supporte pas les tâches HTTP :

Pour les clubs :
- **Schedule** : `0 2 * * *`
- **Command** :
  ```bash
  docker exec CONTAINER_NAME curl -X POST http://localhost:3000/api/scrape/all?trigger=cron
  ```

Pour les tournois :
- **Schedule** : `0 3 * * 1`
- **Command** :
  ```bash
  docker exec CONTAINER_NAME curl -X POST http://localhost:3000/api/scrape/tournaments
  ```

Remplacez `CONTAINER_NAME` par le nom de votre container.

### Étape 3 : Vérifier le port

Le port `3000` est celui injecté par Coolify via `$PORT`. Ajustez si nécessaire.

## Interface Admin

L'interface web inclut une section **Admin** accessible depuis le menu principal :

- **Bouton "Lancer scraping complet"** : Démarre le scraping des clubs/joueurs
- **Progression en temps réel** : Barre de progression, clubs/joueurs, erreurs
- **Historique** : Tableau avec toutes les tâches passées

### Section Tournois

L'interface web inclut également une section **Tournois** avec :

- **Bouton "Scraper les tournois"** : Lance le scraping complet des tournois
- **Progression en temps réel** : Tournois traités, séries, inscriptions
- **Liste des tournois** : Filtrable par niveau et recherche
- **Détails d'un tournoi** : Séries, inscriptions, résultats

## Comportement

### Durée estimée

**Scraping clubs/joueurs :**
- ~530 clubs
- ~30 000 joueurs
- Durée : **2-3 heures**

**Scraping tournois :**
- ~300 tournois
- ~2 500 séries
- ~6 700 inscriptions
- Durée : **15-30 minutes**

### Protection contre les doublons

- Si un scraping est déjà en cours, l'API retourne une erreur 409
- Les données existantes sont préservées (UPSERT avec COALESCE)

### Logs

Les logs sont visibles dans Coolify :
```
[SCRAPE] Démarrage tâche #1 (trigger: cron)
[SCRAPE] 531 clubs à traiter
[SCRAPE] ✅ H004 - 15000 joueurs total
...
[SCRAPE] ✅ Tâche #1 terminée: 531 clubs, 29086 joueurs, 0 erreurs
```

## Statuts des tâches

| Statut | Description |
|--------|-------------|
| `running` | En cours d'exécution |
| `success` | Terminé avec succès |
| `failed` | Erreur fatale |
| `cancelled` | Annulé manuellement |

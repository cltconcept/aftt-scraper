# Scraping des Tournois AFTT

## Aperçu

Ce document décrit le système de scraping des tournois AFTT depuis le site [resultats.aftt.be](https://resultats.aftt.be/?menu=7).

## Données récupérées

Le système scrape les informations suivantes pour chaque tournoi :

### Tournoi (liste principale)
- `t_id` : Identifiant unique du tournoi
- `name` : Nom du tournoi
- `level` : Niveau (Prov. Hainaut, National, Super Division, etc.)
- `date_start` / `date_end` : Dates du tournoi
- `reference` : Référence (ex: HAI-2026-03)
- `series_count` : Nombre de séries

### Séries
- `series_name` : Nom de la série
- `date` : Date de la série
- `time` : Heure de début
- `inscriptions_count` : Nombre d'inscrits
- `inscriptions_max` : Maximum d'inscrits

### Inscriptions
- `player_licence` : Numéro de licence du joueur
- `player_name` : Nom du joueur
- `player_club` : Club du joueur
- `player_ranking` : Classement du joueur
- `series_name` : Série dans laquelle le joueur est inscrit

### Résultats
- `player1_name` / `player2_name` : Noms des joueurs
- `player1_licence` / `player2_licence` : Licences
- `score` : Score du match
- `winner_licence` : Licence du vainqueur
- `round` : Tour (finale, demi-finale, etc.)

## Utilisation en ligne de commande

### Scraper la liste des tournois

```bash
python main.py tournaments
```

### Scraper les détails d'un tournoi spécifique

```bash
python main.py tournament 6310
```

## Endpoints API

### Liste des tournois

```http
GET /api/tournaments
```

Paramètres optionnels :
- `level` : Filtrer par niveau (ex: "Prov. Hainaut")
- `date_from` : Date de début (DD/MM/YYYY)
- `date_to` : Date de fin (DD/MM/YYYY)
- `search` : Recherche par nom ou référence
- `limit` : Nombre max de résultats
- `offset` : Pagination

Exemple de réponse :
```json
{
    "count": 300,
    "tournaments": [
        {
            "t_id": 6310,
            "name": "Castel Cup Phase 1 01/08/2025",
            "level": "Prov. Hainaut",
            "date_start": "01/08/2025",
            "date_end": "01/08/2025",
            "reference": "HAI-2026-03 1",
            "series_count": 1
        }
    ]
}
```

### Liste des niveaux disponibles

```http
GET /api/tournaments/levels
```

### Détails d'un tournoi

```http
GET /api/tournaments/{t_id}
```

### Séries d'un tournoi

```http
GET /api/tournaments/{t_id}/series
```

### Inscriptions d'un tournoi

```http
GET /api/tournaments/{t_id}/inscriptions
GET /api/tournaments/{t_id}/inscriptions?series_name=Castel%20Cup
```

### Résultats d'un tournoi

```http
GET /api/tournaments/{t_id}/results
GET /api/tournaments/{t_id}/results?series_name=Castel%20Cup
```

## Scraping via l'API

### Lancer un scraping complet des tournois

```http
POST /api/scrape/tournaments
```

Réponse :
```json
{
    "status": "started",
    "task_id": "tournaments_20260118_121500",
    "message": "Scraping des tournois démarré en arrière-plan"
}
```

### Vérifier le statut du scraping

```http
GET /api/scrape/tournaments/status
```

Réponse (en cours) :
```json
{
    "running": true,
    "task_id": "tournaments_20260118_121500",
    "status": "running",
    "started_at": "2026-01-18T12:15:00",
    "elapsed_seconds": 120,
    "total_tournaments": 300,
    "completed_tournaments": 50,
    "total_series": 250,
    "total_inscriptions": 1500,
    "total_results": 3000,
    "current_tournament": "Castel Cup Phase 1",
    "errors_count": 0,
    "progress_percent": 16.7
}
```

### Récupérer les logs du scraping

```http
GET /api/scrape/tournaments/logs/{task_id}
```

### Scraper un tournoi individuel

```http
POST /api/tournaments/{t_id}/scrape
```

## Configuration Cron

Pour scraper automatiquement les tournois, ajouter une tâche cron dans Coolify :

```bash
# Tous les lundis à 3h du matin
0 3 * * 1 curl -X POST http://localhost:3000/api/scrape/tournaments
```

Ou utiliser deux tâches séparées :
1. Scraping des clubs/joueurs : tous les jours à 2h
2. Scraping des tournois : tous les lundis à 3h

## Base de données

### Tables créées

- `tournaments` : Liste des tournois
- `tournament_series` : Séries de chaque tournoi
- `tournament_inscriptions` : Inscriptions aux tournois
- `tournament_results` : Résultats des matchs

### Requêtes utiles

```sql
-- Nombre de tournois par niveau
SELECT level, COUNT(*) as count 
FROM tournaments 
GROUP BY level 
ORDER BY count DESC;

-- Joueurs les plus actifs en tournoi
SELECT player_name, player_licence, COUNT(*) as inscriptions
FROM tournament_inscriptions
GROUP BY player_licence
ORDER BY inscriptions DESC
LIMIT 20;

-- Tournois à venir
SELECT * FROM tournaments
WHERE date_start >= date('now')
ORDER BY date_start;
```

## Estimations

- ~300 tournois par saison
- ~2500 séries
- ~6700 joueurs inscrits
- ~38000 résultats

Le scraping complet prend environ **15-30 minutes** selon la connexion.

## Points techniques

### Pagination
La page des tournois est paginée (15 pages). Le scraper récupère automatiquement toutes les pages.

### Gestion des dates
Les dates peuvent être au format :
- Simple : `05/07/2025`
- Plage : `26/07-27/07/2025`

Le scraper parse automatiquement les deux formats.

### Erreurs
Les erreurs de scraping d'un tournoi individuel n'interrompent pas le processus global. Elles sont enregistrées dans les logs et le statut.

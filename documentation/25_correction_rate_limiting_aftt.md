# Correction du Rate Limiting AFTT et Affichage Temps Réel

## Résumé de la demande

L'utilisateur a signalé que les résultats des joueurs ne se mettaient pas à jour sur le site, même si les scrapes cron s'exécutaient avec succès. Il voulait aussi voir en direct les données récupérées pendant le scraping.

## Résumé de la solution

Le problème était causé par le **rate limiting du serveur AFTT** (`data.aftt.be`). Le serveur refuse parfois les connexions quand il reçoit trop de requêtes en peu de temps, ce qui faisait échouer silencieusement le scraping des fiches individuelles des joueurs.

### Modifications apportées

#### 1. `src/scraper/player_scraper.py`
- Ajout de **retries avec délai exponentiel** (3 tentatives par défaut)
- Délais de 2s, 4s, 8s entre les tentatives
- Meilleure gestion des erreurs avec logging détaillé

#### 2. `src/scraper/members_scraper.py`
- Ajout de **retries avec délai exponentiel** (3 tentatives par défaut)
- Même logique que pour les fiches joueurs

#### 3. `src/api/app.py`
- Ajout de **compteurs de matchs scrapés** pour mieux diagnostiquer
- Nouvel endpoint **`/api/stats/detailed`** pour le diagnostic
- **Délai de 0.3s** entre chaque fiche de joueur scrapée
- **Délai de 1s** entre chaque club
- **Délai de 2s** après une erreur pour laisser le serveur récupérer
- **Logs détaillés en temps réel** avec données des joueurs et matchs

#### 4. `web/index.html`
- **Terminal amélioré** avec couleurs par type de log
- **Affichage en temps réel** des données récupérées :
  - Nom du joueur, classement, points
  - Bilan victoires/défaites
  - Derniers matchs avec adversaires et scores
- **Rafraîchissement toutes les secondes** (au lieu de 2s)
- **Terminal plus grand** (600px au lieu de 400px)

## Points techniques importants

### Problème identifié
```
Max retries exceeded with url: /annuaire/membres.php 
(Caused by NewConnectionError: Failed to establish a new connection: [Errno 111] Connection refused)
```

Le serveur AFTT applique du rate limiting et refuse les connexions quand il est surchargé.

### Solution technique
```python
# Retries avec délai exponentiel
for attempt in range(max_retries):
    try:
        if attempt > 0:
            delay = 2 ** attempt  # 2s, 4s, 8s...
            time.sleep(delay)
        response = requests.get(url, params=params, headers=headers, timeout=30)
        return response.text
    except requests.RequestException as e:
        last_error = e
raise last_error
```

### Impact sur le temps de scraping
- Avant : ~3h30 pour 608 clubs et ~32000 joueurs
- Après : Le scraping sera plus lent mais plus fiable
- Les nouveaux délais ajoutent environ ~3 heures supplémentaires
- Total estimé : ~6-7 heures pour un scraping complet

## Contexte

Le scraping doit récupérer pour chaque joueur :
- Informations de base (licence, nom, classement, points)
- Tous les matchs joués (date, adversaire, score, points gagnés/perdus)
- Statistiques par classement (victoires/défaites contre chaque classement)

## Comment vérifier que ça fonctionne

1. Appeler `/api/stats/detailed` pour voir les statistiques complètes
2. Vérifier qu'un joueur spécifique a ses matchs récents : `/api/players/{licence}`
3. Regarder les logs du scraping pour voir le nombre de matchs scrapés

## Exemple de logs en temps réel

Le terminal affiche maintenant les données récupérées en direct :

```
[02:15:32] [SCRAPE] Démarrage tâche #25 (trigger: manual)
[02:15:32] [SCRAPE] 608 clubs à traiter
[02:15:35] [DB] ✅ Club H004 (CP Binchois) sauvegardé

[02:15:36] [JOUEUR] 👤 176506 - CHRISTOPHER DEBESSEL (NC) | 79pts | 12V-22D | 30 matchs
  └─ ✅ 24/01/2026 vs MAEL ALLAERT 3-0 (+5.1pts)
  └─ ✅ 24/01/2026 vs ADRIEN HANOTIÈRE 3-0 (+5.1pts)
  └─ ❌ 24/01/2026 vs NICOLAS MARQUET 1-3 (-2.7pts)

[02:15:38] [JOUEUR] 👤 152174 - KEVIN BRULEZ (C2) | 512pts | 45V-12D | 57 matchs
  └─ ✅ 24/01/2026 vs PIERRE MARTIN 3-1 (+8.2pts)
  └─ ✅ 24/01/2026 vs JEAN DUPONT 3-0 (+6.5pts)
  └─ ✅ 24/01/2026 vs LUC DURAND 3-2 (+9.1pts)

[02:16:45] [SCRAPE] ✅ H004 | 52 joueurs | 48 fiches | Total matchs global: 1247
```

Les couleurs indiquent :
- 🔵 **Bleu** : Nouveau joueur scrapé avec ses stats
- 🟢 **Vert** : Victoire
- 🔴 **Rouge** : Défaite
- 🟣 **Violet** : Club sauvegardé
- 🟢 **Vert fond** : Club terminé avec succès

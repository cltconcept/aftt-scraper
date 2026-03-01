#!/usr/bin/env python3
"""
AFTT Database Builder
=====================
Point d'entrée principal pour le scraping des données AFTT et l'API.

Ce script peut être exécuté :
- Localement : python main.py
- Via Docker : docker run aftt-scraper
- Via Coolify : déploiement automatique

Usage:
    python main.py                    # Scrape tous les clubs
    python main.py clubs              # Scrape uniquement la liste des clubs
    python main.py members H004       # Scrape les membres du club H004
    python main.py members all        # Scrape les membres de tous les clubs
    python main.py player 152174      # Scrape la fiche du joueur (licence)
    python main.py tournaments        # Scrape tous les tournois (liste)
    python main.py tournament 6310    # Scrape les détails d'un tournoi
    python main.py import             # Importe les JSON dans SQLite
    python main.py api                # Lance l'API FastAPI
"""

import sys
import os

# Fix encodage Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Ajouter le répertoire racine et src/ au path
sys.path.insert(0, os.path.dirname(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.logging_config import setup_logging
setup_logging()

from scraper.clubs_scraper import main as scrape_clubs, get_all_clubs
from scraper.members_scraper import main as scrape_members, get_club_members, save_members_to_json
from scraper.player_scraper import main as scrape_player, get_player_info
from scraper.tournament_scraper import main as scrape_tournament, get_all_tournaments, get_tournament_details
from scraper.interclubs_scraper import scrape_all_interclubs_rankings


def scrape_all_members():
    """Scrape les membres de tous les clubs."""
    import json
    
    # Charger la liste des clubs
    clubs_file = "data/clubs.json"
    if not os.path.exists(clubs_file):
        print("[INFO] Liste des clubs non trouvee, recuperation en cours...")
        scrape_clubs()
    
    with open(clubs_file, 'r', encoding='utf-8') as f:
        clubs = json.load(f)
    
    print(f"\n[INFO] Scraping des membres de {len(clubs)} clubs...")
    
    all_members = {}
    errors = []
    
    for i, club in enumerate(clubs, 1):
        code = club['code']
        name = club['name']
        
        # Skip les clubs "Individueel" ou génériques
        if 'individueel' in name.lower() or 'indiv.' in name.lower():
            continue
        
        print(f"  [{i}/{len(clubs)}] {code} - {name}...", end=" ", flush=True)
        
        try:
            members = get_club_members(code)
            count = len(members.get('members', []))
            all_members[code] = members
            save_members_to_json(members, code)
            print(f"{count} membres")
        except Exception as e:
            errors.append((code, str(e)))
            print(f"ERREUR: {e}")
    
    print(f"\n[OK] Scraping termine: {len(all_members)} clubs traites, {len(errors)} erreurs")
    
    if errors:
        print("\nErreurs rencontrees:")
        for code, err in errors[:10]:
            print(f"  - {code}: {err}")
    
    return all_members


def import_to_database():
    """Importe tous les fichiers JSON dans la base SQLite."""
    from database.import_json import import_all
    
    print("\n[IMPORT] Import des donnees JSON vers SQLite...")
    stats = import_all("data")
    
    print("\n[OK] Import termine !")
    return stats


def run_api(host: str = "0.0.0.0", port: int = 8000, reload: bool = False):
    """Lance l'API FastAPI."""
    import uvicorn
    
    print(f"\n[API] Demarrage de l'API sur http://{host}:{port}")
    print(f"[API] Documentation: http://{host}:{port}/docs")
    print("=" * 50)
    
    uvicorn.run("src.api.app:app", host=host, port=port, reload=reload)


def show_help():
    """Affiche l'aide."""
    help_text = """
AFTT Database Builder - Commandes disponibles
==============================================

SCRAPING (récupération des données):
  python main.py clubs              Liste de tous les clubs
  python main.py members H004       Membres d'un club spécifique
  python main.py members all        Membres de tous les clubs
  python main.py player 152174      Fiche d'un joueur
  python main.py tournaments        Liste de tous les tournois
  python main.py tournament 6310    Détails d'un tournoi spécifique
  python main.py interclubs         Classements interclubs (toutes divisions, semaines 1-22)
  python main.py interclubs --weeks 1,2 --divisions 5,10   Filtrage optionnel

DATABASE (stockage):
  python main.py import             Importe les JSON dans SQLite
  python main.py import --reset     Réinitialise la base avant import

API (serveur REST):
  python main.py api                Lance l'API sur le port 8000
  python main.py api --port 3000    Lance l'API sur un port spécifique

EXEMPLES:
  # Workflow complet
  python main.py clubs              # 1. Récupérer les clubs
  python main.py members H004       # 2. Récupérer les membres
  python main.py player 152174      # 3. Récupérer une fiche joueur
  python main.py tournaments        # 4. Récupérer les tournois
  python main.py interclubs         # 5. Récupérer les classements interclubs
  python main.py import             # 6. Importer dans SQLite
  python main.py api                # 7. Lancer l'API
"""
    print(help_text)


def run():
    """Exécute le scraping selon les arguments."""
    args = sys.argv[1:]
    
    print("\n🏓 AFTT Database Builder")
    print("=" * 50)
    
    if not args:
        # Mode par defaut: scrape les clubs
        print("\n[ETAPE 1] Recuperation des clubs...")
        scrape_clubs()
        print("\n[OK] Scraping termine avec succes !")
        
    elif args[0] in ["help", "-h", "--help"]:
        show_help()
        
    elif args[0] == "clubs":
        print("\n[ETAPE] Recuperation des clubs...")
        scrape_clubs()
        
    elif args[0] == "members":
        if len(args) < 2:
            print("Usage: python main.py members <club_code|all>")
            sys.exit(1)
        
        club_code = args[1]
        
        if club_code.lower() == "all":
            print("\n[ETAPE] Recuperation des membres de tous les clubs...")
            scrape_all_members()
        else:
            print(f"\n[ETAPE] Recuperation des membres du club {club_code}...")
            scrape_members(club_code)
    
    elif args[0] == "player":
        if len(args) < 2:
            print("Usage: python main.py player <licence>")
            sys.exit(1)
        
        licence = args[1]
        print(f"\n[ETAPE] Recuperation de la fiche du joueur {licence}...")
        scrape_player(licence)
    
    elif args[0] == "tournaments":
        print("\n[ETAPE] Recuperation de la liste des tournois...")
        tournaments = get_all_tournaments()
        print(f"\n{len(tournaments)} tournois trouves")
        print("\nExemple des 10 premiers tournois :")
        print("-"*60)
        for t in tournaments[:10]:
            print(f"  [{t.t_id}] {t.name} ({t.level}) - {t.date_start}")
        print("  ...")
        print(f"\n[OK] Liste des tournois recuperee !")
    
    elif args[0] == "tournament":
        if len(args) < 2:
            print("Usage: python main.py tournament <t_id>")
            sys.exit(1)
        
        t_id = int(args[1])
        print(f"\n[ETAPE] Recuperation des details du tournoi {t_id}...")
        scrape_tournament(t_id)
    
    elif args[0] == "interclubs":
        print("\n[ETAPE] Recuperation des classements interclubs...")

        # Initialiser la base de donnees pour les nouvelles tables
        from database.connection import init_database
        init_database()

        # Parser les arguments optionnels
        weeks = None
        division_indices = None

        for i, arg in enumerate(args):
            if arg == '--weeks' and i + 1 < len(args):
                weeks = []
                for part in args[i + 1].split(','):
                    part = part.strip()
                    if '-' in part:
                        start, end = part.split('-', 1)
                        weeks.extend(range(int(start), int(end) + 1))
                    else:
                        weeks.append(int(part))
            elif arg == '--divisions' and i + 1 < len(args):
                division_indices = [int(d.strip()) for d in args[i + 1].split(',')]

        def print_callback(msg):
            print(msg)

        stats = scrape_all_interclubs_rankings(
            callback=print_callback,
            weeks=weeks,
            division_indices=division_indices,
        )

        print(f"\n[OK] Scraping interclubs termine !")
        print(f"  Divisions: {stats['total_divisions']}")
        print(f"  Classements: {stats['total_rankings']}")
        print(f"  Erreurs: {len(stats['errors'])}")

    elif args[0] == "import":
        reset = "--reset" in args
        if reset:
            from database.connection import reset_database
            print("\n[RESET] Reinitialisation de la base de donnees...")
            reset_database()
        import_to_database()
    
    elif args[0] == "api":
        # Parser les arguments (variable d'env PORT prioritaire pour Coolify/Docker)
        port = int(os.environ.get("PORT", 8000))
        host = os.environ.get("HOST", "0.0.0.0")
        
        for i, arg in enumerate(args):
            if arg == "--port" and i + 1 < len(args):
                port = int(args[i + 1])
            elif arg == "--host" and i + 1 < len(args):
                host = args[i + 1]
        
        run_api(host=host, port=port)
    
    else:
        print(f"Commande inconnue: {args[0]}")
        print("Utilisez 'python main.py help' pour voir les commandes disponibles.")
        sys.exit(1)
    
    print("=" * 50)


if __name__ == "__main__":
    run()

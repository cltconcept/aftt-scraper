# -*- coding: utf-8 -*-
"""
AFTT Interclubs Rankings Scraper
=================================
Scrape les classements des equipes par division et par semaine
depuis https://data.aftt.be/interclubs/rankings_division.php

Utilise Playwright avec UNE SEULE session navigateur pour les ~8800 pages.
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import time
import logging
import asyncio
from typing import List, Dict, Optional, Callable

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.models import InterclubsDivision, InterclubsRanking

logger = logging.getLogger(__name__)

RANKINGS_URL = "https://data.aftt.be/interclubs/rankings_division.php"
MAX_RETRIES = 3
BASE_DELAY = 2.0
PAGE_DELAY = 0.5


def _extract_divisions(page) -> List[InterclubsDivision]:
    """Extrait toutes les divisions du <select id='divisionSelect'> via Playwright.

    Utilise page.evaluate() pour lire directement le DOM (y compris les valeurs
    generees par JavaScript).
    """
    options_data = page.evaluate("""
        () => {
            const select = document.getElementById('divisionSelect');
            if (!select) return [];
            return Array.from(select.options).map((o, i) => ({
                index: i,
                value: o.value,
                text: o.text.trim()
            }));
        }
    """)

    if not options_data:
        logger.error("Aucun <select> divisionSelect trouve sur la page")
        return []

    divisions = []

    for opt in options_data:
        text = opt['text']

        if not text or text.startswith('--') or 'lectionner' in text.lower():
            continue

        # Extraire categorie et genre du nom
        category = None
        gender = None

        if ' - ' in text:
            parts = [p.strip() for p in text.split(' - ')]
            if len(parts) >= 2:
                category = parts[1]
            if len(parts) >= 3:
                gender = parts[2]

        division = InterclubsDivision(
            division_index=opt['index'],
            division_id=str(opt['value']) if opt['value'] else None,
            division_name=text,
            division_category=category,
            division_gender=gender,
        )
        divisions.append(division)

    logger.info(f"{len(divisions)} divisions trouvees")
    return divisions


def _navigate_to_division_week(page, division_index: int, week: int):
    """Navigue vers une division/semaine specifique.

    division_index est l'index positionnel dans le <select>.
    On utilise expect_navigation pour attendre le rechargement apres form.submit().
    """
    # Valider les entrées (protection contre injection)
    division_index = int(division_index)
    week = int(week)

    # Selectionner la division et soumettre
    with page.expect_navigation(wait_until='networkidle', timeout=15000):
        page.evaluate("""
            (divIdx) => {
                const select = document.getElementById('divisionSelect');
                if (select) {
                    select.selectedIndex = divIdx;
                    select.dispatchEvent(new Event('change', { bubbles: true }));
                    if (select.form) {
                        select.form.submit();
                    }
                }
            }
        """, division_index)
    # Attendre le rendu JS du contenu
    try:
        page.wait_for_selector('table', timeout=5000)
    except TimeoutError:
        pass
    page.wait_for_timeout(500)

    # Modifier la semaine et soumettre
    with page.expect_navigation(wait_until='networkidle', timeout=15000):
        page.evaluate("""
            (weekNum) => {
                const weekInput = document.getElementById('week-input');
                const weekSelect = document.getElementById('week-select');
                if (weekInput) {
                    weekInput.value = String(weekNum);
                }
                if (weekSelect) {
                    weekSelect.value = String(weekNum);
                }
                const form = document.getElementById('week-form');
                if (form) {
                    form.submit();
                }
            }
        """, week)

    # Attendre que le tableau soit rendu
    try:
        page.wait_for_selector('table', timeout=5000)
    except TimeoutError:
        # Certaines divisions (coupes) n'ont pas de tableau de classement
        pass
    page.wait_for_timeout(500)


def _parse_rankings_table(html: str, division_index: int, division_name: str, week: int) -> List[InterclubsRanking]:
    """Parse le tableau HTML des classements.

    Colonnes attendues: #, Equipe, J, G, P, N, FF, Pts
    La table a les classes: table table-sm table-striped text-center
    """
    soup = BeautifulSoup(html, 'html.parser')
    rankings = []

    # Chercher le tableau de classement (class="table ...")
    table = soup.find('table', class_='table')
    if not table:
        tables = soup.find_all('table')
        for t in tables:
            headers = t.find_all('th')
            header_texts = [h.get_text(strip=True).lower() for h in headers]
            if any(h in header_texts for h in ['equipe', 'équipe', 'team', 'pts', 'j']):
                table = t
                break

    if not table:
        return rankings

    # Verifier que c'est un tableau de classement et pas de resultats
    headers = table.find_all('th')
    header_texts = [h.get_text(strip=True).lower() for h in headers]
    if not any(h in header_texts for h in ['equipe', 'équipe', 'team']):
        return rankings

    rows = table.find_all('tr')
    for row in rows:
        cells = row.find_all('td')
        if len(cells) < 8:
            continue

        try:
            cell_texts = [c.get_text(strip=True) for c in cells]

            rank_str = cell_texts[0]
            rank = int(rank_str) if rank_str.isdigit() else None

            team_name = cell_texts[1]
            if not team_name:
                continue

            played = int(cell_texts[2]) if cell_texts[2].isdigit() else 0
            wins = int(cell_texts[3]) if cell_texts[3].isdigit() else 0
            losses = int(cell_texts[4]) if cell_texts[4].isdigit() else 0
            draws = int(cell_texts[5]) if cell_texts[5].isdigit() else 0
            forfeits = int(cell_texts[6]) if cell_texts[6].isdigit() else 0
            points = int(cell_texts[7]) if cell_texts[7].isdigit() else 0

            ranking = InterclubsRanking(
                division_index=division_index,
                division_name=division_name,
                week=week,
                rank=rank,
                team_name=team_name,
                played=played,
                wins=wins,
                losses=losses,
                draws=draws,
                forfeits=forfeits,
                points=points,
            )
            rankings.append(ranking)

        except Exception as e:
            logger.debug(f"Erreur parsing ligne: {e}")

    return rankings


def scrape_all_interclubs_rankings(
    callback: Optional[Callable] = None,
    weeks: Optional[List[int]] = None,
    division_indices: Optional[List[int]] = None,
    delay: float = PAGE_DELAY,
    resume_from: Optional[Dict] = None,
    is_cancelled: Optional[Callable] = None,
) -> Dict:
    """
    Scrape tous les classements interclubs.

    Args:
        callback: Fonction appelee avec (message, data) pour le suivi
        weeks: Liste des semaines a scraper (defaut: 1-22)
        division_indices: Liste des indices de division (defaut: toutes)
        delay: Delai entre chaque page en secondes
        resume_from: Dict {'division_index': X, 'week': Y} pour reprendre

    Returns:
        Dict avec statistiques du scraping
    """
    if weeks is None:
        weeks = list(range(1, 23))

    def log(msg):
        logger.info(msg)
        if callback:
            callback(msg)

    stats = {
        'total_divisions': 0,
        'total_weeks': len(weeks),
        'total_rankings': 0,
        'errors': [],
        'last_success': None,
    }

    # Import ici pour eviter les imports circulaires
    from src.database import queries

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # 1. Charger la page initiale
            log("[INTERCLUBS] Chargement de la page rankings_division.php...")
            page.goto(RANKINGS_URL, timeout=30000)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)

            # 2. Extraire les divisions
            divisions = _extract_divisions(page)
            stats['total_divisions'] = len(divisions)

            if not divisions:
                log("[INTERCLUBS] Aucune division trouvee!")
                return stats

            # Sauvegarder les divisions en base
            for div in divisions:
                queries.insert_interclubs_division(div.to_dict())

            log(f"[INTERCLUBS] {len(divisions)} divisions sauvegardees")

            # Filtrer les divisions si demande
            if division_indices:
                divisions = [d for d in divisions if d.division_index in division_indices]
                log(f"[INTERCLUBS] Filtrage: {len(divisions)} divisions selectionnees")

            # Resume: ignorer les divisions/semaines deja scrapees
            skip_until = None
            if resume_from:
                skip_until = (resume_from.get('division_index'), resume_from.get('week'))
                log(f"[INTERCLUBS] Reprise depuis division {skip_until[0]}, semaine {skip_until[1]}")

            total_combos = len(divisions) * len(weeks)
            completed = 0
            skipping = skip_until is not None

            # 3. Pour chaque division
            for div_idx, division in enumerate(divisions):
                for week in weeks:
                    # Vérifier annulation
                    if is_cancelled and is_cancelled():
                        log("[INTERCLUBS] Scraping annulé par l'utilisateur")
                        return stats

                    # Skip si resume
                    if skipping:
                        if division.division_index == skip_until[0] and week == skip_until[1]:
                            skipping = False
                        else:
                            completed += 1
                            continue

                    completed += 1
                    pct = round(completed / total_combos * 100, 1)

                    retries = 0
                    success = False

                    while retries < MAX_RETRIES and not success:
                        try:
                            _navigate_to_division_week(page, division.division_index, week)
                            html = page.content()

                            rankings = _parse_rankings_table(
                                html, division.division_index, division.division_name, week
                            )

                            # Sauvegarder en base
                            if rankings:
                                queries.insert_interclubs_rankings_batch(
                                    [r.to_dict() for r in rankings]
                                )
                                stats['total_rankings'] += len(rankings)

                            stats['last_success'] = {
                                'division_index': division.division_index,
                                'week': week,
                            }

                            log(f"[INTERCLUBS] [{pct}%] Div {division.division_index} ({division.division_name[:40]}) Sem {week}: {len(rankings)} equipes")

                            success = True
                            time.sleep(delay)

                        except Exception as e:
                            retries += 1
                            wait = BASE_DELAY * (2 ** (retries - 1))
                            error_msg = f"Erreur div {division.division_index} sem {week} (retry {retries}/{MAX_RETRIES}): {e}"
                            logger.warning(error_msg)

                            if retries < MAX_RETRIES:
                                time.sleep(wait)
                                # Recharger la page en cas d'erreur
                                try:
                                    page.goto(RANKINGS_URL, timeout=30000)
                                    page.wait_for_load_state('networkidle')
                                    page.wait_for_timeout(1000)
                                except Exception:
                                    logger.warning("Echec du rechargement de la page après erreur")
                                    pass
                            else:
                                stats['errors'].append(error_msg)
                                log(f"[INTERCLUBS] ERREUR: {error_msg}")

            log(f"[INTERCLUBS] Termine: {stats['total_rankings']} classements, {len(stats['errors'])} erreurs")

        except Exception as e:
            log(f"[INTERCLUBS] Erreur fatale: {e}")
            stats['errors'].append(str(e))
            raise
        finally:
            browser.close()

    return stats


async def scrape_all_interclubs_rankings_async(
    callback: Optional[Callable] = None,
    weeks: Optional[List[int]] = None,
    division_indices: Optional[List[int]] = None,
    delay: float = PAGE_DELAY,
    resume_from: Optional[Dict] = None,
    is_cancelled: Optional[Callable] = None,
) -> Dict:
    """Wrapper async pour utilisation dans FastAPI."""
    return await asyncio.to_thread(
        scrape_all_interclubs_rankings,
        callback=callback,
        weeks=weeks,
        division_indices=division_indices,
        delay=delay,
        resume_from=resume_from,
        is_cancelled=is_cancelled,
    )


if __name__ == "__main__":
    import sys

    print("\nAFFT Interclubs Rankings Scraper")
    print("=" * 50)

    # Arguments optionnels
    weeks = None
    division_indices = None

    if len(sys.argv) > 1:
        # python interclubs_scraper.py --weeks 1,2 --divisions 5,10
        args = sys.argv[1:]
        for i, arg in enumerate(args):
            if arg == '--weeks' and i + 1 < len(args):
                weeks = [int(w) for w in args[i + 1].split(',')]
            elif arg == '--divisions' and i + 1 < len(args):
                division_indices = [int(d) for d in args[i + 1].split(',')]

    def print_callback(msg):
        print(msg)

    stats = scrape_all_interclubs_rankings(
        callback=print_callback,
        weeks=weeks,
        division_indices=division_indices,
    )

    print(f"\nResultats:")
    print(f"  Divisions: {stats['total_divisions']}")
    print(f"  Classements: {stats['total_rankings']}")
    print(f"  Erreurs: {len(stats['errors'])}")

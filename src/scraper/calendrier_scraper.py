# -*- coding: utf-8 -*-
"""
AFTT Interclubs Calendar Scraper
==================================
Scrape le calendrier des matchs interclubs depuis
https://resultats.aftt.be/calendriers

Utilise Playwright car le dropdown de division est un composant JS.
Optimisation : toutes les semaines sont affichees sur une seule page
par division → ~200 pages au total (pas 200x22).
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import time
import logging
import asyncio
from typing import List, Dict, Optional, Callable

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.database.models import InterclubsMatch

logger = logging.getLogger(__name__)

CALENDRIER_URL = "https://resultats.aftt.be/calendriers"
MAX_RETRIES = 3
BASE_DELAY = 2.0
PAGE_DELAY = 0.5

# Mapping jours abreges FR -> rien (on n'en a pas besoin pour le parsing)
DAY_ABBREVS = {'Lu', 'Ma', 'Me', 'Je', 'Ve', 'Sa', 'Di'}

# Regex pour parser les dates: "Sa 13-09-25 / 19:00" ou "Sa 13-09-25"
DATE_PATTERN = re.compile(
    r'(?:\*\*\s*)?'           # ** optionnel (matchs reportes)
    r'([A-Za-z]{2})\s+'      # Jour abrege (Sa, Di, etc.)
    r'(\d{2})-(\d{2})-(\d{2})'  # DD-MM-YY
    r'(?:\s*/\s*(\d{2}:\d{2}))?'  # / HH:MM optionnel
    r'(?:\s*\*\*)?'           # ** optionnel fin
)

# Regex pour les en-tetes de semaine: "Semaine 01 : Du 08-09-2025 au 14-09-2025"
WEEK_PATTERN = re.compile(
    r'Semaine\s+(\d+)\s*:\s*Du\s+(\d{2}-\d{2}-\d{4})\s+au\s+(\d{2}-\d{2}-\d{4})'
)

# Regex pour score: "10-6", "16-0", etc.
SCORE_PATTERN = re.compile(r'^(\d+)\s*-\s*(\d+)$')


def _extract_divisions(page) -> List[dict]:
    """Extrait les divisions du dropdown JS.

    Le dropdown sur resultats.aftt.be utilise un composant JS avec recherche.
    On utilise page.evaluate() pour lire les options.
    """
    # Attendre que le dropdown soit charge
    try:
        page.wait_for_selector('select, .select2, .chosen-select, [data-toggle="dropdown"]', timeout=10000)
    except Exception:
        pass

    # Essayer plusieurs strategies pour trouver le dropdown
    options_data = page.evaluate("""
        () => {
            // Strategie 1: select standard
            const selects = document.querySelectorAll('select');
            for (const select of selects) {
                const opts = Array.from(select.options);
                if (opts.length > 5) {
                    return opts.map((o, i) => ({
                        index: i,
                        value: o.value,
                        text: o.text.trim()
                    }));
                }
            }

            // Strategie 2: select2 ou autre plugin
            const select2 = document.querySelector('.select2-hidden-accessible');
            if (select2) {
                return Array.from(select2.options).map((o, i) => ({
                    index: i,
                    value: o.value,
                    text: o.text.trim()
                }));
            }

            return [];
        }
    """)

    if not options_data:
        logger.error("Aucun dropdown de divisions trouve sur la page")
        return []

    divisions = []
    for opt in options_data:
        text = opt['text']
        if not text or text.startswith('--') or 'lectionner' in text.lower() or 'choisir' in text.lower():
            continue

        # Extraire categorie du nom de division
        category = None
        if ' - ' in text:
            parts = [p.strip() for p in text.split(' - ')]
            if len(parts) >= 2:
                category = parts[1]

        divisions.append({
            'index': opt['index'],
            'value': opt['value'],
            'name': text,
            'category': category,
        })

    logger.info(f"{len(divisions)} divisions trouvees dans le calendrier")
    return divisions


def _select_division(page, division_value: str, division_index: int):
    """Selectionne une division dans le dropdown JS et attend le rechargement."""
    try:
        # Essayer de selectionner par valeur dans un select standard
        page.evaluate("""
            (args) => {
                const selects = document.querySelectorAll('select');
                for (const select of selects) {
                    if (select.options.length > 5) {
                        select.value = args.value;
                        select.dispatchEvent(new Event('change', { bubbles: true }));
                        if (select.form) {
                            select.form.submit();
                        }
                        return true;
                    }
                }
                return false;
            }
        """, {"value": division_value, "index": division_index})

        # Attendre le rechargement de la page
        page.wait_for_load_state('networkidle', timeout=15000)
        page.wait_for_timeout(1000)

    except Exception as e:
        logger.warning(f"Erreur selection division (index={division_index}): {e}")
        # Fallback: naviguer directement avec URL si possible
        try:
            url = f"{CALENDRIER_URL}?div={division_value}"
            page.goto(url, timeout=15000)
            page.wait_for_load_state('networkidle', timeout=15000)
            page.wait_for_timeout(1000)
        except Exception as e2:
            logger.error(f"Fallback URL aussi echoue: {e2}")
            raise


def _parse_date(date_str: str):
    """Parse une date du calendrier AFTT.

    Formats possibles:
    - "Sa 13-09-25 / 19:00"
    - "Di 14-09-25"
    - "** Sa 13-09-25 / 19:00 **" (match reporte)

    Retourne (date_iso, time_str, is_modified)
    """
    if not date_str:
        return None, None, False

    date_str = date_str.strip()
    is_modified = '**' in date_str

    match = DATE_PATTERN.search(date_str)
    if not match:
        return None, None, is_modified

    day_abbr, dd, mm, yy = match.group(1), match.group(2), match.group(3), match.group(4)
    time_str = match.group(5)

    # Convertir YY en YYYY (25 -> 2025)
    year = int(yy)
    if year < 50:
        year += 2000
    else:
        year += 1900

    date_iso = f"{year}-{mm}-{dd}"

    return date_iso, time_str, is_modified


def _parse_score(score_str: str):
    """Parse un score de match (ex: '10-6').

    Retourne (score, home_score, away_score) ou (None, None, None).
    """
    if not score_str:
        return None, None, None

    score_str = score_str.strip()
    match = SCORE_PATTERN.match(score_str)
    if match:
        home = int(match.group(1))
        away = int(match.group(2))
        return score_str, home, away

    return None, None, None


def _parse_calendar_page(html: str, division_name: str, division_category: str = None) -> List[InterclubsMatch]:
    """Parse TOUTES les semaines du calendrier d'une division.

    La page affiche toutes les semaines avec des blocs:
    - En-tete: "Semaine XX : Du DD-MM-YYYY au DD-MM-YYYY"
    - Tableau: Match | Date | Visites | Visiteurs (ou similaire)
    """
    soup = BeautifulSoup(html, 'html.parser')
    matches = []

    # Chercher tous les blocs de semaine
    # Strategie: chercher les en-tetes de semaine, puis les tableaux qui suivent
    current_week = None
    current_week_from = None
    current_week_to = None

    # Parcourir tous les elements pour trouver les semaines et tableaux
    # Les semaines peuvent etre dans des <h3>, <h4>, <div>, <p> etc.
    all_text_elements = soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'div', 'p', 'span', 'strong', 'b'])

    # Map: element -> week info
    week_headers = {}
    for elem in all_text_elements:
        text = elem.get_text(strip=True)
        week_match = WEEK_PATTERN.search(text)
        if week_match:
            week_headers[id(elem)] = {
                'week_name': week_match.group(1),
                'week_date_from': week_match.group(2),
                'week_date_to': week_match.group(3),
                'element': elem,
            }

    if week_headers:
        # Pour chaque en-tete de semaine, trouver le tableau qui suit
        for header_id, week_info in week_headers.items():
            current_week = week_info['week_name']
            current_week_from = week_info['week_date_from']
            current_week_to = week_info['week_date_to']
            elem = week_info['element']

            # Chercher le prochain tableau apres cet element
            table = None
            sibling = elem.find_next('table')
            if sibling:
                table = sibling

            if table:
                rows = table.find_all('tr')
                for row in rows:
                    cells = row.find_all('td')
                    if len(cells) < 4:
                        continue

                    try:
                        cell_texts = [c.get_text(strip=True) for c in cells]

                        # Detecter le format des colonnes
                        # Format attendu: Match | Date | Visites | Visiteurs
                        # Ou: Match | Date | Visites | Visiteurs | Score
                        match_id_str = cell_texts[0]
                        date_str = cell_texts[1]
                        home_team = cell_texts[2]
                        away_team = cell_texts[3]

                        # Ignorer les lignes d'en-tete
                        if match_id_str.lower() in ('match', 'n°', 'no', '#', ''):
                            continue
                        if home_team.lower() in ('visités', 'visited', 'domicile', 'home', 'equipe'):
                            continue

                        # Parser la date
                        date_iso, time_str, is_modified = _parse_date(date_str)

                        # Score (colonne 5 si presente)
                        score_str = cell_texts[4] if len(cells) > 4 else None
                        score, home_score, away_score = _parse_score(score_str)

                        # Detecter les forfeits
                        is_home_forfeit = False
                        is_away_forfeit = False
                        if score_str:
                            score_lower = score_str.strip().lower()
                            if 'ff' in score_lower or 'forfait' in score_lower:
                                if 'ff-' in score_lower or score_lower.startswith('ff'):
                                    is_home_forfeit = True
                                if '-ff' in score_lower or score_lower.endswith('ff'):
                                    is_away_forfeit = True

                        # URL des details du match (lien dans la cellule match_id)
                        details_url = None
                        link = cells[0].find('a')
                        if link and link.get('href'):
                            href = link['href']
                            if not href.startswith('http'):
                                href = f"https://resultats.aftt.be{href}"
                            details_url = href

                        match_obj = InterclubsMatch(
                            division_name=division_name,
                            division_category=division_category,
                            week_name=current_week,
                            week_date_from=current_week_from,
                            week_date_to=current_week_to,
                            match_id=match_id_str,
                            date=date_iso,
                            time=time_str,
                            home_team=home_team,
                            away_team=away_team,
                            score=score,
                            home_score=home_score,
                            away_score=away_score,
                            is_home_forfeit=is_home_forfeit,
                            is_away_forfeit=is_away_forfeit,
                            match_details_url=details_url,
                        )
                        matches.append(match_obj)

                    except Exception as e:
                        logger.debug(f"Erreur parsing ligne calendrier: {e}")

    else:
        # Fallback: pas d'en-tetes de semaine trouves
        # Essayer de parser tous les tableaux directement
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows:
                # Verifier si c'est un en-tete de semaine dans un <tr>
                header_cell = row.find(['th', 'td'], colspan=True)
                if header_cell:
                    text = header_cell.get_text(strip=True)
                    week_match = WEEK_PATTERN.search(text)
                    if week_match:
                        current_week = week_match.group(1)
                        current_week_from = week_match.group(2)
                        current_week_to = week_match.group(3)
                        continue

                cells = row.find_all('td')
                if len(cells) < 4:
                    continue

                try:
                    cell_texts = [c.get_text(strip=True) for c in cells]
                    match_id_str = cell_texts[0]
                    date_str = cell_texts[1]
                    home_team = cell_texts[2]
                    away_team = cell_texts[3]

                    if match_id_str.lower() in ('match', 'n°', 'no', '#', ''):
                        continue
                    if home_team.lower() in ('visités', 'visited', 'domicile', 'home', 'equipe'):
                        continue

                    date_iso, time_str, is_modified = _parse_date(date_str)

                    score_str = cell_texts[4] if len(cells) > 4 else None
                    score, home_score, away_score = _parse_score(score_str)

                    is_home_forfeit = False
                    is_away_forfeit = False
                    if score_str:
                        score_lower = score_str.strip().lower()
                        if 'ff' in score_lower or 'forfait' in score_lower:
                            if 'ff-' in score_lower or score_lower.startswith('ff'):
                                is_home_forfeit = True
                            if '-ff' in score_lower or score_lower.endswith('ff'):
                                is_away_forfeit = True

                    details_url = None
                    link = cells[0].find('a')
                    if link and link.get('href'):
                        href = link['href']
                        if not href.startswith('http'):
                            href = f"https://resultats.aftt.be{href}"
                        details_url = href

                    match_obj = InterclubsMatch(
                        division_name=division_name,
                        division_category=division_category,
                        week_name=current_week or "00",
                        week_date_from=current_week_from,
                        week_date_to=current_week_to,
                        match_id=match_id_str,
                        date=date_iso,
                        time=time_str,
                        home_team=home_team,
                        away_team=away_team,
                        score=score,
                        home_score=home_score,
                        away_score=away_score,
                        is_home_forfeit=is_home_forfeit,
                        is_away_forfeit=is_away_forfeit,
                        match_details_url=details_url,
                    )
                    matches.append(match_obj)

                except Exception as e:
                    logger.debug(f"Erreur parsing ligne calendrier (fallback): {e}")

    return matches


def scrape_all_calendrier(
    callback: Optional[Callable] = None,
    division_names: Optional[List[str]] = None,
    delay: float = PAGE_DELAY,
    is_cancelled: Optional[Callable] = None,
) -> Dict:
    """
    Scrape tous les calendriers interclubs.

    Args:
        callback: Fonction appelee avec un message pour le suivi
        division_names: Liste de noms de divisions a filtrer (defaut: toutes)
        delay: Delai entre chaque page en secondes
        is_cancelled: Fonction qui retourne True si le scraping doit etre annule

    Returns:
        Dict avec statistiques du scraping
    """
    def log(msg):
        logger.info(msg)
        if callback:
            callback(msg)

    stats = {
        'total_divisions': 0,
        'total_matches': 0,
        'divisions_scraped': 0,
        'errors': [],
    }

    from src.database import queries

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            # 1. Charger la page initiale
            log("[CALENDRIER] Chargement de la page calendriers...")
            page.goto(CALENDRIER_URL, timeout=30000)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)

            # 2. Extraire les divisions
            divisions = _extract_divisions(page)
            stats['total_divisions'] = len(divisions)

            if not divisions:
                log("[CALENDRIER] Aucune division trouvee!")
                return stats

            log(f"[CALENDRIER] {len(divisions)} divisions trouvees")

            # Filtrer les divisions si demande
            if division_names:
                filtered = []
                for d in divisions:
                    for name_filter in division_names:
                        if name_filter.lower() in d['name'].lower():
                            filtered.append(d)
                            break
                divisions = filtered
                log(f"[CALENDRIER] Filtrage: {len(divisions)} divisions selectionnees")

            # 3. Pour chaque division: selectionner, parser, sauver
            for div_idx, division in enumerate(divisions):
                if is_cancelled and is_cancelled():
                    log("[CALENDRIER] Scraping annule par l'utilisateur")
                    return stats

                pct = round((div_idx + 1) / len(divisions) * 100, 1)
                div_name = division['name']
                div_category = division.get('category')

                retries = 0
                success = False

                while retries < MAX_RETRIES and not success:
                    try:
                        # Selectionner la division
                        _select_division(page, division['value'], division['index'])

                        # Parser la page
                        html = page.content()
                        matches = _parse_calendar_page(html, div_name, div_category)

                        # Sauvegarder en base
                        if matches:
                            queries.insert_interclubs_matches_batch(
                                [m.to_dict() for m in matches]
                            )
                            stats['total_matches'] += len(matches)

                        stats['divisions_scraped'] += 1
                        log(f"[CALENDRIER] [{pct}%] {div_name[:50]}: {len(matches)} matchs")
                        success = True
                        time.sleep(delay)

                    except Exception as e:
                        retries += 1
                        wait = BASE_DELAY * (2 ** (retries - 1))
                        error_msg = f"Erreur div '{div_name[:40]}' (retry {retries}/{MAX_RETRIES}): {e}"
                        logger.warning(error_msg)

                        if retries < MAX_RETRIES:
                            time.sleep(wait)
                            try:
                                page.goto(CALENDRIER_URL, timeout=30000)
                                page.wait_for_load_state('networkidle')
                                page.wait_for_timeout(1000)
                            except Exception:
                                logger.warning("Echec du rechargement apres erreur")
                        else:
                            stats['errors'].append(error_msg)
                            log(f"[CALENDRIER] ERREUR: {error_msg}")

            log(f"[CALENDRIER] Termine: {stats['total_matches']} matchs, "
                f"{stats['divisions_scraped']}/{stats['total_divisions']} divisions, "
                f"{len(stats['errors'])} erreurs")

        except Exception as e:
            log(f"[CALENDRIER] Erreur fatale: {e}")
            stats['errors'].append(str(e))
            raise
        finally:
            browser.close()

    return stats


async def scrape_all_calendrier_async(
    callback: Optional[Callable] = None,
    division_names: Optional[List[str]] = None,
    delay: float = PAGE_DELAY,
    is_cancelled: Optional[Callable] = None,
) -> Dict:
    """Wrapper async pour utilisation dans FastAPI."""
    return await asyncio.to_thread(
        scrape_all_calendrier,
        callback=callback,
        division_names=division_names,
        delay=delay,
        is_cancelled=is_cancelled,
    )


if __name__ == "__main__":
    import sys

    print("\nAFTT Interclubs Calendar Scraper")
    print("=" * 50)

    division_names = None
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        if arg == '--divisions' and i + 1 < len(args):
            division_names = [d.strip() for d in args[i + 1].split(',')]

    def print_callback(msg):
        print(msg)

    stats = scrape_all_calendrier(
        callback=print_callback,
        division_names=division_names,
    )

    print(f"\nResultats:")
    print(f"  Divisions: {stats['total_divisions']}")
    print(f"  Divisions scrapees: {stats['divisions_scraped']}")
    print(f"  Matchs: {stats['total_matches']}")
    print(f"  Erreurs: {len(stats['errors'])}")

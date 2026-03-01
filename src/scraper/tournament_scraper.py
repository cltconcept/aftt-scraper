"""
AFTT Tournament Scraper
=======================
Script pour récupérer la liste des tournois et leurs détails
depuis le site resultats.aftt.be
"""

import requests
from bs4 import BeautifulSoup
import re
from dataclasses import dataclass, asdict
from typing import List, Optional, Dict, Any
import logging
import time

logger = logging.getLogger(__name__)

# URLs de base
BASE_URL = "https://resultats.aftt.be"
TOURNAMENTS_URL = f"{BASE_URL}/?menu=7"


@dataclass
class Tournament:
    """Représente un tournoi de tennis de table."""
    t_id: int
    name: str
    level: Optional[str] = None
    date_start: Optional[str] = None
    date_end: Optional[str] = None
    reference: Optional[str] = None
    series_count: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TournamentSeries:
    """Représente une série d'un tournoi."""
    tournament_id: int
    series_name: str
    date: Optional[str] = None
    time: Optional[str] = None
    inscriptions_count: int = 0
    inscriptions_max: int = 0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TournamentInscription:
    """Représente une inscription à un tournoi."""
    tournament_id: int
    series_name: str
    player_licence: str
    player_name: str
    player_club: Optional[str] = None
    player_ranking: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class TournamentResult:
    """Représente un résultat de match dans un tournoi."""
    tournament_id: int
    series_name: str
    player1_licence: Optional[str] = None
    player1_name: str = ""
    player2_licence: Optional[str] = None
    player2_name: str = ""
    score: str = ""
    winner_licence: Optional[str] = None
    round: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


def fetch_page(url: str) -> str:
    """
    Récupère le contenu HTML d'une page.
    """
    logger.debug(f"Récupération de la page : {url}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la récupération de la page : {e}")
        raise


def parse_date_range(date_str: str) -> tuple:
    """
    Parse une chaîne de date qui peut être une date simple ou une plage.
    
    Exemples:
    - "05/07/2025" -> ("05/07/2025", "05/07/2025")
    - "26/07-27/07/2025" -> ("26/07/2025", "27/07/2025")
    """
    if not date_str:
        return (None, None)
    
    date_str = date_str.strip()
    
    # Pattern pour plage de dates: "DD/MM-DD/MM/YYYY"
    range_match = re.match(r'(\d{2}/\d{2})-(\d{2}/\d{2})/(\d{4})', date_str)
    if range_match:
        day_month_start = range_match.group(1)
        day_month_end = range_match.group(2)
        year = range_match.group(3)
        return (f"{day_month_start}/{year}", f"{day_month_end}/{year}")
    
    # Date simple: "DD/MM/YYYY"
    simple_match = re.match(r'\d{2}/\d{2}/\d{4}', date_str)
    if simple_match:
        return (date_str, date_str)
    
    return (date_str, date_str)


def extract_t_id_from_url(url: str) -> Optional[int]:
    """Extrait le t_id d'une URL."""
    match = re.search(r't_id=(\d+)', url)
    if match:
        return int(match.group(1))
    return None


def get_tournaments_page(page: int = 1) -> List[Tournament]:
    """
    Récupère la liste des tournois d'une page donnée.
    """
    url = f"{TOURNAMENTS_URL}&cur_page={page}" if page > 1 else TOURNAMENTS_URL
    html_content = fetch_page(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    
    tournaments = []
    
    # Trouver le tableau des tournois
    # Le tableau a des colonnes: Nom, Niveau, Date, Réf., Nombre Séries, Actions
    tables = soup.find_all('table')
    
    for table in tables:
        # Chercher le header qui contient "Nom" et "Niveau"
        headers = table.find_all('th')
        header_texts = [h.get_text(strip=True) for h in headers]
        
        if 'Nom' in header_texts and 'Niveau' in header_texts:
            # C'est le bon tableau
            rows = table.find_all('tr')[1:]  # Skip header row
            
            for row in rows:
                cells = row.find_all('td')
                
                # Skip pagination row
                if len(cells) < 5:
                    continue
                
                # Extraire les données
                name = cells[0].get_text(strip=True) if len(cells) > 0 else ""
                level = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                date_str = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                reference = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                series_count_str = cells[4].get_text(strip=True) if len(cells) > 4 else "0"
                
                # Extraire le t_id depuis les liens d'actions
                t_id = None
                if len(cells) > 5:
                    links = cells[5].find_all('a')
                    for link in links:
                        href = link.get('href', '')
                        t_id = extract_t_id_from_url(href)
                        if t_id:
                            break
                
                if not t_id or not name:
                    continue
                
                # Parser la date
                date_start, date_end = parse_date_range(date_str)
                
                # Parser le nombre de séries
                try:
                    series_count = int(series_count_str)
                except ValueError:
                    series_count = 0
                
                tournament = Tournament(
                    t_id=t_id,
                    name=name,
                    level=level if level else None,
                    date_start=date_start,
                    date_end=date_end,
                    reference=reference if reference else None,
                    series_count=series_count
                )
                tournaments.append(tournament)
            
            break  # On a trouvé le bon tableau
    
    return tournaments


def get_total_pages() -> int:
    """
    Récupère le nombre total de pages de tournois.
    """
    html_content = fetch_page(TOURNAMENTS_URL)
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Chercher les liens de pagination
    pagination_links = soup.find_all('a', href=re.compile(r'cur_page=\d+'))
    
    max_page = 1
    for link in pagination_links:
        href = link.get('href', '')
        match = re.search(r'cur_page=(\d+)', href)
        if match:
            page_num = int(match.group(1))
            max_page = max(max_page, page_num)
    
    return max_page


def get_all_tournaments() -> List[Tournament]:
    """
    Récupère tous les tournois de toutes les pages.
    """
    total_pages = get_total_pages()
    logger.info(f"Récupération de {total_pages} pages de tournois...")
    
    all_tournaments = []
    
    for page in range(1, total_pages + 1):
        logger.info(f"Page {page}/{total_pages}...")
        tournaments = get_tournaments_page(page)
        all_tournaments.extend(tournaments)
        
        # Pause pour ne pas surcharger le serveur
        if page < total_pages:
            time.sleep(0.5)
    
    logger.info(f"Total: {len(all_tournaments)} tournois récupérés")
    return all_tournaments


def get_tournament_series(t_id: int) -> List[TournamentSeries]:
    """
    Récupère les séries d'un tournoi.
    """
    url = f"{BASE_URL}/?menu=7&viewseries=1&t_id={t_id}"
    html_content = fetch_page(url)
    soup = BeautifulSoup(html_content, 'html.parser')
    
    series_list = []
    
    # Trouver le tableau des séries
    # Colonnes: Date, Heure, Série, Nombre Inscriptions, Actions
    tables = soup.find_all('table')
    
    for table in tables:
        headers = table.find_all('th')
        header_texts = [h.get_text(strip=True) for h in headers]
        
        if 'Série' in header_texts or 'Date' in header_texts and 'Heure' in header_texts:
            rows = table.find_all('tr')[1:]  # Skip header row
            
            for row in rows:
                cells = row.find_all('td')
                
                if len(cells) < 4:
                    continue
                
                date = cells[0].get_text(strip=True) if len(cells) > 0 else ""
                time_str = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                series_name = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                inscriptions_str = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                
                if not series_name:
                    continue
                
                # Parser "36 / 36" -> count=36, max=36
                inscriptions_count = 0
                inscriptions_max = 0
                insc_match = re.match(r'(\d+)\s*/\s*(\d+)', inscriptions_str)
                if insc_match:
                    inscriptions_count = int(insc_match.group(1))
                    inscriptions_max = int(insc_match.group(2))
                elif inscriptions_str.isdigit():
                    inscriptions_count = int(inscriptions_str)
                
                series = TournamentSeries(
                    tournament_id=t_id,
                    series_name=series_name,
                    date=date if date else None,
                    time=time_str if time_str else None,
                    inscriptions_count=inscriptions_count,
                    inscriptions_max=inscriptions_max
                )
                series_list.append(series)
            
            break
    
    return series_list


def get_tournament_inscriptions(t_id: int) -> List[TournamentInscription]:
    """
    Récupère les inscriptions d'un tournoi depuis la page viewplayers.
    
    Format de la page: https://resultats.aftt.be/?menu=7&viewplayers=1&t_id=XXX
    Colonnes: Série | Index | Nom | Club | Classement | Actions
    Les inscriptions sont paginées (cur_page=1, 2, 3...).
    """
    all_inscriptions = []
    page = 1
    
    while True:
        if page == 1:
            url = f"{BASE_URL}/?menu=7&viewplayers=1&t_id={t_id}"
        else:
            url = f"{BASE_URL}/?menu=7&viewplayers=1&t_id={t_id}&cur_page={page}"
        
        html_content = fetch_page(url)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        inscriptions_on_page = []
        
        # Trouver le tableau des inscriptions
        # Colonnes: Série, Index, Nom, Club, Classement, Actions
        tables = soup.find_all('table')
        
        for table in tables:
            headers = table.find_all('th')
            header_texts = [h.get_text(strip=True) for h in headers]
            
            # Vérifier si c'est le bon tableau
            if 'Index' in header_texts or 'Nom' in header_texts:
                rows = table.find_all('tr')[1:]  # Skip header row
                
                for row in rows:
                    cells = row.find_all('td')
                    
                    # Format attendu: 6 colonnes (Série, Index, Nom, Club, Classement, Actions)
                    if len(cells) < 5:
                        continue
                    
                    series_name = cells[0].get_text(strip=True) if len(cells) > 0 else ""
                    licence = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                    name = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                    club = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                    ranking = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                    
                    # Vérifier que ce n'est pas une ligne de header ou pagination
                    if not licence or not name:
                        continue
                    if series_name.lower() in ['série', 'serie', 'series']:
                        continue
                    
                    inscription = TournamentInscription(
                        tournament_id=t_id,
                        series_name=series_name,
                        player_licence=licence,
                        player_name=name,
                        player_club=club if club else None,
                        player_ranking=ranking if ranking else None
                    )
                    inscriptions_on_page.append(inscription)
                
                break
        
        all_inscriptions.extend(inscriptions_on_page)
        
        # Vérifier s'il y a une page suivante
        next_link = soup.find('a', string=re.compile(r'\[Suivant\]', re.IGNORECASE))
        if not next_link:
            next_page_link = soup.find('a', href=re.compile(f'cur_page={page + 1}'))
            if not next_page_link:
                break
        
        page += 1
        time.sleep(0.2)  # Rate limiting
        
        # Sécurité: max 50 pages
        if page > 50:
            logger.warning(f"Arrêt à la page 50 pour les inscriptions du tournoi {t_id}")
            break
    
    logger.info(f"Tournoi {t_id}: {len(all_inscriptions)} inscriptions récupérées sur {page} page(s)")
    return all_inscriptions


def get_tournament_results(t_id: int) -> List[TournamentResult]:
    """
    Récupère les résultats d'un tournoi depuis la page viewresults.
    
    Format de la page: https://resultats.aftt.be/?menu=7&viewresults=1&t_id=XXX
    Le tableau contient: Série | Joueur | Nom adversaire | Résultats
    Le vainqueur est en gras (balise <b> ou <strong>).
    Les résultats sont paginés (cur_page=1, 2, 3...).
    """
    all_results = []
    page = 1
    
    while True:
        if page == 1:
            url = f"{BASE_URL}/?menu=7&viewresults=1&t_id={t_id}"
        else:
            url = f"{BASE_URL}/?menu=7&viewresults=1&t_id={t_id}&cur_page={page}"
        
        html_content = fetch_page(url)
        soup = BeautifulSoup(html_content, 'html.parser')
        
        results_on_page = []
        
        # Chercher le tableau de résultats
        # Format: Série | Joueur | Nom adversaire | Résultats
        tables = soup.find_all('table')
        
        for table in tables:
            rows = table.find_all('tr')
            
            for row in rows:
                cells = row.find_all('td')
                
                # Format attendu: 4 colonnes (Série, Joueur1, Joueur2, Score)
                if len(cells) == 4:
                    series_name = cells[0].get_text(strip=True)
                    player1_cell = cells[1]
                    player2_cell = cells[2]
                    score_cell = cells[3]
                    
                    # Extraire les noms de joueurs
                    player1_text = player1_cell.get_text(strip=True)
                    player2_text = player2_cell.get_text(strip=True)
                    score = score_cell.get_text(strip=True)
                    
                    # Vérifier si c'est un header ou une ligne de données
                    if not series_name or series_name.lower() in ['série', 'serie', 'series']:
                        continue
                    
                    # Vérifier le format du score (X/Y ou X-Y)
                    if not re.search(r'\d[/\-]\d', score):
                        continue
                    
                    # Déterminer le vainqueur (en gras)
                    winner_licence = None
                    player1_is_winner = player1_cell.find('b') is not None or player1_cell.find('strong') is not None
                    player2_is_winner = player2_cell.find('b') is not None or player2_cell.find('strong') is not None
                    
                    # Parser les informations du joueur
                    # Format: "NOM PRENOM Classement (Club)"
                    def parse_player_info(text):
                        # Extraire le club entre parenthèses
                        club_match = re.search(r'\(([^)]+)\)\s*$', text)
                        club = club_match.group(1) if club_match else None
                        
                        # Retirer le club du texte
                        name_ranking = re.sub(r'\([^)]+\)\s*$', '', text).strip()
                        
                        # Extraire le classement (NC, E0, E2, D6, C4, B2, etc.)
                        ranking_match = re.search(r'\b(NC|E\d|D\d|C\d|B\d|A\d?)\b', name_ranking)
                        ranking = ranking_match.group(1) if ranking_match else None
                        
                        # Le nom est tout ce qui reste
                        if ranking:
                            name = re.sub(r'\b(NC|E\d|D\d|C\d|B\d|A\d?)\b', '', name_ranking).strip()
                        else:
                            name = name_ranking
                        
                        # Extraire la licence du club (ex: H448 de "H448 Cleo Erquelinnes")
                        licence = None
                        if club:
                            licence_match = re.match(r'^([A-Z]\d{3})', club)
                            if licence_match:
                                licence = licence_match.group(1)
                        
                        return name, ranking, club, licence
                    
                    p1_name, p1_ranking, p1_club, p1_licence = parse_player_info(player1_text)
                    p2_name, p2_ranking, p2_club, p2_licence = parse_player_info(player2_text)
                    
                    # Déterminer le vainqueur
                    if player1_is_winner and p1_licence:
                        winner_licence = p1_licence
                    elif player2_is_winner and p2_licence:
                        winner_licence = p2_licence
                    
                    if p1_name and p2_name:
                        result = TournamentResult(
                            tournament_id=t_id,
                            series_name=series_name,
                            player1_name=p1_name,
                            player1_licence=p1_licence,
                            player2_name=p2_name,
                            player2_licence=p2_licence,
                            score=score,
                            winner_licence=winner_licence
                        )
                        results_on_page.append(result)
        
        all_results.extend(results_on_page)
        
        # Vérifier s'il y a une page suivante
        # Chercher le lien "[Suivant]"
        next_link = soup.find('a', string=re.compile(r'\[Suivant\]', re.IGNORECASE))
        if not next_link:
            # Ou chercher un lien vers la page suivante
            next_page_link = soup.find('a', href=re.compile(f'cur_page={page + 1}'))
            if not next_page_link:
                break
        
        page += 1
        time.sleep(0.2)  # Rate limiting
        
        # Sécurité: max 50 pages
        if page > 50:
            logger.warning(f"Arrêt à la page 50 pour le tournoi {t_id}")
            break
    
    logger.info(f"Tournoi {t_id}: {len(all_results)} résultats récupérés sur {page} page(s)")
    return all_results


def get_tournament_details(t_id: int) -> Dict[str, Any]:
    """
    Récupère tous les détails d'un tournoi (séries, inscriptions, résultats).
    """
    logger.info(f"Récupération des détails du tournoi {t_id}...")
    
    series = get_tournament_series(t_id)
    time.sleep(0.3)
    
    inscriptions = get_tournament_inscriptions(t_id)
    time.sleep(0.3)
    
    results = get_tournament_results(t_id)
    
    return {
        'series': [s.to_dict() for s in series],
        'inscriptions': [i.to_dict() for i in inscriptions],
        'results': [r.to_dict() for r in results]
    }


def scrape_all_tournaments_with_details(log_callback=None) -> Dict[str, Any]:
    """
    Scrape tous les tournois avec leurs détails.
    
    Args:
        log_callback: Fonction optionnelle pour logger les messages (pour l'API)
    
    Returns:
        Dict avec les tournois, séries, inscriptions et résultats
    """
    def log(msg):
        logger.info(msg)
        if log_callback:
            log_callback(msg)
    
    log("[TOURNAMENTS] Récupération de la liste des tournois...")
    tournaments = get_all_tournaments()
    log(f"[TOURNAMENTS] {len(tournaments)} tournois trouvés")
    
    all_series = []
    all_inscriptions = []
    all_results = []
    
    for i, tournament in enumerate(tournaments, 1):
        log(f"[TOURNAMENTS] {i}/{len(tournaments)} - {tournament.name}...")
        
        try:
            details = get_tournament_details(tournament.t_id)
            all_series.extend(details['series'])
            all_inscriptions.extend(details['inscriptions'])
            all_results.extend(details['results'])
            
            log(f"[TOURNAMENTS]   -> {len(details['series'])} séries, {len(details['inscriptions'])} inscriptions, {len(details['results'])} résultats")
        except Exception as e:
            log(f"[TOURNAMENTS]   -> Erreur: {e}")
        
        # Pause entre chaque tournoi
        time.sleep(0.5)
    
    log(f"[TOURNAMENTS] Terminé: {len(tournaments)} tournois, {len(all_series)} séries, {len(all_inscriptions)} inscriptions, {len(all_results)} résultats")
    
    return {
        'tournaments': [t.to_dict() for t in tournaments],
        'series': all_series,
        'inscriptions': all_inscriptions,
        'results': all_results
    }


def main(t_id: int = None):
    """Point d'entrée principal du script."""
    print("\n" + "="*60)
    print("  AFTT TOURNAMENT SCRAPER")
    print("  Récupération des tournois de tennis de table")
    print("="*60 + "\n")
    
    try:
        if t_id:
            # Scraper un tournoi spécifique
            print(f"Scraping du tournoi {t_id}...")
            details = get_tournament_details(t_id)
            
            print(f"\nSéries: {len(details['series'])}")
            for s in details['series'][:5]:
                print(f"  - {s['series_name']}")
            
            print(f"\nInscriptions: {len(details['inscriptions'])}")
            for i in details['inscriptions'][:5]:
                print(f"  - {i['player_name']} ({i['player_licence']})")
            
            print(f"\nRésultats: {len(details['results'])}")
            for r in details['results'][:5]:
                print(f"  - {r['player1_name']} vs {r['player2_name']}: {r['score']}")
        else:
            # Scraper tous les tournois (liste uniquement)
            tournaments = get_all_tournaments()
            
            print(f"\n{len(tournaments)} tournois trouvés\n")
            print("Exemple des 10 premiers tournois :")
            print("-"*40)
            for t in tournaments[:10]:
                print(f"  [{t.t_id}] {t.name} ({t.level}) - {t.date_start}")
            print("  ...")
        
        print(f"\n[OK] Scraping termine avec succes !")
        
    except Exception as e:
        logger.error(f"Erreur : {e}")
        raise


if __name__ == "__main__":
    import sys
    t_id = int(sys.argv[1]) if len(sys.argv) > 1 else None
    main(t_id)

"""
AFTT Player Scraper
====================
Script pour récupérer la fiche détaillée d'un joueur de tennis de table
depuis le site data.aftt.be

Source: https://data.aftt.be/tools/fiche.php
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from dataclasses import dataclass, asdict, field
from typing import List, Optional, Dict
import logging
import os

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# URLs des pages fiche joueur
AFTT_FICHE_URL = "https://data.aftt.be/tools/fiche.php"
AFTT_FICHE_WOMEN_URL = "https://data.aftt.be/tools/fiche_women.php"


@dataclass
class MatchResult:
    """Représente un résultat de match."""
    opponent_name: str
    opponent_ranking: str
    opponent_licence: Optional[str] = None
    opponent_points: Optional[float] = None
    score: str = ""                   # ex: "3-0", "2-3"
    won: bool = False
    points_change: Optional[float] = None
    # Infos de la journée
    date: Optional[str] = None        # ex: "10/01/2026"
    division: Optional[str] = None    # ex: "PHM12/045"
    opponent_club: Optional[str] = None  # ex: "Palette Verte Ecaus."
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PlayerStats:
    """Statistiques par classement adverse."""
    ranking: str                      # Classement adverse (C0, C2, etc.)
    wins: int = 0
    losses: int = 0
    ratio: float = 0.0
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class PlayerInfo:
    """Informations complètes d'un joueur."""
    licence: str
    name: str
    ranking: str                      # Classement actuel (C2, B6, etc.)
    club_code: Optional[str] = None
    
    # Points
    points_start: Optional[float] = None
    points_current: Optional[float] = None
    points_evolution: List[float] = field(default_factory=list)
    
    # Ranking
    ranking_position: Optional[int] = None
    ranking_position_active: Optional[int] = None  # Sans les inactifs
    
    # Statistiques
    stats_by_ranking: List[Dict] = field(default_factory=list)
    total_wins: int = 0
    total_losses: int = 0
    
    # Matchs
    matches: List[Dict] = field(default_factory=list)
    
    # Métadonnées
    last_update: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


def fetch_player_page(licence: str, women: bool = False, max_retries: int = 3) -> str:
    """
    Récupère la fiche d'un joueur via GET avec licenceID.
    Inclut des retries avec délai exponentiel en cas d'échec.
    
    Args:
        licence: Numéro de licence du joueur
        women: Si True, récupère la fiche féminine (fiche_women.php)
        max_retries: Nombre maximum de tentatives
    """
    import time
    
    url = AFTT_FICHE_WOMEN_URL if women else AFTT_FICHE_URL
    fiche_type = "feminine" if women else "masculine"
    logger.info(f"Recuperation de la fiche {fiche_type} du joueur {licence}...")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
    }
    
    # Utiliser GET avec licenceID
    params = {'licenceID': licence}
    
    last_error = None
    for attempt in range(max_retries):
        try:
            # Petit délai entre les requêtes pour ne pas surcharger le serveur
            if attempt > 0:
                delay = 2 ** attempt  # 2s, 4s, 8s...
                logger.info(f"Retry {attempt + 1}/{max_retries} après {delay}s...")
                time.sleep(delay)
            
            response = requests.get(url, params=params, headers=headers, timeout=30)
            response.raise_for_status()
            response.encoding = 'utf-8'
            logger.info(f"Page recuperee avec succes (status: {response.status_code})")
            return response.text
        except requests.RequestException as e:
            last_error = e
            logger.warning(f"Tentative {attempt + 1}/{max_retries} echouee: {e}")
    
    logger.error(f"Echec apres {max_retries} tentatives: {last_error}")
    raise last_error


def extract_player_info(html_content: str, licence: str) -> PlayerInfo:
    """
    Extrait toutes les informations du joueur depuis le HTML.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Initialiser avec les valeurs par defaut
    player = PlayerInfo(licence=licence, name='', ranking='')
    
    # 1. Informations de base (h2 principal)
    h2 = soup.find('h2')
    if h2:
        h2_text = h2.get_text(strip=True)
        # Format: "152174 - KEVIN BRULEZ - C2" ou "177378 - DEBORA FAUCHE - NC  Voir fiche féminine"
        # ou "151410 - LUCAS MENIER -" (sans classement pour les nouveaux joueurs)
        # Nettoyer le texte (enlever "Voir fiche...")
        h2_text = re.sub(r'\s*Voir fiche.*$', '', h2_text, flags=re.IGNORECASE)
        # Note: On utilise \s+-\s+ (espaces OBLIGATOIRES autour du tiret) pour distinguer
        # les séparateurs " - " des tirets dans les noms composés "JEAN-FRANCOIS"
        
        # Essayer d'abord le format avec classement
        match = re.match(r'(\d+)\s+-\s+(.+)\s+-\s+(\w+)$', h2_text)
        if match:
            player.licence = match.group(1)
            player.name = match.group(2).strip()
            player.ranking = match.group(3)
        else:
            # Essayer le format sans classement (ex: "151410 - LUCAS MENIER -")
            match_no_ranking = re.match(r'(\d+)\s+-\s+(.+?)\s*-?\s*$', h2_text)
            if match_no_ranking:
                player.licence = match_no_ranking.group(1)
                player.name = match_no_ranking.group(2).strip()
                player.ranking = ''  # Pas de classement
    
    # 2. Points (Depart et Actuels)
    h3_tags = soup.find_all('h3')
    for h3 in h3_tags:
        text = h3.get_text(strip=True)
        
        if 'pts' in text:
            # Extraire la valeur numerique
            pts_match = re.search(r'([\d.,]+)\s*pts', text)
            if pts_match:
                pts_value = float(pts_match.group(1).replace(',', '.'))
                
                # Trouver le label (h5 precedent)
                prev_h5 = h3.find_previous('h5')
                if prev_h5:
                    label = prev_h5.get_text(strip=True).lower()
                    if 'part' in label or 'start' in label:
                        player.points_start = pts_value
                    elif 'actuel' in label or 'current' in label:
                        player.points_current = pts_value
        
        # Ranking position
        elif text.endswith('e') or text.endswith('ème'):
            rank_match = re.search(r'(\d+)', text)
            if rank_match:
                player.ranking_position = int(rank_match.group(1))
    
    # 3. Date de mise a jour
    update_text = soup.find(string=re.compile(r'Mise à jour|Update', re.IGNORECASE))
    if update_text:
        date_match = re.search(r'(\d{2}/\d{2}/\d{2,4})', str(update_text))
        if date_match:
            player.last_update = date_match.group(1)
    
    # 4. Statistiques par classement (tableau)
    table = soup.find('table')
    if table:
        rows = table.find_all('tr')
        headers = []
        stats_data = {'wins': {}, 'losses': {}, 'ratio': {}}
        
        for row in rows:
            cells = row.find_all(['th', 'td'])
            cell_texts = [c.get_text(strip=True) for c in cells]
            
            if not cell_texts:
                continue
            
            first_cell = cell_texts[0].lower()
            
            # Premiere ligne = headers (classements)
            if not headers and len(cell_texts) > 1:
                headers = cell_texts[1:]  # Skip first empty cell
            elif 'victoire' in first_cell or 'win' in first_cell:
                for i, val in enumerate(cell_texts[1:]):
                    if i < len(headers):
                        try:
                            stats_data['wins'][headers[i]] = int(val)
                        except ValueError:
                            pass
            elif 'faite' in first_cell or 'loss' in first_cell:
                for i, val in enumerate(cell_texts[1:]):
                    if i < len(headers):
                        try:
                            stats_data['losses'][headers[i]] = int(val)
                        except ValueError:
                            pass
            elif 'ratio' in first_cell or '%' in first_cell:
                for i, val in enumerate(cell_texts[1:]):
                    if i < len(headers):
                        try:
                            stats_data['ratio'][headers[i]] = float(val.replace('%', ''))
                        except ValueError:
                            pass
        
        # Construire la liste des stats
        for ranking in headers:
            stat = PlayerStats(
                ranking=ranking,
                wins=stats_data['wins'].get(ranking, 0),
                losses=stats_data['losses'].get(ranking, 0),
                ratio=stats_data['ratio'].get(ranking, 0.0)
            )
            player.stats_by_ranking.append(stat.to_dict())
            player.total_wins += stat.wins
            player.total_losses += stat.losses
    
    # 5. Evolution des points (donnees du graphique)
    scripts = soup.find_all('script')
    for script in scripts:
        text = script.get_text()
        if 'data' in text.lower():
            # Chercher un array de nombres
            arrays = re.findall(r'data:\s*\[([\d.,\s]+)\]', text)
            for arr in arrays:
                try:
                    values = [float(v.strip()) for v in arr.split(',') if v.strip()]
                    if len(values) > 1 and all(100 < v < 3000 for v in values):
                        player.points_evolution = values
                        break
                except ValueError:
                    continue
    
    # 6. Matchs par journée (groupés par card-header)
    # Structure: card avec header (date - division - club) et body contenant les match-cards
    all_cards = soup.find_all('div', class_='card')
    
    for card in all_cards:
        # Chercher le header de la card (contient date, division, club adverse)
        card_header = card.find(class_='card-header')
        if not card_header:
            continue
        
        header_text = card_header.get_text(strip=True)
        
        # Parser le header: "10/01/2026 - PHM12/045 - Palette Verte Ecaus.Total : ..."
        # Format: DATE - DIVISION - CLUB_NAME (suivi potentiellement de "Total : ...")
        header_match = re.match(r'(\d{2}/\d{2}/\d{4})\s*-\s*([A-Z0-9/]+)\s*-\s*(.+?)(?:Total|Les points|$)', header_text)
        
        if not header_match:
            continue
        
        match_date = header_match.group(1)
        division = header_match.group(2)
        opponent_club = header_match.group(3).strip()
        
        # Chercher les match-cards dans cette card
        match_cards = card.find_all(class_='match-card')
        
        for match_card in match_cards:
            # Nom de l'adversaire (dans h6)
            h6 = match_card.find('h6')
            opponent_name = h6.get_text(strip=True) if h6 else ''
            
            # Licence adversaire (dans input hidden)
            licence_input = match_card.find('input', {'name': 'licence'})
            opponent_licence = licence_input.get('value') if licence_input else None
            
            # Classement et points adversaire (dans small)
            smalls = match_card.find_all('small')
            opponent_ranking = ''
            opponent_points = None
            
            for small in smalls:
                text = small.get_text(strip=True)
                if re.match(r'^[A-Z]\d$', text):  # Format classement: C4, B2, etc.
                    opponent_ranking = text
                elif 'pts' in text:
                    pts_match = re.search(r'([\d.]+)\s*pts', text)
                    if pts_match:
                        opponent_points = float(pts_match.group(1))
            
            # Score (dans h5.fw-bold)
            score_elem = match_card.find('h5', class_='fw-bold')
            score_text = score_elem.get_text(strip=True) if score_elem else ''
            
            # Determiner victoire/defaite
            won = False
            if score_text:
                score_match = re.match(r'(\d)-(\d)', score_text)
                if score_match:
                    won = int(score_match.group(1)) > int(score_match.group(2))
            
            # Changement de points (dans badge)
            badge = match_card.find(class_='badge')
            points_change = None
            if badge:
                badge_text = badge.get_text(strip=True)
                pts_match = re.search(r'([+-]?[\d.]+)\s*pts', badge_text)
                if pts_match:
                    points_change = float(pts_match.group(1))
            
            match_result = MatchResult(
                opponent_name=opponent_name,
                opponent_ranking=opponent_ranking,
                opponent_licence=opponent_licence,
                opponent_points=opponent_points,
                score=score_text,
                won=won,
                points_change=points_change,
                date=match_date,
                division=division,
                opponent_club=opponent_club
            )
            player.matches.append(match_result.to_dict())
    
    logger.info(f"Joueur extrait: {player.name} ({player.ranking}) - {len(player.matches)} matchs")
    return player


def get_player_info(licence: str, include_women: bool = True) -> dict:
    """
    Fonction principale pour recuperer les infos d'un joueur.
    
    Args:
        licence: Numéro de licence du joueur
        include_women: Si True, récupère aussi la fiche féminine (si disponible)
    
    Returns:
        dict avec les infos du joueur (fiche masculine + féminine si applicable)
    """
    # Récupérer la fiche masculine
    html_men = fetch_player_page(licence, women=False)
    player_men = extract_player_info(html_men, licence)
    
    result = player_men.to_dict()
    result['fiche_type'] = 'masculine'
    
    # Vérifier si une fiche féminine existe avec des matchs (pour les joueuses)
    if include_women:
        try:
            html_women = fetch_player_page(licence, women=True)
            
            # Vérifier si la page contient des données valides (pas d'erreurs PHP)
            if 'Warning' not in html_women or 'Undefined array key' not in html_women:
                player_women = extract_player_info(html_women, licence)
                
                # Seulement si la fiche féminine a des matchs joués
                # (évite d'afficher une fiche vide pour les hommes)
                if player_women.matches and len(player_women.matches) > 0:
                    result['women_stats'] = {
                        'ranking': player_women.ranking,
                        'points_start': player_women.points_start,
                        'points_current': player_women.points_current,
                        'points_evolution': player_women.points_evolution,
                        'ranking_position': player_women.ranking_position,
                        'stats_by_ranking': player_women.stats_by_ranking,
                        'total_wins': player_women.total_wins,
                        'total_losses': player_women.total_losses,
                        'matches': player_women.matches,
                    }
                    logger.info(f"Fiche feminine trouvee: {player_women.total_wins}V - {player_women.total_losses}D")
        except Exception as e:
            logger.debug(f"Pas de fiche feminine ou erreur: {e}")
    
    return result


def save_player_to_json(player_data: dict, filepath: str = None) -> str:
    """
    Sauvegarde les infos du joueur dans un fichier JSON.
    """
    licence = player_data.get('licence', 'unknown')
    if filepath is None:
        filepath = f"data/player_{licence}.json"
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(player_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Joueur sauvegarde dans : {filepath}")
    return filepath


def display_player_summary(player: dict) -> None:
    """
    Affiche un resume des infos du joueur (masculin et feminin si applicable).
    """
    print("\n" + "="*70)
    print(f"JOUEUR: {player['licence']} - {player['name']} - {player['ranking']}")
    print("="*70)
    
    # === FICHE MASCULINE ===
    print("\n" + "="*70)
    print("  FICHE MASCULINE (Interclubs Hommes)")
    print("="*70)
    
    # Points
    print("\n[POINTS]")
    print("-"*40)
    if player.get('points_start'):
        print(f"  Depart    : {player['points_start']} pts")
    if player.get('points_current'):
        print(f"  Actuels   : {player['points_current']} pts")
    if player.get('points_start') and player.get('points_current'):
        diff = player['points_current'] - player['points_start']
        sign = '+' if diff >= 0 else ''
        print(f"  Evolution : {sign}{diff:.1f} pts")
    
    # Ranking
    if player.get('ranking_position'):
        print(f"\n[RANKING]")
        print("-"*40)
        print(f"  Position  : {player['ranking_position']}e")
    
    # Stats
    if player.get('stats_by_ranking'):
        print(f"\n[STATISTIQUES PAR CLASSEMENT]")
        print("-"*40)
        print(f"  {'Clt':<6} {'V':<5} {'D':<5} {'Ratio':<8}")
        print("-"*40)
        for stat in player['stats_by_ranking']:
            print(f"  {stat['ranking']:<6} {stat['wins']:<5} {stat['losses']:<5} {stat['ratio']}%")
        print("-"*40)
        print(f"  {'TOTAL':<6} {player['total_wins']:<5} {player['total_losses']:<5}")
    
    # Matchs masculins groupés par journée
    matches = player.get('matches', [])
    if matches:
        wins = sum(1 for m in matches if m.get('won'))
        losses = len(matches) - wins
        print(f"\n[MATCHS] ({len(matches)} total: {wins}V - {losses}D)")
        print("="*80)
        
        # Grouper par date et club
        matches_by_day = {}
        for m in matches:
            key = (m.get('date', ''), m.get('division', ''), m.get('opponent_club', ''))
            if key not in matches_by_day:
                matches_by_day[key] = []
            matches_by_day[key].append(m)
        
        # Afficher par journée
        for (date, division, club), day_matches in matches_by_day.items():
            day_wins = sum(1 for m in day_matches if m.get('won'))
            day_losses = len(day_matches) - day_wins
            day_pts = sum(m.get('points_change', 0) or 0 for m in day_matches)
            
            print(f"\n  [{date}] {division} vs {club} ({day_wins}V-{day_losses}D = {day_pts:+.1f} pts)")
            print("-"*80)
            print(f"    {'Score':<6} {'Adversaire':<25} {'Clt':<5} {'Pts Adv':<10} {'Gain':<10}")
            print("-"*80)
            for m in day_matches:
                pts = f"{m.get('points_change', 0):+.1f}" if m.get('points_change') else ''
                pts_adv = f"{m.get('opponent_points', 0):.0f}" if m.get('opponent_points') else ''
                name = m['opponent_name'][:23] if len(m['opponent_name']) > 23 else m['opponent_name']
                result = "✓" if m.get('won') else "✗"
                print(f"    {m['score']:<6} {name:<25} {m['opponent_ranking']:<5} {pts_adv:<10} {pts:<10} {result}")
    
    # === FICHE FEMININE (si disponible) ===
    women = player.get('women_stats')
    if women:
        print("\n" + "="*70)
        print("  FICHE FEMININE (Interclubs Dames)")
        print("="*70)
        
        print("\n[POINTS]")
        print("-"*40)
        if women.get('points_start'):
            print(f"  Depart    : {women['points_start']} pts")
        if women.get('points_current'):
            print(f"  Actuels   : {women['points_current']} pts")
        if women.get('points_start') and women.get('points_current'):
            diff = women['points_current'] - women['points_start']
            sign = '+' if diff >= 0 else ''
            print(f"  Evolution : {sign}{diff:.1f} pts")
        
        if women.get('ranking_position'):
            print(f"\n[RANKING]")
            print("-"*40)
            print(f"  Position  : {women['ranking_position']}e")
        
        if women.get('stats_by_ranking'):
            print(f"\n[STATISTIQUES PAR CLASSEMENT]")
            print("-"*40)
            print(f"  {'Clt':<6} {'V':<5} {'D':<5} {'Ratio':<8}")
            print("-"*40)
            for stat in women['stats_by_ranking']:
                print(f"  {stat['ranking']:<6} {stat['wins']:<5} {stat['losses']:<5} {stat['ratio']}%")
            print("-"*40)
            print(f"  {'TOTAL':<6} {women['total_wins']:<5} {women['total_losses']:<5}")
        
        # Matchs feminins groupés par journée
        w_matches = women.get('matches', [])
        if w_matches:
            wins = sum(1 for m in w_matches if m.get('won'))
            losses = len(w_matches) - wins
            print(f"\n[MATCHS] ({len(w_matches)} total: {wins}V - {losses}D)")
            print("="*80)
            
            # Grouper par date et club
            matches_by_day = {}
            for m in w_matches:
                key = (m.get('date', ''), m.get('division', ''), m.get('opponent_club', ''))
                if key not in matches_by_day:
                    matches_by_day[key] = []
                matches_by_day[key].append(m)
            
            # Afficher par journée
            for (date, division, club), day_matches in matches_by_day.items():
                day_wins = sum(1 for m in day_matches if m.get('won'))
                day_losses = len(day_matches) - day_wins
                day_pts = sum(m.get('points_change', 0) or 0 for m in day_matches)
                
                print(f"\n  [{date}] {division} vs {club} ({day_wins}V-{day_losses}D = {day_pts:+.1f} pts)")
                print("-"*80)
                print(f"    {'Score':<6} {'Adversaire':<25} {'Clt':<5} {'Pts Adv':<10} {'Gain':<10}")
                print("-"*80)
                for m in day_matches:
                    pts = f"{m.get('points_change', 0):+.1f}" if m.get('points_change') else ''
                    pts_adv = f"{m.get('opponent_points', 0):.0f}" if m.get('opponent_points') else ''
                    name = m['opponent_name'][:23] if len(m['opponent_name']) > 23 else m['opponent_name']
                    result = "✓" if m.get('won') else "✗"
                    print(f"    {m['score']:<6} {name:<25} {m['opponent_ranking']:<5} {pts_adv:<10} {pts:<10} {result}")
    
    print("\n" + "="*70)
    if player.get('last_update'):
        print(f"Mise a jour : {player['last_update']}")
    print("="*70 + "\n")


def main(licence: str = "152174"):
    """Point d'entree principal du script."""
    print("\n" + "="*60)
    print("  AFTT PLAYER SCRAPER")
    print(f"  Recuperation de la fiche du joueur {licence}")
    print("="*60 + "\n")
    
    try:
        # Recuperer les infos
        player = get_player_info(licence)
        
        if not player.get('name'):
            logger.warning("Aucune information recuperee pour ce joueur")
            return player
        
        # Afficher un resume
        display_player_summary(player)
        
        # Sauvegarder
        save_player_to_json(player)
        
        print(f"[OK] Fiche du joueur {player['name']} recuperee avec succes !")
        
        return player
        
    except Exception as e:
        logger.error(f"Erreur : {e}")
        raise


if __name__ == "__main__":
    import sys
    licence = sys.argv[1] if len(sys.argv) > 1 else "152174"
    main(licence)

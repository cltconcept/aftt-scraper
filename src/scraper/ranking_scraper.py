# -*- coding: utf-8 -*-
"""
AFTT Ranking Scraper
====================
Script pour récupérer la liste complète des joueurs d'un club
depuis le classement numérique (data.aftt.be/ranking/clubs.php)

Cette source contient TOUS les joueurs (actifs + inactifs),
contrairement à l'annuaire qui ne contient que les joueurs actifs.

Utilise Playwright pour rendre le JavaScript.
"""

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
import re
import logging
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict

# Pattern de validation pour les codes club (ex: H004, BW023)
CLUB_CODE_PATTERN = re.compile(r'^[A-Z]{1,3}\d{2,4}$')

logger = logging.getLogger(__name__)

RANKING_URL = "https://data.aftt.be/ranking/clubs.php"


@dataclass
class RankingPlayer:
    """Joueur du classement numérique."""
    position: int                    # Position dans le classement (avec inactifs)
    position_active: Optional[int]   # Position sans les inactifs (None si inactif)
    licence: str                     # Numéro de licence
    name: str                        # Nom du joueur
    ranking: str                     # Classement (NC, E6, C2, etc.)
    club_code: str                   # Code du club
    matches: int                     # Nombre de matchs joués
    points: float                    # Points actuels
    gender: str = 'M'                # 'M' ou 'F'
    is_active: bool = True           # Si le joueur est actif
    
    def to_dict(self) -> dict:
        return asdict(self)


async def get_club_ranking_players_async(club_code: str, timeout: int = 30000) -> Dict:
    """
    Version async pour FastAPI.
    Exécute le scraping synchrone dans un thread séparé pour éviter
    les problèmes Windows avec asyncio subprocess.
    """
    # Exécuter la version synchrone dans un thread pool
    return await asyncio.to_thread(get_club_ranking_players, club_code, timeout)


def get_club_ranking_players(club_code: str, timeout: int = 30000) -> Dict:
    """
    Récupère tous les joueurs d'un club depuis le classement numérique.
    
    Args:
        club_code: Code du club (ex: 'H004')
        timeout: Timeout en millisecondes
    
    Returns:
        Dict avec les joueurs messieurs et dames
    """
    club_code = club_code.strip().upper()
    if not CLUB_CODE_PATTERN.match(club_code):
        raise ValueError(f"Code club invalide: {club_code}. Format attendu: lettres + chiffres (ex: H004)")
    logger.info(f"Récupération du classement pour le club {club_code}...")
    
    result = {
        'club_code': club_code,
        'players_men': [],
        'players_women': [],
    }
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        try:
            # Charger la page
            logger.info("Chargement de la page ranking...")
            page.goto(RANKING_URL, timeout=timeout)
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(2000)
            
            # Sélectionner le club via JavaScript
            logger.info(f"Sélection du club {club_code}...")
            page.evaluate(f"""
                () => {{
                    const select = document.getElementById('clubSelect');
                    if (select) {{
                        select.value = '{club_code}';
                        const event = new Event('change', {{ bubbles: true }});
                        select.dispatchEvent(event);
                        if (select.form) {{
                            select.form.submit();
                        }}
                    }}
                }}
            """)
            
            # Attendre le rechargement
            page.wait_for_load_state('networkidle')
            page.wait_for_timeout(3000)
            
            # Vérifier que le club est bien sélectionné
            selected = page.evaluate("() => document.getElementById('clubSelect')?.value")
            if selected != club_code:
                logger.warning(f"Club sélectionné: {selected}, attendu: {club_code}")
            
            # Récupérer le HTML
            html = page.content()
            logger.info(f"HTML récupéré: {len(html)} caractères")
            
            # Parser les joueurs
            soup = BeautifulSoup(html, 'html.parser')
            
            # Trouver les datatables messieurs et dames
            datatable_men = soup.find(id='datatable-messieurs')
            datatable_women = soup.find(id='datatable-dames')
            
            # Parser les joueurs messieurs
            if datatable_men:
                result['players_men'] = _parse_datatable(datatable_men, club_code, 'M')
                logger.info(f"Joueurs messieurs: {len(result['players_men'])}")
            
            # Parser les joueuses
            if datatable_women:
                result['players_women'] = _parse_datatable(datatable_women, club_code, 'F')
                logger.info(f"Joueuses: {len(result['players_women'])}")
            
        except Exception as e:
            logger.error(f"Erreur lors du scraping: {e}")
            raise
        finally:
            browser.close()
    
    return result


def _parse_datatable(table, club_code: str, gender: str) -> List[Dict]:
    """
    Parse un datatable de joueurs.
    
    Format des colonnes:
    0: Pos (position avec inactifs)
    1: Pos N (position sans inactifs) ou "Inactive"
    2: Nom
    3: Clt. (classement)
    4: Club
    5: Match
    6: Points
    7: Action (lien avec licence)
    """
    players = []
    rows = table.find_all('tr')
    
    for row in rows[1:]:  # Skip header
        cells = row.find_all('td')
        if len(cells) < 7:
            continue
        
        try:
            cell_texts = [c.get_text(strip=True) for c in cells]
            
            # Position avec inactifs
            position = int(cell_texts[0]) if cell_texts[0].isdigit() else 0
            
            # Position sans inactifs ou "Inactive"
            is_active = cell_texts[1] != 'Inactive'
            position_active = int(cell_texts[1]) if cell_texts[1].isdigit() else None
            
            # Nom
            name = cell_texts[2]
            
            # Classement
            ranking = cell_texts[3]
            
            # Matchs
            matches = int(cell_texts[5]) if cell_texts[5].isdigit() else 0
            
            # Points
            try:
                points = float(cell_texts[6])
            except (ValueError, IndexError):
                points = 0.0
            
            # Licence (dans le lien "Voir fiche")
            licence = None
            action_cell = cells[7] if len(cells) > 7 else None
            if action_cell:
                link = action_cell.find('a')
                if link:
                    href = link.get('href', '')
                    # Extraire la licence de l'URL (ex: fiche.php?licenceID=152174)
                    licence_match = re.search(r'licenceID=(\d+)', href)
                    if licence_match:
                        licence = licence_match.group(1)
                    else:
                        # Essayer avec un pattern différent
                        licence_match = re.search(r'(\d{6})', href)
                        if licence_match:
                            licence = licence_match.group(1)
                
                # Si pas trouvé dans le lien, chercher dans un formulaire
                if not licence:
                    form = action_cell.find('form')
                    if form:
                        input_field = form.find('input', {'name': 'licence'})
                        if input_field:
                            licence = input_field.get('value', '')
            
            if not licence:
                # Dernier recours: chercher dans toute la ligne
                licence_match = re.search(r'\b(\d{6})\b', str(row))
                if licence_match:
                    licence = licence_match.group(1)
            
            if name and licence:
                player = RankingPlayer(
                    position=position,
                    position_active=position_active,
                    licence=licence,
                    name=name,
                    ranking=ranking,
                    club_code=club_code,
                    matches=matches,
                    points=points,
                    gender=gender,
                    is_active=is_active
                )
                players.append(player.to_dict())
                
        except Exception as e:
            logger.debug(f"Erreur parsing ligne: {e}")
    
    return players


if __name__ == "__main__":
    # Test
    import sys
    club = sys.argv[1] if len(sys.argv) > 1 else 'H004'
    
    print(f"\nRécupération des joueurs du club {club}...")
    result = get_club_ranking_players(club)
    
    print(f"\nJoueurs messieurs: {len(result['players_men'])}")
    for p in result['players_men'][:10]:
        print(f"  {p['licence']}: {p['name']} - {p['ranking']} ({p['points']} pts)")
    
    print(f"\nJoueurs dames: {len(result['players_women'])}")

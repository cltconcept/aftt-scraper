"""
AFTT Clubs Scraper
==================
Script pour récupérer la liste de tous les clubs de tennis de table
depuis le site data.aftt.be
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from dataclasses import dataclass, asdict
from typing import List, Optional
import logging

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# URL de la page des classements AFTT
AFTT_RANKINGS_URL = "https://data.aftt.be/interclubs/rankings.php"


@dataclass
class Club:
    """Représente un club de tennis de table AFFT."""
    code: str
    name: str
    province: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


def extract_province_from_code(code: str) -> Optional[str]:
    """
    Extrait la province/région à partir du code du club.
    
    Les préfixes connus sont :
    - A : Antwerpen (Anvers)
    - BBW : Brabant Wallon / Bruxelles
    - H : Hainaut
    - L : Liège
    - Lx : Luxembourg
    - N : Namur
    - OVL : Oost-Vlaanderen (Flandre Orientale)
    - Vl-B : Vlaams-Brabant (Brabant Flamand)
    - WVL : West-Vlaanderen (Flandre Occidentale)
    - VTTL : Fédération Flamande
    - AFTT : Fédération Francophone
    - FR : France (mutation)
    """
    province_mapping = {
        'A': 'Antwerpen',
        'BBW': 'Brabant Wallon / Bruxelles',
        'H': 'Hainaut',
        'L': 'Liège',
        'Lx': 'Luxembourg',
        'N': 'Namur',
        'OVL': 'Oost-Vlaanderen',
        'Vl-B': 'Vlaams-Brabant',
        'WVL': 'West-Vlaanderen',
        'VTTL': 'VTTL (Fédération Flamande)',
        'AFTT': 'AFTT (Fédération Francophone)',
        'FR': 'France (mutation)',
    }
    
    # Essayer de matcher les préfixes du plus long au plus court
    for prefix in sorted(province_mapping.keys(), key=len, reverse=True):
        if code.upper().startswith(prefix.upper()):
            return province_mapping[prefix]
    
    return None


def parse_club_option(option_text: str) -> Optional[Club]:
    """
    Parse une option du select pour extraire le code et le nom du club.
    
    Format attendu : "CODE - NOM"
    Exemple : "A003 - Salamander"
    """
    if not option_text or option_text.startswith('--'):
        return None
    
    # Pattern pour extraire le code et le nom
    match = re.match(r'^([A-Za-z0-9\-_]+)\s*-\s*(.+)$', option_text.strip())
    
    if match:
        code = match.group(1).strip()
        name = match.group(2).strip()
        province = extract_province_from_code(code)
        return Club(code=code, name=name, province=province)
    
    return None


def fetch_clubs_page() -> str:
    """
    Récupère le contenu HTML de la page des classements AFTT.
    """
    logger.info(f"Récupération de la page : {AFTT_RANKINGS_URL}")
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
    }
    
    try:
        response = requests.get(AFTT_RANKINGS_URL, headers=headers, timeout=30)
        response.raise_for_status()
        logger.info(f"Page récupérée avec succès (status: {response.status_code})")
        return response.text
    except requests.RequestException as e:
        logger.error(f"Erreur lors de la récupération de la page : {e}")
        raise


def extract_clubs_from_html(html_content: str) -> List[Club]:
    """
    Extrait la liste des clubs depuis le contenu HTML.
    """
    logger.info("Parsing du HTML...")
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Chercher le select contenant les clubs
    # Le select a généralement un attribut qui permet de l'identifier
    select_element = soup.find('select')
    
    if not select_element:
        logger.warning("Aucun élément select trouvé sur la page")
        return []
    
    clubs = []
    options = select_element.find_all('option')
    
    logger.info(f"Nombre d'options trouvées : {len(options)}")
    
    for option in options:
        option_text = option.get_text(strip=True)
        option_value = option.get('value', '')
        
        club = parse_club_option(option_text)
        if club:
            clubs.append(club)
    
    logger.info(f"Nombre de clubs extraits : {len(clubs)}")
    return clubs


def get_all_clubs() -> List[Club]:
    """
    Fonction principale pour récupérer tous les clubs.
    """
    html_content = fetch_clubs_page()
    clubs = extract_clubs_from_html(html_content)
    return clubs


def save_clubs_to_json(clubs: List[Club], filepath: str = "data/clubs.json") -> None:
    """
    Sauvegarde la liste des clubs dans un fichier JSON.
    """
    import os
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    clubs_data = [club.to_dict() for club in clubs]
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(clubs_data, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Clubs sauvegardés dans : {filepath}")


def display_clubs_summary(clubs: List[Club]) -> None:
    """
    Affiche un résumé des clubs par province.
    """
    from collections import Counter
    
    provinces = Counter(club.province for club in clubs if club.province)
    
    print("\n" + "="*60)
    print("RÉSUMÉ DES CLUBS PAR PROVINCE/RÉGION")
    print("="*60)
    
    for province, count in sorted(provinces.items(), key=lambda x: -x[1]):
        print(f"  {province}: {count} clubs")
    
    print("-"*60)
    print(f"  TOTAL: {len(clubs)} clubs")
    print("="*60 + "\n")


def main():
    """Point d'entrée principal du script."""
    print("\n" + "="*60)
    print("  AFTT CLUBS SCRAPER")
    print("  Récupération des clubs de tennis de table belges")
    print("="*60 + "\n")
    
    try:
        # Récupérer tous les clubs
        clubs = get_all_clubs()
        
        if not clubs:
            logger.error("Aucun club n'a été récupéré")
            return
        
        # Afficher un résumé
        display_clubs_summary(clubs)
        
        # Afficher les 10 premiers clubs comme exemple
        print("Exemple des 10 premiers clubs :")
        print("-"*40)
        for club in clubs[:10]:
            print(f"  [{club.code}] {club.name} ({club.province})")
        print("  ...")
        
        # Sauvegarder dans un fichier JSON
        save_clubs_to_json(clubs)
        
        print(f"\n[OK] {len(clubs)} clubs recuperes avec succes !")
        
    except Exception as e:
        logger.error(f"Erreur : {e}")
        raise


if __name__ == "__main__":
    main()

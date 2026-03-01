"""
AFTT Members Scraper
====================
Script pour récupérer la liste des membres d'un club de tennis de table
depuis le site data.aftt.be

Source: https://data.aftt.be/annuaire/membres.php
"""

import requests
from bs4 import BeautifulSoup
import json
import re
from dataclasses import dataclass, asdict
from typing import List, Optional
import logging
import os

logger = logging.getLogger(__name__)

# URL de la page de l'annuaire des membres
AFTT_MEMBERS_URL = "https://data.aftt.be/annuaire/membres.php"

# Session HTTP partagée pour réutiliser les connexions TCP (keep-alive)
_session = requests.Session()
_session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
})


@dataclass
class Member:
    """Représente un membre d'un club de tennis de table AFTT."""
    licence: str                      # Numéro de licence
    name: str                         # Nom du joueur
    category: str                     # Catégorie (SEN, VET, JUN, etc.)
    ranking: str                      # Classement actuel (ex: C2, B6, etc.)
    club_code: str                    # Code du club
    gender: Optional[str] = None      # 'M' pour messieurs, 'F' pour dames (si disponible)
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ClubInfo:
    """Informations détaillées d'un club de tennis de table AFTT."""
    code: str
    name: str
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Optional[str] = None      # ASBL, etc.
    website: Optional[str] = None
    has_shower: Optional[bool] = None
    
    # Informations du local
    venue_name: Optional[str] = None
    venue_address: Optional[str] = None
    venue_phone: Optional[str] = None
    venue_pmr_access: Optional[bool] = None
    venue_remarks: Optional[str] = None
    
    # Équipes
    teams_men: int = 0
    teams_women: int = 0
    teams_youth: int = 0
    teams_veterans: int = 0
    
    # Labels
    label: Optional[str] = None
    palette: Optional[str] = None
    
    def to_dict(self) -> dict:
        return asdict(self)


def extract_club_info_from_html(soup: BeautifulSoup, club_code: str, club_name: str) -> dict:
    """
    Extrait les informations détaillées du club depuis le HTML.
    
    Sections extraites:
    - Informations du club (email, téléphone, statut, site web, douche)
    - Locaux du club (nom, adresse, téléphone, accès PMR, remarques)
    - Équipes du club (messieurs, dames, jeunes, vétérans)
    - Labellisation et Palettes
    """
    info = ClubInfo(code=club_code, name=club_name)
    
    # Trouver toutes les cards Bootstrap
    cards = soup.find_all('div', class_='card')
    
    for card in cards:
        header = card.find(class_='card-header')
        body = card.find(class_='card-body')
        
        if not header or not body:
            continue
            
        header_text = header.get_text(strip=True).lower()
        body_text = body.get_text()
        
        # === Section: Informations du club ===
        if 'informations du club' in header_text:
            # Nom complet du club (dans h4)
            h4 = body.find('h4')
            if h4:
                info.full_name = h4.get_text(strip=True)
            
            # Parser les lignes
            lines = [l.strip() for l in body_text.split('\n') if l.strip()]
            for line in lines:
                if ':' in line:
                    parts = line.split(':', 1)
                    key = parts[0].strip().lower()
                    value = parts[1].strip() if len(parts) > 1 else ''
                    
                    if 'email' in key:
                        info.email = value if value else None
                    elif 'phone' in key or 'téléphone' in key or 'tel' in key:
                        info.phone = value if value else None
                    elif 'statut' in key:
                        info.status = value if value else None
                    elif 'douche' in key:
                        info.has_shower = value.lower() in ['oui', 'yes', 'true', '1']
            
            # Site web (chercher le lien)
            link = body.find('a', href=True)
            if link:
                href = link.get('href', '')
                if href and 'http' in href:
                    info.website = href
                        
        # === Section: Locaux du club ===
        elif 'locaux du club' in header_text:
            lines = [l.strip() for l in body_text.split('\n') if l.strip()]
            for line in lines:
                if ':' in line:
                    parts = line.split(':', 1)
                    key = parts[0].strip().lower()
                    value = parts[1].strip() if len(parts) > 1 else ''
                    
                    if key == 'nom':
                        info.venue_name = value if value else None
                    elif 'adresse' in key:
                        info.venue_address = value if value else None
                    elif 'phone' in key or 'téléphone' in key or 'tel' in key:
                        info.venue_phone = value if value else None
                    elif 'pmr' in key or 'accès' in key:
                        info.venue_pmr_access = value.lower() in ['oui', 'yes', 'true', '1']
                    elif 'remarque' in key:
                        info.venue_remarks = value if value else None
                        
        # === Section: Équipes du club ===
        elif 'quipes du club' in header_text or 'equipes' in header_text:
            lines = [l.strip() for l in body_text.split('\n') if l.strip()]
            for line in lines:
                if ':' in line:
                    parts = line.split(':', 1)
                    key = parts[0].strip().lower()
                    value = parts[1].strip() if len(parts) > 1 else '0'
                    
                    try:
                        num = int(value)
                    except ValueError:
                        num = 0
                        
                    if 'messieurs' in key or 'men' in key:
                        info.teams_men = num
                    elif 'dames' in key or 'women' in key:
                        info.teams_women = num
                    elif 'jeunes' in key or 'youth' in key:
                        info.teams_youth = num
                    elif 'térans' in key or 'veterans' in key:
                        info.teams_veterans = num
                        
        # === Section: Labellisation et Palettes ===
        elif 'labellisation' in header_text or 'palette' in header_text:
            lines = [l.strip() for l in body_text.split('\n') if l.strip()]
            for line in lines:
                if ':' in line:
                    parts = line.split(':', 1)
                    key = parts[0].strip().lower()
                    value = parts[1].strip() if len(parts) > 1 else ''
                    
                    if 'label' in key and 'palette' not in key:
                        info.label = value if value and value.lower() != 'aucun' else None
                    elif 'palette' in key:
                        info.palette = value if value and 'aucune' not in value.lower() else None
    
    return info.to_dict()


def fetch_club_members_page(club_code: str, max_retries: int = 3) -> str:
    """
    Récupère le contenu HTML de la page des membres d'un club.
    Inclut des retries avec délai exponentiel en cas d'échec.
    
    La page utilise un formulaire POST avec le paramètre 'indice'.
    Source: https://data.aftt.be/annuaire/membres.php
    """
    import time
    
    logger.info(f"Recuperation des membres du club {club_code} via POST...")

    # Le formulaire utilise POST avec le paramètre 'indice'
    data = {'indice': club_code}

    last_error = None
    for attempt in range(max_retries):
        try:
            # Petit délai entre les requêtes pour ne pas surcharger le serveur
            if attempt > 0:
                delay = 2 ** attempt  # 2s, 4s, 8s...
                logger.info(f"Retry {attempt + 1}/{max_retries} après {delay}s...")
                time.sleep(delay)

            response = _session.post(AFTT_MEMBERS_URL, data=data, timeout=30)
            response.raise_for_status()
            response.encoding = response.apparent_encoding
            logger.info(f"Page recuperee avec succes (status: {response.status_code})")
            return response.text
        except requests.RequestException as e:
            last_error = e
            logger.warning(f"Tentative {attempt + 1}/{max_retries} echouee: {e}")
    
    logger.error(f"Echec apres {max_retries} tentatives: {last_error}")
    raise last_error


def extract_members_from_html(html_content: str, club_code: str) -> dict:
    """
    Extrait la liste des membres et les informations du club depuis le contenu HTML.
    
    Structure attendue du tableau des membres:
    - Colonne 0: Position (ou index)
    - Colonne 1: Licence
    - Colonne 2: Nom
    - Colonne 3: Categorie (SEN, VET, etc.)
    - Colonne 4: Classement (B2, C4, etc.)
    """
    logger.info("Parsing du HTML...")
    soup = BeautifulSoup(html_content, 'html.parser')
    
    club_name = None
    
    # Trouver le nom du club dans le select en cherchant par valeur exacte
    select = soup.find('select')
    if select:
        for opt in select.find_all('option'):
            if opt.get('value') == club_code:
                option_text = opt.get_text(strip=True)
                if ' - ' in option_text:
                    club_name = option_text.split(' - ', 1)[1]
                break
    
    # Fallback: charger depuis clubs.json si le nom n'a pas ete trouve
    if not club_name:
        try:
            clubs_file = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'clubs.json')
            if os.path.exists(clubs_file):
                with open(clubs_file, 'r', encoding='utf-8') as f:
                    clubs = json.load(f)
                    for club in clubs:
                        if club.get('code') == club_code:
                            club_name = club.get('name')
                            break
        except Exception:
            pass
    
    # Extraire les informations detaillees du club
    logger.info("Extraction des informations du club...")
    club_info = extract_club_info_from_html(soup, club_code, club_name or '')
    
    # Construire le resultat
    result = {
        'club_code': club_code,
        'club_name': club_name,
        'club_info': club_info,
        'members': []
    }
    
    # Trouver tous les tableaux
    tables = soup.find_all('table')
    logger.info(f"Nombre de tableaux trouves : {len(tables)}")
    
    for table in tables:
        rows = table.find_all('tr')
        
        if len(rows) < 2:
            continue
        
        # Parser les lignes du tableau (skip la premiere ligne si c'est un header)
        for row in rows[1:]:
            cells = row.find_all('td')
            
            if len(cells) < 4:
                continue
            
            try:
                # Ajuster les indices selon la structure du tableau
                # Format possible: Pos | Licence | Nom | Categorie | Classement
                # ou: Licence | Nom | Categorie | Classement
                
                if len(cells) >= 5:
                    # Format avec position
                    licence = cells[1].get_text(strip=True)
                    name = cells[2].get_text(strip=True)
                    category = cells[3].get_text(strip=True)
                    ranking = cells[4].get_text(strip=True)
                else:
                    # Format sans position
                    licence = cells[0].get_text(strip=True)
                    name = cells[1].get_text(strip=True)
                    category = cells[2].get_text(strip=True)
                    ranking = cells[3].get_text(strip=True)
                
                # Valider que c'est bien un membre (licence numerique)
                if not licence or not name:
                    continue
                
                # Verifier que la licence ressemble a un numero
                if not any(c.isdigit() for c in licence):
                    continue
                
                member = Member(
                    licence=licence,
                    name=name,
                    category=category,
                    ranking=ranking,
                    club_code=club_code
                )
                result['members'].append(member.to_dict())
                
            except Exception as e:
                logger.warning(f"Erreur lors du parsing d'une ligne : {e}")
                continue
    
    logger.info(f"Membres extraits : {len(result['members'])}")
    return result


def get_club_members(club_code: str) -> dict:
    """
    Fonction principale pour recuperer les membres d'un club.
    """
    html_content = fetch_club_members_page(club_code)
    members = extract_members_from_html(html_content, club_code)
    return members


def save_members_to_json(members: dict, club_code: str, filepath: str = None) -> str:
    """
    Sauvegarde la liste des membres dans un fichier JSON.
    """
    if filepath is None:
        filepath = f"data/members_{club_code}.json"
    
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(members, f, ensure_ascii=False, indent=2)
    
    logger.info(f"Membres sauvegardes dans : {filepath}")
    return filepath


def display_members_summary(data: dict) -> None:
    """
    Affiche un resume complet du club et de ses membres.
    """
    print("\n" + "="*70)
    print(f"CLUB: {data['club_code']} - {data.get('club_name', 'Inconnu')}")
    print("="*70)
    
    # Afficher les informations du club
    club_info = data.get('club_info', {})
    if club_info:
        print("\n[INFORMATIONS DU CLUB]")
        print("-"*40)
        if club_info.get('full_name'):
            print(f"  Nom complet : {club_info['full_name']}")
        if club_info.get('email'):
            print(f"  Email       : {club_info['email']}")
        if club_info.get('phone'):
            print(f"  Telephone   : {club_info['phone']}")
        if club_info.get('status'):
            print(f"  Statut      : {club_info['status']}")
        if club_info.get('website'):
            print(f"  Site web    : {club_info['website']}")
        if club_info.get('has_shower') is not None:
            print(f"  Douche      : {'Oui' if club_info['has_shower'] else 'Non'}")
        
        # Local
        if club_info.get('venue_name') or club_info.get('venue_address'):
            print("\n[LOCAL]")
            print("-"*40)
            if club_info.get('venue_name'):
                print(f"  Nom         : {club_info['venue_name']}")
            if club_info.get('venue_address'):
                print(f"  Adresse     : {club_info['venue_address']}")
            if club_info.get('venue_phone'):
                print(f"  Telephone   : {club_info['venue_phone']}")
            if club_info.get('venue_pmr_access') is not None:
                print(f"  Acces PMR   : {'Oui' if club_info['venue_pmr_access'] else 'Non'}")
            if club_info.get('venue_remarks'):
                print(f"  Remarques   : {club_info['venue_remarks']}")
        
        # Equipes
        teams_total = (club_info.get('teams_men', 0) + club_info.get('teams_women', 0) + 
                       club_info.get('teams_youth', 0) + club_info.get('teams_veterans', 0))
        if teams_total > 0:
            print("\n[EQUIPES]")
            print("-"*40)
            print(f"  Messieurs   : {club_info.get('teams_men', 0)}")
            print(f"  Dames       : {club_info.get('teams_women', 0)}")
            print(f"  Jeunes      : {club_info.get('teams_youth', 0)}")
            print(f"  Veterans    : {club_info.get('teams_veterans', 0)}")
            print(f"  TOTAL       : {teams_total} equipes")
        
        # Labels
        if club_info.get('label') or club_info.get('palette'):
            print("\n[LABELLISATION]")
            print("-"*40)
            print(f"  Label       : {club_info.get('label') or 'Aucun'}")
            print(f"  Palette     : {club_info.get('palette') or 'Aucune'}")
    
    # Afficher les membres
    member_list = data.get('members', [])
    
    # Grouper par categorie
    from collections import Counter
    categories = Counter(m.get('category', 'N/A') for m in member_list)
    
    print(f"\n[MEMBRES PAR CATEGORIE]")
    print("-"*40)
    for cat, count in sorted(categories.items()):
        print(f"  {cat}: {count} membres")
    
    print(f"\n[LISTE DES MEMBRES] ({len(member_list)} total)")
    print("-"*70)
    print(f"{'Licence':<10} {'Nom':<35} {'Cat':<6} {'Clt':<6}")
    print("-"*70)
    
    # Afficher les 10 premiers membres
    for m in member_list[:10]:
        name = m['name'][:33] if len(m['name']) > 33 else m['name']
        print(f"{m['licence']:<10} {name:<35} {m['category']:<6} {m['ranking']:<6}")
    
    if len(member_list) > 10:
        print(f"  ... et {len(member_list) - 10} autres membres")
    
    print("\n" + "="*70)
    print(f"TOTAL: {len(member_list)} membres")
    print("="*70 + "\n")


def main(club_code: str = "H004"):
    """Point d'entree principal du script."""
    print("\n" + "="*60)
    print("  AFTT MEMBERS SCRAPER")
    print(f"  Recuperation des membres du club {club_code}")
    print("="*60 + "\n")
    
    try:
        # Recuperer les membres
        members = get_club_members(club_code)
        
        total = len(members.get('members', []))
        if total == 0:
            logger.warning("Aucun membre n'a ete recupere - Sauvegarde HTML pour debug")
            # Sauvegarder le HTML brut pour debug
            html = fetch_club_members_page(club_code)
            debug_path = f"data/debug_members_{club_code}.html"
            os.makedirs("data", exist_ok=True)
            with open(debug_path, 'w', encoding='utf-8') as f:
                f.write(html)
            logger.info(f"HTML sauvegarde pour debug dans : {debug_path}")
            return members
        
        # Afficher un resume
        display_members_summary(members)
        
        # Sauvegarder dans un fichier JSON
        save_members_to_json(members, club_code)
        
        print(f"[OK] {total} membres recuperes avec succes !")
        
        return members
        
    except Exception as e:
        logger.error(f"Erreur : {e}")
        raise


if __name__ == "__main__":
    import sys
    club_code = sys.argv[1] if len(sys.argv) > 1 else "H004"
    main(club_code)

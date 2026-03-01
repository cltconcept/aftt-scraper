"""
Configuration centralisée du logging pour l'application AFFT.
Importer ce module une seule fois au démarrage (main.py ou app.py).
"""
import logging
from src.config import LOG_LEVEL


def setup_logging():
    """Configure le logging pour toute l'application."""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL, logging.INFO),
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
    )
    # Réduire le bruit des librairies tierces
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('playwright').setLevel(logging.WARNING)

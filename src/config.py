"""
Configuration centralisée de l'application AFFT.
Toutes les variables sont configurables via variables d'environnement.
"""
import os

# Base de données
DB_PATH = os.environ.get('AFTT_DB_PATH',
    os.path.join(os.path.dirname(__file__), '..', 'data', 'aftt.db'))

# Serveur API
HOST = os.environ.get('AFTT_HOST', '0.0.0.0')
PORT = int(os.environ.get('AFTT_PORT', os.environ.get('PORT', '8000')))

# CORS
CORS_ORIGINS = os.environ.get('AFTT_CORS_ORIGINS', '*').split(',')

# Logging
LOG_LEVEL = os.environ.get('AFTT_LOG_LEVEL', 'INFO').upper()

# Scraping
SCRAPE_DELAY = float(os.environ.get('AFTT_SCRAPE_DELAY', '0.3'))
SCRAPE_RETRY_DELAY_BASE = float(os.environ.get('AFTT_RETRY_DELAY', '2.0'))
SCRAPE_MAX_RETRIES = int(os.environ.get('AFTT_MAX_RETRIES', '3'))
SCRAPE_TIMEOUT = int(os.environ.get('AFTT_SCRAPE_TIMEOUT', '30'))

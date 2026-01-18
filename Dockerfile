# AFTT Database Builder
# Image Docker pour le scraping et l'API

FROM python:3.11-slim

# Métadonnées
LABEL maintainer="AFTT Data Team"
LABEL description="AFTT Tennis de Table - Scraper & API"

# Variables d'environnement
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV AFTT_DB_PATH=/app/data/aftt.db

# Créer le répertoire de travail
WORKDIR /app

# Installer les dépendances système pour Playwright + outils système de base
RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    gnupg \
    coreutils \
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpango-1.0-0 \
    libcairo2 \
    libatspi2.0-0 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Copier et installer les dépendances Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Installer les navigateurs Playwright (Chromium uniquement)
RUN playwright install chromium
RUN playwright install-deps chromium

# Copier le code source
COPY . .

# Créer le dossier data
RUN mkdir -p /app/data

# Exposer les ports possibles (8000 local, 3000 Coolify)
EXPOSE 8000 3000

# Volume pour persister les données
VOLUME ["/app/data"]

# Commande par défaut: lancer l'API (utilise la variable PORT si définie)
CMD ["python", "main.py", "api"]

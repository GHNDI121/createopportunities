# Utilise une image Python officielle légère
FROM python:3.11-slim-bullseye

# Installer les dépendances système nécessaires (OCR, audio, etc.)
RUN apt-get update && \
    apt-get install -y --no-install-recommends tesseract-ocr libsndfile1 ffmpeg gcc && \
    apt-get upgrade -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Définir le dossier de travail
WORKDIR /app

# Copier les fichiers du projet, y compris chromedriver-win64
COPY . .
COPY chromedriver-win64/ ./chromedriver-win64/

# Installer les dépendances Python (fusionné en une seule commande pour le cache Docker)
RUN pip install --upgrade pip && pip install -r requirements.txt

# Exposer le port de l'API (FastAPI sur 80 pour compatibilité Jenkins)
EXPOSE 80

# Commande de démarrage (adapter si besoin)
CMD ["uvicorn", "API_ghndi:app", "--host", "0.0.0.0", "--port", "80"]

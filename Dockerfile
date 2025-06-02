# Utilise une image Python officielle légère
FROM python:3.11-slim

# Installer les dépendances système nécessaires (OCR, audio, etc.)
RUN apt-get update && \
    apt-get install -y tesseract-ocr libsndfile1 ffmpeg gcc && \
    rm -rf /var/lib/apt/lists/*

# Définir le dossier de travail
WORKDIR /app

# Copier les fichiers du projet
COPY . .

# Installer les dépendances Python
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Exposer le port de l'API (FastAPI sur 80 pour compatibilité Jenkins)
EXPOSE 80

# Commande de démarrage (adapter si besoin)
CMD ["uvicorn", "API_ghndi:app", "--host", "0.0.0.0", "--port", "80"]

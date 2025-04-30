from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pipeline import OpportunityPipeline
import os
import shutil
import requests

app = FastAPI()

# Middleware pour gérer les CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialisation du pipeline
pipeline = OpportunityPipeline()

# Endpoint pour vérifier la configuration du jeton d'accès
@app.post("/verify-token/")
async def verify_token():
    """
    Vérifie si le jeton d'accès Salesforce est configuré correctement.
    """
    try:
        access_token = os.getenv("accessToken")
        if not access_token:
            return JSONResponse(content={"error": "Le jeton d'accès Salesforce n'est pas configuré."}, status_code=400)
        return {"message": "Le jeton d'accès Salesforce est configuré correctement."}
    except Exception as e:
        return JSONResponse(content={"error": f"Erreur lors de la vérification du jeton : {str(e)}"}, status_code=500)

# Endpoint pour vérifier la connexion à Salesforce
@app.get("/check-connection/")
async def check_connection():
    """
    Vérifie la connexion à Salesforce en utilisant le jeton d'accès.
    """
    try:
        # Charger les informations depuis key.env
        access_token = os.getenv("accessToken")
        salesforce_base_url = os.getenv("SALESFORCE_BASE_URL")

        if not access_token or not salesforce_base_url:
            return JSONResponse(content={"error": "Les informations d'authentification Salesforce sont manquantes."}, status_code=400)

        # URL pour vérifier la connexion
        url = f"{salesforce_base_url}/services/data/v63.0/"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        # Effectuer la requête GET
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return {"message": "Connexion à Salesforce réussie."}
        elif response.status_code == 401:
            return JSONResponse(content={"error": "Jeton d'accès invalide ou expiré. Veuillez générer un nouveau jeton."}, status_code=401)
        else:
            return JSONResponse(content={"error": f"Erreur de connexion à Salesforce : {response.status_code}, {response.text}"}, status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": f"Erreur lors de la vérification de la connexion : {str(e)}"}, status_code=500)

# Endpoint pour traiter un fichier ou un texte pour créer des opportunités
@app.post("/process-opportunity/")
async def process_opportunity(file: UploadFile = File(None), text: str = Form(None), file_type: str = Form(None)):
    """
    Traite un fichier (image/audio) ou un texte pour détecter des opportunités.
    """
    try:
        # Vérification des entrées
        if not file and not text:
            return JSONResponse(content={"error": "Veuillez fournir un fichier ou un texte à traiter."}, status_code=400)

        if file:
            # Sauvegarder temporairement le fichier
            temp_file_path = f"temp_{file.filename}"
            with open(temp_file_path, "wb") as temp_file:
                shutil.copyfileobj(file.file, temp_file)

            # Appel des méthodes appropriées
            if file_type == "image":
                texte = pipeline.handle_image_file(temp_file_path)
            elif file_type == "audio":
                texte = pipeline.handle_audio_file(temp_file_path)
            else:
                return JSONResponse(content={"error": "Type de fichier non supporté. Utilisez 'image' ou 'audio'."}, status_code=400)

            # Supprimer le fichier temporaire
            os.remove(temp_file_path)
        else:
            # Si un texte brut est fourni
            texte = text

        # Traiter le texte pour détecter les opportunités
        pipeline.process_text(texte)

        # Vérification des opportunités détectées
        if pipeline.opportunities_set:
            return {"message": "Opportunités détectées avec succès.", "opportunities": list(pipeline.opportunities_set)}
        else:
            return {"message": "Aucune opportunité détectée."}
    except Exception as e:
        return JSONResponse(content={"error": f"Erreur lors du traitement : {str(e)}"}, status_code=500)

# Endpoint pour envoyer les opportunités à Salesforce
@app.get("/send-opportunities/")
async def send_opportunities():
    """
    Envoie les opportunités détectées à Salesforce.
    """
    try:
        if not pipeline.opportunities_set:
            return {"message": "Aucune opportunité à envoyer."}

        opportunities = []
        for opportunity_text in pipeline.opportunities_set:
            # Envoyer chaque opportunité à Salesforce
            response = pipeline.send_opportunity_to_salesforce(opportunity_text)
            if response:
                opportunities.append(response)

        return {"message": "Opportunités envoyées à Salesforce.", "opportunities": opportunities}
    except Exception as e:
        return JSONResponse(content={"error": f"Erreur lors de l'envoi : {str(e)}"}, status_code=500)

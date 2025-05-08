from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from pipeline import OpportunityPipeline
from FONCTION import parse_opportunity_text
import os
import shutil
import requests
from dotenv import load_dotenv
import base64
import hashlib
import secrets

app = FastAPI()

load_dotenv(dotenv_path="key.env")

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

@app.get("/login")
async def login():
    """
    Endpoint pour initier le processus d'authentification OAuth avec Salesforce.
    """
    try:
        client_id = os.getenv("Clé_consommateur_salesforce")
        callback_url = os.getenv("SALESFORCE_CALLBACK_URL")
        salesforce_base_url = os.getenv("SALESFORCE_BASE_URL")

        if not client_id or not callback_url or not salesforce_base_url:
            return JSONResponse(content={"error": "Les informations d'authentification OAuth sont incomplètes."}, status_code=400)

        # Générer le code_verifier et le code_challenge
        code_verifier = secrets.token_urlsafe(64)
        code_challenge = base64.urlsafe_b64encode(
            hashlib.sha256(code_verifier.encode()).digest()
        ).rstrip(b"=").decode()

        # Stocker le code_verifier dans une variable d'environnement temporaire
        os.environ["CODE_VERIFIER"] = code_verifier

        # Construire l'URL d'autorisation avec le code_challenge
        auth_url = (
            f"{salesforce_base_url}/services/oauth2/authorize?"
            f"response_type=code&client_id={client_id}&redirect_uri={callback_url}&"
            f"code_challenge={code_challenge}&code_challenge_method=S256"
        )

        return {"auth_url": auth_url}
    except Exception as e:
        return JSONResponse(content={"error": f"Erreur lors de la génération de l'URL d'authentification : {str(e)}"}, status_code=500)


@app.get("/callback")
async def callback(code: str):
    """
    Endpoint pour gérer le callback OAuth après l'autorisation Salesforce.
    """
    try:
        client_id = os.getenv("Clé_consommateur_salesforce")
        client_secret = os.getenv("Secret_consommateur_salesforce")
        callback_url = os.getenv("SALESFORCE_CALLBACK_URL")
        salesforce_base_url = os.getenv("SALESFORCE_BASE_URL")
        code_verifier = os.getenv("CODE_VERIFIER")

        if not client_id or not client_secret or not callback_url or not salesforce_base_url or not code_verifier:
            return JSONResponse(content={"error": "Les informations d'authentification OAuth sont incomplètes."}, status_code=400)

        # URL pour échanger le code d'autorisation contre un jeton d'accès
        token_url = f"{salesforce_base_url}/services/oauth2/token"

        # Préparer les données pour la requête POST
        data = {
            "grant_type": "authorization_code",
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uri": callback_url,
            "code": code,
            "code_verifier": code_verifier
        }

        # Effectuer la requête POST
        response = requests.post(token_url, data=data)

        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            instance_url = token_data.get("instance_url")

            if not access_token or not instance_url:
                return JSONResponse(content={"error": "Réponse invalide de Salesforce : jeton ou URL manquant."}, status_code=400)

            # Mettre à jour le fichier key.env avec le nouveau jeton
            with open("key.env", "r") as file:
                lines = file.readlines()

            with open("key.env", "w") as file:
                for line in lines:
                    if line.startswith("accessToken="):
                        file.write(f"accessToken={access_token}\n")
                    elif line.startswith("SALESFORCE_BASE_URL="):
                        file.write(f"SALESFORCE_BASE_URL={instance_url}\n")
                    else:
                        file.write(line)

            return {"message": "Authentification réussie.", "access_token": access_token, "instance_url": instance_url}
        else:
            return JSONResponse(content={"error": f"Erreur lors de l'échange du code d'autorisation : {response.status_code}, {response.text}"}, status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": f"Erreur lors du callback OAuth : {str(e)}"}, status_code=500)


@app.get("/check-connection/")
async def check_connection():
    """
    Vérifie la connexion à Salesforce en utilisant les informations existantes (jeton d'accès et URL d'instance).
    """
    try:
        # Charger les informations d'authentification depuis key.env
        access_token = os.getenv("accessToken")
        instance_url = os.getenv("SALESFORCE_BASE_URL")
        api_version = os.getenv("apiversion")

        if not access_token or not instance_url or not api_version:
            return JSONResponse(content={"error": "Les informations d'authentification Salesforce sont manquantes ou incomplètes."}, status_code=400)

        # Construire l'URL pour vérifier la connexion
        url = f"{instance_url}/services/data/v{api_version}/sobjects/"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        # Effectuer une requête GET pour vérifier la connexion
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return {"message": "Connexion à Salesforce réussie."}
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
    Envoie directement les opportunités détectées à Salesforce après les avoir formatées en JSON.
    """
    try:
        if not pipeline.opportunities_set:
            return {"message": "Aucune opportunité à envoyer."}

        opportunities = []
        access_token = os.getenv("accessToken")
        salesforce_base_url = os.getenv("SALESFORCE_BASE_URL")

        if not access_token or not salesforce_base_url:
            return JSONResponse(content={"error": "Les informations d'authentification Salesforce sont manquantes."}, status_code=400)

        for opportunity_text in pipeline.opportunities_set:
            # Formater l'opportunité en JSON
            opportunity_data = parse_opportunity_text(opportunity_text)
            if opportunity_data:
                # URL de l'API Salesforce pour créer une opportunité
                url = f"{salesforce_base_url}/services/data/v63.0/sobjects/Opportunity"

                # En-têtes de la requête
                headers = {
                    "Authorization": f"Bearer {access_token}",
                    "Content-Type": "application/json"
                }

                # Envoyer la requête POST
                response = requests.post(url, json=opportunity_data, headers=headers)

                if response.status_code == 201:
                    opportunities.append(response.json())
                else:
                    print(f"Erreur lors de l'envoi à Salesforce : {response.status_code}, {response.text}")

        if opportunities:
            return {"message": "Opportunités envoyées à Salesforce.", "opportunities": opportunities}
        else:
            return {"message": "Aucune opportunité n'a pu être envoyée."}

    except Exception as e:
        return JSONResponse(content={"error": f"Erreur lors de l'envoi : {str(e)}"}, status_code=500)

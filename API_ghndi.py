from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pipeline import OpportunityPipeline
import os
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

# Fonction pour vérifier la configuration du jeton d'accès
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

# Fonction pour vérifier la connexion à Salesforce
@app.get("/check-connection/")
async def check_connection():
    """
    Vérifie la connexion à Salesforce en utilisant le jeton d'accès.
    """
    try:
        access_token = os.getenv("accessToken")
        salesforce_base_url = os.getenv("SALESFORCE_BASE_URL")

        if not access_token or not salesforce_base_url:
            return JSONResponse(content={"error": "Les informations d'authentification Salesforce sont manquantes."}, status_code=400)

        # URL pour vérifier la connexion
        url = f"{salesforce_base_url}/services/data/v63.0/"
        headers = {
            "Authorization": f"Bearer {access_token}"
        }

        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            return {"message": "Connexion à Salesforce réussie."}
        else:
            return JSONResponse(content={"error": f"Erreur de connexion à Salesforce : {response.status_code}, {response.text}"}, status_code=response.status_code)
    except Exception as e:
        return JSONResponse(content={"error": f"Erreur lors de la vérification de la connexion : {str(e)}"}, status_code=500)

# Endpoint pour envoyer les opportunités à Salesforce
@app.post("/send-opportunities/")
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

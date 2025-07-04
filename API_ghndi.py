from fastapi import FastAPI, UploadFile, File, Form, Body
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pipeline import OpportunityPipeline
from FONCTION import parse_prospect_text, add_prospect, add_contact, add_account, parse_contact_text, parse_account_text, parse_opportunity_text, add_opportunity
from offre import OffreScraper
from memoire import supprimer_opportunite, charger_opportunites
import os
import shutil
import requests
from dotenv import load_dotenv
import base64
import hashlib
import secrets
import json

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

# Ajout d'une variable globale pour stocker le dernier texte traité par process_opportunity
last_processed_text = None

# endpoint pour la connexion à Salesforce
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

# endpoint pour le callback recuperer le jeton d'accés de salesforce et l'url
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

#endpoint pour vérifier la connexion à Salesforce
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

# Endpoint pour afficher les offres scrapées
@app.get("/scraped-offers/")
async def scraped_offers():
    """
    Retourne la liste des offres scrapées à partir du notebook scraping.ipynb.
    Stocke les offres dans memoire_offres.json pour éviter de rescraper à chaque fois.
    """
    try:
        from scraping import execute_notebook
        notebook_path = "scraping.ipynb"
        offres = execute_notebook(notebook_path)
        if offres:
            # Stocker les offres dans memoire_offres.json
            with open("memoire_offres.json", "w", encoding="utf-8") as f:
                json.dump(offres, f, ensure_ascii=False, indent=2)
            return {"offres": offres}
        else:
            return {"message": "Aucune offre scrapée trouvée."}
    except Exception as e:
        return JSONResponse(content={"error": f"Erreur lors de la récupération des offres scrapées : {str(e)}"}, status_code=500)


# Endpoint pour traiter un fichier ou un texte pour créer des opportunités
@app.post("/process-opportunity/")
async def process_opportunity(
    file: UploadFile = File(None), 
    text: str = Form(None), 
    file_type: str = Form(None), 
    index: int = Form(None)
    ):
    """
    Traite un fichier (image/audio), un texte, ou les offres scrapées pour détecter des opportunités.
    Stocke le dernier texte traité dans last_processed_text pour usage par contact/compte.
    """
    global last_processed_text
    try:
        # Vérification des entrées
        if not file and not text and file_type != "scraping":
            return JSONResponse(content={"error": "Veuillez fournir un fichier, un texte ou choisir le scraping à traiter."}, status_code=400)

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
                os.remove(temp_file_path)
                return JSONResponse(content={"error": "Type de fichier non supporté. Utilisez 'image', 'audio' ou 'scraping'."}, status_code=400)

            # Supprimer le fichier temporaire
            os.remove(temp_file_path)
            # Vérification des doublons avant d'ajouter au set des opportunités
            if texte in pipeline.opportunities_set:
                return {"message": "L'opportunité existe déjà.", "opportunity": texte}
            # Ajouter l'opportunité au set
            pipeline.opportunities_set.add(texte)
            # Traiter le texte pour détecter les opportunités
            pipeline.process_text(texte)
            last_processed_text = texte
        elif file_type == "scraping":
            # Utiliser les offres stockées si elles existent
            import os
            offres_data = None
            if os.path.exists("memoire_offres.json"):
                try:
                    with open("memoire_offres.json", "r", encoding="utf-8") as f:
                        offres_data = json.load(f)
                except Exception as e:
                    offres_data = None
            if not offres_data:
                # Si pas de cache, rescraper
                from scraping import execute_notebook, dict_to_text
                notebook_path = "scraping.ipynb"
                offres_data = execute_notebook(notebook_path)
                # Stocker pour la prochaine fois
                with open("memoire_offres.json", "w", encoding="utf-8") as f:
                    json.dump(offres_data, f, ensure_ascii=False, indent=2)
            from scraping import dict_to_text
            if index is not None:
                if offres_data and 0 <= index < len(offres_data):
                    texte = dict_to_text(offres_data[index])
                    pipeline.handle_scraped_offers_from_list(offres_data, index=index)
                    last_processed_text = texte
            else:
                textes_traites = []
                if offres_data:
                    pipeline.handle_scraped_offers_from_list(offres_data)
                    for offre in offres_data:
                        texte = dict_to_text(offre)
                        textes_traites.append(texte)
                    last_processed_text = textes_traites
            if pipeline.opportunities_set:
                return {"message": "Opportunités scrapées détectées avec succès.", "opportunities": list(pipeline.opportunities_set)}
            else:
                return {"message": "Aucune opportunité détectée via le scraping."}
        else:
            # Si un texte brut est fourni
            texte = text
            if texte in pipeline.opportunities_set:
                return {"message": "L'opportunité existe déjà.", "opportunity": texte}
            pipeline.opportunities_set.add(texte)
            pipeline.process_text(texte)
            last_processed_text = texte

        # Vérification des opportunités détectées
        if pipeline.opportunities_set:
            return {"message": "Opportunités détectées avec succès.", "opportunities": list(pipeline.opportunities_set)}
        else:
            return {"message": "Aucune opportunité détectée."}
    except Exception as e:
        return JSONResponse(content={"error": f"Erreur lors du traitement : {str(e)}"}, status_code=500)

# Endpoint pour supprimer une opportunité
@app.delete("/delete-opportunity/")
async def delete_opportunity(opportunite: dict):
    """
    Supprime une opportunité du fichier mémoire_opportunites.json.
    L'opportunité doit être envoyée dans le body de la requête (format JSON).
    """
    try:
        success = supprimer_opportunite(opportunite)
        if success:
            return {"message": "Opportunité supprimée avec succès."}
        else:
            return JSONResponse(content={"error": "Opportunité non trouvée."}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"error": f"Erreur lors de la suppression : {str(e)}"}, status_code=500)
    
# endpoint pour créer un compte
@app.post("/account_created/")
async def account_created():
    """
    Crée un compte à partir du dernier texte traité par process_opportunity, en utilisant le modèle LLM et l'envoie à Salesforce.
    """
    global last_processed_text
    try:
        if not last_processed_text:
            return JSONResponse(content={"error": "Aucun texte traité récemment. Veuillez d'abord appeler /process-opportunity/."}, status_code=400)
        # Utiliser last_processed_text pour générer le compte
        account_text = pipeline.process_account(last_processed_text)
        # Récupérer le texte généré (retourner le texte pour le parser)
        account_data = parse_account_text(account_text)
        print(f"Données formatées pour Salesforce (Account) : {account_data}")  # Log pour vérifier le contenu de account_data
        # Vérification des champs obligatoires
        if not account_data.get("Name") or not account_data.get("Type") or not account_data.get("class_id__c"):
            return JSONResponse(content={"error": "Informations manquantes pour créer le compte. Veuillez compléter les champs obligatoires (Nom, Type, Classe de compte)."}, status_code=400)
        access_token = os.getenv("accessToken")
        salesforce_base_url = os.getenv("SALESFORCE_BASE_URL")
        result = add_account(account_data, access_token, salesforce_base_url)
        return {"result": result, "raw_text": account_text}
    except Exception as e:
        return JSONResponse(content={"error": f"Erreur lors de la création du compte : {str(e)}"}, status_code=500)


# Endpoint pour créer un contact
@app.post("/contact_created/")
async def contact_created():
    """
    Crée un contact à partir du dernier texte traité par process_opportunity, en utilisant le modèle LLM et l'envoie à Salesforce.
    """
    global last_processed_text
    try:
        if not last_processed_text:
            return JSONResponse(content={"error": "Aucun texte traité récemment. Veuillez d'abord appeler /process-opportunity/."}, status_code=400)
        # Utiliser last_processed_text pour générer le contact
        contact_text = pipeline.process_contact(last_processed_text)
        # Récupérer le texte généré (retourner le texte pour le parser)
        contact_data = parse_contact_text(contact_text)
        print(f"Données formatées pour Salesforce (Contact) : {contact_data}")
        # Vérification des champs obligatoires
        if not contact_data.get("FirstName") or not contact_data.get("LastName") or not contact_data.get("AccountId"):
            return JSONResponse(content={"error": "Informations manquantes pour créer le contact. Veuillez compléter les champs obligatoires (Prénom, Nom, Compte)."}, status_code=400)
        access_token = os.getenv("accessToken")
        salesforce_base_url = os.getenv("SALESFORCE_BASE_URL")
        result = add_contact(contact_data, access_token, salesforce_base_url)
        return {"result": result, "raw_text": contact_text}
    except Exception as e:
        return JSONResponse(content={"error": f"Erreur lors de la création du contact : {str(e)}"}, status_code=500)


# Endpoint pour envoyer un prospect à Salesforce
@app.post("/send-prospect/")
async def send_prospect(prospect: dict = Body(...)):
    """
    Envoie un prospect unique à Salesforce (objet Lead).
    """
    try:
        access_token = os.getenv("accessToken")
        salesforce_base_url = os.getenv("SALESFORCE_BASE_URL")
        if not access_token or not salesforce_base_url:
            return JSONResponse(content={"error": "Les informations d'authentification Salesforce sont manquantes."}, status_code=400)
        # On parse le prospect si besoin (si c'est un texte)
        if isinstance(prospect, str):
            from FONCTION import parse_prospect_text
            prospect_data = parse_prospect_text(prospect)
        else:
            prospect_data = prospect
        # Vérification des champs obligatoires
        if not prospect_data.get("FirstName") or not prospect_data.get("LastName") or not prospect_data.get("Company"):
            return JSONResponse(content={"error": "Champs obligatoires manquants pour le prospect (Prénom, Nom, Société)."}, status_code=400)
        from FONCTION import add_prospect
        result = add_prospect(prospect_data, access_token, salesforce_base_url)
        if "error" in result:
            return JSONResponse(content={"error": result["error"]}, status_code=400)
        return {"message": "Prospect envoyé à Salesforce.", "result": result}
    except Exception as e:
        return JSONResponse(content={"error": f"Erreur lors de l'envoi du prospect : {str(e)}"}, status_code=500)

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
        for opp_text in pipeline.opportunities_set:
            opp_data = parse_opportunity_text(opp_text)
            print(f"Données formatées pour Salesforce : {opp_data}")
            # Vérification explicite des champs obligatoires (exemple : nom, étape, compte)
            if not opp_data.get("Name") or not opp_data.get("StageName") or not opp_data.get("AccountId"):
                return JSONResponse(content={"error": "Informations manquantes pour créer l'opportunité. Veuillez compléter les champs obligatoires (Nom, Étape, Compte)."}, status_code=400)
            result = add_opportunity(opp_data, access_token, salesforce_base_url)
            if "error" in result:
                err = result["error"].lower()
                if ("accountid" in err or "no such account" in err or "compte" in err):
                    return JSONResponse(content={"error": "Le compte n'existe pas dans Salesforce. Veuillez d'abord créer le compte."}, status_code=400)
                if ("contactid" in err or "no such contact" in err or "contact" in err):
                    return JSONResponse(content={"error": "Le contact n'existe pas dans Salesforce. Veuillez d'abord créer le contact."}, status_code=400)
                return JSONResponse(content={"error": result["error"]}, status_code=400)
            else:
                opportunities.append(result)
        if opportunities:
            return {"message": "Opportunités envoyées à Salesforce.", "opportunities": opportunities}
        else:
            return {"message": "Aucune opportunité n'a pu être envoyée."}
    except Exception as e:
        return JSONResponse(content={"error": f"Erreur lors de l'envoi : {str(e)}"}, status_code=500)

# Monter le dossier html-css en tant que fichiers statiques
app.mount("/static", StaticFiles(directory="html-css"), name="static")

# Rediriger la racine vers l'interface utilisateur HTML
@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")
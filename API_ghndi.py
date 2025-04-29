from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pipeline import OpportunityPipeline
import os
import shutil

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

# Route pour importer une image ou un fichier audio
@app.post("/process-and-send/")
async def process_and_send(file: UploadFile = File(...), file_type: str = Form(...)):
    """
    Traite un fichier (image ou audio), détecte les opportunités, les analyse et les envoie à Salesforce.
    """
    try:
        # Vérification du type de fichier
        if file_type not in ["image", "audio"]:
            return JSONResponse(content={"error": "Type de fichier non supporté. Utilisez 'image' ou 'audio'."}, status_code=400)

        # Sauvegarder temporairement le fichier
        temp_file_path = f"temp_{file.filename}"
        with open(temp_file_path, "wb") as temp_file:
            shutil.copyfileobj(file.file, temp_file)

        # Appel des méthodes appropriées
        if file_type == "image":
            texte = pipeline.handle_image_file(temp_file_path)
        elif file_type == "audio":
            texte = pipeline.handle_audio_file(temp_file_path)

        # Supprimer le fichier temporaire
        os.remove(temp_file_path)

        # Vérification des opportunités détectées
        if pipeline.opportunities_set:
            opportunities = []
            for opportunity_text in pipeline.opportunities_set:
                # Envoyer chaque opportunité à Salesforce
                response = pipeline.send_opportunity_to_salesforce(opportunity_text)
                if response:
                    opportunities.append(response)

            return {"message": "Opportunités traitées et envoyées à Salesforce.", "opportunities": opportunities}
        else:
            return {"message": "Aucune opportunité détectée."}
    except Exception as e:
        return JSONResponse(content={"error": f"Erreur lors du traitement : {str(e)}"}, status_code=500)

# endpoint pour soumettre du texte
@app.post("/process-text/")
async def process_text(text: str = Form(...)):
    """
    Permet de soumettre un texte pour détecter des opportunités.
    """
    try:
        pipeline.process_text(text)
        return {"message": "Texte traité avec succès.", "opportunities": list(pipeline.opportunities_set)}
    except Exception as e:
        return JSONResponse(content={"error": f"Erreur lors du traitement : {str(e)}"}, status_code=500)

# endpoint pour récupérer toutes les opportunités détectées
@app.get("/opportunities/")
async def get_opportunities():
    """
    Récupère toutes les opportunités détectées.
    """
    return {"opportunities": list(pipeline.opportunities_set)}

# Importation des bibliothèques nécessaires
from groq import Groq, GroqError
import pytesseract
from PIL import Image
import requests
from io import BytesIO
import os
import io
import speech_recognition as sr
from pydub import AudioSegment
from dotenv import load_dotenv
from tkinter import Tk, filedialog
import re
from datetime import datetime, timedelta
from simple_salesforce import Salesforce

# Charger les variables d'environnement depuis le fichier key.env
load_dotenv(dotenv_path="key.env")

# Charger la clé API depuis une variable d'environnement
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise GroqError("La clé API GROQ_API_KEY n'est pas définie dans les variables d'environnement.")

# Initialisation du client Groq
client = Groq(api_key=GROQ_API_KEY)

#modele de creation d'opportunité
def detect_opportunities(texte):
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Vous êtes commerciale, vous remplissez des champs pour la création d'opportunités commerciales dans un CRM.\n\n"
                    "Les opportunités peuvent être détectées dans des textes de différentes sources (mail, image, audio, etc.).\n\n"
                    "⚠️ Vous devez respecter STRICTEMENT les règles suivantes :\n"
                    "1. Une opportunité = un besoin commercial ou un groupe de besoins liés exprimés par un client.\n"
                    "2. Ne créez qu'UNE opportunité par besoin ou ensemble de besoins liés à un même objectif.\n"
                    "3. Ne créez PAS d’opportunités combinées (ex. un renouvellement + un projet).\n"
                    "4. Ne dupliquez PAS les opportunités (pas de répétition pour le même besoin).\n"
                    "5. Ignorez les actions internes ou les discussions qui ne comportent pas un besoin client explicite.\n\n"
                    "Pour chaque opportunité détectée, vous générez les champs suivants :\n"
                    "- Étape : prend la valeur «Prospection» à la création de l’opportunité.\n"
                    "- Nom de l'opportunité : basé sur le sujet ou le besoin exprimé dans le texte, en une phrase claire et concise.\n"
                    "- Nom du compte : nom de l'organisation mentionnée dans le texte.\n"
                    "- Pays : prend la valeur «Sénégal» par défaut sauf indication contraire.\n"
                    "- Date de clôture :\n"
                    "    - Si une date est une **échéance**, **deadline** ou **date limite**; utilise-la \n"
                    "    - Sinon s'il n'y a pas de date ou de date representant le date de cloture, fixe la date **une semaine après aujourd’hui** et écris-la au format **jj/mm/aaaa**.\n"
                    "    - Si une date est mentionnée mais **pas au bon format**, convertis-la en **jj/mm/aaaa**.\n"
                    "    - Si seuls le **jour et le mois** sont donnés, ajoute **l’année actuelle** (EX: on est en 2025 , Si on nous donne le 25/04 , nous allons mettre comme date de cloture 25/04/2025).\n"
                    "    - Si seuls le **mois et l’année** sont donnés, utilise **le dernier jour du mois** comme valeur de jour (EX: Si on nous donne le 25/04 , nous allons mettre comme date de cloture 30/04/2025).\n"
                    "- Origine de la piste : prend la valeur «Demande client spontanée» par défaut.\n"
                    "- Type : choisir parmi les éléments suivants selon le contexte :\n"
                    "    - «vente directe»\n"
                    "    - «renouvellement hors contrat»\n"
                    "    - «contrat de maintenance»\n"
                    "    - «projet»\n"
                    "- Date de depot : la date de traitement de l'opportunité c'est à dire de la création (par défaut aujourd'hui).\n"
                    "- nature de dossier: choisir parmi «appels d’offre», «sans concurrence», «DRP», «DRPCO», «consultation» selon le contenu du texte.\n"
                    "Remplissez également les champs MEDDIC suivants qui sont aussi importants pour la création d'opportunités :\n"
                    "1. Métrique : objectif mesurable attendu (ex : gain, durée, réduction de coûts...),sinon analyse le contexte du texte du texte et en tirer la métrique\n"
                    "2. Champion : personne interne au client qui pousse en faveur de l'achat (si connue), sinon mettre <à informer>\n"
                    "3. Acheteur économique : décisionnaire financier (si connu), sinon mettre le nom du client\n"
                    "4. Problème, challenge : problème ou besoin exprimé\n"
                    "5. Critère de décision : éléments clés pour le choix d’un fournisseur, sinon mettre <à informer>\n"
                    "6. Procédure de décision : étapes/processus d’achat, sinon mettre <à informer>\n"
                    "7- Nature du livrable commercial: «offre» ou «budget» selon que le client attend une proposition chiffrée ou une estimation.\n\n"
                    "8. Fiscalité : choisir parmi «HT», «HD», «HTC», «HTVA»\n"
                    "9. Contact pour la livraison : personne à contacter pour la livraison (si connue)\n"
                    "10. Contact pour l’exécution du projet : personne impliquée dans la mise en œuvre (si connue)\n\n"
                    "Retournez uniquement les opportunités détectées, au format texte, sans aucun commentaire ou explication supplémentaire."
                ),
            },
            {
                "role": "user",
                "content": f"Voici un texte pour créer des opportunités :\n\n{texte}",
            },
        ],
        temperature=0, 
        max_completion_tokens=512,
        top_p=1,
        stream=True,
        stop=None,
    )

    # Lecture et récupération du résultat
    opportunities_text = ""
    for chunk in completion:
        if chunk.choices[0].delta.content:
            opportunities_text += chunk.choices[0].delta.content

    return opportunities_text


#modele de traitement d'image pour l'extraction de texte

def ask_image_extract_text():
    print("Choisissez le mode d'entrée de l'image :")
    print("1 - Charger depuis mes fichiers")
    print("2 - Télécharger via une URL")
    mode = input("Entrez 1 ou 2 : ")

    try:
        if mode == '1':
            # Utilisation d'une boîte de dialogue pour sélectionner un fichier
            root = Tk()
            root.withdraw()  # Masquer la fenêtre principale de Tkinter
            file_path = filedialog.askopenfilename(title="Sélectionnez une image", filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.bmp;*.tiff")])
            if not file_path:
                print("Aucun fichier sélectionné.")
                return ""
            image = Image.open(file_path)

        elif mode == '2':
            url = input("Entrez l'URL de l'image : ")
            response = requests.get(url)
            image = Image.open(BytesIO(response.content))

        else:
            print("Choix invalide.")
            return ""

        # Vérification de type
        if not isinstance(image, Image.Image):
            raise TypeError("Objet image non valide pour l'OCR.")

        # Extraction du texte
        texte = pytesseract.image_to_string(image, lang='fra+eng')
        return texte.strip()

    except Exception as e:
        print(f"Erreur lors de l'import ou de l'extraction : {e}")
        return ""

# Fonction de transcription d'un fichier audio WAV
def transcribe_audio_file(file_path):
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(file_path) as source:
            audio = recognizer.record(source)
        text = recognizer.recognize_google(audio, language="fr-FR")
        return text
    except Exception as e:
        return f"Erreur lors de la transcription : {str(e)}"


# Fonction pour enregistrer de l'audio depuis le micro
def record_audio_from_microphone():
    recognizer = sr.Recognizer()
    mic = sr.Microphone()

    try:
        print("Enregistrement... veuillez parler.")
        with mic as source:
            recognizer.adjust_for_ambient_noise(source)
            audio = recognizer.listen(source)
        print("Transcription en cours...")
        text = recognizer.recognize_google(audio, language="fr-FR")
        return text
    except Exception as e:
        return f"Erreur lors de l'enregistrement : {str(e)}"


# Fonction pour convertir tout format audio en WAV
def convert_audio_to_wav(input_path, output_path="converted_audio.wav"):
    try:
        audio = AudioSegment.from_file(input_path)
        audio.export(output_path, format="wav")
        return output_path
    except Exception as e:
        print(f"Erreur lors de la conversion : {e}")
        return None


#modele de traitement audio pour l'extraction de texte

def ask_audio_input():
    print("Veuillez choisir une option :")
    print("1. Sélectionner un fichier audio")
    print("2. Enregistrer un message vocal")
    choice = input("Entrez votre choix (1 ou 2) : ")

    if choice == '1':
        try:
            # Utilisation d'une boîte de dialogue pour sélectionner un fichier
            root = Tk()
            root.withdraw()  # Masquer la fenêtre principale de Tkinter
            file_path = filedialog.askopenfilename(title="Sélectionnez un fichier audio", filetypes=[("Fichiers audio", "*.mp3;*.wav;*.ogg;*.flac")])
            if not file_path:
                print("Aucun fichier sélectionné.")
                return None

            # Convertir vers WAV quel que soit le format
            converted_path = convert_audio_to_wav(file_path)
            if converted_path:
                text = transcribe_audio_file(converted_path)
            else:
                text = None

            print("Texte extrait de l'audio :")
            print(text)
            return text
        except Exception as e:
            print(f"Erreur lors de la sélection ou du traitement du fichier : {e}")
            return None

    elif choice == '2':
        text = record_audio_from_microphone()
        return text

    else:
        print("Choix invalide, veuillez entrer 1 ou 2.")
        return None

def extract_text_from_audio(file_path):
    """
    Transcrit le texte d'un fichier audio à partir d'un chemin de fichier.
    """
    try:
        # Convertir l'audio en WAV si nécessaire
        wav_path = convert_audio_to_wav(file_path)
        if not wav_path:
            raise ValueError("Impossible de convertir l'audio en WAV.")

        # Transcrire l'audio
        texte = transcribe_audio_file(wav_path)
        return texte.strip()
    except Exception as e:
        print(f"Erreur lors de la transcription de l'audio : {e}")
        return ""

def parse_opportunity_text(opportunity_text):
    """
    Analyse le texte d'une opportunité et retourne un dictionnaire JSON avec les noms de champs Salesforce.
    """
    try:
        # Connexion à Salesforce
        sf = Salesforce(instance_url=os.getenv("SALESFORCE_BASE_URL"),
                        session_id=os.getenv("accessToken"))

        # Mapping des champs locaux vers les champs Salesforce
        fields = {
            "StageName": r"Étape\s*:\s*(.+)",
            "Name": r"Nom de l'opportunité\s*:\s*(.+)",
            "AccountId": r"Nom du compte\s*:\s*(.+)",
            "Pays__c": r"Pays\s*:\s*(.+)",
            "CloseDate": r"Date de clôture\s*:\s*(.+)",
            "LeadSource": r"Origine de la piste\s*:\s*(.+)",
            "Type": r"Type\s*:\s*(.+)",
            "Date_Depot__c": r"Date de dépôt\s*:\s*(.+)",
            "nature_de_dossier__c": r"Nature du dossier\s*:\s*(.+)",
            "Nature_du_livrable_commercial__c": r"Nature du livrable commercial\s*:\s*(.+)",
            "Contact_pour_la_livraison__c": r"Contact pour la livraison\s*:\s*(.+)",
            "Contact_pour_execution_projet__c": r"Contact pour l’exécution du projet\s*:\s*(.+)",
            "Métrique": r"Métrique\s*:\s*(.+)",
            "Champion": r"Champion\s*:\s*(.+)",
            "Acheteur_économique": r"Acheteur économique\s*:\s*(.+)",
            "Problème_challenge": r"Problème, challenge\s*:\s*(.+)",
            "Critère_de_décision": r"Critère de décision\s*:\s*(.+)",
            "Procédure_de_décision": r"Procédure de décision\s*:\s*(.+)",
            "Fiscalité": r"Fiscalité\s*:\s*(.+)"
        }

        parsed_data = {}
        for key, pattern in fields.items():
            match = re.search(pattern, opportunity_text)
            if match:
                value = match.group(1).strip()

                if key in ["CloseDate", "Date_Depot__c"]:
                    try:
                        value = datetime.strptime(value, "%d/%m/%Y").strftime("%Y-%m-%d")
                    except ValueError:
                        # Si la date n'est pas valide, fixer une date par défaut
                        if key == "CloseDate":
                            value = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
                        elif key == "Date_Depot__c":
                            value = datetime.now().strftime("%Y-%m-%d")

                if key == "AccountId":
                    # Recherche de l'ID du compte sur Salesforce
                    account_name = value
                    query = f"SELECT Id FROM Account WHERE Name = '{account_name}' LIMIT 1"
                    result = sf.query(query)
                    if result['records']:
                        value = result['records'][0]['Id']
                    else:
                        raise ValueError(f"Aucun compte trouvé pour le nom : {account_name}")

                if key in ["Contact_pour_la_livraison__c", "Contact_pour_execution_projet__c"]:
                    if not value:
                        # Recherche d'un contact lié au compte
                        account_id = parsed_data.get("AccountId")
                        if account_id:
                            contact_query = f"SELECT Name FROM Contact WHERE AccountId = '{account_id}' LIMIT 1"
                            contact_result = sf.query(contact_query)
                            if contact_result['records']:
                                value = contact_result['records'][0]['Name']
                            else:
                                value = "<à informer>"

                parsed_data[key] = value

        # Ajout des champs MEDDIC avec des valeurs par défaut si non renseignés
        meddic_fields = [
            "Métrique", "Champion", "Acheteur_économique", "Problème_challenge",
            "Critère_de_décision", "Procédure_de_décision", "Fiscalité"
        ]
        for field in meddic_fields:
            if field not in parsed_data:
                parsed_data[field] = "<à informer>"

        return parsed_data
    except Exception as e:
        print(f"Erreur lors de l'analyse du texte de l'opportunité : {e}")
        return {}


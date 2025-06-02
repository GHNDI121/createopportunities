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
import urllib.parse

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
                    "- Date de dépôt : la date de traitement de l'opportunité c'est à dire la date de la création (par défaut aujourd'hui), mais La date de dépôt doit toujours être antérieure à la date de clôture.\n"
                    "- nature de dossier: choisir parmi «Appels d'offres», «Sans concurrence», «DRP», «DRPCO», «Consultation» selon le contenu du texte tout en respectant la syntaxe d'écriture.\n"
                    "1. Métrique : objectif mesurable attendu (ex : gain, durée, réduction de coûts...),sinon analyse le contexte du texte du texte et en tirer la métrique\n"
                    "2. Champion : personne interne au client qui pousse en faveur de l'achat (si connue), sinon mettre à préciser\n"
                    "3. Acheteur économique : décisionnaire financier (si connu), sinon mettre le nom du client\n"
                    "4. Problème, challenge : problème ou besoin exprimé\n"
                    "5. Critère de décision : éléments clés pour le choix d’un fournisseur, sinon mettre à préciser\n"
                    "6. Procédure de décision : étapes/processus d’achat, sinon mettre à préciser\n"
                    "7- Nature du livrable commercial: «offre» ou «budget» selon que le client attend une proposition chiffrée ou une estimation.\n\n"
                    "8. Fiscalité : choisir parmi «HT», «HD», «HTC», «HTVA»\n"
                    "9. Contact pour la livraison : personne à contacter pour la livraison (si connue)\n"
                    "10. Contact pour l’exécution du projet : personne impliquée dans la mise en œuvre (si connue)\n\n"
                    "Retournez uniquement les opportunités détectées, au format texte, en evitant les doublons, sans aucun commentaire ou explication supplémentaire."
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
            "nature_de_dossier__c": r"Nature de dossier\s*:\s*(.+)",
            "Nature_du_livrable_commercial__c": r"Nature du livrable commercial\s*:\s*(.+)",
            "Contact_pour_la_livraison__c": r"Contact pour la livraison\s*:\s*(.+)",
            "Contact_pour_l_ex_cution_du_projet__c": r"Contact pour l’exécution du projet\s*:\s*(.+)",
            "metrique__c": r"Métrique\s*:\s*(.+)",
            "Champion__c": r"Champion\s*:\s*(.+)",
            "Acheteur_conomique__c": r"Acheteur économique\s*:\s*(.+)",
            "Probl_me_challenge__c": r"Problème, challenge\s*:\s*(.+)",
            "Crit_re_de_d_cision__c": r"Critère de décision\s*:\s*(.+)",
            "Proc_dure_de_d_cision__c": r"Procédure de décision\s*:\s*(.+)",
            "Fiscalit__c": r"Fiscalité\s*:\s*(.+)"
        }

        valid_nature_de_dossier = ["appels_offres", "Sans concurrence", "drp", "DRPCO", "consultation"]
        # Mapping explicite des valeurs textuelles vers les noms d'API Salesforce attendus
        nature_de_dossier_mapping = {
            "Appels d'offres": "appels_offres",
            "Sans concurrence": "Sans concurrence",
            "DRP": "drp",
            "DRPCO": "DRPCO",
            "Consultation": "consultation"
        }

        parsed_data = {}
        for key, pattern in fields.items():
            match = re.search(pattern, opportunity_text)
            if match:
                value = match.group(1).strip()
                print(f"Champ extrait : {key} = {value}")  # Log des champs extraits

                if key == "CloseDate":
                    try:
                        value = datetime.strptime(value, "%d/%m/%Y").strftime("%Y-%m-%d")
                    except ValueError:
                        print(f"Erreur de format de date pour CloseDate, valeur : {value}")
                        value = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")

                if key == "Date_Depot__c":
                    try:
                        value = datetime.strptime(value, "%d/%m/%Y").strftime("%Y-%m-%d")
                    except ValueError:
                        print(f"Erreur de format de date pour Date_Depot__c, valeur : {value}")
                        value = datetime.now().strftime("%Y-%m-%d")

                if key == "AccountId":
                    account_name = value.replace("'", "\\'")
                    query = f"SELECT Id FROM Account WHERE Name = '{account_name}' LIMIT 1"
                    result = sf.query(query)
                    if result['records']:
                        value = result['records'][0]['Id']
                    else:
                        print(f"Aucun compte trouvé pour le nom : {account_name}")  # Log si aucun compte trouvé
                        value = None

                if key in ["Contact_pour_la_livraison__c", "Contact_pour_l_ex_cution_du_projet__c"]:
                    if value:
                        contact_query = f"SELECT Id FROM Contact WHERE Name = '{value}' and AccountId = '{parsed_data.get('AccountId')}' LIMIT 1"
                        contact_result = sf.query(contact_query)
                        if not contact_result['records']:
                            account_id = parsed_data.get("AccountId")
                            if account_id:
                                contact_query = f"SELECT Id, Name FROM Contact WHERE AccountId = '{account_id}' LIMIT 1"
                                contact_result = sf.query(contact_query)
                                if contact_result['records']:
                                    value = contact_result['records'][0]['Id']
                                else:
                                    print(f"Aucun contact trouvé pour le compte : {account_id}")  # Log si aucun contact trouvé
                                    value = None
                            else:
                                value = "<à informer>"
                    else:
                        account_id = parsed_data.get("AccountId")
                        if account_id:
                            contact_query = f"SELECT Id, Name FROM Contact WHERE AccountId = '{account_id}' LIMIT 1"
                            contact_result = sf.query(contact_query)
                            if contact_result['records']:
                                value = contact_result['records'][0]['Id']
                            else:
                                print(f"Aucun contact trouvé pour le compte : {account_id}")  # Log si aucun contact trouvé
                                value = None

                if key == "nature_de_dossier__c":
                    # Mapping direct sans normalisation
                    mapped_value = nature_de_dossier_mapping.get(value)
                    if mapped_value and mapped_value in valid_nature_de_dossier:
                        value = mapped_value
                    else:
                        print(f"Valeur invalide pour nature_de_dossier__c : {value}")
                        value = "À préciser"

                parsed_data[key] = value
                print(f"Donnée formatée : {key} = {value}")  # Log des données formatées

        return parsed_data

    except Exception as e:
        print(f"Erreur lors de l'analyse du texte de l'opportunité : {e}")  # Log des exceptions
        return parsed_data  # Retourne les données partiellement extraites même en cas d'erreur

def add_opportunity(opportunity_data, access_token, salesforce_base_url):
    """
    Ajoute une opportunité à Salesforce en utilisant la méthode insert de simple_salesforce.

    :param opportunity_data: Dictionnaire contenant les données de l'opportunité formatée.
    :param access_token: Jeton d'accès pour l'authentification Salesforce.
    :param salesforce_base_url: URL de base de l'instance Salesforce.
    :return: Réponse de Salesforce ou message d'erreur.
    """
    try:
        # Connexion à Salesforce
        sf = Salesforce(instance_url=salesforce_base_url, session_id=access_token)

        # Insertion de l'opportunité
        result = sf.Opportunity.create(opportunity_data)

        return result

    except Exception as e:
        return {"error": f"Exception lors de l'insertion de l'opportunité : {str(e)}"}

def create_compte(texte):
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Vous êtes commerciale, vous remplissez des champs pour la création d’un compte client dans un CRM.\n\n"
                    "Vous devez respecter STRICTEMENT les règles suivantes :\n"
                    "1. Chaque compte correspond à une seule organisation distincte détectée dans le texte.\n"
                    "2. Si plusieurs organisations sont mentionnées, créez un compte pour chacune.\n"
                    "3. N'incluez **aucun doublon** (une organisation = un seul compte).\n"
                    "À partir d’un texte libre, vous devez extraire les informations utiles pour créer un compte client. Respectez STRICTEMENT les règles suivantes pour remplir ces champs obligatoires :\n\n"
                    "- Type : valeur par défaut = «Prospect»\n"
                    "- Nom du compte : à détecter dans le texte.\n"
                    "- Classe de compte : choisir parmi la liste suivante selon le profil de l’organisation mentionnée :\n"
                    "  Grand compte, Moyen compte, Petit compte, Administration publique, ONG, Partenaire stratégique, Fournisseur, Client final, Prospect, Distributeur, Interne\n"
                    "- Téléphone : à détecter dans le texte si présent.\n"
                    "- Secteur d’activité : choisir parmi la liste suivante :\n"
                    "  btp-be ; education ; etablissement financier ; industrie mines oil and gas ; operateur telephonique et isp ; organismes et projet ; secteurs public et gouvernement ; société de service ; tourisme\n"
                    "- Note client : Normal, Risqué, Top client (selon les termes utilisés dans le texte ou l’attitude perçue, sinon mettre «Normal»).\n"
                    "- NINEA : détecter dans le texte si présent, sinon mettre «à compléter».\n"
                    "- RC : détecter dans le texte si présent, sinon mettre «à compléter».\n"
                    "- RSE : détecter dans le texte (si mentionné, mettre «oui», sinon «non», si aucune info, mettre «aucun»).\n"
                    "- Normes et certification internationales : détecter dans le texte (si mentionné, mettre «oui», sinon «non», si aucune info, mettre «aucun»).\n\n"
                    "⚠️ Si une information n’est pas trouvée, indique «à compléter» sauf pour les valeurs par défaut définies.\n"
                    "⚠️ Retourne uniquement les champs obligatoires, sans aucun commentaire ni explication supplémentaire.\n\n"
                ),
            },
            {
                "role": "user",
                "content": f"Voici un texte pour créer un compte client :\n\n{texte}",
            },
        ],
        temperature=0, 
        max_completion_tokens=512,
        top_p=1,
        stream=True,
        stop=None,
    )

    compte_text = ""
    for chunk in completion:
        if chunk.choices[0].delta.content:
            compte_text += chunk.choices[0].delta.content

    return compte_text

def create_contact(texte):
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": (
                    "Vous êtes commerciale, vous remplissez des champs pour la création d’un contact dans un CRM.\n\n"
                    "Vous devez respecter STRICTEMENT les règles suivantes :\n"
                    "1. Chaque contact correspond à une seule personne mentionnée dans le texte.\n"
                    "2. Si plusieurs personnes sont identifiées, créez une fiche contact pour chacune.\n"
                    "3. Ne créez pas de doublons : une personne = un seul contact.\n"
                    "À partir d’un texte libre, vous devez extraire les informations nécessaires pour créer une fiche contact.\n\n"
                    "Voici les règles strictes à suivre pour remplir les champs obligatoires :\n"
                    "- Prénom : détecter dans le texte, sinon mettre «à compléter».\n"
                    "- Nom : détecter dans le texte, sinon mettre «à compléter».\n"
                    "- Nom du compte : organisation à laquelle est rattachée la personne, sinon «à compléter».\n"
                    "- Fonction : choisir parmi la liste suivante (si proche dans le texte, prendre la plus proche correspondance) :\n"
                    "  directeur general, directeur general adjoint, responsable achats, responsable administratif, DAF, DSI, directeur informatique, responsable informatique, responsable reseaux et systeme, responsable des marchés, RSSI, finances, directeur financier, responsable comptable, agent comptable\n"
                    "- Adresse mail : détecter si présente, sinon récupérer un mail dans le texte.\n"
                    "- Devise du compte : valeur fixe = «XOF - Franc CFA (BCEAO)»\n\n"
                    "⚠️ Si une information est absente, mettre «à compléter», sauf pour la devise qui est toujours fixée.\n"
                    "⚠️ Retourner uniquement les champs obligatoires, sans explication ni ajout.\n\n"
                ),
            },
            {
                "role": "user",
                "content": f"Voici un texte pour créer un contact :\n\n{texte}",
            },
        ],
        temperature=0, 
        max_completion_tokens=512,
        top_p=1,
        stream=True,
        stop=None,
    )

    contact_text = ""
    for chunk in completion:
        if chunk.choices[0].delta.content:
            contact_text += chunk.choices[0].delta.content

    return contact_text

def add_opportunity(opportunity_data, access_token, salesforce_base_url):
    """
    Ajoute une opportunité à Salesforce en utilisant la méthode insert de simple_salesforce.

    :param opportunity_data: Dictionnaire contenant les données de l'opportunité formatée.
    :param access_token: Jeton d'accès pour l'authentification Salesforce.
    :param salesforce_base_url: URL de base de l'instance Salesforce.
    :return: Réponse de Salesforce ou message d'erreur.
    """
    try:
        # Connexion à Salesforce
        sf = Salesforce(instance_url=salesforce_base_url, session_id=access_token)

        # Insertion de l'opportunité
        result = sf.Opportunity.create(opportunity_data)

        return result

    except Exception as e:
        return {"error": f"Exception lors de l'insertion de l'opportunité : {str(e)}"}

def add_contact(contact_data, access_token, salesforce_base_url):
    """
    Ajoute un contact à Salesforce.
    :param contact_data: Dictionnaire contenant les données du contact formaté.
    :param access_token: Jeton d'accès pour l'authentification Salesforce.
    :param salesforce_base_url: URL de base de l'instance Salesforce.
    :return: Réponse de Salesforce ou message d'erreur.
    """
    try:
        sf = Salesforce(instance_url=salesforce_base_url, session_id=access_token)
        result = sf.Contact.create(contact_data)
        return result
    except Exception as e:
        return {"error": f"Exception lors de l'insertion du contact : {str(e)}"}

def add_account(account_data, access_token, salesforce_base_url):
    """
    Ajoute un compte à Salesforce.
    :param account_data: Dictionnaire contenant les données du compte formaté.
    :param access_token: Jeton d'accès pour l'authentification Salesforce.
    :param salesforce_base_url: URL de base de l'instance Salesforce.
    :return: Réponse de Salesforce ou message d'erreur.
    """
    try:
        sf = Salesforce(instance_url=salesforce_base_url, session_id=access_token)
        result = sf.Account.create(account_data)
        return result
    except Exception as e:
        return {"error": f"Exception lors de l'insertion du compte : {str(e)}"}

def parse_contact_text(contact_text):
    """
    Analyse le texte d'un contact et retourne un dictionnaire JSON avec les noms de champs Salesforce.
    Extraction par regex, pas de valeur par défaut, uniquement les champs extraits, nettoyage des clés.
    """
    try:
        sf = Salesforce(instance_url=os.getenv("SALESFORCE_BASE_URL"), session_id=os.getenv("accessToken"))
        fields = {
            "FirstName": r"^[\-\•\s]*Pr[ée]nom\s*:\s*(.+?)(?:\n|$)",
            "LastName": r"^[\-\•\s]*Nom\s*:\s*(.+?)(?:\n|$)",
            "AccountId": r"^[\-\•\s]*Nom du compte\s*:\s*(.+?)(?:\n|$)",
            "Fonction__c": r"^[\-\•\s]*Fonction\s*:\s*(.+?)(?:\n|$)",
            "Email": r"^[\-\•\s]*Adresse mail\s*:\s*(.+?)(?:\n|$)",
            "CurrencyIsoCode": r"^[\-\•\s]*Devise du compte\s*:\s*(.+?)(?:\n|$)"
        }
        contact_data = {}
        # Extraction stricte prénom/nom
        for key, pattern in fields.items():
            match = re.search(pattern, contact_text, re.IGNORECASE | re.MULTILINE)
            if match:
                value = match.group(1).strip()
                print(f"Champ extrait : {key} = {value}")
                if key == "AccountId":
                    account_name = value.replace("'", "\\'")
                    query = f"SELECT Id FROM Account WHERE Name = '{account_name}' LIMIT 1"
                    try:
                        result = sf.query(query)
                        if result['records']:
                            value = result['records'][0]['Id']
                        else:
                            print(f"Aucun compte trouvé pour le nom : {account_name}")
                            value = None
                    except Exception as e:
                        print(f"Erreur lors de la recherche d'AccountId : {e}")
                        value = None
                contact_data[key] = value
        # Devise toujours XOF
        contact_data["CurrencyIsoCode"] = "XOF"
        
        # Nettoyage des clés non Salesforce
        champs_sf = [
            "FirstName", "LastName", "AccountId", "Fonction__c", "Email", "CurrencyIsoCode"
        ]
        contact_data = {k: v for k, v in contact_data.items() if k in champs_sf and v is not None}
        return contact_data
    except Exception as e:
        print(f"Erreur lors du parsing du contact : {e}")
        return {}

def parse_account_text(account_text):
    """
    Analyse le texte d'un compte et retourne un dictionnaire JSON avec les noms de champs Salesforce.
    Extraction par regex, pas de valeur par défaut, uniquement les champs extraits, nettoyage des clés.
    """
    try:
        sf = Salesforce(instance_url=os.getenv("SALESFORCE_BASE_URL"), session_id=os.getenv("accessToken"))
        fields = {
            "Name": r"Nom du compte\s*:\s*(.+)",
            "Type": r"Type\s*:\s*(.+)",
            "class_id__c": r"Classe de compte\s*:\s*(.+)",
            "Phone": r"T[ée]l[ée]phone\s*:\s*(.+)",
            "Industry": r"Secteur d’activit[ée]\s*:\s*(.+)",
            "Note_client__c": r"Note client\s*:\s*(.+)",
            "Ninea__c": r"NINEA\s*:\s*(.+)",
            "RC__c": r"RC\s*:\s*(.+)",
            "RSE__c": r"RSE\s*:\s*(.+)",
            "normes_certification__c": r"Normes? et certification[s]? internationales?\s*:\s*(.+)"
        }
        account_data = {}
        for key, pattern in fields.items():
            match = re.search(pattern, account_text, re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                print(f"Champ extrait : {key} = {value}")
                if key == "class_id__c":
                    classe_value = value
                    classe_query = f"SELECT Id FROM Classe__c WHERE Name = '{classe_value}' LIMIT 1"
                    classe_result = sf.query(classe_query)
                    if classe_result['records']:
                        classe_id = classe_result['records'][0]['Id']
                    else:
                        classe_create = sf.Classe__c.create({"Name": classe_value})
                        classe_id = classe_create.get('id')
                    account_data["class_id__c"] = classe_id
                    print(f"Champ extrait : class_id__c = {classe_id}")
                else:
                    account_data[key] = value
        for wrong_key in ["Classe_id__c", "classe_id__c"]:
            if wrong_key in account_data:
                del account_data[wrong_key]
        champs_sf = [
            "Name", "Type", "class_id__c", "Phone", "Industry", "Note_client__c",
            "Ninea__c", "RC__c", "RSE__c", "normes_certification__c"
        ]
        account_data = {k: v for k, v in account_data.items() if k in champs_sf and v is not None}
        return account_data
    except Exception as e:
        print(f"Erreur lors du parsing du compte : {e}")
        return {}

from FONCTION import detect_opportunities, transcribe_audio_file, convert_audio_to_wav, create_contact, create_compte
from PIL import Image
import pytesseract
import re
import requests
import os
from dotenv import load_dotenv
from scraping import execute_notebook, dict_to_text
from offre import OffreScraper
from memoire import ajouter_texte, texte_existe, ajouter_opportunite, opportunite_existe, ajouter_contact, ajouter_compte, contact_existe, compte_existe

load_dotenv(dotenv_path="key.env")
class OpportunityPipeline:
    def __init__(self):
        self.opportunities_set = set()

    def handle_image_file(self, file_path):
        try:
            # Charger l'image et extraire le texte
            image = Image.open(file_path)
            texte = pytesseract.image_to_string(image, lang='fra+eng')
            if texte:
                self.process_text(texte)
            return texte
        except Exception as e:
            print(f"Erreur lors du traitement de l'image : {e}")
            return None

    def handle_audio_file(self, file_path):
        try:
            # Convertir l'audio en WAV et transcrire
            wav_path = convert_audio_to_wav(file_path)
            if wav_path:
                texte = transcribe_audio_file(wav_path)
                if texte:
                    self.process_text(texte)
                return texte
            return None
        except Exception as e:
            print(f"Erreur lors du traitement de l'audio : {e}")
            return None

    def process_text(self, texte):
        # Extraire les opportunités du texte sans vérifier si le texte a déjà été utilisé
        raw_opportunities = detect_opportunities(texte)
        # Séparer chaque opportunité par des lignes vides
        blocs = re.split(r"\n\s*\n", raw_opportunities.strip())

        for bloc in blocs:
            normalized = bloc.strip()
            if normalized and normalized not in self.opportunities_set:
                # Vérifier si l'opportunité existe déjà dans la mémoire
                if opportunite_existe({"texte": normalized}):
                    print("Opportunité déjà présente dans la mémoire, ignorée.")
                    continue
                print("Nouvelle opportunité détectée :\n", normalized)  # Affichage unique
                self.opportunities_set.add(normalized)
                ajouter_opportunite({"texte": normalized})
            elif normalized:
                print("Opportunité déjà détectée, ignorée.")
        # Ajouter le texte à la mémoire après traitement
        ajouter_texte(texte)
        return raw_opportunities


    def handle_scraped_offers(self, notebook_path, index=None):
        """
        Crée des opportunités à partir des offres scrapées.
        Si index est None, traite toutes les offres. Sinon, traite seulement l'offre à l'index donné.
        """
        offres = execute_notebook(notebook_path)
        if not offres:
            print("Aucune offre scrapée dans le marché public.")
            return

        if index is not None:
            # Créer une opportunité à partir d'une offre spécifique
            try:
                offre = offres[index]
                texte = dict_to_text(offre)
                self.process_text(texte)
                if not texte_existe(texte):
                    ajouter_texte(texte)  # Ajout du texte à la mémoire seulement s'il n'existe pas déjà
            except IndexError:
                print(f"Index {index} hors limites pour les offres scrapées.")
        else:
            # Créer des opportunités pour toutes les offres
            for offre in offres:
                texte = dict_to_text(offre)
                self.process_text(texte)
                if not texte_existe(texte):
                    ajouter_texte(texte)  # Ajout du texte à la mémoire seulement s'il n'existe pas déjà

    def handle_scraped_offers_from_list(self, offres_data, index=None):
        """
        Crée des opportunités à partir d'une liste d'offres déjà extraites.
        Si index est None, traite toutes les offres. Sinon, traite seulement l'offre à l'index donné.
        """
        if not offres_data:
            print("Aucune offre scrapée dans le marché public.")
            return

        if index is not None:
            # Créer une opportunité à partir d'une offre spécifique
            try:
                offre = offres_data[index]
                texte = dict_to_text(offre)
                self.process_text(texte)
                if not texte_existe(texte):
                    ajouter_texte(texte)
            except IndexError:
                print(f"Index {index} hors limites pour les offres scrapées.")
        else:
            # Créer des opportunités pour toutes les offres
            for offre in offres_data:
                texte = dict_to_text(offre)
                self.process_text(texte)
                if not texte_existe(texte):
                    ajouter_texte(texte)

    def process_contact(self, texte):
        """
        Traite un texte pour créer un contact à partir du modèle create_contact.
        Ajoute le contact à la mémoire s'il n'existe pas déjà (vérification uniquement sur le contact, pas sur le texte).
        Retourne le texte généré pour traitement ultérieur.
        """
        contact_text = create_contact(texte)
        print("Contact généré :\n", contact_text)
        # Ajout à la mémoire sur la base du texte généré (pas de parsing)
        if contact_existe(contact_text):
            print("Contact déjà présent dans la mémoire, ignoré.")
        else:
            ajouter_contact(contact_text)
            print("Contact ajouté à la mémoire.")
        return contact_text

    def process_account(self, texte):
        """
        Traite un texte pour créer un compte à partir du modèle create_compte.
        Ajoute le compte à la mémoire s'il n'existe pas déjà (vérification uniquement sur le compte, pas sur le texte).
        Retourne le texte généré pour traitement ultérieur.
        """
        account_text = create_compte(texte)
        print("Compte généré :\n", account_text)
        if compte_existe(account_text):
            print("Compte déjà présent dans la mémoire, ignoré.")
        else:
            ajouter_compte(account_text)
            print("Compte ajouté à la mémoire.")
        return account_text


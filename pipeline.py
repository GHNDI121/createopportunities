from FONCTION import detect_opportunities, transcribe_audio_file, convert_audio_to_wav, parse_opportunity_text
from PIL import Image
import pytesseract
import re
import requests
import os
from dotenv import load_dotenv

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
        raw_opportunities = detect_opportunities(texte)
        # Séparer chaque opportunité par des lignes vides
        blocs = re.split(r"\n\s*\n", raw_opportunities.strip())

        for bloc in blocs:
            normalized = bloc.strip()
            if normalized and normalized not in self.opportunities_set:
                print("Nouvelle opportunité détectée :\n", normalized)  # Affichage unique
                self.opportunities_set.add(normalized)
            elif normalized:
                print("Opportunité déjà détectée, ignorée.")


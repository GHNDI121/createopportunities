import json
import os
from typing import List, Dict

TEXTS_FILE = "memoire_textes.json"
OPPORTUNITES_FILE = "memoire_opportunites.json"
COMPTES_FILE = "memoire_comptes.json"
CONTACTS_FILE = "memoire_contacts.json"

def charger_textes() -> List[str]:
    if os.path.exists(TEXTS_FILE):
        with open(TEXTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def ajouter_texte(texte: str):
    textes = charger_textes()
    if texte not in textes:
        textes.append(texte)
        with open(TEXTS_FILE, "w", encoding="utf-8") as f:
            json.dump(textes, f, ensure_ascii=False, indent=2)

def texte_existe(texte: str) -> bool:
    return texte in charger_textes()

def charger_opportunites() -> List[Dict]:
    if os.path.exists(OPPORTUNITES_FILE):
        with open(OPPORTUNITES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def ajouter_opportunite(opportunite: Dict):
    opportunites = charger_opportunites()
    if opportunite not in opportunites:
        opportunites.append(opportunite)
        with open(OPPORTUNITES_FILE, "w", encoding="utf-8") as f:
            json.dump(opportunites, f, ensure_ascii=False, indent=2)

def supprimer_opportunite(opportunite: dict):
    """
    Supprime une opportunité du fichier memoire_opportunites.json si elle existe.
    La recherche se fait sur le champ 'texte' s'il existe, sinon sur 'Name' ou un ensemble de champs principaux.
    """
    opportunites = charger_opportunites()
    key_fields = ["texte", "Name", "Nom de l'opportunité"]
    # Trouver la clé d'identification présente
    for key in key_fields:
        if key in opportunite:
            value = opportunite[key]
            for o in opportunites:
                if o.get(key) == value:
                    opportunites.remove(o)
                    with open(OPPORTUNITES_FILE, "w", encoding="utf-8") as f:
                        json.dump(opportunites, f, ensure_ascii=False, indent=2)
                    return True
            break  # On ne cherche qu'une seule clé d'identification
    # Si aucune clé unique, on tente une correspondance partielle sur les champs principaux
    for o in opportunites:
        if all(opportunite.get(k) == o.get(k) for k in opportunite.keys() if k in o):
            opportunites.remove(o)
            with open(OPPORTUNITES_FILE, "w", encoding="utf-8") as f:
                json.dump(opportunites, f, ensure_ascii=False, indent=2)
            return True
    return False

def opportunite_existe(opportunite: Dict) -> bool:
    return opportunite in charger_opportunites()

def charger_comptes() -> List[Dict]:
    if os.path.exists(COMPTES_FILE):
        with open(COMPTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def ajouter_compte(compte: Dict):
    comptes = charger_comptes()
    if compte not in comptes:
        comptes.append(compte)
        with open(COMPTES_FILE, "w", encoding="utf-8") as f:
            json.dump(comptes, f, ensure_ascii=False, indent=2)

def compte_existe(compte: Dict) -> bool:
    return compte in charger_comptes()

def charger_contacts() -> List[Dict]:
    if os.path.exists(CONTACTS_FILE):
        with open(CONTACTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def ajouter_contact(contact: Dict):
    contacts = charger_contacts()
    if contact not in contacts:
        contacts.append(contact)
        with open(CONTACTS_FILE, "w", encoding="utf-8") as f:
            json.dump(contacts, f, ensure_ascii=False, indent=2)

def contact_existe(contact: Dict) -> bool:
    return contact in charger_contacts()

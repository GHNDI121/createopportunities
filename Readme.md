# Document de Conception Technique : AUTOMATISATION PROCESSUS DE CREATION D’OPPORTUNITE : INTEGRATION D’IA SUR SALESFORCE 

## I) Contexte

### 1) Problématique

Neurotech, opérateur panafricain de services informatiques et de talents, dans sa vision de mieux gérer sa relation client et d’optimiser sa croissance, a souhaité améliorer son processus de création d’opportunité. Au fur et à mesure que les sources d’opportunités se sont ajoutées, il devient difficile de créer manuellement et correctement l’ensemble des opportunités, ce qui est source de lenteurs, d’erreurs et d’inefficacité.  

En effet, les sales vont parfois à la rencontre des clients, prennent des notes ou des enregistrements, tout comme ils reçoivent parfois des mails venant des clients et ils sont obligés de produire un compte rendu et de remplir manuellement des champs pour la création d’opportunité.  

Par ailleurs, Neurotech a prévu d’intégrer l’IA et le ML dans son CRM dans l’optique d’améliorer ses performances et de limiter les tâches chronophages. Ce projet est donc une occasion d’optimiser certains processus tout en exploitant les différents avantages de l’IA.  


### 2) Champs de création d’opportunité

En effet Salesforce comporte des objets composés de champs. Dans notre cas de figure, c’est l’objet opportunité qui nous intéresse.  
L’objet opportunité comporte des champs de remplissage qui sont obligatoires pour la création d’une nouvelle opportunité. Et parmi ces champs, il y en a qui sont vides et d’autres qui comportent une liste d’enregistrement au choix.  

#### • Champs vides :
1. **Nom de l’opportunité**  
2. **Nom du compte**  
3. **Date de clôture**  

#### • Champs comportant une liste d’enregistrement : 
1. **Étape**  
2. **Pays**  
3. **Origine de la piste**  
4. **Type**  

##### Cependant chaque champ comportant une liste d’enregistrement a sa particularité :
1. **Étape** : Il prend la valeur « Prospection » à l’étape de la création d’opportunité et peut varier au cours du projet.  
2. **Pays** : Ce champ prend la valeur de « Sénégal » par défaut à la création de l’opportunité, sauf s’il est renseigné au préalable dans le texte.  
3. **Origine de la piste** : Ce champ prend l’enregistrement « demande client spontanée » à l’étape de création d’opportunité par défaut à moins qu’on détecte un renseignement plus adéquat dans le texte.  
4. **Type** : Il comporte 4 éléments dans sa liste d’enregistrement (« vente directe », « renouvellement hors contrat », « contrat de maintenance », « projet ») et doit contenir l’enregistrement le plus adéquat lors de la création d’opportunité.  

**NB :** Le champ « date de clôture » renvoie la date une semaine après sa date de création par défaut si elle n'est pas renseignée.  


### 3) Solution

La solution attendue est l’optimisation de ce processus par le biais de l’intelligence artificielle et ainsi alléger le travail des Sales.  


## II°) Document de conception technique

### 1. Architecture générale

Le projet est structuré autour de plusieurs modules interconnectés pour automatiser la création d'opportunités dans Salesforce. L'architecture suit un pipeline de traitement des données, allant de la récupération des données brutes (emails, images, audios, offres web) à leur traitement et intégration dans Salesforce via une API. Un module de mémoire permet d'éviter les doublons lors de la création d'opportunités, comptes et contacts.

### 2. Composants principaux

#### a) **FONCTION.py**
- Contient les fonctions utilitaires pour extraire et traiter les données provenant de différentes sources (texte, image, audio).
- **Principales fonctionnalités** :
  - Extraction de texte depuis des images via OCR (`pytesseract`).
  - Transcription d'audio en texte via `speechrecognition` et conversion en WAV (`pydub`).
  - Utilisation de la bibliothèque `Groq` pour l'appel à un LLM (modèle de langage) afin de détecter et structurer les opportunités, comptes et contacts.
  - Gestion de la clé API Groq via les variables d'environnement.
  - Modèle de détection d'opportunités basé sur un LLM pour identifier les informations pertinentes et remplir les champs nécessaires.
  - Analyse des opportunités détectées pour générer un dictionnaire JSON structuré.
  - Fonctions de parsing et d'ajout d'opportunité, de compte et de contact séparées, prenant en charge la structuration des données pour Salesforce.
  - Gestion des erreurs et validation des entrées pour garantir la robustesse des traitements.

#### b) **pipeline.py**
- Implémente le pipeline de traitement des données.
- **Principales fonctionnalités** :
  - Gestion des entrées (texte, image, audio, offres web scrapées).
  - Appel au modèle de détection d'opportunités pour extraire les informations pertinentes.
  - Élimination des doublons dans les opportunités, comptes et contacts détectés grâce au module `memoire.py` (stockage dans des fichiers JSON).
  - Stockage des opportunités dans un ensemble pour éviter les répétitions.
  - Normalisation des opportunités détectées pour garantir leur unicité.
  - Prise en charge du traitement des offres scrapées depuis le notebook `scraping.ipynb` (exécution automatique du notebook et conversion des offres en texte).
  - Envoi des opportunités détectées à Salesforce via l'API REST.

#### c) **API_ghndi.py**
- Fournit une interface RESTful pour interagir avec le pipeline.
- **Principales fonctionnalités** :
  - Endpoints pour l'authentification OAuth Salesforce (login, callback, vérification de connexion).
  - Endpoint pour traiter des fichiers (image/audio) et détecter des opportunités.
  - Endpoint pour soumettre du texte ou enregistrer un audio pour analyse.
  - Endpoint pour récupérer toutes les opportunités détectées ou les offres scrapées depuis le notebook.
  - Endpoint pour créer un compte ou un contact à partir du dernier texte traité.
  - Endpoint pour envoyer les opportunités détectées directement à Salesforce.
  - Utilise `FastAPI` pour la création de l'API et `CORS` pour permettre des requêtes cross-origin.
  - Utilisation de variables d'environnement pour la configuration Salesforce et Groq.
  - Intégration du pipeline et gestion des erreurs pour chaque endpoint.

#### d) **scraping.ipynb & scraping.py**
- Le notebook `scraping.ipynb` permet de scraper les offres du site `marchespublics.sn` et de les convertir en liste de dictionnaires.
- Le script `scraping.py` exécute le notebook, extrait les offres et les convertit en texte structuré pour le pipeline.

#### e) **memoire.py**
- Module de gestion de la mémoire pour éviter les doublons (textes, opportunités, comptes, contacts) via des fichiers JSON.
- Permet de vérifier l'existence et d'ajouter chaque entité de façon unique.

#### f) **key.env**
- Contient les variables d'environnement nécessaires pour le projet (Groq, Salesforce, Jenkins, etc.).

#### g) **requirements.txt**
- Liste toutes les dépendances nécessaires au projet, incluant :
  - IA (groq)
  - Scraping (selenium, webdriver-manager, pandas, nbformat, nbconvert)
  - API (fastapi, uvicorn, python-multipart)
  - Mémoire (json)
  - OCR (pytesseract, Pillow)
  - Audio (pydub, speechrecognition, pyaudio)
  - Autres utilitaires (dotenv, streamlit, simple-salesforce, etc.)

### 3. Rôle des dépendances

Voici le rôle des dépendances réellement importées dans les fichiers principaux du projet :

- fastapi -> Création de l'API REST (endpoints, gestion des requêtes HTTP).
- fastapi.responses (JSONResponse, RedirectResponse, HTMLResponse) -> Gestion des réponses HTTP spécifiques (JSON, redirection, HTML).
- fastapi.middleware.cors.CORSMiddleware -> Autorisation des requêtes cross-origin (CORS) pour l'API.
- dotenv (load_dotenv) -> Chargement des variables d'environnement depuis le fichier `key.env`.
- os -> Accès aux variables d'environnement, gestion des chemins de fichiers.
- secrets, base64, hashlib -> Génération sécurisée de tokens et gestion de l'authentification OAuth (Salesforce).
- requests -> Requêtes HTTP pour communiquer avec Salesforce ou d'autres services web.
- PIL (Pillow) -> Ouverture et manipulation d'images (extraction de texte via OCR).
- pytesseract -> Extraction de texte à partir d'images (OCR).
- groq -> Appel au modèle LLM Groq pour la détection et la structuration des opportunités, comptes, contacts.
- pydub -> Conversion et manipulation de fichiers audio (ex : conversion en WAV).
- speechrecognition -> Transcription d'audio en texte.
- tkinter (Tk, filedialog) -> Interface graphique pour la sélection de fichiers (optionnel, pour l'utilisateur local).
- datetime, timedelta -> Manipulation des dates (calcul de la date de clôture, etc.).
- simple_salesforce -> Connexion et manipulation d'objets Salesforce via leur API.
- re -> Traitement et découpage de texte avec des expressions régulières.
- nbformat -> Lecture et manipulation de fichiers Jupyter Notebook.
- nbconvert (PythonExporter) -> Conversion de notebooks Jupyter en scripts Python exécutables.
- pandas -> Manipulation de données tabulaires (dans le notebook de scraping).
- selenium, webdriver_manager, selenium.webdriver, selenium.common.exceptions, selenium.webdriver.support -> Automatisation du navigateur pour le scraping web.
- json -> Lecture, écriture et manipulation de données au format JSON (stockage mémoire, parsing, etc.).

Chaque dépendance listée ci-dessus est utilisée dans au moins un des fichiers suivants : `API_ghndi.py`, `FONCTION.py`, `memoire.py`, `pipeline.py`, `scraping.ipynb`, `scraping.py` et joue un rôle précis dans le traitement, l'automatisation, l'IA, le scraping, l'API ou la gestion des données du projet.


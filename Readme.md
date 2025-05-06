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

Le projet est structuré autour de plusieurs modules interconnectés pour automatiser la création d'opportunités dans Salesforce. L'architecture suit un pipeline de traitement des données, allant de la récupération des données brutes (emails, images, audios) à leur traitement et intégration dans Salesforce via une API.  


### 2. Composants principaux

#### a) **FONCTION.py**
- Contient les fonctions utilitaires pour extraire et traiter les données provenant de différentes sources (texte, image, audio).
- **Principales fonctionnalités** :
  - Extraction de texte depuis des images via OCR (`pytesseract`).
  - Transcription d'audio en texte via `speechrecognition`.
  - Conversion de fichiers audio en format WAV pour compatibilité.
  - Modèle de détection d'opportunités basé sur un LLM (Large Language Model) pour identifier les informations pertinentes et remplir les champs nécessaires.
  - Analyse des opportunités détectées pour générer un dictionnaire JSON structuré.
  - Gestion des erreurs et validation des entrées pour garantir la robustesse des traitements.

#### b) **pipeline.py**
- Implémente le pipeline de traitement des données.
- **Principales fonctionnalités** :
  - Gestion des entrées (texte, image, audio).
  - Appel au modèle de détection d'opportunités pour extraire les informations pertinentes.
  - Élimination des doublons dans les opportunités détectées.
  - Stockage des opportunités dans un ensemble pour éviter les répétitions.
  - Normalisation des opportunités détectées pour garantir leur unicité.
  - Envoi des opportunités détectées à Salesforce via l'API REST.

#### c) **API_ghndi.py**
- Fournit une interface RESTful pour interagir avec le pipeline.
- **Principales fonctionnalités** :
  - Endpoint pour traiter des fichiers (image/audio) et détecter des opportunités.
  - Endpoint pour soumettre du texte ou enregistrer un audio pour analyse.
  - Endpoint pour récupérer toutes les opportunités détectées.
  - Endpoint pour envoyer les opportunités détectées directement à Salesforce.
  - Endpoint pour vérifier la connexion à Salesforce.
  - Gestion des erreurs et validation des types de fichiers pour une meilleure expérience utilisateur.
  - Utilise `FastAPI` pour la création de l'API et `CORS` pour permettre des requêtes cross-origin.

#### d) **key.env**
- Contient les variables d'environnement nécessaires pour le projet.
- **Principales informations** :
  - Clé API pour le modèle LLM (`GROQ_API_KEY`).
  - Identifiants et URL pour l'authentification et l'accès à Salesforce.
  - Gestion sécurisée des informations sensibles via des variables d'environnement.

### 3. Flux de données

1. **Entrée des données** :  
   - Les données peuvent provenir de trois sources : texte (chat), image, ou audio.  
   - Les fichiers sont soit chargés depuis le système de fichiers, soit fournis via une URL.  

2. **Traitement des données** :  
   - Les images sont analysées pour extraire du texte via OCR.  
   - Les fichiers audio sont transcrits en texte après conversion en format WAV.  
   - Le texte brut est analysé par un modèle LLM pour détecter les opportunités.  

3. **Détection des opportunités** :  
   - Le modèle LLM génère les champs nécessaires pour chaque opportunité détectée.  
   - Les opportunités sont normalisées et stockées dans un ensemble pour éviter les doublons.  

4. **Sortie des données** :  
   - Les opportunités détectées sont affichées dans la console ou renvoyées via l'API.  
   - Les opportunités peuvent être directement créées dans Salesforce via l'API REST.

### 4. Diagramme d'architecture
```
[données]
     |
     v
[traitement]
     |
     v
[Modèle LLM]
     |
     v
[   API   ]
     |
     v
[Salesforce]
```  


### 5. Technologies utilisées

- **Python** : Langage principal pour le développement.  
- **FastAPI** : Création de l'API RESTful.  
- **pytesseract** : OCR pour extraire du texte des images.  
- **speechrecognition** : Transcription d'audio en texte.  
- **groq** : Utilisé pour la détection d'opportunités.  
- **dotenv** : Gestion des variables d'environnement.  
- **tkinter** : Interface utilisateur pour la sélection de fichiers.


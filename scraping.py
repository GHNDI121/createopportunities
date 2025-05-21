import nbformat 
from nbconvert import PythonExporter 

def execute_notebook(notebook_path):
    """
    Exécute le notebook de scraping et retourne les données extraites.
    """
    try:
        # Charger le notebook
        with open(notebook_path, "r", encoding="utf-8") as f:
            notebook = nbformat.read(f, as_version=4)

        # Convertir le notebook en script Python
        exporter = PythonExporter()
        script, _ = exporter.from_notebook_node(notebook)

        # Exécuter le script et récupérer les données
        exec_globals = {}
        exec(script, exec_globals)

        # Vérifier si les données sont disponibles
        if "offres_liste" in exec_globals:
            return exec_globals["offres_liste"]
        else:
            print("Aucune donnée n'a été extraite du notebook.")
            return []

    except Exception as e:
        print(f"Erreur lors de l'exécution du notebook : {e}")
        return []

def dict_to_text(data):
    """
    Transforme un dictionnaire en texte formaté en utilisant des f-strings.

    Args:
        data (dict): Le dictionnaire contenant les données.

    Returns:
        str: Le texte formaté.
    """
    return (f"{data.get('Autorité', 'Une autorité')} a lancé l'offre ayant comme objet {data.get('Objet', 'un objet non spécifié')}. "
            f"La date limite de clôture de l'offre est {data.get('Date limite', 'une date non spécifiée')}. "
            f"{data.get('Détail', 'Aucun détail fourni.')}")

if __name__ == "__main__":
    # Chemin vers le notebook de scraping
    notebook_path = "scraping.ipynb"

    # Exécuter le notebook et récupérer les données
    offres = execute_notebook(notebook_path)

    # Afficher les nouvelles offres
    for offre in offres:
        print(dict_to_text(offre))
        print("-" * 40)
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
from datetime import datetime
import json

class OffreScraper:
    def __init__(self, chrome_driver_path="chromedriver-win64/chromedriver.exe"):
        self.chrome_driver_path = chrome_driver_path
        self.options = Options()
        self.options.add_argument('--headless')  # Exécuter en mode sans tête (sans interface graphique)
        self.options.add_argument('--disable-gpu')
        self.options.add_argument('--no-sandbox')

    def scrape_offres(self, url):
        driver = webdriver.Chrome(service=Service(self.chrome_driver_path), options=self.options)
        offres_liste = []
        try:
            driver.get(url)
            current_year = datetime.now().year
            rows = driver.find_elements(By.CSS_SELECTOR, "table.content_table tbody tr")[1:]  # pour sauter l'entête
            data = []
            for row in rows[1:]:
                try:
                    cols = row.find_elements(By.TAG_NAME, "td")
                    if len(cols) < 6:
                        continue

                    # ✅ Tenter de récupérer le lien AVANT de continuer
                    try:
                        detail_td = cols[5]
                        div = detail_td.find_element(By.TAG_NAME, "div")
                        a_tags = div.find_elements(By.TAG_NAME, "a")
                        if not a_tags:
                            continue  # Pas de lien => ce n'est pas une ligne d'offre
                        detail_link = a_tags[0].get_attribute("href")
                    except:
                        continue  # Évite les erreurs sur les lignes non valides

                    # ✅ Extraire les autres infos de la ligne
                    ref = cols[0].text.strip() or "NA"
                    objet = cols[1].text.strip() or "NA"
                    autorite = cols[2].text.strip() or "NA"
                    publie_le = cols[3].text.strip() or "NA"
                    date_limite = cols[4].text.strip() or "NA"

                    # ✅ Ouvrir le lien dans un nouvel onglet
                    driver.execute_script("window.open(arguments[0]);", detail_link)
                    driver.switch_to.window(driver.window_handles[1])

                    try:
                        table_elem = WebDriverWait(driver, 5).until(
                            EC.presence_of_element_located((By.CSS_SELECTOR, "table.no-style"))
                        )
                        td_elem = table_elem.find_element(By.TAG_NAME, "td")
                        detail_text = td_elem.text.strip() or "NA"
                    except Exception as e:
                        print(f"⚠️ Détail non trouvé pour {ref} : {e}")
                        detail_text = "NA"

                    driver.close()
                    driver.switch_to.window(driver.window_handles[0])

                    data.append([ref, objet, autorite, publie_le, date_limite, detail_text])

                except Exception as e:
                    print(f"❌ Erreur sur l’offre {ref if 'ref' in locals() else 'inconnue'} : {e}")
                    continue

            # Utiliser pandas pour formater la sortie comme dans le notebook
            df = pd.DataFrame(data, columns=["Référence", "Objet", "Autorité", "Publié le", "Date limite", "Détail"])
            offres_liste = df.to_dict(orient='records')
        finally:
            driver.quit()
        return offres_liste

# Exemple d'utilisation :
# scraper = OffreScraper(r"C:\Users\SURFACE STUDIO\OneDrive\Bureau\Stage Neurotech\IA CRM\projet-neurotech\nouveau depart\chromedriver-win64\chromedriver.exe")
# url = "http://www.marchespublics.sn/index.php?option=com_loffres&task=view&idcat=002&Itemid=104&gestion=2025&statut=1"
# offres = scraper.scrape_offres(url)
# print(offres)
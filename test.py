from offre import OffreScraper

# Exemple d'utilisation :
scraper = OffreScraper("chromedriver-win64/chromedriver.exe")
url = "http://www.marchespublics.sn/index.php?option=com_loffres&task=view&idcat=002&Itemid=104&gestion=2025&statut=1"
offres = scraper.scrape_offres(url)
print(offres)
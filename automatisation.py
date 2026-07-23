import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import urllib.parse
import requests
import pandas as pd
import unicodedata

print("Démarrage du pipeline d'intelligence territoriale...")

# ---------------------------------------------------------
# 1. VEILLE OSINT (Recherche ciblée)
# ---------------------------------------------------------
villes_cibles = [
    "Avignon", "Toulouse", "Dunkerque", "Fos-sur-Mer", "Montataire",
    "Le Havre", "Saint-Vulbas", "Saint-Priest", "Valenciennes", "Nantes"
]
veille_data = {"generated_at": datetime.now().isoformat(), "communes": {}}

print("Démarrage du balayage média...")
for ville in villes_cibles:
    query = urllib.parse.quote(f'"{ville}" AND (logistique OR usine OR implantation OR friche OR ZAN OR PLUi)')
    url = f"https://news.google.com/rss/search?q={query}&hl=fr&gl=FR&ceid=FR:fr"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            root = ET.fromstring(response.read())
            items = []
            for item in root.findall('.//item')[:3]: 
                items.append({
                    "title": item.find('title').text,
                    "link": item.find('link').text
                })
            if items:
                veille_data["communes"][ville] = {"items": items}
        time.sleep(1) # Pause anti-blocage
    except Exception as e:
        print(f"Erreur sur la veille de {ville}: {e}")

with open('veille.json', 'w', encoding='utf-8') as f:
    json.dump(veille_data, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------
# 2. CARTOFRICHES (Aspiration de la Base Nationale Détaillée)
# ---------------------------------------------------------
print("\nRecherche de la dernière base nationale Cartofriches...")
try:
    api_url = "https://www.data.gouv.fr/api/1/datasets/?q=cartofriches"
    res = requests.get(api_url).json()
    csv_url = None
    
    for dataset in res.get('data', []):
        for resource in dataset.get('resources', []):
            if resource.get('format', '').lower() == 'csv':
                csv_url = resource['url']
                break
        if csv_url: break

    if not csv_url:
        raise Exception("Impossible de localiser le CSV officiel.")

    print(f"Téléchargement du socle de données depuis : {csv_url}")
    df = pd.read_csv(csv_url, sep=None, engine='python', on_bad_lines='skip', dtype=str)
    df.columns = [unicodedata.normalize('NFKD', str(c)).encode('ASCII', 'ignore').decode('utf-8').lower().strip() for c in df.columns]

    # Colonnes expertes
    col_commune = next((c for c in df.columns if 'commune' in c or 'ville' in c), None)
    col_nom = next((c for c in df.columns if 'nom_site' in c or ('nom' in c and 'site' in c)), None)
    col_surface = next((c for c in df.columns if 'surface' in c), None)
    col_statut = next((c for c in df.columns if 'statut' in c and 'site' in c), None)
    col_type = next((c for c in df.columns if 'type' in c and 'friche' in c), None)
    col_resume = next((c for c in df.columns if 'resume' in c or 'environnement' in c), None)

    if not col_nom: col_nom = next((c for c in df.columns if 'nom' in c), None)

    friches_data = {"generated_at": datetime.now().isoformat(), "communes": {}}

    if col_commune:
        df[col_commune] = df[col_commune].astype(str).str.title().str.strip()

        print("Structuration des données foncières avancées en cours...")
        for commune, group in df.groupby(col_commune):
            sites_list = []
            for _, row in group.iterrows():
                nom_site = str(row[col_nom]) if col_nom and pd.notna(row[col_nom]) else "Site à requalifier"
                surface = str(row[col_surface]) if col_surface and pd.notna(row[col_surface]) else "N/C"
                statut = str(row[col_statut]) if col_statut and pd.notna(row[col_statut]) else "Non précisé"
                type_friche = str(row[col_type]) if col_type and pd.notna(row[col_type]) else "Non précisé"
                resume = str(row[col_resume]) if col_resume and pd.notna(row[col_resume]) else ""

                if nom_site.lower() == 'nan': nom_site = "Site à requalifier"

                if nom_site != "Site à requalifier" or surface != "N/C":
                    sites_list.append({
                        "nom": nom_site.strip(),
                        "surface": surface.strip(),
                        "statut": statut.strip(),
                        "type": type_friche.strip(),
                        "resume": resume.strip()
                    })

            score_max = 5 if len(sites_list) > 5 else (4 if len(sites_list) > 2 else (3 if len(sites_list) > 0 else 1))

            if len(sites_list) > 0:
                friches_data["communes"][commune] = {
                    "score_max": score_max,
                    "friches_count": len(sites_list),
                    "sites": sites_list[:15]
                }

    with open('friches_national.json', 'w', encoding='utf-8') as f:
        json.dump(friches_data, f, ensure_ascii=False, indent=2)

    print(f"Extraction terminée : {len(friches_data['communes'])} territoires analysés.")

except Exception as e:
    print(f"Alerte sur le traitement foncier : {e}")

print("Architecture mise à jour avec succès.")

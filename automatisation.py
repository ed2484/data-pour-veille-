import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import urllib.parse
import time
import requests
import pandas as pd
import unicodedata
import io

print("Démarrage du pipeline d'intelligence territoriale (MODE CARTOFRICHES REEL)...")

# ---------------------------------------------------------
# 1. VEILLE OSINT
# ---------------------------------------------------------
villes_cibles = ["Avignon", "Toulouse", "Dunkerque", "Fos-sur-Mer", "Montataire", "Le Havre", "Saint-Vulbas", "Saint-Priest", "Valenciennes", "Nantes"]
veille_data = {"generated_at": datetime.now().isoformat(), "communes": {}}

for ville in villes_cibles:
    query = urllib.parse.quote(f'"{ville}" AND (logistique OR usine OR implantation OR friche OR ZAN)')
    url = f"https://news.google.com/rss/search?q={query}&hl=fr&gl=FR&ceid=FR:fr"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            root = ET.fromstring(response.read())
            items = [{"title": item.find('title').text, "link": item.find('link').text} for item in root.findall('.//item')[:3]]
            if items: veille_data["communes"][ville] = {"items": items}
        time.sleep(1)
    except Exception as e:
        print(f"Erreur veille sur {ville}: {e}")

with open('veille.json', 'w', encoding='utf-8') as f:
    json.dump(veille_data, f, ensure_ascii=False, indent=2)

# ---------------------------------------------------------
# 2. CARTOFRICHES (Branchement direct API data.gouv.fr)
# ---------------------------------------------------------
print("\nConnexion à la base gouvernementale du Cerema...")
try:
    # Identifiant unique et officiel du jeu de données Cartofriches
    dataset_id = "5f96b256d0bd85aab1b9f71c"
    api_url = f"https://www.data.gouv.fr/api/1/datasets/{dataset_id}/"
    res = requests.get(api_url).json()
    
    csv_url = None
    for resource in res.get('resources', []):
        if resource.get('format', '').lower() == 'csv':
            csv_url = resource['url']
            break

    if not csv_url:
        raise Exception("Lien CSV introuvable dans le dataset officiel.")

    print(f"Téléchargement du fichier national : {csv_url}")
    
    # requests brut pour contourner les blocages SSL du gouvernement
    s = requests.get(csv_url).content
    df = pd.read_csv(io.StringIO(s.decode('utf-8', errors='replace')), sep=None, engine='python')

    # Nettoyage massif des noms de colonnes pour éviter les crashs
    df.columns = [str(c).lower().strip() for c in df.columns]

    # Détection intelligente des colonnes selon la nomenclature de l'État
    col_commune = next((c for c in df.columns if c in ['nom_commune', 'commune', 'libcom', 'ville']), None)
    col_nom = next((c for c in df.columns if c in ['site_nom', 'nom_site', 'nom_friche', 'nom_usuel', 'nom']), None)
    col_surf = next((c for c in df.columns if 'surf' in c), None)
    col_statut = next((c for c in df.columns if 'statut' in c or 'etat' in c or 'avancement' in c), None)
    col_type = next((c for c in df.columns if 'type' in c or 'vocation' in c), None)

    friches_data = {"generated_at": datetime.now().isoformat(), "communes": {}}

    # Fonction pour casser les majuscules et les tirets et faire matcher avec ta base
    def normaliser(nom):
        if pd.isna(nom): return ""
        return unicodedata.normalize('NFKD', str(nom)).encode('ASCII', 'ignore').decode('utf-8').lower().replace('-', ' ').strip()

    if col_commune:
        df['commune_norm'] = df[col_commune].apply(normaliser)

        print("Traitement des friches en cours...")
        for commune_norm, group in df.groupby('commune_norm'):
            if not commune_norm: continue
            
            # On récupère le nom propre de la ville pour l'affichage (ex: "Chalon-sur-Saône")
            vrai_nom = str(group[col_commune].iloc[0]).title()
            
            sites_list = []
            for _, row in group.iterrows():
                n = str(row[col_nom]) if col_nom and pd.notna(row[col_nom]) else "Site à qualifier"
                s = str(row[col_surf]) if col_surf and pd.notna(row[col_surf]) else "N/C"
                st = str(row[col_statut]) if col_statut and pd.notna(row[col_statut]) else "Non précisé"
                ty = str(row[col_type]) if col_type and pd.notna(row[col_type]) else "Friche"
                
                if n.lower() != 'nan':
                    # Arrondi propre de la surface si c'est un nombre
                    try: 
                        s = f"{float(s):.1f}"
                    except: 
                        pass

                    sites_list.append({
                        "nom": n, 
                        "surface": s, 
                        "statut": st, 
                        "type": ty, 
                        "resume": "Identifié via l'inventaire national du Cerema"
                    })

            # Attribution de la notation d'opportunité foncière
            score = 5 if len(sites_list) >= 5 else (4 if len(sites_list) >= 2 else 3)
            
            if sites_list:
                friches_data["communes"][vrai_nom] = {
                    "score_max": score,
                    "friches_count": len(sites_list),
                    "sites": sites_list[:15] # Plafond à 15 sites majeurs
                }

        with open('friches_national.json', 'w', encoding='utf-8') as f:
            json.dump(friches_data, f, ensure_ascii=False, indent=2)

        print(f"Succès total : {len(friches_data['communes'])} communes intégrées au radar.")
    else:
        print("Erreur : Impossible d'isoler la colonne des communes dans le fichier de l'État.")

except Exception as e:
    print(f"Erreur critique sur l'extraction Cartofriches : {e}")

print("Architecture mise à jour avec succès.")

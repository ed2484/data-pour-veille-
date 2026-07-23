import json
import pandas as pd
import unicodedata
from datetime import datetime
import zipfile
import os

print("Extraction des vraies données Cartofriches...")

zip_path = "cartofriches.zip"
extract_path = "extracted_data"

if os.path.exists(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)

csv_files = [os.path.join(extract_path, f) for f in os.listdir(extract_path) if f.endswith('.csv')]
if not csv_files:
    raise Exception("Aucun fichier CSV trouvé dans le ZIP.")

fichier_csv_reel = csv_files[0]

def normaliser(nom):
    if pd.isna(nom): return ""
    return unicodedata.normalize('NFKD', str(nom)).encode('ASCII', 'ignore').decode('utf-8').lower().replace('-', ' ').replace("'", " ").strip()

friches_data = {"generated_at": datetime.now().isoformat(), "communes": {}}

try:
    # Lecture par morceaux pour avaler le gros fichier sans planter
    for chunk in pd.read_csv(fichier_csv_reel, sep=None, engine='python', low_memory=False, chunksize=10000):
        chunk.columns = [str(c).strip().lower() for c in chunk.columns]
        
        col_commune = next((c for c in chunk.columns if c in ['comm_nom', 'commune', 'libcom', 'ville']), None)
        col_nom = next((c for c in chunk.columns if c in ['site_nom', 'nom_site', 'nom_friche', 'nom']), None)
        col_statut = next((c for c in chunk.columns if 'statut' in c or 'occupation' in c), None)
        col_type = next((c for c in chunk.columns if 'type' in c or 'activite_libelle' in c), None)
        col_surf = next((c for c in chunk.columns if 'surf' in c), None)

        if col_commune and col_nom:
            for _, row in chunk.iterrows():
                commune_brute = row.get(col_commune)
                if pd.isna(commune_brute): continue
                
                vrai_nom_ville = str(commune_brute).strip().title()
                nom_site = str(row.get(col_nom, "")).strip()
                
                if not nom_site or nom_site.lower() == 'nan': continue
                
                statut = str(row.get(col_statut, "Non précisé"))
                if pd.isna(statut) or statut.lower() == 'nan': statut = "Non précisé"
                
                type_friche = str(row.get(col_type, "Friche"))
                if pd.isna(type_friche) or type_friche.lower() == 'nan': type_friche = "Friche"
                
                surface = "N/C"
                try:
                    s_val = row.get(col_surf)
                    if pd.notna(s_val):
                        surface = f"{float(s_val):.1f}"
                except:
                    pass

                if vrai_nom_ville not in friches_data["communes"]:
                    friches_data["communes"][vrai_nom_ville] = {
                        "score_max": 4,
                        "friches_count": 0,
                        "sites": []
                    }
                
                # Évite les doublons stricts de sites pour une même ville
                existing_names = [s["nom"] for s in friches_data["communes"][vrai_nom_ville]["sites"]]
                if nom_site not in existing_names and len(existing_names) < 20:
                    friches_data["communes"][vrai_nom_ville]["sites"].append({
                        "nom": nom_site,
                        "surface": surface,
                        "statut": statut,
                        "type": type_friche,
                        "resume": f"Statut : {statut} | Type : {type_friche}"
                    })
                    friches_data["communes"][vrai_nom_ville]["friches_count"] += 1

    # Ajustement des scores selon le nombre de friches
    for ville, data in friches_data["communes"].items():
        cnt = data["friches_count"]
        data["score_max"] = 5 if cnt >= 5 else (4 if cnt >= 2 else 3)

    with open('friches_national.json', 'w', encoding='utf-8') as f:
        json.dump(friches_data, f, ensure_ascii=False, indent=2)
    print("Fichier JSON généré avec succès depuis le CSV brut.")

except Exception as e:
    print(f"Erreur : {e}")

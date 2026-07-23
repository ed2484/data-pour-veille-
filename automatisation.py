import json
import pandas as pd
import unicodedata
from datetime import datetime
import zipfile
import os

print("Décompression et traitement du fichier Cartofriches local...")

# 1. Décompression automatique du fichier ZIP présent sur GitHub
zip_path = "cartofriches.zip"
extract_path = "extracted_data"

if os.path.exists(zip_path):
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_path)
    print("Fichier ZIP décompressé avec succès.")
else:
    raise FileNotFoundError("Le fichier cartofriches.zip est introuvable à la racine du dépôt.")

# Trouver le fichier CSV extrait (peu importe son nom exact à l'intérieur du zip)
csv_files = [os.path.join(extract_path, f) for f in os.listdir(extract_path) if f.endswith('.csv')]
if not csv_files:
    raise Exception("Aucun fichier CSV trouvé dans le dossier compressé.")

fichier_csv_reel = csv_files[0]

try:
    # 2. Lecture du fichier CSV par Pandas
    df = pd.read_csv(fichier_csv_reel, sep=None, engine='python', low_memory=False)
    
    # Nettoyage des noms de colonnes
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Identification des colonnes clés d'après ta structure
    col_commune = 'comm_nom' if 'comm_nom' in df.columns else next((c for c in df.columns if 'comm' in c), None)
    col_nom = 'site_nom' if 'site_nom' in df.columns else next((c for c in df.columns if 'nom' in c), None)
    col_statut = 'site_statut' if 'site_statut' in df.columns else 'site_occupation'
    col_type = 'activite_libelle' if 'activite_libelle' in df.columns else 'site_type'
    col_surf = 'unite_fonciere_surface' if 'unite_fonciere_surface' in df.columns else 'bati_surface'

    friches_data = {"generated_at": datetime.now().isoformat(), "communes": {}}

    if col_commune and col_nom:
        def normaliser(nom):
            if pd.isna(nom): return ""
            return unicodedata.normalize('NFKD', str(nom)).encode('ASCII', 'ignore').decode('utf-8').lower().replace('-', ' ').strip()

        df['commune_norm'] = df[col_commune].apply(normaliser)

        print("Agrégation des données par commune...")
        for commune_norm, group in df.groupby('commune_norm'):
            if not commune_norm: continue
            
            vrai_nom = str(group[col_commune].iloc[0]).title()
            
            sites_list = []
            for _, row in group.iterrows():
                nom_site = str(row[col_nom]) if pd.notna(row.get(col_nom)) else "Site à requalifier"
                statut = str(row[col_statut]) if pd.notna(row.get(col_statut)) else "Non précisé"
                type_friche = str(row[col_type]) if pd.notna(row.get(col_type)) else "Friche"
                
                surface = "N/C"
                try:
                    surf_val = row.get(col_surf)
                    if pd.notna(surf_val):
                        surface = f"{float(surf_val):.1f}"
                except:
                    pass

                if nom_site.lower() != 'nan' and nom_site != "":
                    sites_list.append({
                        "nom": nom_site.strip(),
                        "surface": surface,
                        "statut": statut.strip(),
                        "type": type_friche.strip(),
                        "resume": f"Statut : {statut} | Type : {type_friche}"
                    })

            score_max = 5 if len(sites_list) >= 5 else (4 if len(sites_list) >= 2 else 3)

            if sites_list:
                friches_data["communes"][vrai_nom] = {
                    "score_max": score_max,
                    "friches_count": len(sites_list),
                    "sites": sites_list[:15]
                }

        # 3. Génération du fichier JSON final pour ton site HTML
        with open('friches_national.json', 'w', encoding='utf-8') as f:
            json.dump(friches_data, f, ensure_ascii=False, indent=2)

        print(f"Succès ! {len(friches_data['communes'])} communes traitées et injectées dans 'friches_national.json'.")

    else:
        print("Erreur : Colonnes 'comm_nom' ou 'site_nom' introuvables.")

except Exception as e:
    print(f"Erreur critique lors du traitement : {e}")

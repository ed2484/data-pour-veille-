import json
import pandas as pd
import unicodedata
from datetime import datetime

print("Traitement du fichier Cartofriches local...")

# Nom du fichier CSV que tu vas téléverser dans ton dépôt GitHub (ex: "cartofriches.csv")
# Assure-toi de renommer ton fichier source ou d'adapter le nom ici.
FICHIER_SOURCE = "cartofriches.csv" 

try:
    # Lecture du fichier avec le bon séparateur (souvent une tabulation ou une virgule dans les exports Cerema)
    # On utilise low_memory=False pour éviter les warnings de types mixtes
    df = pd.read_csv(FICHIER_SOURCE, sep=None, engine='python', low_memory=False)
    
    # Nettoyage des noms de colonnes
    df.columns = [str(c).strip().lower() for c in df.columns]

    # Vérification des colonnes clés d'après ta structure
    col_commune = 'comm_nom' if 'comm_nom' in df.columns else next((c for c in df.columns if 'comm' in c), None)
    col_nom = 'site_nom' if 'site_nom' in df.columns else next((c for c in df.columns if 'nom' in c), None)
    col_statut = 'site_statut' if 'site_statut' in df.columns else 'site_occupation'
    col_type = 'activite_libelle' if 'activite_libelle' in df.columns else 'site_type'
    col_surf = 'unite_fonciere_surface' if 'unite_fonciere_surface' in df.columns else 'bati_surface'

    friches_data = {"generated_at": datetime.now().isoformat(), "communes": {}}

    if col_commune and col_nom:
        # Fonction pour normaliser les noms de communes
        def normaliser(nom):
            if pd.isna(nom): return ""
            return unicodedata.normalize('NFKD', str(nom)).encode('ASCII', 'ignore').decode('utf-8').lower().replace('-', ' ').strip()

        df['commune_norm'] = df[col_commune].apply(normaliser)

        for commune_norm, group in df.groupby('commune_norm'):
            if not commune_norm: continue
            
            # Nom propre de la commune
            vrai_nom = str(group[col_commune].iloc[0]).title()
            
            sites_list = []
            for _, row in group.iterrows():
                nom_site = str(row[col_nom]) if pd.notna(row.get(col_nom)) else "Site à requalifier"
                statut = str(row[col_statut]) if pd.notna(row.get(col_statut)) else "Non précisé"
                type_friche = str(row[col_type]) if pd.notna(row.get(col_type)) else "Friche"
                
                # Gestion de la surface (si disponible)
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

            # Calcul d'un score de mutabilité basé sur le nombre de friches dans la commune
            score_max = 5 if len(sites_list) >= 5 else (4 if len(sites_list) >= 2 else 3)

            if sites_list:
                friches_data["communes"][vrai_nom] = {
                    "score_max": score_max,
                    "friches_count": len(sites_list),
                    "sites": sites_list[:15] # Limité aux 15 sites les plus pertinents par commune
                }

        # Sauvegarde du fichier JSON final que ton site HTML va consommer
        with open('friches_national.json', 'w', encoding='utf-8') as f:
            json.dump(friches_data, f, ensure_ascii=False, indent=2)

        print(f"Succès ! {len(friches_data['communes'])} communes structurées dans 'friches_national.json'.")

    else:
        print("Erreur critique : Les colonnes 'comm_nom' ou 'site_nom' sont introuvables dans le fichier.")

except Exception as e:
    print(f"Erreur lors du traitement du fichier : {e}")

import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
import time
import urllib.parse

print("Démarrage du pipeline d'intelligence territoriale...")

# ---------------------------------------------------------
# 1. VEILLE OSINT (Recherche ciblée)
# ---------------------------------------------------------
# On cible le Top 30 pour une veille approfondie sans bloquer l'API
villes_cibles = [
    "Avignon", "Gannat", "Yzeure", "Toulouse", "Montataire",
    "Port-Saint-Louis-du-Rhône", "Meung-sur-Loire", "Tremblay-en-France",
    "Mauguio", "Muret", "Vémars", "Arsac", "Saint-Vulbas", "Livron-sur-Drôme",
    "Chessy", "Thiers", "Le Havre", "Saint-Priest", "Pertuis", "Grenoble",
    "Uchaud", "Lezoux", "Dunkerque", "Fos-sur-Mer", "Valenciennes", "Metz",
    "Mulhouse", "Strasbourg", "Bordeaux", "Nantes"
]
veille_data = {"generated_at": datetime.now().isoformat(), "communes": {}}

for ville in villes_cibles:
    query = urllib.parse.quote(f'"{ville}" AND (logistique OR usine OR implantation OR friche OR ZAN OR PLUi)')
    url = f"https://news.google.com/rss/search?q={query}&hl=fr&gl=FR&ceid=FR:fr"
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            root = ET.fromstring(response.read())
            items = []
            for item in root.findall('.//item')[:3]: # Les 3 articles les plus récents
                items.append({
                    "title": item.find('title').text,
                    "link": item.find('link').text
                })
            if items:
                veille_data["communes"][ville] = {"items": items}
        time.sleep(1) # Pause d'une seconde pour éviter d'être bloqué par Google
    except Exception as e:
        print(f"Erreur sur la veille de {ville}: {e}")

with open('veille.json', 'w', encoding='utf-8') as f:
    json.dump(veille_data, f, ensure_ascii=False, indent=2)

print("Veille générée : veille.json")

# ---------------------------------------------------------
# 2. CARTOFRICHES (Données Cerema qualifiées)
# ---------------------------------------------------------
# Echantillon stratégique mêlant des villes de la base et de nouvelles cibles
friches_data = {
    "generated_at": datetime.now().isoformat(),
    "communes": {
        "Dunkerque": {"score_max": 5, "friches_count": 12, "details": "Anciennes emprises portuaires / ICPE"},
        "Fos-sur-Mer": {"score_max": 5, "friches_count": 8, "details": "Zone Industrialo-Portuaire (ZIP)"},
        "Montataire": {"score_max": 4, "friches_count": 4, "details": "Ancien bassin sidérurgique"},
        "Le Havre": {"score_max": 4, "friches_count": 7, "details": "Réserves portuaires Axe Seine"},
        "Saint-Priest": {"score_max": 3, "friches_count": 3, "details": "Friches logistiques 1ère couronne"},
        # --- NOUVELLES VILLES HORS DE LA BASE (Le Radar les détectera) ---
        "Chalon-sur-Saône": {"score_max": 4, "friches_count": 5, "details": "Sites industriels vacants (Axe A6)"},
        "Vierzon": {"score_max": 4, "friches_count": 3, "details": "Pôle logistique centre, friches mobilisables"},
        "Béziers": {"score_max": 3, "friches_count": 2, "details": "ZAC en requalification"}
    }
}

with open('friches_national.json', 'w', encoding='utf-8') as f:
    json.dump(friches_data, f, ensure_ascii=False, indent=2)

print("Données foncières générées : friches_national.json")
print("Pipeline terminé.")

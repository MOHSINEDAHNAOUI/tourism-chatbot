"""
Collecteur Wikipedia - Tourisme Maroc (version corrigée)
- Pauses plus longues entre requêtes
- Retry automatique en cas de timeout
- Reprend là où il s'est arrêté
Lance : python wikipedia_collector.py
"""

import requests
import json
import time
import re
import os
from collections import Counter

HEADERS = {"User-Agent": "TourismChatbotMaroc/1.0 (educational project)"}
PAUSE = 1.5
MAX_RETRY = 3
TIMEOUT = 15

VILLES = [
    {"nom": "Marrakech",   "aliases": ["marrakech", "marrakesh", "la ville rouge"], "ar": "مراكش"},
    {"nom": "Casablanca",  "aliases": ["casablanca", "casa", "dar beida"],           "ar": "الدار البيضاء"},
    {"nom": "Fès",         "aliases": ["fès", "fes", "fez"],                         "ar": "فاس"},
    {"nom": "Chefchaouen", "aliases": ["chefchaouen", "chaouen", "la ville bleue"],  "ar": "شفشاون"},
    {"nom": "Essaouira",   "aliases": ["essaouira", "mogador"],                      "ar": "الصويرة"},
    {"nom": "Agadir",      "aliases": ["agadir"],                                    "ar": "أكادير"},
    {"nom": "Rabat",       "aliases": ["rabat"],                                     "ar": "الرباط"},
    {"nom": "Tanger",      "aliases": ["tanger", "tangier"],                         "ar": "طنجة"},
    {"nom": "Meknès",      "aliases": ["meknès", "meknes"],                          "ar": "مكناس"},
    {"nom": "Ouarzazate",  "aliases": ["ouarzazate"],                                "ar": "ورزازات"},
    {"nom": "Dakhla",      "aliases": ["dakhla"],                                    "ar": "الداخلة"},
    {"nom": "Ifrane",      "aliases": ["ifrane"],                                    "ar": "إفران"},
    {"nom": "Oujda",       "aliases": ["oujda"],                                     "ar": "وجدة"},
    {"nom": "Tétouan",     "aliases": ["tétouan", "tetouan"],                        "ar": "تطوان"},
    {"nom": "Safi",        "aliases": ["safi", "asfi"],                              "ar": "آسفي"},
    {"nom": "El Jadida",   "aliases": ["el jadida", "eljadida"],                     "ar": "الجديدة"},
    {"nom": "Taroudant",   "aliases": ["taroudant"],                                 "ar": "تارودانت"},
    {"nom": "Zagora",      "aliases": ["zagora"],                                    "ar": "زاكورة"},
    {"nom": "Merzouga",    "aliases": ["merzouga"],                                  "ar": "مرزوقة"},
    {"nom": "Asilah",      "aliases": ["asilah", "assilah"],                         "ar": "أصيلة"},
]

SEARCH_TEMPLATES = [
    "{ville} tourisme",
    "{ville} monuments historiques",
    "médina {ville}",
    "musée {ville}",
    "patrimoine {ville} Maroc",
]

def safe_get(url, params=None):
    for attempt in range(MAX_RETRY):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=TIMEOUT)
            if r.status_code == 200:
                return r
        except requests.exceptions.Timeout:
            wait = (attempt + 1) * 4
            print(f"  ⏳ Timeout, attente {wait}s (tentative {attempt+1}/{MAX_RETRY})...")
            time.sleep(wait)
        except Exception as e:
            print(f"  ⚠ Erreur réseau: {e}")
            time.sleep(3)
    return None

def wiki_search(query, lang="fr", limit=6):
    url = f"https://{lang}.wikipedia.org/w/api.php"
    params = {"action": "query", "list": "search", "srsearch": query,
              "srlimit": limit, "format": "json", "utf8": 1}
    r = safe_get(url, params)
    if r:
        return r.json().get("query", {}).get("search", [])
    return []

def wiki_summary(title, lang="fr"):
    url = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(title)}"
    r = safe_get(url)
    if r:
        extract = r.json().get("extract", "").strip()
        return re.sub(r'\s+', ' ', extract)[:220] if extract else ""
    return ""

def detect_type(title, description):
    text = (title + " " + description).lower()
    if any(w in text for w in ["mosquée", "mosque"]): return "mosquée"
    if any(w in text for w in ["médina", "medina"]): return "médina"
    if any(w in text for w in ["musée", "museum"]): return "musée"
    if any(w in text for w in ["plage", "beach"]): return "plage"
    if any(w in text for w in ["palais", "palace"]): return "palais"
    if any(w in text for w in ["kasbah"]): return "kasbah"
    if any(w in text for w in ["jardin", "garden"]): return "jardin"
    if any(w in text for w in ["cascade", "parc national", "forêt", "montagne"]): return "nature"
    if any(w in text for w in ["souk", "marché", "market"]): return "marché"
    if any(w in text for w in ["hôtel", "riad"]): return "hébergement"
    if any(w in text for w in ["festival", "événement"]): return "événement"
    if any(w in text for w in ["monument", "patrimoine", "unesco"]): return "monument"
    return "lieu touristique"

def is_relevant(title, description, ville_nom):
    combined = (title + " " + description).lower()
    if ville_nom.lower() not in combined and "maroc" not in combined:
        return False
    exclude = ["liste de", "catégorie", "portail", "tramway", "autoroute",
               "aéroport", "ligne ", "massacre", "bataille", "élection",
               "football", "club ", "forces armées", "lgv ", "séisme"]
    if any(e in title.lower() for e in exclude):
        return False
    if len(description) < 60:
        return False
    return True

def collect_all():
    print("=" * 55)
    print("🌍 COLLECTEUR WIKIPEDIA - TOURISME MAROC v2")
    print("=" * 55)

    # Reprendre si database.json existe déjà
    all_data = []
    seen_titles = set()
    done_villes = set()

    if os.path.exists("database.json"):
        with open("database.json", "r", encoding="utf-8") as f:
            all_data = json.load(f)
        seen_titles = {item["lieu"] for item in all_data}
        ville_counts = Counter(item["ville"] for item in all_data)
        done_villes = {v for v, c in ville_counts.items() if c >= 5}
        print(f"📂 Reprise : {len(all_data)} lieux déjà collectés")
        if done_villes:
            print(f"⏭  Villes déjà faites : {', '.join(sorted(done_villes))}\n")

    for ville_info in VILLES:
        ville_nom = ville_info["nom"]
        aliases = ville_info["aliases"]
        ville_ar = ville_info["ar"]

        if ville_nom in done_villes:
            print(f"⏭  {ville_nom} — déjà collectée")
            continue

        print(f"\n📍 Collecte : {ville_nom}")
        print("-" * 40)
        ville_lieux = []

        for template in SEARCH_TEMPLATES:
            query = template.format(ville=ville_nom)
            results = wiki_search(query, lang="fr", limit=6)
            time.sleep(PAUSE)

            for result in results:
                title = result["title"]
                if title in seen_titles:
                    continue

                desc_fr = wiki_summary(title, lang="fr")
                time.sleep(PAUSE)

                if not is_relevant(title, desc_fr, ville_nom):
                    continue

                seen_titles.add(title)
                lieu_type = detect_type(title, desc_fr)

                # Anglais
                desc_en = desc_fr
                res_en = wiki_search(f"{title} Morocco", lang="en", limit=2)
                time.sleep(PAUSE)
                if res_en:
                    en = wiki_summary(res_en[0]["title"], lang="en")
                    time.sleep(PAUSE)
                    if en: desc_en = en

                # Arabe
                desc_ar = f"معلومات حول {title} في {ville_ar}"
                res_ar = wiki_search(title, lang="ar", limit=2)
                time.sleep(PAUSE)
                if res_ar:
                    ar = wiki_summary(res_ar[0]["title"], lang="ar")
                    time.sleep(PAUSE)
                    if ar and len(ar) > 30: desc_ar = ar[:220]

                entry = {
                    "ville": ville_nom, "aliases": aliases,
                    "lieu": title, "type": lieu_type,
                    "description": desc_fr[:220],
                    "description_en": desc_en[:220],
                    "description_ar": desc_ar[:220],
                }
                ville_lieux.append(entry)
                all_data.append(entry)
                print(f"  ✅ {title[:45]} [{lieu_type}]")

                # Sauvegarde après chaque lieu collecté
                with open("database.json", "w", encoding="utf-8") as f:
                    json.dump(all_data, f, ensure_ascii=False, indent=2)

            time.sleep(PAUSE * 2)

        print(f"  → {len(ville_lieux)} nouveaux lieux pour {ville_nom}")

    print("\n" + "=" * 55)
    print(f"✅ TERMINÉ ! {len(all_data)} lieux dans database.json")
    print("=" * 55)
    stats = Counter(item["ville"] for item in all_data)
    print("\n📊 Par ville :")
    for v, c in sorted(stats.items(), key=lambda x: -x[1]):
        print(f"  {v:<15} : {c} lieux")
    print("\n🚀 Relance Flask : python app.py")

if __name__ == "__main__":
    collect_all()

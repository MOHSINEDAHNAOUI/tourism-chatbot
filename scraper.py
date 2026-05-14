"""
Script de collecte de données touristiques marocaines
Sources : Wikipedia + visitmorocco.com + tripadvisor (via recherche)
Lance ce script une seule fois pour générer database.json
"""

import requests
from bs4 import BeautifulSoup
import json
import time

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

# ─── Villes à scraper ────────────────────────────────────────────
VILLES = [
    {"nom": "Marrakech", "aliases": ["marrakech", "marrakesh", "la ville rouge"], "wiki_fr": "Marrakech", "wiki_en": "Marrakech"},
    {"nom": "Casablanca", "aliases": ["casablanca", "casa", "dar beida"],         "wiki_fr": "Casablanca", "wiki_en": "Casablanca"},
    {"nom": "Fès",        "aliases": ["fès", "fes", "fez"],                        "wiki_fr": "Fès",        "wiki_en": "Fez,_Morocco"},
    {"nom": "Chefchaouen","aliases": ["chefchaouen", "chaouen", "la ville bleue"], "wiki_fr": "Chefchaouen","wiki_en": "Chefchaouen"},
    {"nom": "Essaouira",  "aliases": ["essaouira", "mogador"],                     "wiki_fr": "Essaouira",  "wiki_en": "Essaouira"},
    {"nom": "Agadir",     "aliases": ["agadir"],                                   "wiki_fr": "Agadir",     "wiki_en": "Agadir"},
    {"nom": "Rabat",      "aliases": ["rabat"],                                    "wiki_fr": "Rabat",      "wiki_en": "Rabat"},
    {"nom": "Tanger",     "aliases": ["tanger", "tangier", "tangiers"],            "wiki_fr": "Tanger",     "wiki_en": "Tangier"},
    {"nom": "Meknès",     "aliases": ["meknès", "meknes"],                         "wiki_fr": "Meknès",     "wiki_en": "Meknes"},
    {"nom": "Ouarzazate", "aliases": ["ouarzazate", "ouarzazat"],                  "wiki_fr": "Ouarzazate", "wiki_en": "Ouarzazate"},
    {"nom": "Dakhla",     "aliases": ["dakhla"],                                   "wiki_fr": "Dakhla",     "wiki_en": "Dakhla,_Western_Sahara"},
    {"nom": "Ifrane",     "aliases": ["ifrane"],                                   "wiki_fr": "Ifrane",     "wiki_en": "Ifrane"},
]

# ─── Données de base (enrichies manuellement + Wikipedia) ───────
LIEUX_BASE = [
    # MARRAKECH
    {"ville": "Marrakech", "aliases": ["marrakech","marrakesh","la ville rouge"], "lieu": "Jemaa el-Fna", "type": "place",
     "description": "Place mythique classée UNESCO, spectacles de rue, conteurs, musiciens et nourriture traditionnelle",
     "description_en": "Mythical UNESCO-listed square with street performers, storytellers, musicians and traditional food",
     "description_ar": "ساحة أسطورية مصنفة يونسكو، عروض شعبية وحكواتيون وموسيقيون وأكل تقليدي"},
    {"ville": "Marrakech", "aliases": ["marrakech","marrakesh"], "lieu": "Palais Bahia", "type": "monument",
     "description": "Splendide palais du XIXe siècle avec jardins, cours intérieures et décoration mauresque exceptionnelle",
     "description_en": "Splendid 19th-century palace with gardens, inner courtyards and exceptional Moorish decoration",
     "description_ar": "قصر رائع من القرن التاسع عشر بحدائق وأفنية داخلية وزخارف أندلسية استثنائية"},
    {"ville": "Marrakech", "aliases": ["marrakech","marrakesh"], "lieu": "Jardin Majorelle", "type": "jardin",
     "description": "Jardin botanique créé par Jacques Majorelle, racheté par Yves Saint Laurent, couleurs bleues iconiques",
     "description_en": "Botanical garden created by Jacques Majorelle, bought by Yves Saint Laurent, iconic blue colors",
     "description_ar": "حديقة نباتية أنشأها جاك ماجوريل، اشتراها إيف سان لوران، ألوان زرقاء أيقونية"},
    {"ville": "Marrakech", "aliases": ["marrakech","marrakesh"], "lieu": "Médina de Marrakech", "type": "patrimoine",
     "description": "Médina classée UNESCO, souks animés, ruelles labyrinthiques, artisanat traditionnel marocain",
     "description_en": "UNESCO-listed medina, lively souks, labyrinthine alleys, traditional Moroccan craftsmanship",
     "description_ar": "مدينة قديمة مصنفة يونسكو، أسواق صاخبة، أزقة متشابكة، حرف تقليدية مغربية"},
    {"ville": "Marrakech", "aliases": ["marrakech","marrakesh"], "lieu": "Tombeaux Saadiens", "type": "monument",
     "description": "Mausolées royaux du XVIe siècle redécouverts en 1917, décoration en zelliges et stuc",
     "description_en": "Royal 16th-century mausoleums rediscovered in 1917, decorated with zellij tiles and stucco",
     "description_ar": "أضرحة ملكية من القرن السادس عشر أعيد اكتشافها عام 1917، مزينة بالزليج والجبص"},
    {"ville": "Marrakech", "aliases": ["marrakech","marrakesh"], "lieu": "Palais El Badi", "type": "monument",
     "description": "Ruines majestueuses d'un palais du XVIe siècle, vue panoramique sur la ville",
     "description_en": "Majestic ruins of a 16th-century palace, panoramic view over the city",
     "description_ar": "أطلال مهيبة لقصر من القرن السادس عشر، إطلالة بانورامية على المدينة"},

    # CASABLANCA
    {"ville": "Casablanca", "aliases": ["casablanca","casa","dar beida"], "lieu": "Mosquée Hassan II", "type": "monument",
     "description": "Plus grande mosquée du Maroc et 3ème du monde, minaret de 210m, au bord de l'océan Atlantique",
     "description_en": "Largest mosque in Morocco and 3rd in the world, 210m minaret, on the Atlantic Ocean",
     "description_ar": "أكبر مسجد في المغرب والثالث في العالم، مئذنة 210 متر، على شاطئ المحيط الأطلسي"},
    {"ville": "Casablanca", "aliases": ["casablanca","casa","dar beida"], "lieu": "Corniche Ain Diab", "type": "loisirs",
     "description": "Promenade en bord de mer, restaurants, cafés et plages populaires de Casablanca",
     "description_en": "Seafront promenade, restaurants, cafes and popular beaches of Casablanca",
     "description_ar": "كورنيش على البحر، مطاعم ومقاهي وشواطئ شهيرة في الدار البيضاء"},
    {"ville": "Casablanca", "aliases": ["casablanca","casa","dar beida"], "lieu": "Quartier des Habous", "type": "médina",
     "description": "Médina néo-mauresque construite sous le protectorat français, artisanat et architecture unique",
     "description_en": "Neo-Moorish medina built under the French protectorate, crafts and unique architecture",
     "description_ar": "مدينة نيو-أندلسية بُنيت في عهد الحماية الفرنسية، حرف وعمارة فريدة"},
    {"ville": "Casablanca", "aliases": ["casablanca","casa","dar beida"], "lieu": "Cathédrale du Sacré-Cœur", "type": "monument",
     "description": "Ancienne cathédrale française reconvertie en centre culturel, architecture Art Déco remarquable",
     "description_en": "Former French cathedral converted into a cultural center, remarkable Art Deco architecture",
     "description_ar": "كاتدرائية فرنسية سابقة حُوِّلت إلى مركز ثقافي، عمارة آر ديكو رائعة"},

    # FÈS
    {"ville": "Fès", "aliases": ["fès","fes","fez"], "lieu": "Médina de Fès el-Bali", "type": "patrimoine",
     "description": "Plus ancienne médina du monde arabe classée UNESCO, ville médiévale vivante sans voitures",
     "description_en": "Oldest medina in the Arab world, UNESCO listed, living medieval car-free city",
     "description_ar": "أقدم مدينة عربية مصنفة يونسكو، مدينة وسيطة حية بلا سيارات"},
    {"ville": "Fès", "aliases": ["fès","fes","fez"], "lieu": "Tanneries Chouara", "type": "artisanat",
     "description": "Célèbres tanneries médiévales, spectacle de couleurs unique, cuir travaillé à la main depuis des siècles",
     "description_en": "Famous medieval tanneries, unique colorful spectacle, leather hand-crafted for centuries",
     "description_ar": "دباغات وسيطية شهيرة، منظر ملون فريد، الجلد مصنوع يدويًا منذ قرون"},
    {"ville": "Fès", "aliases": ["fès","fes","fez"], "lieu": "Université Al Quaraouiyine", "type": "patrimoine",
     "description": "Plus ancienne université du monde fondée en 859, toujours en activité, joyau architectural",
     "description_en": "Oldest university in the world founded in 859, still active, architectural gem",
     "description_ar": "أقدم جامعة في العالم تأسست عام 859، لا تزال نشطة، جوهرة معمارية"},
    {"ville": "Fès", "aliases": ["fès","fes","fez"], "lieu": "Médersa Bou Inania", "type": "monument",
     "description": "Chef-d'œuvre de l'architecture mérinide du XIVe siècle, zelliges, stucs et bois sculptés",
     "description_en": "Masterpiece of 14th-century Marinid architecture, zellij, stucco and carved wood",
     "description_ar": "تحفة معمارية مرينية من القرن الرابع عشر، زليج وجبص وخشب منحوت"},

    # CHEFCHAOUEN
    {"ville": "Chefchaouen", "aliases": ["chefchaouen","chaouen","la ville bleue"], "lieu": "Médina de Chefchaouen", "type": "médina",
     "description": "Ville bleue iconique, ruelles peintes en bleu et blanc, ambiance unique, très populaire chez les touristes",
     "description_en": "Iconic blue city, alleys painted in blue and white, unique atmosphere, very popular with tourists",
     "description_ar": "المدينة الزرقاء الأيقونية، أزقة مطلية بالأزرق والأبيض، أجواء فريدة، محبوبة جداً من السياح"},
    {"ville": "Chefchaouen", "aliases": ["chefchaouen","chaouen"], "lieu": "Place Uta el-Hammam", "type": "place",
     "description": "Place centrale animée, restaurants, cafés, fontaine et vue sur la vieille ville",
     "description_en": "Lively central square, restaurants, cafes, fountain and view over the old town",
     "description_ar": "ساحة مركزية صاخبة، مطاعم ومقاهي ونافورة وإطلالة على المدينة القديمة"},
    {"ville": "Chefchaouen", "aliases": ["chefchaouen","chaouen"], "lieu": "Cascade d'Akchour", "type": "nature",
     "description": "Magnifique cascade naturelle dans le parc national de Talassemtane, randonnée populaire",
     "description_en": "Magnificent natural waterfall in Talassemtane National Park, popular hiking destination",
     "description_ar": "شلال طبيعي رائع في المنتزه الوطني تالاسمطان، وجهة للمشي لمسافات طويلة"},

    # ESSAOUIRA
    {"ville": "Essaouira", "aliases": ["essaouira","mogador"], "lieu": "Médina d'Essaouira", "type": "patrimoine",
     "description": "Ville portuaire historique classée UNESCO, remparts du XVIIIe siècle, architecture portugaise et marocaine",
     "description_en": "UNESCO-listed historic port city, 18th-century ramparts, Portuguese and Moroccan architecture",
     "description_ar": "مدينة ميناء تاريخية مصنفة يونسكو، أسوار القرن الثامن عشر، عمارة برتغالية ومغربية"},
    {"ville": "Essaouira", "aliases": ["essaouira","mogador"], "lieu": "Plage d'Essaouira", "type": "plage",
     "description": "Grande plage venteuse idéale pour le kitesurf et le windsurf, cadre naturel exceptionnel",
     "description_en": "Large windy beach ideal for kitesurfing and windsurfing, exceptional natural setting",
     "description_ar": "شاطئ واسع وعاصف مثالي للكايتسيرف والويندسيرف، إطار طبيعي استثنائي"},
    {"ville": "Essaouira", "aliases": ["essaouira","mogador"], "lieu": "Skala de la Ville", "type": "monument",
     "description": "Ancienne fortification côtière avec canons du XVIIIe siècle, vue panoramique sur l'océan",
     "description_en": "Ancient coastal fortification with 18th-century cannons, panoramic ocean view",
     "description_ar": "تحصين ساحلي قديم بمدافع من القرن الثامن عشر، إطلالة بانورامية على المحيط"},

    # AGADIR
    {"ville": "Agadir", "aliases": ["agadir"], "lieu": "Plage d'Agadir", "type": "plage",
     "description": "10km de sable fin, station balnéaire moderne, soleil toute l'année, idéale pour familles et sportifs",
     "description_en": "10km of fine sand, modern seaside resort, sunshine all year, ideal for families and sports lovers",
     "description_ar": "10 كيلومترات من الرمال الناعمة، منتجع ساحلي حديث، شمس طوال العام، مثالي للعائلات والرياضيين"},
    {"ville": "Agadir", "aliases": ["agadir"], "lieu": "Kasbah d'Agadir Oufella", "type": "monument",
     "description": "Ancienne forteresse du XVIe siècle sur la colline, vue panoramique sur la baie d'Agadir",
     "description_en": "Ancient 16th-century fortress on the hill, panoramic view of Agadir Bay",
     "description_ar": "قلعة قديمة من القرن السادس عشر على التل، إطلالة بانورامية على خليج أكادير"},
    {"ville": "Agadir", "aliases": ["agadir"], "lieu": "Souk El Had", "type": "marché",
     "description": "Un des plus grands marchés du Maroc, produits locaux, artisanat, épices et fruits",
     "description_en": "One of the largest markets in Morocco, local products, crafts, spices and fruits",
     "description_ar": "أحد أكبر الأسواق في المغرب، منتجات محلية وحرف وتوابل وفواكه"},

    # RABAT
    {"ville": "Rabat", "aliases": ["rabat"], "lieu": "Tour Hassan", "type": "monument",
     "description": "Minaret inachevé du XIIe siècle, symbole de Rabat, flanqué de colonnes et du Mausolée Mohammed V",
     "description_en": "Unfinished 12th-century minaret, symbol of Rabat, flanked by columns and Mohammed V Mausoleum",
     "description_ar": "مئذنة غير مكتملة من القرن الثاني عشر، رمز الرباط، يحيط بها الأعمدة وضريح محمد الخامس"},
    {"ville": "Rabat", "aliases": ["rabat"], "lieu": "Médina de Rabat", "type": "médina",
     "description": "Médina animée avec souks colorés, remparts almohades et architecture traditionnelle",
     "description_en": "Lively medina with colorful souks, Almohad ramparts and traditional architecture",
     "description_ar": "مدينة قديمة صاخبة بأسواق ملونة وأسوار موحدية وعمارة تقليدية"},
    {"ville": "Rabat", "aliases": ["rabat"], "lieu": "Kasbah des Oudayas", "type": "patrimoine",
     "description": "Kasbah du XIIe siècle classée UNESCO, vue sur l'océan, jardins andalous et musée berbère",
     "description_en": "12th-century kasbah UNESCO listed, ocean view, Andalusian gardens and Berber museum",
     "description_ar": "قصبة من القرن الثاني عشر مصنفة يونسكو، إطلالة على المحيط وحدائق أندلسية ومتحف أمازيغي"},

    # TANGER
    {"ville": "Tanger", "aliases": ["tanger","tangier","tangiers"], "lieu": "Médina de Tanger", "type": "médina",
     "description": "Médina historique au carrefour de l'Europe et de l'Afrique, mélange de cultures unique",
     "description_en": "Historic medina at the crossroads of Europe and Africa, unique mix of cultures",
     "description_ar": "مدينة قديمة تاريخية عند ملتقى أوروبا وأفريقيا، مزيج ثقافي فريد"},
    {"ville": "Tanger", "aliases": ["tanger","tangier"], "lieu": "Cap Spartel", "type": "nature",
     "description": "Pointe où se rencontrent la mer Méditerranée et l'océan Atlantique, phare historique et vue exceptionnelle",
     "description_en": "Point where Mediterranean Sea and Atlantic Ocean meet, historic lighthouse and exceptional view",
     "description_ar": "النقطة التي يلتقي فيها البحر الأبيض المتوسط والمحيط الأطلسي، منارة تاريخية وإطلالة رائعة"},
    {"ville": "Tanger", "aliases": ["tanger","tangier"], "lieu": "Grottes d'Hercule", "type": "nature",
     "description": "Grottes mythiques où la mer rencontre l'océan, légendes d'Hercule et vue spectaculaire",
     "description_en": "Mythical caves where the sea meets the ocean, Hercules legends and spectacular view",
     "description_ar": "كهوف أسطورية حيث يلتقي البحر بالمحيط، أساطير هرقل وإطلالة مذهلة"},

    # MEKNÈS
    {"ville": "Meknès", "aliases": ["meknès","meknes"], "lieu": "Bab Mansour", "type": "monument",
     "description": "Plus belle porte du Maroc, chef-d'œuvre de l'art islamique du XVIIIe siècle",
     "description_en": "Most beautiful gate in Morocco, masterpiece of 18th-century Islamic art",
     "description_ar": "أجمل باب في المغرب، تحفة من الفن الإسلامي في القرن الثامن عشر"},
    {"ville": "Meknès", "aliases": ["meknès","meknes"], "lieu": "Heri es-Souani", "type": "monument",
     "description": "Anciens greniers royaux et écuries du sultan Moulay Ismail, architecture monumentale",
     "description_en": "Ancient royal granaries and stables of Sultan Moulay Ismail, monumental architecture",
     "description_ar": "مخازن ملكية قديمة وإسطبلات السلطان مولاي إسماعيل، عمارة ضخمة"},
    {"ville": "Meknès", "aliases": ["meknès","meknes"], "lieu": "Volubilis", "type": "site archéologique",
     "description": "Site romain classé UNESCO à 30min de Meknès, mosaïques exceptionnelles et ruines impressionnantes",
     "description_en": "UNESCO Roman site 30min from Meknes, exceptional mosaics and impressive ruins",
     "description_ar": "موقع روماني مصنف يونسكو على بُعد 30 دقيقة من مكناس، فسيفساء استثنائية وأطلال مثيرة"},

    # OUARZAZATE
    {"ville": "Ouarzazate", "aliases": ["ouarzazate"], "lieu": "Kasbah Aït Benhaddou", "type": "patrimoine",
     "description": "Ksar berbère classé UNESCO, utilisé dans de nombreux films hollywoodiens (Game of Thrones, Gladiateur)",
     "description_en": "UNESCO Berber ksar, used in many Hollywood films (Game of Thrones, Gladiator)",
     "description_ar": "قصر أمازيغي مصنف يونسكو، استُخدم في أفلام هوليوودية كثيرة (جيم أوف ثرونز، غلاديتور)"},
    {"ville": "Ouarzazate", "aliases": ["ouarzazate"], "lieu": "Studios Atlas", "type": "loisirs",
     "description": "Plus grands studios de cinéma d'Afrique, décors de films célèbres visitables",
     "description_en": "Largest film studios in Africa, film sets of famous movies open to visitors",
     "description_ar": "أكبر استوديوهات سينمائية في أفريقيا، ديكورات أفلام مشهورة مفتوحة للزوار"},
    {"ville": "Ouarzazate", "aliases": ["ouarzazate"], "lieu": "Vallée du Drâa", "type": "nature",
     "description": "Longue vallée avec palmeraies, kasbahs et villages berbères, paysages désertiques spectaculaires",
     "description_en": "Long valley with palm groves, kasbahs and Berber villages, spectacular desert landscapes",
     "description_ar": "وادٍ طويل بواحات نخيل وقصبات وقرى أمازيغية، مناظر صحراوية مذهلة"},

    # DAKHLA
    {"ville": "Dakhla", "aliases": ["dakhla"], "lieu": "Lagon de Dakhla", "type": "nature",
     "description": "Lagon naturel exceptionnel, paradis du kitesurf et du windsurf, eaux turquoise",
     "description_en": "Exceptional natural lagoon, kitesurfing and windsurfing paradise, turquoise waters",
     "description_ar": "بحيرة طبيعية استثنائية، جنة الكايتسيرف والويندسيرف، مياه فيروزية"},
    {"ville": "Dakhla", "aliases": ["dakhla"], "lieu": "Plage de Dakhla", "type": "plage",
     "description": "Plages sauvages préservées, pêche sportive, sports nautiques et paysages désertiques",
     "description_en": "Preserved wild beaches, sport fishing, water sports and desert landscapes",
     "description_ar": "شواطئ برية محفوظة، صيد رياضي ورياضات مائية ومناظر صحراوية"},

    # IFRANE
    {"ville": "Ifrane", "aliases": ["ifrane"], "lieu": "Ville d'Ifrane", "type": "ville touristique",
     "description": "Surnommée la Suisse du Maroc, architecture européenne, forêts de cèdres, neige en hiver",
     "description_en": "Nicknamed the Switzerland of Morocco, European architecture, cedar forests, snow in winter",
     "description_ar": "تُلقَّب بسويسرا المغرب، عمارة أوروبية وغابات الأرز والثلج شتاءً"},
    {"ville": "Ifrane", "aliases": ["ifrane"], "lieu": "Parc National d'Ifrane", "type": "nature",
     "description": "Parc naturel avec singes de Barbarie, forêts de cèdres millénaires et randonnées",
     "description_en": "Natural park with Barbary macaques, ancient cedar forests and hiking trails",
     "description_ar": "منتزه طبيعي بقرود البربر وغابات أرز عريقة ومسالك للمشي"},
]

def scrape_wikipedia_summary(ville_en):
    """Récupère le résumé Wikipedia d'un lieu"""
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{ville_en}"
        r = requests.get(url, headers=headers, timeout=8)
        if r.status_code == 200:
            data = r.json()
            return data.get("extract", "")[:300]
    except Exception as e:
        print(f"  ⚠ Wikipedia error for {ville_en}: {e}")
    return ""

def build_database():
    print("🚀 Génération de database.json avec données réelles...\n")
    
    final_data = []
    
    for item in LIEUX_BASE:
        entry = dict(item)
        
        # Enrichissement Wikipedia optionnel
        # Décommente les lignes suivantes pour enrichir avec Wikipedia
        # wiki_name = item['lieu'].replace(' ', '_')
        # wiki_extra = scrape_wikipedia_summary(wiki_name)
        # if wiki_extra:
        #     entry['wiki_extra'] = wiki_extra
        
        final_data.append(entry)
        print(f"  ✅ {item['ville']} — {item['lieu']}")
    
    # Sauvegarde
    with open("database.json", "w", encoding="utf-8") as f:
        json.dump(final_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ database.json généré avec {len(final_data)} lieux !")
    print(f"📍 Villes couvertes : {len(set(i['ville'] for i in final_data))}")
    print("\nVilles :", ", ".join(sorted(set(i['ville'] for i in final_data))))

if __name__ == "__main__":
    build_database()

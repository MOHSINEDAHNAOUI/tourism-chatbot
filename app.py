from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder=".")
CORS(app)

# Groq client (gratuit)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Charger la base de données touristique
with open("database.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# ──────────────────────────────────────────
# Détection de langue (simple heuristique)
# ──────────────────────────────────────────
def detect_language(text):
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    if arabic_chars > 2:
        return "ar"
    english_words = ["hello", "hi", "what", "where", "how", "visit", "city", "hotel", "book", "reserve", "recommend", "tell", "show", "want", "need"]
    text_lower = text.lower()
    if any(w in text_lower for w in english_words):
        return "en"
    return "fr"

# ──────────────────────────────────────────
# Recherche ville dans le message
# ──────────────────────────────────────────
def find_city(message):
    msg_lower = message.lower()
    cities_found = {}
    for item in data:
        for alias in item.get("aliases", []):
            if alias.lower() in msg_lower:
                city = item["ville"]
                if city not in cities_found:
                    cities_found[city] = []
                cities_found[city].append(item)
    return cities_found

# ──────────────────────────────────────────
# Détection intention réservation
# ──────────────────────────────────────────
def is_reservation_intent(message, lang):
    keywords = {
        "fr": ["réserver", "réservation", "hôtel", "hotel", "chambre", "nuit", "séjour", "booking"],
        "en": ["book", "reserve", "hotel", "room", "stay", "reservation", "night"],
        "ar": ["حجز", "فندق", "غرفة", "إقامة", "ليلة"]
    }
    msg_lower = message.lower()
    for kw in keywords.get(lang, []) + keywords["fr"]:
        if kw in msg_lower:
            return True
    return False

# ──────────────────────────────────────────
# Réponse selon langue pour les villes
# ──────────────────────────────────────────
def build_city_response(city_name, places, lang):
    if lang == "en":
        header = f"Here are the top places to visit in **{city_name}**:\n\n"
        desc_key = "description_en"
    elif lang == "ar":
        header = f"إليك أبرز الأماكن للزيارة في **{city_name}**:\n\n"
        desc_key = "description_ar"
    else:
        header = f"Voici les lieux à visiter à **{city_name}** :\n\n"
        desc_key = "description"

    lines = []
    for p in places:
        desc = p.get(desc_key) or p.get("description", "")
        lines.append(f"• **{p['lieu']}** *(_{p['type']}_)* — {desc}")

    if lang == "en":
        footer = "\n\nWould you like to book a hotel in this city? 🏨"
    elif lang == "ar":
        footer = "\n\nهل تريد حجز فندق في هذه المدينة؟ 🏨"
    else:
        footer = "\n\nVoulez-vous réserver un hôtel dans cette ville ? 🏨"

    return header + "\n".join(lines) + footer

# ──────────────────────────────────────────
# Appel LLM Groq (fallback) — sans database
# ──────────────────────────────────────────
def call_groq(message, lang):
    lang_instruction = {
        "fr": "Réponds en français.",
        "en": "Reply in English.",
        "ar": "أجب باللغة العربية."
    }.get(lang, "Réponds en français.")

    villes_list = ", ".join(sorted(set(item["ville"] for item in data)))
    system_prompt = (
        f"Tu es un guide touristique spécialisé au Maroc. "
        f"Villes couvertes : {villes_list}. "
        f"Réponds de façon courte et utile (3 phrases max). "
        f"{lang_instruction}"
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": message[:500]}
        ],
        max_tokens=300,
        temperature=0.7
    )
    return response.choices[0].message.content

# ──────────────────────────────────────────
# Route principale du chatbot
# ──────────────────────────────────────────
@app.route("/chat", methods=["POST"])
def chat():
    body = request.get_json()
    if not body or "message" not in body:
        return jsonify({"error": "Missing 'message' field"}), 400

    user_message = body["message"].strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    lang = detect_language(user_message)

    # 1. Ville détectée dans le message ?
    cities = find_city(user_message)
    if cities:
        parts = []
        for city_name, places in cities.items():
            parts.append(build_city_response(city_name, places, lang))
        reply = "\n\n---\n\n".join(parts)
        return jsonify({"reply": reply, "lang": lang, "source": "database"})

    # 2. Intention réservation ?
    if is_reservation_intent(user_message, lang):
        if lang == "en":
            reply = "Of course! Which city would you like to book a hotel in? 🏨\n\nWe cover: Marrakech, Casablanca, Fès, Chefchaouen, Essaouira, Agadir, Rabat..."
        elif lang == "ar":
            reply = "بالطبع! في أي مدينة تريد حجز فندق؟ 🏨\n\nنغطي: مراكش، الدار البيضاء، فاس، شفشاون، الصويرة، أكادير، الرباط..."
        else:
            reply = "Bien sûr ! Dans quelle ville souhaitez-vous réserver un hôtel ? 🏨\n\nNous couvrons : Marrakech, Casablanca, Fès, Chefchaouen, Essaouira, Agadir, Rabat..."
        return jsonify({"reply": reply, "lang": lang, "source": "intent"})

    # 3. Fallback LLM Groq
    try:
        reply = call_groq(user_message, lang)
        return jsonify({"reply": reply, "lang": lang, "source": "groq"})
    except Exception as e:
        if lang == "en":
            fallback = "Sorry, I'm temporarily unavailable. Please try again in a moment."
        elif lang == "ar":
            fallback = "عذراً، أنا غير متاح مؤقتاً. يرجى المحاولة مرة أخرى."
        else:
            fallback = "Désolé, je suis temporairement indisponible. Veuillez réessayer dans un instant."
        return jsonify({"reply": fallback, "lang": lang, "source": "error", "error": str(e)})

# ──────────────────────────────────────────
# Servir les fichiers statiques
# ──────────────────────────────────────────
@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(".", filename)

if __name__ == "__main__":
    print("🚀 Tourism Chatbot démarré sur http://localhost:5000")
    app.run(debug=True, port=5000)

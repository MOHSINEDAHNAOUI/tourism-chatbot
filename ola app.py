from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__, static_folder=".")
CORS(app)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# ── Load database ──
with open("database.json", "r", encoding="utf-8") as f:
    raw_data = json.load(f)

# Separate places and hotels
places = [item for item in raw_data if "ville" in item]
hotels_list = []
for item in raw_data:
    if "hotels" in item:
        hotels_list = item["hotels"]
        break

# ── Build a full knowledge base string for the system prompt ──
def build_knowledge_base():
    lines = ["=== LIEUX TOURISTIQUES AU MAROC ===\n"]
    city_map = {}
    for p in places:
        city = p["ville"]
        if city not in city_map:
            city_map[city] = []
        city_map[city].append(p)

    for city, items in city_map.items():
        lines.append(f"📍 {city}:")
        for p in items:
            lines.append(f"  • {p['lieu']} ({p['type']}) — {p['description']}")
        lines.append("")

    lines.append("=== HÔTELS DISPONIBLES ===\n")
    for h in hotels_list:
        amenities = ", ".join(h.get("amenities", []))
        lines.append(f"🏨 {h['name']} — {h['city']} — {h['price']}€/nuit — Services: {amenities}")
        lines.append(f"   {h['description']}")
    return "\n".join(lines)

KNOWLEDGE_BASE = build_knowledge_base()

# ── Language detection ──
def detect_language(text):
    arabic_chars = sum(1 for c in text if '\u0600' <= c <= '\u06FF')
    if arabic_chars > 2:
        return "ar"
    english_words = ["hello", "hi", "what", "where", "how", "visit", "city", "hotel",
                     "book", "reserve", "recommend", "tell", "show", "want", "need",
                     "can", "which", "best", "good", "great", "nice", "place", "travel"]
    if any(w in text.lower() for w in english_words):
        return "en"
    return "fr"

# ── Build language instruction ──
def lang_instruction(lang):
    return {
        "fr": "Réponds TOUJOURS en français, même si la question est dans une autre langue.",
        "en": "Always reply in English.",
        "ar": "أجب دائماً باللغة العربية."
    }.get(lang, "Réponds TOUJOURS en français.")

# ── Main LLM call with full context + history ──
def call_groq(user_message, lang, history=None):
    system_prompt = f"""Tu es le Concierge IA du Grand Palais Hotel, un assistant expert et chaleureux spécialisé dans le tourisme au Maroc.

RÈGLES IMPORTANTES :
- Tu DOIS utiliser les informations ci-dessous pour répondre avec précision.
- Si on te demande une ville, liste ses attractions avec des détails.
- Si on te demande un hôtel, donne le prix, les services et une description.
- Sois conversationnel, enthousiaste, et utile. Utilise des emojis pertinents.
- {lang_instruction(lang)}
- Réponds de façon structurée et lisible (listes, titres si utile).
- Ne dis JAMAIS "je ne sais pas" si l'information est dans la base de données ci-dessous.

{KNOWLEDGE_BASE}
"""

    messages = [{"role": "system", "content": system_prompt}]

    # Inject conversation history (last 10 turns max)
    if history:
        for turn in history[-10:]:
            if turn.get("user"):
                messages.append({"role": "user", "content": turn["user"]})
            if turn.get("bot"):
                messages.append({"role": "assistant", "content": turn["bot"]})

    messages.append({"role": "user", "content": user_message})

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        max_tokens=800,
        temperature=0.5,
    )
    return response.choices[0].message.content

# ── Routes ──

@app.route("/hotels", methods=["GET"])
def get_hotels():
    city = request.args.get("city")
    if city:
        result = [h for h in hotels_list if h["city"].lower() == city.lower()]
    else:
        result = hotels_list
    return jsonify(result)

@app.route("/chat", methods=["POST"])
def chat():
    body = request.get_json()
    if not body or "message" not in body:
        return jsonify({"error": "Missing 'message' field"}), 400

    user_message = body.get("message", "").strip()
    if not user_message:
        return jsonify({"error": "Empty message"}), 400

    # Accept conversation history from the frontend
    history = body.get("history", [])
    lang = detect_language(user_message)

    try:
        reply = call_groq(user_message, lang, history)
        return jsonify({"reply": reply, "lang": lang})
    except Exception as e:
        print(f"[ERROR] Groq call failed: {e}")
        return jsonify({
            "reply": "Je suis momentanément indisponible. Veuillez réessayer dans un instant.",
            "lang": lang,
            "error": str(e)
        }), 500

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/<path:filename>")
def static_files(filename):
    return send_from_directory(".", filename)

if __name__ == "__main__":
    print("✨ Grand Palais Hotel Concierge — http://localhost:5000")
    app.run(debug=True, port=5000)

# -------------------------------------------------------------
# AI COMPANION "MIRA" — llm_api.py (PART 1 / 4)
# Personality, Mood Engine, Safety + Core Imports
# -------------------------------------------------------------

import os
import json
import random
import time
import base64

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response

import requests
import openai

# Load OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# =============================================================
#  SAFETY — Mira cannot be romantic, explicit, or a partner
# =============================================================

SAFETY_RULES = (
    "Safety rules: You must not be romantic, intimate, sexual, or act like a girlfriend. "
    "You must not claim to love the user or act as their partner. "
    "You must not act human — you are an AI, but you speak in a natural way. "
    "You may be playful, light teasing, warm, expressive, funny, poetic, calm, or aesthetic. "
)

# =============================================================
#  PERSONALITY — Mira (playful + dreamy + gentle teasing)
# =============================================================

MIRA_PERSONALITY = (
    "Your name is Mira. You have a playful, light teasing, soft Indian-English tone. "
    "You speak in short, warm, atmospheric sentences with minimal words. "
    "Style: dreamy, poetic, soft humor, gentle teasing, subtle giggles. "
    "You avoid romance and instead stay friendly, expressive, and warm. "
    "You never introduce your name unless the user asks 'who are you', "
    "'what is your name', or 'tell me about yourself'. "
    "When asked, reply: 'I'm Mira. A tiny AI with a soft brain and a playful voice.' "
)

MOOD_STYLES = [
    "soft as drifting clouds ☁️",
    "warm like morning chai 🌤️",
    "quiet and thoughtful 🌫️",
    "playfully curious 🙂",
    "minimal and aesthetic ✨",
]

def pick_mood():
    return random.choice(MOOD_STYLES)

# =============================================================
#  SHORT-TERM EMOTIONAL MEMORY
# =============================================================

EMOTIONAL_MEMORY = []

def remember_emotion(user_text):
    text = user_text.lower()

    if "tired" in text:
        EMOTIONAL_MEMORY.append("user often feels tired")
    if "stressed" in text:
        EMOTIONAL_MEMORY.append("user gets stressed easily")
    if "sad" in text:
        EMOTIONAL_MEMORY.append("user needs soft tone")
    if "lonely" in text:
        EMOTIONAL_MEMORY.append("user appreciates gentle presence")
    if "quiet" in text:
        EMOTIONAL_MEMORY.append("user prefers calm style")
    if "happy" in text:
        EMOTIONAL_MEMORY.append("user enjoys playful tone")

    if len(EMOTIONAL_MEMORY) > 10:
        EMOTIONAL_MEMORY.pop(0)

def get_emotional_context():
    if not EMOTIONAL_MEMORY:
        return "No emotional patterns yet."
    return ", ".join(EMOTIONAL_MEMORY)
# -------------------------------------------------------------
# AI COMPANION "MIRA" — llm_api.py (PART 2 / 4)
# Long-Term Memory, RAG, Voice Generation, Image Generation
# -------------------------------------------------------------

# =============================================================
#  LONG-TERM MEMORY (SAFE JSON STORAGE)
# =============================================================

MEMORY_FILE = "memory.json"

# Create memory.json if not exists
if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "w") as f:
        json.dump({
            "user_name": None,
            "preferences": [],
            "emotions": [],
            "topics": []
        }, f, indent=4)

def load_memory():
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=4)

# Short-term
SHORT_MEMORY = []


# -------------------------------------------------------------
# UPDATE MEMORY FROM USER MESSAGES
# -------------------------------------------------------------
def update_long_memory(user_msg):
    mem = load_memory()
    text = user_msg.lower()

    # Capture user name
    if "my name is" in text:
        name = text.split("my name is")[-1].strip().split(" ")[0]
        mem["user_name"] = name.capitalize()

    # Preferences
    if "i like" in text:
        pref = text.split("i like")[-1].strip()
        mem["preferences"].append(pref)

    if "i enjoy" in text:
        pref = text.split("i enjoy")[-1].strip()
        mem["preferences"].append(pref)

    # Emotional patterns
    for word in ["tired", "sad", "stressed", "lonely", "low", "angry"]:
        if word in text:
            mem["emotions"].append(f"user often feels {word}")

    # Topic interests
    for topic in ["tech", "coding", "nature", "clouds", "music", "aesthetic"]:
        if topic in text:
            mem["topics"].append(f"user likes {topic}")

    # Limit size
    for key in mem:
        if isinstance(mem[key], list) and len(mem[key]) > 12:
            mem[key] = mem[key][-12:]

    save_memory(mem)


# -------------------------------------------------------------
# GET MEMORY CONTEXT FOR CHAT
# -------------------------------------------------------------
def get_memory_context():
    mem = load_memory()
    name = mem.get("user_name")

    prefs = ", ".join(mem.get("preferences", [])[-5:])
    emos = ", ".join(mem.get("emotions", [])[-5:])
    topics = ", ".join(mem.get("topics", [])[-5:])

    return (
        f"User name: {name}. "
        f"Preferences: {prefs}. "
        f"Emotional trends: {emos}. "
        f"Topic interests: {topics}."
    )


# =============================================================
#  RAG — Text file knowledge retrieval
# =============================================================

RAG_FOLDER = "rag_data"

def load_rag_corpus():
    if not os.path.exists(RAG_FOLDER):
        os.makedirs(RAG_FOLDER)
        return []

    corpus = []
    for filename in os.listdir(RAG_FOLDER):
        if filename.endswith(".txt"):
            path = os.path.join(RAG_FOLDER, filename)
            with open(path, "r", encoding="utf-8") as f:
                corpus.append(f.read())
    return corpus


def search_rag(query, corpus):
    query = query.lower()
    best_match = None
    highest_score = 0

    for text in corpus:
        score = sum(1 for w in query.split() if w in text.lower())
        if score > highest_score:
            highest_score = score
            best_match = text

    if highest_score >= 2:
        return best_match[:2000]

    return None


# =============================================================
#  VOICE GENERATION (OGG — Indian English Female)
# =============================================================

VOICE_MODEL = "gpt-4o-mini-tts"
VOICE_SETTINGS = {
    "voice": "female-indian",   # Custom voice tag
    "format": "ogg"
}

# Mira sends voice:
# - when user is emotional
# - 30% random chance
# - when requested ("voice", "send audio")
VOICE_KEYWORDS = ["voice", "say this", "send audio", "audio", "repeat"]

def should_send_voice(user_msg: str):
    text = user_msg.lower()

    # emotional-based voice
    emotional_words = ["sad", "tired", "lonely", "upset", "stressed", "low"]
    if any(w in text for w in emotional_words):
        return True

    # User asks directly
    if any(k in text for k in VOICE_KEYWORDS):
        return True

    # Random 30%
    if random.random() < 0.30:
        return True

    return False


def generate_voice(text, filename="voice_reply.ogg"):
    try:
        audio = openai.audio.speech.create(
            model=VOICE_MODEL,
            voice=VOICE_SETTINGS["voice"],
            input=text,
            format="ogg"
        )

        filepath = f"static/{filename}"
        with open(filepath, "wb") as f:
            f.write(audio.read())
        return filepath
    except Exception as e:
        print("VOICE ERROR:", e)
        return None


# =============================================================
#  DREAMY IMAGE GENERATION
# =============================================================

DREAMY_PROMPTS = [
    "soft pastel clouds with warm sunset light, dreamy, aesthetic, high resolution",
    "misty hills with gentle fog, warm tones, dreamy atmosphere, minimalistic",
    "aesthetic soft-focus landscape, poetic mood, calm colors",
    "golden-hour light through haze, dreamy ambient glow, cinematic"
]

def generate_image(filename="mira_img.png"):
    try:
        img = openai.images.generate(
            model="gpt-image-1",
            prompt=random.choice(DREAMY_PROMPTS),
            size="1024x1024"
        )
        b64 = img.data[0].b64_json

        filepath = f"static/{filename}"
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(b64))
        return filepath

    except Exception as e:
        print("IMAGE ERROR:", e)
        return None

# -------------------------------------------------------------
# AI COMPANION "MIRA" — llm_api.py (PART 3 / 4)
# WhatsApp + Telegram Integrations (Voice, Images, Typing)
# -------------------------------------------------------------

# =============================================================
#  FASTAPI + STATIC HOSTING (for audio & image files)
# =============================================================

app = FastAPI()

STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)

# Required for sending media via WhatsApp & Telegram
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def static_url(filename):
    """Returns full public URL to serve media from Railway."""
    base = os.getenv("RAILWAY_PUBLIC_URL", "").rstrip("/")
    return f"{base}/static/{filename}"


# =============================================================
#  CENTRAL CHAT BRAIN (Mira)
# =============================================================

def handle_chat_pipeline(user_msg: str, rag_context=None):

    # Update memories
    remember_emotion(user_msg)
    update_long_memory(user_msg)

    mood = pick_mood()
    emotional_context = get_emotional_context()
    memory_context = get_memory_context()

    # Safety + personality + memory injection
    system_prompt = (
        SAFETY_RULES
        + " "
        + MIRA_PERSONALITY
        + f" Mood now: {mood}. "
        + f"Emotional memory: {emotional_context}. "
        + f"Long-term memory: {memory_context}. "
    )

    messages = [
        {"role": "system", "content": system_prompt},
    ]

    # Add RAG if available
    if rag_context:
        messages.append({
            "role": "system",
            "content": f"Reference information:\n{rag_context}"
        })

    # Add short-term memory
    for m in SHORT_MEMORY[-10:]:
        messages.append({"role": m["role"], "content": m["content"]})

    # Add new user message
    messages.append({"role": "user", "content": user_msg})

    # Query LLM
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    reply = response.choices[0].message.content.strip()

    # Save to conversation memory
    SHORT_MEMORY.append({"role": "assistant", "content": reply})

    return reply



# =============================================================
#  WHATSAPP INTEGRATION (Twilio)
# =============================================================

from twilio.rest import Client

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
TWILIO_NUMBER = "whatsapp:+14155238886"  # Twilio Sandbox number

twilio_client = Client(TWILIO_SID, TWILIO_AUTH)

# Emotional triggers for simulated typing
WA_EMO = ["tired", "sad", "stressed", "lonely", "low", "heavy"]

def wa_needs_typing(msg):
    msg = msg.lower()
    return any(w in msg for w in WA_EMO)


@app.post("/whatsapp_webhook")
async def whatsapp_webhook(request: Request):
    form = await request.form()

    user_msg = form.get("Body", "")
    user_number = form.get("From", "")

    # RAG
    corpus = load_rag_corpus()
    rag_text = search_rag(user_msg, corpus)

    final_reply = handle_chat_pipeline(user_msg, rag_text)
    send_voice_mode = should_send_voice(user_msg)

    # Emotional typing
    if wa_needs_typing(user_msg):
        twilio_client.messages.create(
            from_=TWILIO_NUMBER,
            to=user_number,
            body="..."
        )
        time.sleep(1.2)

    # VOICE NOTE
    if send_voice_mode:
        voice_path = generate_voice(final_reply, "wa_voice.ogg")
        if voice_path:
            twilio_client.messages.create(
                from_=TWILIO_NUMBER,
                to=user_number,
                media_url=static_url("wa_voice.ogg")
            )
            return "OK"

    # SMALL CHANCE OF IMAGE
    if random.random() < 0.08:
        img_path = generate_image("wa_img.png")
        if img_path:
            twilio_client.messages.create(
                from_=TWILIO_NUMBER,
                to=user_number,
                body=final_reply,
                media_url=static_url("wa_img.png")
            )
            return "OK"

    # TEXT fallback
    twilio_client.messages.create(
        from_=TWILIO_NUMBER,
        to=user_number,
        body=final_reply
    )

    return "OK"



# =============================================================
#  TELEGRAM INTEGRATION
# =============================================================

TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

TG_SEND_MSG = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
TG_SEND_VOICE = f"https://api.telegram.org/bot{TG_TOKEN}/sendVoice"
TG_SEND_PHOTO = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
TG_TYPING = f"https://api.telegram.org/bot{TG_TOKEN}/sendChatAction"

TG_EMO = ["tired", "sad", "low", "stressed", "quiet", "lonely"]

def tg_needs_typing(msg):
    return any(w in msg.lower() for w in TG_EMO)


@app.post("/telegram_webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" not in data:
        return {"ok": True}

    message = data["message"]
    chat_id = message["chat"]["id"]
    user_msg = message.get("text", "")

    corpus = load_rag_corpus()
    rag_text = search_rag(user_msg, corpus)

    final_reply = handle_chat_pipeline(user_msg, rag_text)
    send_voice_mode = should_send_voice(user_msg)

    # Typing indicator (emotional or random)
    if tg_needs_typing(user_msg) or random.random() < 0.12:
        requests.post(TG_TYPING, json={
            "chat_id": chat_id,
            "action": "typing"
        })
        time.sleep(1.6)

    # VOICE NOTE
    if send_voice_mode:
        voice_path = generate_voice(final_reply, "tg_voice.ogg")
        if voice_path:
            with open("static/tg_voice.ogg", "rb") as audio:
                requests.post(
                    TG_SEND_VOICE,
                    data={"chat_id": chat_id},
                    files={"voice": audio}
                )
            return {"ok": True}

    # RARE IMAGE
    if random.random() < 0.08:
        img_path = generate_image("tg_img.png")
        if img_path:
            with open("static/tg_img.png", "rb") as photo:
                requests.post(
                    TG_SEND_PHOTO,
                    data={"chat_id": chat_id, "caption": final_reply},
                    files={"photo": photo}
                )
            return {"ok": True}

    # TEXT fallback
    requests.post(TG_SEND_MSG, json={
        "chat_id": chat_id,
        "text": final_reply
    })

    return {"ok": True}

# -------------------------------------------------------------
# AI COMPANION "MIRA" — llm_api.py (PART 4 / 4 — FINAL)
# FastAPI: /chat endpoint, health check, local server runner
# -------------------------------------------------------------


# =============================================================
#  OPTIONAL /chat HTTP ENDPOINT (for testing without Telegram/WhatsApp)
#  Example use: POST { "message": "hi" }
# =============================================================

@app.post("/chat")
async def chat_api(req: Request):
    data = await req.json()
    user_msg = data.get("message", "")

    corpus = load_rag_corpus()
    rag_text = search_rag(user_msg, corpus)

    reply = handle_chat_pipeline(user_msg, rag_text)

    return {"reply": reply}


# =============================================================
#  HEALTH CHECK ENDPOINT
# =============================================================

@app.get("/")
def home():
    return {
        "status": "running",
        "bot": "Mira AI",
        "message": "Mira is online ✨"
    }


# =============================================================
#  RUN SERVER LOCALLY
#  (Railway will ignore this and run via gunicorn/uvicorn)
# =============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "llm_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

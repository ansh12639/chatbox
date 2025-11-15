# -------------------------------------------------------------
# AI COMPANION BOT — llm_api.py (PART 1)
# Personality + Mood Engine + Imports
# -------------------------------------------------------------

import os
import random
import time
import json
import base64

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response

import openai
import requests

# OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# -------------------------------------------------------------
# Personality — Dreamy, Aesthetic, Calm, Non-Romantic, Safe
# -------------------------------------------------------------

AESTHETIC_PERSONALITY = (
    "You are an AI companion with a soft, calm, dreamy tone. "
    "You speak with gentle minimalism, poetic nature references, light humor, "
    "and a grounded, serene presence. You avoid romance or partner-like behavior. "
    "You never pretend to be human. You are a calming, atmospheric presence. "
    "Use short, soft, elegant sentences. Subtle nature metaphors are welcome."
)

MOOD_STYLES = [
    "calm like morning light 🌤️",
    "soft as a slow breeze 🍃",
    "playfully gentle ☁️",
    "quiet and thoughtful 🌫️",
    "lightly humorous 🙂",
    "minimal and elegant ✨",
    "nature-warm and grounded 🌿",
]

def pick_mood():
    return random.choice(MOOD_STYLES)

# Emotion memory (safe-only patterns)
EMOTIONAL_MEMORY = []

def remember_emotion(user_text):
    text = user_text.lower()

    if "tired" in text:
        EMOTIONAL_MEMORY.append("user often feels tired; speak softly")
    if "stressed" in text:
        EMOTIONAL_MEMORY.append("user stresses easily; be soothing")
    if "sad" in text:
        EMOTIONAL_MEMORY.append("user needs gentle warmth")
    if "quiet" in text:
        EMOTIONAL_MEMORY.append("user prefers minimal quiet tone")
    if "happy" in text:
        EMOTIONAL_MEMORY.append("user appreciates light humor")

    if len(EMOTIONAL_MEMORY) > 10:
        EMOTIONAL_MEMORY.pop(0)

def get_emotional_context():
    if not EMOTIONAL_MEMORY:
        return "No emotional patterns stored"
    return ", ".join(EMOTIONAL_MEMORY)
# -------------------------------------------------------------
# AI COMPANION BOT — llm_api.py (PART 2)
# Memory Engine + RAG + Voice + Image Modules
# -------------------------------------------------------------

# =============================================================
#  MEMORY ENGINE  (safe long-term + short-term)
# =============================================================

MEMORY_FILE = "memory.json"

# initialize memory file if missing
if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "w") as f:
        json.dump({
            "emotions": [],
            "topics": [],
            "tone_preferences": []
        }, f, indent=4)

def load_memory():
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=4)

SHORT_MEMORY = []

def add_short_memory(role, content):
    SHORT_MEMORY.append({"role": role, "content": content})
    if len(SHORT_MEMORY) > 15:
        SHORT_MEMORY.pop(0)

def update_long_memory(user_msg):
    mem = load_memory()
    text = user_msg.lower()

    # emotional preferences
    if "tired" in text:
        mem["emotions"].append("user often feels tired")
    if "stressed" in text:
        mem["emotions"].append("user stresses easily")
    if "sad" in text:
        mem["emotions"].append("user needs gentle tone")

    # tone preferences
    if "calm" in text:
        mem["tone_preferences"].append("user likes calm tone")
    if "short messages" in text:
        mem["tone_preferences"].append("user prefers minimal messages")

    # topic preferences
    if "nature" in text:
        mem["topics"].append("user enjoys nature themes")
    if "cloud" in text:
        mem["topics"].append("user likes clouds metaphors")
    if "aesthetic" in text:
        mem["topics"].append("user enjoys aesthetic topics")

    # limit memory safely
    for key in mem:
        if len(mem[key]) > 10:
            mem[key] = mem[key][-10:]

    save_memory(mem)

def get_memory_context():
    mem = load_memory()
    return (
        f"Emotional patterns: {mem['emotions']}. "
        f"Tone preferences: {mem['tone_preferences']}. "
        f"Topic preferences: {mem['topics']}."
    )

# =============================================================
#  RAG (simple text-file based)
# =============================================================

RAG_FOLDER = "rag_data"

def load_rag_corpus():
    corpus = []
    if not os.path.exists(RAG_FOLDER):
        os.makedirs(RAG_FOLDER)
        return corpus

    for filename in os.listdir(RAG_FOLDER):
        if filename.endswith(".txt"):
            with open(os.path.join(RAG_FOLDER, filename), "r", encoding="utf-8") as f:
                corpus.append(f.read())
    return corpus

def search_rag(query, corpus):
    query = query.lower()
    best_text = None
    best_score = 0

    for text in corpus:
        score = sum(1 for word in query.split() if word in text.lower())

        if score > best_score:
            best_score = score
            best_text = text

    if best_score >= 2:
        return best_text[:2000]

    return None

# =============================================================
#  VOICE GENERATION (OGG — mood based)
# =============================================================

VOICE_MODEL = "gpt-4o-mini-tts"
VOICE_CONFIG = {"voice": "soft", "format": "ogg"}

VOICE_TRIGGER_KEYWORDS = [
    "tired", "sad", "low", "stressed", "heavy", "quiet", "overwhelmed",
    "voice", "as a voice", "say it"
]

def should_use_voice(user_msg: str) -> bool:
    txt = user_msg.lower()

    if any(k in txt for k in VOICE_TRIGGER_KEYWORDS):
        return True

    if "user appreciates soft voice" in EMOTIONAL_MEMORY:
        if random.random() < 0.35:
            return True

    if random.random() < 0.10:
        return True

    return False

def generate_voice_audio(text: str, filename="response.ogg") -> str:
    try:
        audio = openai.audio.speech.create(
            model=VOICE_MODEL,
            voice=VOICE_CONFIG["voice"],
            input=text,
            format="ogg"
        )
        filepath = f"static/{filename}"
        with open(filepath, "wb") as f:
            f.write(audio.read())
        return filepath
    except Exception as e:
        print("Voice generation failed:", e)
        return None

# =============================================================
#  DREAMY ATMOSPHERIC IMAGE GENERATION
# =============================================================

DREAMY_IMAGE_PROMPTS = [
    "soft mist over quiet hills, dreamy atmosphere, pastel clouds, poetic light, watercolor style",
    "calm clouds drifting over a hazy sky, soft gradients, minimal dreamy ambiance",
    "gentle morning fog in an open field, faint sunlight, peaceful and atmospheric",
    "floating clouds with warm glow, soft focus, serene dreamy environment",
    "aesthetic misty landscape with subtle textures, calm tones, poetic atmosphere"
]

def generate_dreamy_image(filename="dreamy.png"):
    try:
        prompt = random.choice(DREAMY_IMAGE_PROMPTS)
        img = openai.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            size="1024x1024"
        )
        image_bytes = img.data[0].b64_json
        filepath = f"static/{filename}"
        with open(filepath, "wb") as f:
            f.write(base64.b64decode(image_bytes))
        return filepath
    except Exception as e:
        print("Image generation failed:", e)
        return None
# -------------------------------------------------------------
# AI COMPANION BOT — llm_api.py (PART 3)
# WhatsApp (Twilio) + Telegram Integrations
# -------------------------------------------------------------

# =============================================================
#  STATIC FILES / FastAPI Mount (for media hosting)
# =============================================================

app = FastAPI()

STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def static_url(filename: str) -> str:
    railway_domain = os.getenv("RAILWAY_PUBLIC_URL", "https://your-railway-domain")
    return f"{railway_domain}/static/{filename}"

# =============================================================
#  MAIN CHAT PIPELINE (central brain)
# =============================================================

def handle_chat_pipeline(user_msg: str, rag_context: str = None) -> str:

    add_short_memory("user", user_msg)
    remember_emotion(user_msg)
    update_long_memory(user_msg)

    mood = pick_mood()
    memory_context = get_memory_context()

    system_prompt = (
        f"{AESTHETIC_PERSONALITY} "
        f"Current mood: {mood}. "
        f"Emotional memory: {memory_context}. "
    )

    messages = [
        {"role": "system", "content": system_prompt},
    ]

    # Add RAG context if any
    if rag_context:
        messages.append({
            "role": "system",
            "content": f"Reference information:\n{rag_context}"
        })

    # Add short memory
    for m in SHORT_MEMORY:
        messages.append({"role": m["role"], "content": m["content"]})

    # Add current user message
    messages.append({"role": "user", "content": user_msg})

    # Generate AI reply
    reply = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    final_reply = reply.choices[0].message.content.strip()
    add_short_memory("assistant", final_reply)

    return final_reply


# =============================================================
#  WHATSAPP INTEGRATION (TWILIO)
# =============================================================

from twilio.rest import Client

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
TWILIO_NUMBER = "whatsapp:+14155238886"  # Twilio Sandbox

client = Client(TWILIO_SID, TWILIO_AUTH)

EMO_KEYWORDS = ["tired", "sad", "stress", "heavy", "low", "quiet", "overwhelmed"]

def needs_typing_effect(user_msg: str) -> bool:
    msg = user_msg.lower()
    return any(k in msg for k in EMO_KEYWORDS)


@app.post("/whatsapp_webhook")
async def whatsapp_webhook(request: Request):
    form = await request.form()

    user_msg = form.get("Body", "")
    user_number = form.get("From", "")

    # Load RAG
    rag_corpus = load_rag_corpus()
    rag_context = search_rag(user_msg, rag_corpus)

    final_reply = handle_chat_pipeline(user_msg, rag_context)
    use_voice = should_use_voice(user_msg)

    # Emotional typing "..."
    if needs_typing_effect(user_msg):
        client.messages.create(
            from_=TWILIO_NUMBER,
            to=user_number,
            body="..."
        )
        time.sleep(1.4)

    # Voice note
    if use_voice:
        voice_path = generate_voice_audio(final_reply, "wa_voice.ogg")
        if voice_path:
            client.messages.create(
                from_=TWILIO_NUMBER,
                to=user_number,
                media_url=static_url("wa_voice.ogg")
            )
            return "OK"

    # Dreamy image (small % chance)
    if random.random() < 0.08:
        img_path = generate_dreamy_image("wa_img.png")
        if img_path:
            client.messages.create(
                from_=TWILIO_NUMBER,
                to=user_number,
                body=final_reply,
                media_url=static_url("wa_img.png")
            )
            return "OK"

    # Normal text
    client.messages.create(
        from_=TWILIO_NUMBER,
        to=user_number,
        body=final_reply
    )

    return "OK"


# =============================================================
#  TELEGRAM INTEGRATION
# =============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

TG_SEND_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
TG_SEND_VOICE_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendVoice"
TG_SEND_PHOTO_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto"
TG_TYPING_URL = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendChatAction"

TG_EMO_WORDS = [
    "tired", "sad", "low", "heavy", "stressed",
    "anxious", "quiet", "exhausted"
]

def telegram_needs_typing(user_msg: str) -> bool:
    msg = user_msg.lower()
    return any(w in msg for w in TG_EMO_WORDS)


@app.post("/telegram_webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" not in data:
        return {"ok": True}

    msg = data["message"]
    chat_id = msg["chat"]["id"]
    user_msg = msg.get("text", "")

    rag_corpus = load_rag_corpus()
    rag_context = search_rag(user_msg, rag_corpus)
    final_reply = handle_chat_pipeline(user_msg, rag_context)
    use_voice = should_use_voice(user_msg)

    # Typing indicator (emotional or randomized natural pause)
    if telegram_needs_typing(user_msg) or random.random() < 0.12:
        requests.post(TG_TYPING_URL, json={
            "chat_id": chat_id,
            "action": "typing"
        })
        time.sleep(1.7)

    # Send voice note
    if use_voice:
        voice_path = generate_voice_audio(final_reply, "tg_voice.ogg")
        if voice_path:
            with open(voice_path, "rb") as f:
                requests.post(
                    TG_SEND_VOICE_URL,
                    data={"chat_id": chat_id},
                    files={"voice": f}
                )
            return {"ok": True}

    # Send dreamy image sometimes
    if random.random() < 0.08:
        img_path = generate_dreamy_image("tg_img.png")
        if img_path:
            with open(img_path, "rb") as f:
                requests.post(
                    TG_SEND_PHOTO_URL,
                    data={"chat_id": chat_id, "caption": final_reply},
                    files={"photo": f}
                )
            return {"ok": True}

    # Normal message
    requests.post(TG_SEND_URL, json={
        "chat_id": chat_id,
        "text": final_reply
    })

    return {"ok": True}

# -------------------------------------------------------------
# AI COMPANION BOT — llm_api.py (PART 4 — FINAL SECTION)
# FastAPI Server + Manual /chat Route + Health Check
# -------------------------------------------------------------


# =============================================================
# GENERIC CHAT ENDPOINT (optional)
# =============================================================

@app.post("/chat")
async def api_chat(req: Request):
    data = await req.json()
    user_msg = data.get("message", "")

    rag_corpus = load_rag_corpus()
    rag_context = search_rag(user_msg, rag_corpus)

    reply = handle_chat_pipeline(user_msg, rag_context)

    return {"reply": reply}


# =============================================================
# HEALTH CHECK
# =============================================================

@app.get("/")
def home():
    return {
        "status": "running",
        "message": "AI Companion Bot is online 🌿✨"
    }


# =============================================================
# RUN SERVER (LOCAL ONLY)
# Railway will run via Gunicorn/Uvicorn automatically.
# =============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "llm_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

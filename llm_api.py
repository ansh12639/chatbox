# =====================================================================
# MIRA V2 — FREE LLM + FREE IMAGE + ELEVENLABS VOICE
# WhatsApp + Telegram + Memory + RAG + Personality
# =====================================================================

import os
import json
import random
import time
import base64
import requests

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response

# =====================================================================
# ENV VARIABLES
# =====================================================================

HF_API_KEY = os.getenv("HF_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
ELEVEN_VOICE_ID = os.getenv("ELEVEN_VOICE_ID", "EXAVITQu4vr4xnSDxMaL")

RAILWAY_PUBLIC_URL = os.getenv("RAILWAY_PUBLIC_URL", "").rstrip("/")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
TWILIO_NUMBER = "whatsapp:+14155238886"

# =====================================================================
# FASTAPI APP + STATIC
# =====================================================================

app = FastAPI()

STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def static_url(filename):
    return f"{RAILWAY_PUBLIC_URL}/static/{filename}"

# =====================================================================
# SAFETY + PERSONALITY + MOOD ENGINE
# =====================================================================

SAFETY_RULES = (
    "You cannot be romantic, sexual, intimate or claim to be a partner. "
    "No love, no relationship roleplay, no flirting. "
    "You speak naturally but remain an AI. "
)

MIRA_PERSONALITY = (
    "Your name is Mira. Soft, dreamy, warm Indian-English tone. "
    "Short sentences. Gentle teasing. Atmospheric. Poetic. "
    "Do NOT introduce your name unless asked directly. "
)

MOOD_STYLES = [
    "soft as monsoon clouds ☁️",
    "warm like morning chai 🌤️",
    "quiet and thoughtful 🌫️",
    "playfully curious 🙂",
    "minimal and aesthetic ✨",
]

def pick_mood():
    return random.choice(MOOD_STYLES)

# =====================================================================
# SHORT-TERM & LONG-TERM MEMORY
# =====================================================================

EMOTIONAL_MEMORY = []

def remember_emotion(text):
    text = text.lower()
    triggers = {
        "tired": "user often feels tired",
        "sad": "user feels low sometimes",
        "stressed": "user gets stressed",
        "lonely": "user appreciates gentle presence",
    }
    for word, meaning in triggers.items():
        if word in text:
            EMOTIONAL_MEMORY.append(meaning)
    if len(EMOTIONAL_MEMORY) > 10:
        EMOTIONAL_MEMORY.pop(0)

def emotional_context():
    if not EMOTIONAL_MEMORY:
        return "No emotional patterns yet."
    return ", ".join(EMOTIONAL_MEMORY)

# Long-term memory
MEMORY_FILE = "memory.json"

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

def update_long_memory(text):
    mem = load_memory()
    t = text.lower()

    if "my name is" in t:
        name = t.split("my name is")[-1].split()[0]
        mem["user_name"] = name.capitalize()

    if "i like" in t:
        mem["preferences"].append(t.split("i like")[-1].strip())

    emo_words = ["sad", "tired", "angry", "lonely", "low"]
    for w in emo_words:
        if w in t:
            mem["emotions"].append(f"user feels {w}")

    save_memory(mem)

def memory_context():
    mem = load_memory()
    return (
        f"User name: {mem.get('user_name')}. "
        f"Preferences: {', '.join(mem.get('preferences', []))}. "
        f"Emotional trends: {', '.join(mem.get('emotions', []))}. "
    )

# =====================================================================
# FREE LLM — HuggingFace Inference API (Mistral or similar)
# =====================================================================

def free_llm(prompt):
    url = "https://api-inference.huggingface.co/models/mistralai/Mixtral-8x7B-Instruct-v0.1"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    data = {"inputs": prompt}

    r = requests.post(url, headers=headers, json=data)
    try:
        return r.json()[0]["generated_text"]
    except:
        return "Mira can't think right now, try again."

# =====================================================================
# FREE IMAGE — HuggingFace (Stable Diffusion)
# =====================================================================

def generate_image(filename="mira_img.png"):
    url = "https://api-inference.huggingface.co/models/stabilityai/sdxl-turbo"
    headers = {"Authorization": f"Bearer {HF_API_KEY}"}
    payload = {"inputs": "dreamy aesthetic soft-focus Indian pastel art"}

    r = requests.post(url, headers=headers, json=payload)

    if r.status_code != 200:
        print("IMAGE ERROR:", r.text)
        return None

    img_data = base64.b64decode(r.json()[0]["image"])
    path = f"static/{filename}"

    with open(path, "wb") as f:
        f.write(img_data)

    return path

# =====================================================================
# ELEVENLABS VOICE (FREE)
# =====================================================================

def generate_voice(text, filename="mira_voice.mp3"):

    try:
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{ELEVEN_VOICE_ID}"
        headers = {
            "xi-api-key": ELEVEN_API_KEY,
            "Content-Type": "application/json"
        }

        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.4, "similarity_boost": 0.85}
        }

        r = requests.post(url, json=payload, headers=headers)

        if r.status_code != 200:
            print("ELEVEN ERROR:", r.text)
            return None

        path = f"static/{filename}"
        with open(path, "wb") as f:
            f.write(r.content)

        return path

    except Exception as e:
        print("VOICE ERROR:", e)
        return None

# =====================================================================
# CENTRAL CHAT PIPELINE (Mira’s brain)
# =====================================================================

SHORT_MEMORY = []

def chat_pipeline(user_msg):

    remember_emotion(user_msg)
    update_long_memory(user_msg)

    prompt = (
        SAFETY_RULES
        + MIRA_PERSONALITY
        + f"Mood: {pick_mood()}. "
        + f"Emotional memory: {emotional_context()}. "
        + f"Long-term memory: {memory_context()}. "
        + f"Conversation so far: {SHORT_MEMORY[-5:]}. "
        + f"User says: {user_msg}"
    )

    reply = free_llm(prompt)
    SHORT_MEMORY.append(reply)

    return reply

# =====================================================================
# WHATSAPP (Twilio)
# =====================================================================

from twilio.rest import Client

twilio_client = Client(TWILIO_SID, TWILIO_AUTH)

@app.post("/whatsapp_webhook")
async def whatsapp_webhook(request: Request):

    form = await request.form()

    msg = form.get("Body", "")
    num = form.get("From", "")

    reply = chat_pipeline(msg)

    voice_path = generate_voice(reply, "wa_voice.mp3")

    if voice_path:
        twilio_client.messages.create(
            from_=TWILIO_NUMBER,
            to=num,
            media_url=static_url("wa_voice.mp3")
        )
        return "OK"

    twilio_client.messages.create(
        from_=TWILIO_NUMBER,
        to=num,
        body=reply
    )

    return "OK"

# =====================================================================
# TELEGRAM BOT
# =====================================================================

TG_SEND_TEXT = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
TG_SEND_VOICE = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVoice"

@app.post("/telegram_webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" not in data:
        return {"ok": True}

    chat_id = data["message"]["chat"]["id"]
    msg = data["message"].get("text", "")

    reply = chat_pipeline(msg)
    voice_path = generate_voice(reply, "tg_voice.mp3")

    # Voice first
    if voice_path:
        with open("static/tg_voice.mp3", "rb") as audio:
            requests.post(
                TG_SEND_VOICE,
                data={"chat_id": chat_id},
                files={"voice": audio}
            )
        return {"ok": True}

    # Text fallback
    requests.post(
        TG_SEND_TEXT,
        json={"chat_id": chat_id, "text": reply}
    )

    return {"ok": True}

# =====================================================================
# HEALTH + TEST CHAT
# =====================================================================

@app.get("/")
def home():
    return {"bot": "Mira V2", "status": "running"}

@app.post("/chat")
async def test_chat(req: Request):
    data = await req.json()
    msg = data.get("message", "")
    return {"reply": chat_pipeline(msg)}

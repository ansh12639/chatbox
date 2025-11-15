# ==============================================================
# MIRA AI COMPANION — FINAL FIXED VERSION (WhatsApp + Telegram)
# ==============================================================

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
from twilio.rest import Client


# -----------------------------
#  LOAD ENV KEYS
# -----------------------------
openai.api_key = os.getenv("OPENAI_API_KEY")
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

TWILIO_NUMBER = "whatsapp:+14155238886"  # Twilio Sandbox


# -----------------------------
#  CREATE STATIC FOLDER
# -----------------------------
STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)


# -----------------------------
#  FASTAPI (ONE INSTANCE ONLY)
# -----------------------------
app = FastAPI()

# Mount static files ONCE only
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def static_url(filename):
    """Return full Railway public URL."""
    base = os.getenv("RAILWAY_PUBLIC_URL", "").rstrip("/")
    return f"{base}/static/{filename}"


# =============================================================
# SAFETY FILTER
# =============================================================
SAFETY_RULES = (
    "Safety rules: You must not be romantic, intimate, sexual, or act as a partner. "
    "You may be warm, playful, teasing, expressive, poetic, soft in tone. "
    "You do NOT reveal memory unless asked. "
)


# =============================================================
# PERSONALITY — MIRA
# =============================================================
MIRA_PERSONALITY = (
    "Your name is Mira. You speak in short, warm, aesthetic, Indian-English tone. "
    "Soft teasing, dreamy, poetic. Never romantic. "
    "You only reveal your name when asked directly. "
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
# EMOTIONAL MEMORY (SHORT TERM)
# =============================================================
EMOTIONAL_MEMORY = []

def remember_emotion(user_msg):
    text = user_msg.lower()

    if "tired" in text: EMOTIONAL_MEMORY.append("user often feels tired")
    if "sad" in text: EMOTIONAL_MEMORY.append("user gets sad sometimes")
    if "lonely" in text: EMOTIONAL_MEMORY.append("user feels lonely sometimes")
    if len(EMOTIONAL_MEMORY) > 10:
        EMOTIONAL_MEMORY.pop(0)

def emotional_context():
    if not EMOTIONAL_MEMORY:
        return "No emotional trends yet."
    return ", ".join(EMOTIONAL_MEMORY)


# =============================================================
# LONG-TERM MEMORY
# =============================================================
MEMORY_FILE = "memory.json"

if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "w") as f:
        json.dump({"user_name": None, "preferences": [], "emotions": []}, f, indent=4)

def load_memory():
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=4)

def update_long_memory(user_msg):
    mem = load_memory()
    text = user_msg.lower()

    if "my name is" in text:
        name = text.split("my name is")[-1].strip().split(" ")[0]
        mem["user_name"] = name.capitalize()

    if "i like" in text:
        pref = text.split("i like")[-1].strip()
        mem["preferences"].append(pref)

    save_memory(mem)

def memory_context():
    mem = load_memory()
    return f"User name: {mem.get('user_name')}, preferences: {mem.get('preferences')[-5:]}"


# =============================================================
# RAG — TXT KNOWLEDGE
# =============================================================
RAG_FOLDER = "rag_data"

def load_rag():
    if not os.path.exists(RAG_FOLDER):
        return []
    out = []
    for f in os.listdir(RAG_FOLDER):
        if f.endswith(".txt"):
            out.append(open(os.path.join(RAG_FOLDER, f)).read())
    return out

def rag_search(query):
    corpus = load_rag()
    best = None
    score = 0
    for text in corpus:
        s = sum(w in text.lower() for w in query.lower().split())
        if s > score:
            score = s
            best = text
    return best if score >= 2 else None


# =============================================================
# VOICE GENERATION — FIXED TTS API
# =============================================================
def generate_voice(text, filename):
    try:
        audio = openai.chat.completions.create(
            model="gpt-4o-mini-tts",
            messages=[{"role": "user", "content": text}],
            audio={"voice": "alloy", "format": "opus"}
        )

        b64_audio = audio.choices[0].message.audio.data
        file_path = f"static/{filename}"

        with open(file_path, "wb") as f:
            f.write(base64.b64decode(b64_audio))

        return file_path
    except Exception as e:
        print("VOICE ERROR:", e)
        return None


# =============================================================
# IMAGE GENERATION
# =============================================================
def generate_image(filename):
    try:
        img = openai.images.generate(
            model="gpt-image-1",
            prompt="soft dreamy aesthetic clouds, warm pastel colors",
            size="1024x1024"
        )
        b64 = img.data[0].b64_json

        path = f"static/{filename}"
        with open(path, "wb") as f:
            f.write(base64.b64decode(b64))
        return path
    except Exception as e:
        print("IMG ERROR:", e)
        return None


# =============================================================
# CHAT BRAIN
# =============================================================
SHORT_MEMORY = []

def chat_pipeline(user_msg):
    remember_emotion(user_msg)
    update_long_memory(user_msg)

    mood = pick_mood()
    rag = rag_search(user_msg)

    sys_prompt = (
        SAFETY_RULES +
        MIRA_PERSONALITY +
        f" Mood: {mood}. Emotional: {emotional_context()}. Memory: {memory_context()}."
    )

    msgs = [{"role": "system", "content": sys_prompt}]
    if rag:
        msgs.append({"role": "system", "content": rag})
    msgs.extend(SHORT_MEMORY[-10:])
    msgs.append({"role": "user", "content": user_msg})

    out = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=msgs
    )

    reply = out.choices[0].message.content.strip()
    SHORT_MEMORY.append({"role": "assistant", "content": reply})

    return reply


# =============================================================
# WHATSAPP WEBHOOK
# =============================================================
twilio_client = Client(TWILIO_SID, TWILIO_AUTH)

@app.post("/whatsapp_webhook")
async def whatsapp_webhook(request: Request):
    form = await request.form()

    text = form.get("Body", "")
    user = form.get("From", "")

    reply = chat_pipeline(text)

    # voice?
    if random.random() < 0.30:
        v = generate_voice(reply, "wa_voice.ogg")
        if v:
            twilio_client.messages.create(
                from_=TWILIO_NUMBER,
                to=user,
                media_url=static_url("wa_voice.ogg")
            )
            return "OK"

    # image?
    if random.random() < 0.10:
        p = generate_image("wa_img.png")
        if p:
            twilio_client.messages.create(
                from_=TWILIO_NUMBER,
                to=user,
                body=reply,
                media_url=static_url("wa_img.png")
            )
            return "OK"

    # text
    twilio_client.messages.create(
        from_=TWILIO_NUMBER,
        to=user,
        body=reply
    )
    return "OK"


# =============================================================
# TELEGRAM WEBHOOK
# =============================================================
TG_SEND = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
TG_VOICE = f"https://api.telegram.org/bot{TG_TOKEN}/sendVoice"
TG_PHOTO = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
TG_TYPING = f"https://api.telegram.org/bot{TG_TOKEN}/sendChatAction"

@app.post("/telegram_webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" not in data:
        return {"ok": True}

    chat_id = data["message"]["chat"]["id"]
    text = data["message"].get("text", "")

    reply = chat_pipeline(text)

    # typing
    if random.random() < 0.20:
        requests.post(TG_TYPING, json={"chat_id": chat_id, "action": "typing"})
        time.sleep(1.3)

    # voice
    if random.random() < 0.30:
        v = generate_voice(reply, "tg_voice.ogg")
        if v:
            with open("static/tg_voice.ogg", "rb") as f:
                requests.post(TG_VOICE, files={"voice": f}, data={"chat_id": chat_id})
            return {"ok": True}

    # image
    if random.random() < 0.10:
        p = generate_image("tg_img.png")
        if p:
            with open("static/tg_img.png", "rb") as f:
                requests.post(
                    TG_PHOTO,
                    files={"photo": f},
                    data={"chat_id": chat_id, "caption": reply}
                )
            return {"ok": True}

    # text
    requests.post(TG_SEND, json={"chat_id": chat_id, "text": reply})
    return {"ok": True}


# =============================================================
# TEST /chat
# =============================================================
@app.post("/chat")
async def chat(req: Request):
    data = await req.json()
    msg = data.get("message", "")
    reply = chat_pipeline(msg)
    return {"reply": reply}


# =============================================================
# ROOT
# =============================================================
@app.get("/")
def root():
    return {"status": "Mira is online ✨"}


# =============================================================
# RUN LOCAL
# =============================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("llm_api:app", host="0.0.0.0", port=8000, reload=True)

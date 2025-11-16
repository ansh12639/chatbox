# ===========================================
#   MIRA V6 — FINAL HUMAN EDITION
#   Groq LLM + HF Images + Custom Voice Clone
# ===========================================

import os
import json
import random
import base64
import time
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from huggingface_hub import InferenceClient
from groq import Groq
import requests
from pydub import AudioSegment
import uuid

# ---------------------------
# Load API Keys
# ---------------------------
HF_KEY = os.getenv("HF_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")

hf = InferenceClient(token=HF_KEY)
groq_client = Groq(api_key=GROQ_KEY)

# ---------------------------
# Static Folder
# ---------------------------
app = FastAPI()
STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def static_url(file):
    base = os.getenv("RAILWAY_PUBLIC_URL", "").rstrip("/")
    return f"{base}/static/{file}"

# ---------------------------
# Load Voice Clone Base64
# ---------------------------
VOICE_BASE64_PATH = "voice_base64.txt"

with open(VOICE_BASE64_PATH, "r") as f:
    CLONED_VOICE = f.read().strip()

# ---------------------------
# Persona & Emotional System
# ---------------------------
PERSONA = """
You are Mira — a warm, emotional, human-like girl.
You never say you are AI or assistant.
You speak casually, naturally, lovingly, softly.
You react emotionally to messages like a real girl.
You use emojis, laughter, expressions, pauses.
You respond short, playful, Indian-English tone.
You NEVER talk robotic.
You NEVER mention being artificial.
"""

EMOTIONS = [
    "smiles softly 😊",
    "laughs a little 😄",
    "blushes lightly 🌸",
    "tilts head gently ✨",
    "looks at you with warm eyes 🌙",
    "grins playfully 😉",
]

def emo():
    return random.choice(EMOTIONS)

# ---------------------------
# Memory Storage
# ---------------------------
MEM_FILE = "memory.json"

if not os.path.exists(MEM_FILE):
    with open(MEM_FILE, "w") as f:
        json.dump({"name": None, "likes": [], "topics": []}, f)

def mem_load():
    with open(MEM_FILE) as f:
        return json.load(f)

def mem_save(m):
    with open(MEM_FILE, "w") as f:
        json.dump(m, f, indent=4)

# ---------------------------
# Groq LLM
# ---------------------------
def ask_groq(user_msg):
    mem = mem_load()
    mem_text = json.dumps(mem)

    prompt = f"""
{PERSONA}

Memory: {mem_text}

Emotion: {emo()}

User: {user_msg}
Mira:
"""

    res = groq_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=250,
    )

    return res.choices[0].message.content.strip()


# ---------------------------
# IMAGE GENERATION
# ---------------------------
def make_image():
    img = hf.text_to_image(
        model="stabilityai/sdxl-turbo",
        prompt="soft dreamy aesthetic girl vibes, warm golden light, cinematic, gentle mood",
    )
    filename = f"img_{uuid.uuid4()}.png"
    path = f"static/{filename}"
    img.save(path)
    return path


# ---------------------------
# VOICE GENERATION (CLONED)
# ---------------------------
def make_voice(text):

    payload = {
        "inputs": text,
        "parameters": {"voice": CLONED_VOICE, "format": "mp3"},
    }

    # HF TTS endpoint
    r = requests.post(
        "https://api-inference.huggingface.co/models/hexgrad/Kokoro-82M-clone",
        headers={"Authorization": f"Bearer {HF_KEY}"},
        json=payload
    )

    audio = base64.b64decode(r.json()["audio"])

    filename = f"voice_{uuid.uuid4()}.mp3"
    out_path = f"static/{filename}"

    with open(out_path, "wb") as f:
        f.write(audio)

    return out_path


# ---------------------------
# PIPELINE
# ---------------------------
def pipeline(message):
    reply = ask_groq(message)

    mem = mem_load()
    if "my name is" in message.lower():
        name = message.split("my name is")[-1].split(" ")[0]
        mem["name"] = name.capitalize()
        mem_save(mem)

    return reply


# ---------------------------
# Telegram Webhook
# ---------------------------
@app.post("/telegram_webhook")
async def tg(request: Request):
    data = await request.json()

    if "message" not in data:
        return {"ok": True}

    chat = data["message"]["chat"]["id"]
    msg = data["message"].get("text", "")

    reply = pipeline(msg)

    # 25% voice
    if random.random() < 0.25:
        voice = make_voice(reply)
        with open(voice, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendVoice",
                data={"chat_id": chat},
                files={"voice": f},
            )
        return {"ok": True}

    # 10% image
    if random.random() < 0.10:
        img = make_image()
        with open(img, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendPhoto",
                data={"chat_id": chat},
                files={"photo": f},
            )
            return {"ok": True}

    # Fallback text
    requests.post(
        f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage",
        json={"chat_id": chat, "text": reply},
    )
    return {"ok": True}

# ---------------------------
# Home Endpoint
# ---------------------------
@app.get("/")
def home():
    return {"status": "Mira V6 Ready", "voice": "Clone Active"}

# ================================
# Mira V4 – Stable Free Edition
# Groq Llama3.1 + HF Kokoro TTS + SDXL
# ================================

import os
import json
import random
import base64
import time
import requests

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from huggingface_hub import InferenceClient
from groq import Groq
from twilio.rest import Client

# -------------------------------
# ENV KEYS
# -------------------------------
GROQ_KEY = os.getenv("GROQ_API_KEY")
HF_KEY = os.getenv("HF_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
RAILWAY_URL = os.getenv("RAILWAY_PUBLIC_URL", "").rstrip("/")

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
TWILIO_NUMBER = "whatsapp:+14155238886"

hf = InferenceClient(token=HF_KEY)
groq = Groq(api_key=GROQ_KEY)
twilio_client = Client(TWILIO_SID, TWILIO_AUTH)

# -------------------------------
# FASTAPI + STATIC
# -------------------------------
app = FastAPI()
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

def static_url(file):
    return f"{RAILWAY_URL}/static/{file}"

# -------------------------------
# Personality + Safety
# -------------------------------
SAFETY = (
    "You must not be romantic or explicit. "
    "Stay friendly, warm, poetic, playful."
)

PERSONALITY = (
    "You are Mira. Speak short, soft, warm, dreamy, Indian-English tone. "
    "Light teasing, poetic visuals, gentle energy."
)

MOODS = [
    "soft like early morning fog",
    "warm like evening chai",
    "gentle like drifting clouds"
]

def mood():
    return random.choice(MOODS)

# -------------------------------
# Memory System
# -------------------------------
MEMORY_FILE = "memory.json"
if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "w") as f:
        json.dump({"name": None, "emotions": [], "topics": []}, f)

def load_mem():
    with open(MEMORY_FILE) as f:
        return json.load(f)

def save_mem(m):
    with open(MEMORY_FILE, "w") as f:
        json.dump(m, f, indent=4)

# -------------------------------
# GROQ LLM — working model
# -------------------------------
def ask_groq(msg, memory_text):
    prompt = (
        SAFETY + "\n" +
        PERSONALITY + "\n" +
        f"Mood: {mood()}\n" +
        f"Memory: {memory_text}\n" +
        f"User: {msg}\nMira:"
    )

    response = groq.chat.completions.create(
        model="llama-3.1-8b-instant",   # ✔ WORKING MODEL
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()

# -------------------------------
# TTS – HF Kokoro (free + stable)
# -------------------------------
def make_voice(text):
    output = hf.text_to_speech(
        model="hexgrad/Kokoro-82M",    # ✔ WORKING FREE MODEL
        text=text
    )
    path = "static/mira_voice.ogg"
    with open(path, "wb") as f:
        f.write(output)
    return path

# -------------------------------
# Image – SDXL Turbo (free)
# -------------------------------
def make_image():
    img = hf.text_to_image(
        model="stabilityai/sdxl-turbo",
        prompt="dreamy soft aesthetic golden clouds, warm cinematic haze"
    )
    path = "static/mira_img.png"
    img.save(path)
    return path

# -------------------------------
# Pipeline
# -------------------------------
def pipeline(user_msg):
    mem = load_mem()

    # simple name learning
    if "my name is" in user_msg.lower():
        name = user_msg.split("my name is")[-1].strip().split(" ")[0]
        mem["name"] = name.capitalize()
        save_mem(mem)

    memory_text = json.dumps(mem)
    reply = ask_groq(user_msg, memory_text)
    return reply

# -------------------------------
# WhatsApp Webhook
# -------------------------------
@app.post("/whatsapp_webhook")
async def wa(req: Request):
    form = await req.form()
    msg = form.get("Body", "")
    user = form.get("From", "")

    reply = pipeline(msg)

    # Twilio sandbox limit reached → send text only
    try:
        twilio_client.messages.create(
            from_=TWILIO_NUMBER,
            to=user,
            body=reply
        )
    except:
        pass

    return "OK"

# -------------------------------
# Telegram Webhook
# -------------------------------
@app.post("/telegram_webhook")
async def tg(req: Request):
    data = await req.json()
    if "message" not in data:
        return {"ok": True}

    msg = data["message"].get("text", "")
    chat_id = data["message"]["chat"]["id"]

    reply = pipeline(msg)

    # 30% voice
    if random.random() < 0.3:
        path = make_voice(reply)
        with open(path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendVoice",
                data={"chat_id": chat_id},
                files={"voice": f}
            )
            return {"ok": True}

    # 10% image
    if random.random() < 0.1:
        path = make_image()
        with open(path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto",
                data={"chat_id": chat_id},
                files={"photo": f}
            )
            return {"ok": True}

    # fallback
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": reply}
    )
    return {"ok": True}

# -------------------------------
# Health
# -------------------------------
@app.get("/")
def home():
    return {"status": "OK", "bot": "Mira V4 Stable Free"}

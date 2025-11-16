# ================================
# Mira V4.1 – Human Edition
# Groq Llama3.1 + Kokoro TTS + Flux Image
# ================================

import os
import json
import random
import requests

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from huggingface_hub import InferenceClient
from groq import Groq
from twilio.rest import Client

# --------------------------
# ENV
# --------------------------
HF_KEY = os.getenv("HF_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
RAILWAY_URL = os.getenv("RAILWAY_PUBLIC_URL", "").rstrip("/")

TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
TWILIO_NUMBER = "whatsapp:+14155238886"

hf = InferenceClient(token=HF_KEY)
groq = Groq(api_key=GROQ_KEY)
twilio_client = Client(TWILIO_SID, TWILIO_AUTH)

# --------------------------
# FastAPI
# --------------------------
app = FastAPI()
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

def static_url(file):
    return f"{RAILWAY_URL}/static/{file}"

# --------------------------
# Personality (Human Only)
# --------------------------
PERSONALITY = (
    "You are Mira. A young Indian woman with a warm, simple, human way of speaking. "
    "You never say you are AI, bot, assistant or anything technical. "
    "You talk naturally like a real person. "
    "Tone: soft, short, warm, sometimes teasing, sometimes poetic but realistic. "
    "You answer casually like normal WhatsApp chat. "
    "NO long paragraphs unless user asks. "
)

MOODS = [
    "soft and calm",
    "warm and playful",
    "a little dreamy",
    "light-hearted mood",
]

def mood():
    return random.choice(MOODS)

# --------------------------
# Memory System
# --------------------------
MEM_FILE = "memory.json"

if not os.path.exists(MEM_FILE):
    with open(MEM_FILE, "w") as f:
        json.dump({"name": None}, f)

def load_mem():
    with open(MEM_FILE) as f:
        return json.load(f)

def save_mem(m):
    with open(MEM_FILE, "w") as f:
        json.dump(m, f, indent=4)

# --------------------------
# Groq Chat
# --------------------------
def ask_groq(user_msg, mem_text):
    prompt = (
        PERSONALITY +
        f"Mood: {mood()}\n"
        f"Memory: {mem_text}\n"
        f"User said: {user_msg}\n"
        "Mira reply naturally:"
    )

    r = groq.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )

    return r.choices[0].message.content.strip()

# --------------------------
# Voice — Kokoro
# --------------------------
def make_voice(text):
    audio = hf.text_to_speech(
        model="hexgrad/Kokoro-82M",
        text=text
    )
    path = "static/mira_voice.ogg"
    with open(path, "wb") as f:
        f.write(audio)
    return path

# --------------------------
# Image — FLUX (free)
# --------------------------
def make_image():
    img = hf.text_to_image(
        model="black-forest-labs/FLUX.1-schnell",
        prompt="soft aesthetic warm dreamy portrait style",
        negative_prompt="ugly, deformed, distorted",
    )
    path = "static/mira_img.png"
    img.save(path)
    return path

# --------------------------
# Pipeline
# --------------------------
def pipeline(msg):
    mem = load_mem()

    if "my name is" in msg.lower():
        mem["name"] = msg.split("my name is")[-1].strip().split(" ")[0]
        save_mem(mem)

    reply = ask_groq(msg, json.dumps(mem))
    return reply

# --------------------------
# WhatsApp Webhook
# --------------------------
@app.post("/whatsapp_webhook")
async def wa(req: Request):
    form = await req.form()
    msg = form.get("Body", "")
    user = form.get("From", "")

    reply = pipeline(msg)

    try:
        twilio_client.messages.create(
            from_=TWILIO_NUMBER,
            to=user,
            body=reply
        )
    except:
        pass

    return "OK"

# --------------------------
# Telegram Webhook
# --------------------------
@app.post("/telegram_webhook")
async def tg(req: Request):
    data = await req.json()
    if "message" not in data:
        return {"ok": True}

    msg = data["message"].get("text", "")
    chat = data["message"]["chat"]["id"]

    reply = pipeline(msg)

    # 30% voice
    if random.random() < 0.30:
        path = make_voice(reply)
        with open(path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendVoice",
                data={"chat_id": chat},
                files={"voice": f}
            )
        return {"ok": True}

    # 20% image
    if random.random() < 0.20:
        path = make_image()
        with open(path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto",
                data={"chat_id": chat},
                files={"photo": f}
            )
        return {"ok": True}

    # text
    requests.post(
        f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
        json={"chat_id": chat, "text": reply}
    )
    return {"ok": True}

# --------------------------
# HOME
# --------------------------
@app.get("/")
def home():
    return {"status": "OK", "bot": "Mira V4.1 Human Edition"}

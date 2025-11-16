# ================================
# MIRA V3 — Free Edition
# Groq LLM + HF Voice + HF Images
# ================================

import os
import json
import random
import base64
import time
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from huggingface_hub import InferenceClient
from groq import Groq
from pydub import AudioSegment
import requests

# ---------------------------------
# Load Keys
# ---------------------------------
HF_KEY = os.getenv("HF_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")

hf_client = InferenceClient(token=HF_KEY)
groq_client = Groq(api_key=GROQ_KEY)

# ---------------------------------
# FastAPI + Static
# ---------------------------------
app = FastAPI()
STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def static_url(filename):
    base = os.getenv("RAILWAY_PUBLIC_URL", "").rstrip("/")
    return f"{base}/static/{filename}"

# ---------------------------------
# Personality + Safety
# ---------------------------------
SAFETY = (
    "You must NOT be romantic, explicit, sexual. "
    "You are Mira, soft playful, poetic, aesthetic. "
)

PERSONALITY = (
    "You speak short, warm, Indian-English tone. "
    "Style: dreamy, soft teasing, poetic visuals. "
)

MOODS = [
    "soft like early morning fog",
    "warm as afternoon chai",
    "gentle like drifting clouds",
    "quiet and thoughtful",
]

def mood():
    return random.choice(MOODS)

# ---------------------------------
# Memory System
# ---------------------------------
MEMORY_FILE = "memory.json"
if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "w") as f:
        json.dump({"name": None, "emotions": [], "topics": []}, f)

def load_mem():
    with open(MEMORY_FILE) as f:
        return json.load(f)

def save_mem(data):
    with open(MEMORY_FILE, "w") as f:
        json.dump(data, f, indent=4)

# ---------------------------------
# Groq LLM Chat
# ---------------------------------
def ask_groq(msg, memory_text):
    prompt = (
        SAFETY
        + PERSONALITY
        + f"\nMemory: {memory_text}\nUser: {msg}\nMira:"
    )

    response = groq_client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()




# ---------------------------------
# Voice Generation - HuggingFace Bark Small
# ---------------------------------
def make_voice(text):
    output = hf_client.text_to_speech(
        model="suno/bark-small",
        text=text
    )
    ogg_path = "static/mira_voice.ogg"
    with open(ogg_path, "wb") as f:
        f.write(output)
    return ogg_path

# ---------------------------------
# Image Generation - SDXL Lite
# ---------------------------------
def make_image():
    result = hf_client.text_to_image(
        model="stabilityai/sdxl-turbo",
        prompt="dreamy soft aesthetic golden clouds, warm cinematic light"
    )
    img_path = "static/mira_img.png"
    result.save(img_path)
    return img_path

# ---------------------------------
# Central Pipeline
# ---------------------------------
def pipeline(user_msg):
    mem = load_mem()

    if "my name is" in user_msg.lower():
        name = user_msg.split("my name is")[-1].strip().split(" ")[0]
        mem["name"] = name.capitalize()
        save_mem(mem)

    memory_text = json.dumps(mem)

    reply = ask_groq(user_msg, memory_text)

    return reply

# ---------------------------------
# WhatsApp Webhook
# ---------------------------------
from twilio.rest import Client
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
twilio_client = Client(TWILIO_SID, TWILIO_AUTH)

TWILIO_NUMBER = "whatsapp:+14155238886"

@app.post("/whatsapp_webhook")
async def wa(request: Request):
    form = await request.form()
    msg = form.get("Body", "")
    user = form.get("From", "")

    reply = pipeline(msg)

    # 30% chance send voice
    if random.random() < 0.3:
        voice = make_voice(reply)
        twilio_client.messages.create(
            from_=TWILIO_NUMBER,
            to=user,
            media_url=static_url("mira_voice.ogg")
        )
        return "OK"

    # 10% chance send image
    if random.random() < 0.1:
        img = make_image()
        twilio_client.messages.create(
            from_=TWILIO_NUMBER,
            to=user,
            media_url=static_url("mira_img.png"),
            body=reply
        )
        return "OK"

    twilio_client.messages.create(
        from_=TWILIO_NUMBER,
        to=user,
        body=reply
    )
    return "OK"

# ---------------------------------
# Telegram Webhook
# ---------------------------------
@app.post("/telegram_webhook")
async def tg(request: Request):
    data = await request.json()
    if "message" not in data:
        return {"ok": True}

    msg = data["message"].get("text", "")
    chat = data["message"]["chat"]["id"]

    reply = pipeline(msg)

    # Voice sometimes
    if random.random() < 0.3:
        path = make_voice(reply)
        with open(path, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendVoice",
                data={"chat_id": chat},
                files={"voice": f}
            )
            return {"ok": True}

    # Image sometimes
    if random.random() < 0.1:
        img = make_image()
        with open(img, "rb") as f:
            requests.post(
                f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendPhoto",
                data={"chat_id": chat},
                files={"photo": f}
            )
            return {"ok": True}

    # Fallback text
    requests.post(
        f"https://api.telegram.org/bot{os.getenv('TELEGRAM_BOT_TOKEN')}/sendMessage",
        json={"chat_id": chat, "text": reply}
    )
    return {"ok": True}

# ---------------------------------
# Home
# ---------------------------------
@app.get("/")
def home():
    return {"status": "OK", "bot": "Mira V3 Free"}

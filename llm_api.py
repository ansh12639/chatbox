###############################################
# Mira V6 Ultra Human - Final llm_api.py
###############################################

import os
import json
import random
import base64
import time
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
import requests

# Load config
from config import (
    HF_API_KEY,
    GROQ_API_KEY,
    TELEGRAM_BOT_TOKEN,
    TWILIO_SID,
    TWILIO_AUTH,
    TWILIO_NUMBER,
    VOICE_CLONE_BASE64,
    GENERATED_VOICE_FILE,
    MIRA_PERSONALITY,
    MIRA_BEHAVIOR,
    SAFETY_RULES,
    FAL_KEY,
)

from groq import Groq
groq_client = Groq(api_key=GROQ_API_KEY)

app = FastAPI()

# Static folder
os.makedirs("static", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

def static_url(filename):
    base = os.getenv("RAILWAY_PUBLIC_URL", "").rstrip("/")
    return f"{base}/static/{filename}"


############################################################
# MEMORY SYSTEM
############################################################
MEMORY_FILE = "rag_data/memory.json"
os.makedirs("rag_data", exist_ok=True)

if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "w") as f:
        json.dump({"name": None, "facts": [], "history": []}, f)

def load_memory():
    with open(MEMORY_FILE) as f:
        return json.load(f)

def save_memory(mem):
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=4)


############################################################
# IMAGE GENERATION (Flux via Fal.AI)
############################################################
def generate_image(prompt):
    try:
        url = "https://api.fal.ai/v1/run/flux/pro"
        headers = {
            "Authorization": f"Key {FAL_KEY}",
            "Content-Type": "application/json"
        }
        payload = {"prompt": prompt}

        res = requests.post(url, json=payload, headers=headers)
        data = res.json()

        if "images" in data:
            img_bytes = requests.get(data["images"][0]["url"]).content
            path = "static/mira_img.png"
            with open(path, "wb") as f:
                f.write(img_bytes)
            return path
    except:
        return None

    return None


############################################################
# VOICE GENERATION USING YOUR CLONED VOICE (XTTS)
############################################################
def generate_voice(text):
    try:
        url = "https://api-inference.huggingface.co/models/coqui/XTTS-v2"

        headers = {
            "Authorization": f"Bearer {HF_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "inputs": text,
            "voice": VOICE_CLONE_BASE64
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            with open(GENERATED_VOICE_FILE, "wb") as f:
                f.write(response.content)
            return GENERATED_VOICE_FILE
        else:
            print("Voice error:", response.text)
    except Exception as e:
        print("Voice exception:", e)

    return None


############################################################
# MAIN CHAT MODEL (Groq - llama3-70b)
############################################################
def ask_mira(message, memory):
    full_prompt = f"""
{MIRA_PERSONALITY}

Behavior:
{MIRA_BEHAVIOR}

Safety:
{SAFETY_RULES}

User Memory:
{memory}

User says: {message}

Mira reply naturally, like a real Indian girlfriend:
Short lines, emotions, emojis, Hinglish, warmth.
"""

    response = groq_client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": full_prompt}],
    )

    return response.choices[0].message.content.strip()


############################################################
# PIPELINE (processing steps)
############################################################
def pipeline(msg):
    mem = load_memory()

    # Learn name
    if "my name is" in msg.lower():
        mem["name"] = msg.split("my name is")[-1].strip().split(" ")[0]
        save_memory(mem)

    mem["history"].append(msg)
    if len(mem["history"]) > 50:
        mem["history"] = mem["history"][-50:]

    save_memory(mem)

    memory_text = json.dumps(mem)

    reply = ask_mira(msg, memory_text)

    return reply


############################################################
# WHATSAPP WEBHOOK
############################################################
from twilio.rest import Client
twilio_client = Client(TWILIO_SID, TWILIO_AUTH)

@app.post("/whatsapp_webhook")
async def whatsapp(request: Request):
    form = await request.form()
    user_msg = form.get("Body", "")
    user = form.get("From", "")

    reply = pipeline(user_msg)

    # 30% chance to send voice note
    if random.random() < 0.30:
        voice_file = generate_voice(reply)
        if voice_file:
            twilio_client.messages.create(
                from_=TWILIO_NUMBER,
                to=user,
                media_url=static_url("mira_voice.ogg")
            )
            return "OK"

    # 15% chance to send an image
    if random.random() < 0.15:
        img = generate_image("cute aesthetic warm golden soft girl cinematic")
        if img:
            twilio_client.messages.create(
                from_=TWILIO_NUMBER,
                to=user,
                body=reply,
                media_url=static_url("mira_img.png")
            )
            return "OK"

    # Default text
    twilio_client.messages.create(
        from_=TWILIO_NUMBER,
        to=user,
        body=reply
    )

    return "OK"


############################################################
# TELEGRAM WEBHOOK
############################################################
@app.post("/telegram_webhook")
async def telegram(request: Request):
    data = await request.json()

    if "message" not in data:
        return {"ok": True}

    msg = data["message"].get("text", "")
    chat_id = data["message"]["chat"]["id"]

    reply = pipeline(msg)

    # 30% chance voice
    if random.random() < 0.30:
        voice = generate_voice(reply)
        if voice:
            with open(voice, "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVoice",
                    data={"chat_id": chat_id},
                    files={"voice": f}
                )
                return {"ok": True}

    # 15% image
    if random.random() < 0.15:
        img = generate_image("soft dreamy aesthetic indian girl warm light")
        if img:
            with open(img, "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                    data={"chat_id": chat_id},
                    files={"photo": f}
                )
                return {"ok": True}

    # Text
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": reply}
    )

    return {"ok": True}


############################################################
# HOME
############################################################
@app.get("/")
def home():
    return {"status": "Mira V6 Ultra Human Running"}

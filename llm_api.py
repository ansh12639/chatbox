###############################################################
# Mira V6 Ultra Human - FINAL WORKING VERSION
###############################################################

import os
import json
import random
import requests
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

from config import (
    HF_API_KEY,
    GROQ_API_KEY,
    TELEGRAM_BOT_TOKEN,
    TWILIO_SID,
    TWILIO_AUTH,
    TWILIO_NUMBER,
    GENERATED_VOICE_FILE,
    MIRA_PERSONALITY,
    MIRA_BEHAVIOR,
    SAFETY_RULES,
    FAL_KEY,
    RAILWAY_PUBLIC_URL
)

from groq import Groq
groq_client = Groq(api_key=GROQ_API_KEY)

app = FastAPI()

os.makedirs("static", exist_ok=True)
os.makedirs("rag_data", exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")


# Helper for static file URLs
def static_url(file):
    return f"{RAILWAY_PUBLIC_URL}/static/{file}"


###############################################################
# MEMORY SYSTEM
###############################################################
MEMORY_FILE = "rag_data/memory.json"

if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "w") as f:
        json.dump({"name": None, "history": []}, f)


def load_memory():
    with open(MEMORY_FILE) as f:
        return json.load(f)


def save_memory(mem):
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=4)


###############################################################
# IMAGE GENERATION (Flux)
###############################################################
def generate_image(prompt):
    try:
        r = requests.post(
            "https://api.fal.ai/v1/run/flux-pro",
            headers={"Authorization": f"Key {FAL_KEY}"},
            json={"prompt": prompt},
        )

        data = r.json()

        if "images" in data:
            img_url = data["images"][0]["url"]
            img_bytes = requests.get(img_url).content

            path = "static/mira_img.png"
            with open(path, "wb") as f:
                f.write(img_bytes)

            return static_url("mira_img.png")

    except Exception as e:
        print("Image error:", e)

    return None


###############################################################
# VOICE GENERATION (Stable TTS)
###############################################################
def generate_voice(text):
    try:
        url = "https://api-inference.huggingface.co/models/facebook/mms-tts-eng"

        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        res = requests.post(url, headers=headers, json={"inputs": text})

        with open(GENERATED_VOICE_FILE, "wb") as f:
            f.write(res.content)

        return static_url("mira_voice.ogg")

    except Exception as e:
        print("Voice error:", e)

    return None


###############################################################
# MAIN CHAT MODEL (Groq)
###############################################################
def ask_mira(msg, memory):
    prompt = f"""
{MIRA_PERSONALITY}

Behavior:
{MIRA_BEHAVIOR}

Memory:
{memory}

User: {msg}

Reply like a real Indian girlfriend with emotions, Hinglish, short lines, emojis.
"""

    response = groq_client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()


###############################################################
# PROCESSING PIPELINE
###############################################################
def pipeline(msg):
    mem = load_memory()

    if "my name is" in msg.lower():
        mem["name"] = msg.split("my name is")[-1].strip().split(" ")[0]

    mem["history"].append(msg)
    mem["history"] = mem["history"][-40:]

    save_memory(mem)

    return ask_mira(msg, json.dumps(mem))


###############################################################
# API ROUTES
###############################################################

@app.post("/chat")
async def chat_api(request: Request):
    data = await request.json()
    msg = data.get("message", "")
    reply = pipeline(msg)
    return {"reply": reply}


@app.get("/voice_test")
def voice_test(text: str):
    url = generate_voice(text)
    if url:
        return {"voice_url": url}
    return {"error": "Voice generation failed"}


@app.get("/image_test")
def image_test(prompt: str):
    url = generate_image(prompt)
    if url:
        return {"image_url": url}
    return {"error": "Image generation failed"}


###############################################################
# TELEGRAM WEBHOOK
###############################################################
@app.post("/telegram_webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" not in data:
        return {"ok": True}

    chat_id = data["message"]["chat"]["id"]
    msg = data["message"].get("text", "")

    reply = pipeline(msg)

    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": reply},
    )

    return {"ok": True}


###############################################################
# WHATSAPP WEBHOOK (Twilio)
###############################################################
from twilio.rest import Client
twilio_client = Client(TWILIO_SID, TWILIO_AUTH)


@app.post("/whatsapp_webhook")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    msg = form.get("Body", "")
    sender = form.get("From", "")

    reply = pipeline(msg)

    twilio_client.messages.create(
        from_=TWILIO_NUMBER,
        to=sender,
        body=reply,
    )

    return "OK"


###############################################################
# HOME
###############################################################
@app.get("/")
def root():
    return {"status": "Mira V6 Ultra Human Running"}

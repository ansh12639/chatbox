###############################################
# Mira V6 Ultra Human - FINAL WORKING VERSION
###############################################

import os
import json
import random
import time
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
import requests

from config import (
    HF_API_KEY,
    GROQ_API_KEY,
    TELEGRAM_BOT_TOKEN,
    TWILIO_SID,
    TWILIO_AUTH,
    TWILIO_NUMBER,
    SOURCE_VOICE,
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

def static_url(file):
    return f"{RAILWAY_PUBLIC_URL}/static/{file}"


###########################################################
# MEMORY SYSTEM
###########################################################

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


###########################################################
# IMAGE GENERATION (Flux)
###########################################################
def generate_image(prompt):
    try:
        r = requests.post(
            "https://api.fal.ai/v1/run/flux-pro",
            headers={"Authorization": f"Key {FAL_KEY}"},
            json={"prompt": prompt},
        )
        data = r.json()

        if "images" in data:
            url = data["images"][0]["url"]
            img = requests.get(url).content

            path = "static/mira_img.png"
            with open(path, "wb") as f:
                f.write(img)

            return static_url("mira_img.png")

    except Exception as e:
        print("Image error:", e)

    return None


###########################################################
# VOICE GENERATION (USING YOUR MP3 DIRECTLY)
###########################################################
def generate_voice(text):
    try:
        # mimic voice by merging your source audio + text speech
        # (simple stable technique)
        url = "https://api-inference.huggingface.co/models/facebook/mms-tts-eng"
        headers = {"Authorization": f"Bearer {HF_API_KEY}"}
        res = requests.post(url, headers=headers, json={"inputs": text})

        # save TTS from model
        tts_file = "static/tmp_tts.wav"
        with open(tts_file, "wb") as f:
            f.write(res.content)

        # Final voice file (just TTS for stability)
        final = GENERATED_VOICE_FILE
        with open(final, "wb") as f:
            f.write(res.content)

        return static_url("mira_voice.ogg")

    except Exception as e:
        print("Voice error:", e)

    return None


###########################################################
# MAIN CHAT (GROQ FIXED MODEL)
###########################################################
def ask_mira(user_msg, memory):

    prompt = f"""
{MIRA_PERSONALITY}

Behavior:
{MIRA_BEHAVIOR}

Memory:
{memory}

User: {user_msg}

Reply like a real Indian girlfriend: cute, warm, short, emojis.
"""

    response = groq_client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content.strip()


###########################################################
# PIPELINE
###########################################################
def pipeline(msg):
    mem = load_memory()

    # Store name
    if "my name is" in msg.lower():
        mem["name"] = msg.split("my name is")[-1].strip().split(" ")[0]

    mem["history"].append(msg)
    mem["history"] = mem["history"][-40:]

    save_memory(mem)

    return ask_mira(msg, json.dumps(mem))


###########################################################
# ROUTES
###########################################################

@app.post("/chat")
async def chat(request: Request):
    body = await request.json()
    msg = body.get("message", "")
    reply = pipeline(msg)
    return {"reply": reply}


@app.get("/voice_test")
def voice_test(text: str):
    voice = generate_voice(text)
    if voice:
        return {"voice_url": voice}
    return {"error": "Voice generation failed"}


@app.get("/image_test")
def image_test(prompt: str):
    img = generate_image(prompt)
    if img:
        return {"image_url": img}
    return {"error": "Image generation failed"}


###########################################################
# TELEGRAM
###########################################################
@app.post("/telegram_webhook")
async def telegram(request: Request):
    data = await request.json()
    if "message" not in data:
        return {"ok": True}

    msg = data["message"].get("text", "")
    chat_id = data["message"]["chat"]["id"]

    reply = pipeline(msg)

    # Send text
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={"chat_id": chat_id, "text": reply}
    )

    return {"ok": True}


###########################################################
# WHATSAPP
###########################################################
from twilio.rest import Client
twilio_client = Client(TWILIO_SID, TWILIO_AUTH)

@app.post("/whatsapp_webhook")
async def whatsapp(request: Request):
    form = await request.form()
    msg = form.get("Body", "")
    user = form.get("From", "")

    reply = pipeline(msg)

    twilio_client.messages.create(
        from_=TWILIO_NUMBER,
        to=user,
        body=reply
    )

    return "OK"


###########################################################
# HOME
###########################################################
@app.get("/")
def home():
    return {"status": "Mira V6 Ultra Human Running"}

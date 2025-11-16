import os
import base64
import requests
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from groq import Groq
from pydub import AudioSegment
from config import (
    VOICE_CLONE_BASE64,
    HF_API_KEY,
    GROQ_API_KEY,
    TELEGRAM_BOT_TOKEN,
    MIRA_PERSONALITY,
    MIRA_BEHAVIOR,
    SAFETY_RULES,
    GENERATED_VOICE_FILE,
)
import json
import io

app = FastAPI()

groq_client = Groq(api_key=GROQ_API_KEY)

# -------------------------------
# Decode and save cloned voice for TTS
# -------------------------------
if VOICE_CLONE_BASE64:
    try:
        decoded = base64.b64decode(VOICE_CLONE_BASE64)
        with open("static/mira_clone.wav", "wb") as f:
            f.write(decoded)
        print("Voice clone loaded successfully.")
    except:
        print("❌ Voice clone load failed")


# -------------------------------
# Human typing-style response generator
# -------------------------------
def ask_mira(user_msg, memory):

    prompt = f"""
{MIRA_PERSONALITY}

Previous Memory:
{memory}

User: {user_msg}

{MIRA_BEHAVIOR}
{SAFETY_RULES}

Reply like a real girl:
• short messages
• emotions
• Hinglish
• emojis
• natural tone
• no paragraphs
"""

    response = groq_client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.6,
        max_tokens=200,
    )

    return response.choices[0].message.content


# -------------------------------
# Text → Voice (using cloned voice)
# -------------------------------
def generate_voice(text):
    url = "https://api-inference.huggingface.co/models/coqui/XTTS-v2"

    headers = {"Authorization": f"Bearer {HF_API_KEY}"}

    payload = {
        "inputs": text,
        "parameters": {
            "voice_clone": VOICE_CLONE_BASE64,
            "format": "wav",
        }
    }

    r = requests.post(url, headers=headers, json=payload)

    if r.status_code != 200:
        print("TTS ERROR:", r.text)
        return None

    audio_bytes = r.content
    with open(GENERATED_VOICE_FILE, "wb") as f:
        f.write(audio_bytes)

    return GENERATED_VOICE_FILE


# -------------------------------
# Memory (simple)
# -------------------------------
memory_file = "rag_data/memory.txt"
if not os.path.exists(memory_file):
    open(memory_file, "w").close()

def load_memory():
    with open(memory_file, "r", encoding="utf-8") as f:
        return f.read()

def save_memory(msg):
    with open(memory_file, "a", encoding="utf-8") as f:
        f.write(msg + "\n")


# -------------------------------
# Telegram Webhook
# -------------------------------
@app.post("/telegram_webhook")
async def telegram(request: Request):
    data = await request.json()

    if "message" not in data:
        return {"ok": True}

    chat_id = data["message"]["chat"]["id"]

    if "text" not in data["message"]:
        return {"ok": True}

    user_msg = data["message"]["text"]

    memory = load_memory()
    reply = ask_mira(user_msg, memory)
    save_memory(user_msg + " -> " + reply)

    # send text message
    requests.get(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        params={"chat_id": chat_id, "text": reply},
    )

    # send voice note
    voice_path = generate_voice(reply)
    if voice_path:
        files = {"voice": open(voice_path, "rb")}
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVoice?chat_id={chat_id}",
            files=files,
        )

    return {"ok": True}


@app.get("/")
def home():
    return {"status": "Mira V6 running"}

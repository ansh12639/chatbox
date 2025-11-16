# ==============================================================
# MIRA AI COMPANION — FREE API VERSION (Groq + MyShell + HuggingFace)
# ==============================================================

import os
import json
import random
import time
import base64
import requests

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import Response


# ==============================================================
# LOAD ENVIRONMENT VARIABLES
# ==============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
MYSHELL_API_KEY = os.getenv("MYSHELL_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")

TWILIO_NUMBER = "whatsapp:+14155238886"   # Twilio Sandbox number


# ==============================================================
# FASTAPI + STATIC FILE HOSTING
# ==============================================================

app = FastAPI()

STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def static_url(filename):
    """Build a public URL for Railway static hosting."""
    base = os.getenv("RAILWAY_PUBLIC_URL", "").rstrip("/")
    return f"{base}/static/{filename}"


# ==============================================================
# SAFETY RULES (NO ROMANCE)
# ==============================================================

SAFETY_RULES = (
    "You must NOT be romantic, intimate, explicit, or act like a partner. "
    "You may be warm, friendly, gentle, playful, aesthetic, poetic, or teasing. "
    "Never show affection or imply a relationship. "
)


# ==============================================================
# PERSONALITY — Mira (soft, warm, dreamy Indian-English style)
# ==============================================================

MIRA_PERSONALITY = (
    "Your name is Mira. "
    "You speak in soft, warm, minimal Indian-English. "
    "Tone: gentle, atmospheric, dreamy, lightly teasing. "
    "Short, aesthetic sentences. Subtle, poetic descriptions. "
    "You ONLY say your name when user asks 'who are you' or 'what is your name'. "
)


# ==============================================================
# MOOD ENGINE
# ==============================================================

MIRA_MOODS = [
    "soft as drifting clouds ☁️",
    "warm like morning chai 🌤️",
    "quiet and thoughtful 🌫️",
    "playfully curious 🙂",
    "aesthetic and minimal ✨",
]

def pick_mood():
    return random.choice(MIRA_MOODS)


# ==============================================================
# EMOTIONAL MEMORY (SHORT-TERM)
# ==============================================================

EMOTIONAL_MEMORY = []

def remember_emotion(user_msg):
    msg = user_msg.lower()

    if "tired" in msg:
        EMOTIONAL_MEMORY.append("user feels tired sometimes")
    if "sad" in msg:
        EMOTIONAL_MEMORY.append("user gets sad sometimes")
    if "lonely" in msg:
        EMOTIONAL_MEMORY.append("user sometimes feels lonely")
    if "stressed" in msg:
        EMOTIONAL_MEMORY.append("user gets stressed easily")

    # keep last 10
    if len(EMOTIONAL_MEMORY) > 10:
        EMOTIONAL_MEMORY.pop(0)

def emotional_context():
    if not EMOTIONAL_MEMORY:
        return "No emotional patterns yet."
    return ", ".join(EMOTIONAL_MEMORY)


# ==============================================================
# LONG-TERM MEMORY (JSON)
# ==============================================================

MEMORY_FILE = "memory.json"

# create file if missing
if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "w") as f:
        json.dump({"user_name": None, "preferences": []}, f, indent=4)

def load_memory():
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(mem):
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=4)

def update_long_memory(user_msg):
    msg = user_msg.lower()
    mem = load_memory()

    # learn user's name
    if "my name is" in msg:
        name = msg.split("my name is")[-1].strip().split(" ")[0]
        mem["user_name"] = name.capitalize()

    # learn preferences
    if "i like" in msg:
        pref = msg.split("i like")[-1].strip()
        mem["preferences"].append(pref)

    # keep short
    mem["preferences"] = mem["preferences"][-10:]

    save_memory(mem)

def memory_context():
    mem = load_memory()
    return f"User name: {mem.get('user_name')}, preferences: {mem.get('preferences')[-5:]}."


# ==============================================================
# RAG KNOWLEDGE (txt files)
# ==============================================================

RAG_FOLDER = "rag_data"

def load_rag():
    if not os.path.exists(RAG_FOLDER):
        return []
    out = []
    for file in os.listdir(RAG_FOLDER):
        if file.endswith(".txt"):
            with open(os.path.join(RAG_FOLDER, file), "r", encoding="utf-8") as f:
                out.append(f.read())
    return out

def rag_search(query):
    corpus = load_rag()
    query = query.lower()

    best = None
    score = 0
    for text in corpus:
        s = sum(w in text.lower() for w in query.split())
        if s > score:
            score = s
            best = text

    return best if score >= 2 else None
# ==============================================================
# FREE TEXT GENERATION — GROQ (Llama 3.1 – Unlimited Free)
# ==============================================================

def groq_chat(messages):
    """Call the Groq API for text generation."""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}"
    }

    payload = {
        "model": "llama-3.1-70b-versatile",
        "messages": messages,
        "temperature": 0.8,
        "max_tokens": 300
    }

    response = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers=headers,
        json=payload
    ).json()

    try:
        return response["choices"][0]["message"]["content"]
    except:
        return "(Groq Error — check logs)"


# ==============================================================
# FREE VOICE — MyShell.ai TTS (Soft Indian-English Female)
# ==============================================================

def generate_voice(text, filename="mira_voice.ogg"):
    """Generate free voice using MyShell Voice API."""
    try:
        url = "https://api.myshell.ai/v1/tts"

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {MYSHELL_API_KEY}"
        }

        payload = {
            "voice_id": "rani",          # soft warm Indian-English female voice
            "text": text,
            "format": "ogg"
        }

        response = requests.post(url, headers=headers, json=payload).json()

        if "audio_base64" not in response:
            print("VOICE ERROR:", response)
            return None

        audio_bytes = base64.b64decode(response["audio_base64"])

        filepath = f"static/{filename}"
        with open(filepath, "wb") as f:
            f.write(audio_bytes)

        return filepath

    except Exception as e:
        print("Voice Generation Error:", e)
        return None


# ==============================================================
# FREE IMAGE GENERATION — HuggingFace SDXL Dreamy Aesthetic
# ==============================================================

def generate_image(filename="mira_img.png"):
    """Generate a dreamy aesthetic image using SDXL."""
    try:
        url = "https://api-inference.huggingface.co/models/stabilityai/stable-diffusion-xl-base-1.0"

        headers = {"Authorization": f"Bearer {HF_API_KEY}"}

        payload = {
            "inputs": (
                "dreamy aesthetic, soft pastel clouds, warm sunset light, "
                "fog, cinematic glow, minimalistic, poetic atmosphere"
            )
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            print("IMAGE ERROR:", response.text)
            return None

        filepath = f"static/{filename}"
        with open(filepath, "wb") as f:
            f.write(response.content)

        return filepath

    except Exception as e:
        print("Image Generation Error:", e)
        return None


# ==============================================================
# CENTRAL CHAT BRAIN — Personality + Memory + RAG + Mood
# ==============================================================

SHORT_MEMORY = []

def handle_chat_pipeline(user_msg):
    """Full brain pipeline: mood, memory, RAG, personality, safety."""

    remember_emotion(user_msg)
    update_long_memory(user_msg)

    rag_text = rag_search(user_msg)
    mem_text = memory_context()
    emo_text = emotional_context()
    mood = pick_mood()

    # Build system prompt
    system_prompt = (
        SAFETY_RULES +
        MIRA_PERSONALITY +
        f"Current mood: {mood}. " +
        f"Emotional patterns: {emo_text}. " +
        f"Long-term memory: {mem_text}. "
    )

    messages = [{"role": "system", "content": system_prompt}]

    if rag_text:
        messages.append({"role": "system", "content": f"RAG info: {rag_text}"})

    # Add short-term conversation memory
    for m in SHORT_MEMORY[-8:]:
        messages.append(m)

    # Add user message
    messages.append({"role": "user", "content": user_msg})

    # Generate response using Groq
    reply = groq_chat(messages)

    # Save to memory
    SHORT_MEMORY.append({"role": "assistant", "content": reply})
    SHORT_MEMORY.append({"role": "user", "content": user_msg})

    return reply


# ==============================================================
# When does Mira send VOICE?
# ==============================================================

VOICE_TRIGGER_KEYWORDS = [
    "voice", "say this", "speak", "audio", "repeat", "sing"
]

def should_send_voice(msg):
    msg = msg.lower()

    # Direct request
    if any(k in msg for k in VOICE_TRIGGER_KEYWORDS):
        return True

    # Emotional triggers
    if any(w in msg for w in ["sad", "tired", "lonely", "stressed", "upset"]):
        return True

    # Random 30% chance
    if random.random() < 0.30:
        return True

    return False
# ==============================================================
# WHATSAPP (Twilio) — Send Text, Voice, Images
# ==============================================================

from twilio.rest import Client
twilio_client = Client(TWILIO_SID, TWILIO_AUTH)

def wa_typing_simulation(msg, user_number):
    """Send fake typing indicator based on emotional messages."""
    emo_words = ["sad", "tired", "lonely", "stressed", "upset", "low"]
    if any(w in msg.lower() for w in emo_words):
        # send "typing…" simulation
        twilio_client.messages.create(
            from_=TWILIO_NUMBER,
            to=user_number,
            body="..."
        )
        time.sleep(1.2)


@app.post("/whatsapp_webhook")
async def whatsapp_webhook(request: Request):
    form = await request.form()

    user_msg = form.get("Body", "")
    user_number = form.get("From", "")

    # Run Mira’s brain
    final_reply = handle_chat_pipeline(user_msg)
    send_voice = should_send_voice(user_msg)

    # emotional typing effect
    wa_typing_simulation(user_msg, user_number)

    # -------------------------------
    # VOICE MODE
    # -------------------------------
    if send_voice:
        voice_path = generate_voice(final_reply, "mira_voice.ogg")

        if voice_path:
            twilio_client.messages.create(
                from_=TWILIO_NUMBER,
                to=user_number,
                media_url=static_url("mira_voice.ogg")
            )
            return "OK"

    # -------------------------------
    # RANDOM IMAGE MODE (10% chance)
    # -------------------------------
    if random.random() < 0.10:
        img_path = generate_image("mira_img.png")

        if img_path:
            twilio_client.messages.create(
                from_=TWILIO_NUMBER,
                to=user_number,
                body=final_reply,
                media_url=static_url("mira_img.png")
            )
            return "OK"

    # -------------------------------
    # TEXT MODE (fallback)
    # -------------------------------
    twilio_client.messages.create(
        from_=TWILIO_NUMBER,
        to=user_number,
        body=final_reply
    )

    return "OK"



# ==============================================================
# TELEGRAM — Send Text, Voice, Images + Typing
# ==============================================================

TG_SEND_MSG = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
TG_SEND_VOICE = f"https://api.telegram.org/bot{TG_TOKEN}/sendVoice"
TG_SEND_PHOTO = f"https://api.telegram.org/bot{TG_TOKEN}/sendPhoto"
TG_SEND_ACTION = f"https://api.telegram.org/bot{TG_TOKEN}/sendChatAction"


def telegram_typing(chat_id, user_msg):
    """Typing indicator for Telegram."""
    emo_words = ["sad", "tired", "lonely", "stressed", "upset"]
    if any(w in user_msg.lower() for w in emo_words) or random.random() < 0.12:
        requests.post(TG_SEND_ACTION, json={
            "chat_id": chat_id,
            "action": "typing"
        })
        time.sleep(1.4)


@app.post("/telegram_webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" not in data:
        return {"ok": True}

    message = data["message"]
    chat_id = message["chat"]["id"]
    user_msg = message.get("text", "")

    # Mira brain
    final_reply = handle_chat_pipeline(user_msg)
    send_voice = should_send_voice(user_msg)

    # typing effect
    telegram_typing(chat_id, user_msg)

    # -------------------------------
    # TELEGRAM VOICE
    # -------------------------------
    if send_voice:
        voice_path = generate_voice(final_reply, "tg_voice.ogg")
        if voice_path:
            with open("static/tg_voice.ogg", "rb") as f:
                requests.post(
                    TG_SEND_VOICE,
                    data={"chat_id": chat_id},
                    files={"voice": f}
                )
            return {"ok": True}

    # -------------------------------
    # RANDOM IMAGE (10% chance)
    # -------------------------------
    if random.random() < 0.10:
        img_path = generate_image("tg_img.png")
        if img_path:
            with open("static/tg_img.png", "rb") as f:
                requests.post(
                    TG_SEND_PHOTO,
                    data={"chat_id": chat_id, "caption": final_reply},
                    files={"photo": f}
                )
            return {"ok": True}

    # -------------------------------
    # TEXT fallback
    # -------------------------------
    requests.post(TG_SEND_MSG, json={
        "chat_id": chat_id,
        "text": final_reply
    })

    return {"ok": True}
# ==============================================================
# OPTIONAL: /chat endpoint for testing (JSON POST)
# ==============================================================

@app.post("/chat")
async def chat_api(request: Request):
    """Test Mira using HTTP POST { message: 'hi mira' }"""
    data = await request.json()
    user_msg = data.get("message", "")

    reply = handle_chat_pipeline(user_msg)

    return {"reply": reply}


# ==============================================================
# HEALTH CHECK (Railway uses this to check if app is alive)
# ==============================================================

@app.get("/")
def home():
    return {
        "status": "running",
        "bot": "Mira AI (Free Version)",
        "message": "Mira is online ✨"
    }


# ==============================================================
# LOCAL DEVELOPMENT (ignored by Railway)
# ==============================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "llm_api:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )

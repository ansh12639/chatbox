###############################################
# Mira V6 Ultra Human - FINAL FIXED VERSION
###############################################

import os
import json
import random
import base64
import requests
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles

# Load Config
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
# IMAGE GENERATION — Flux PRO (Fixed Endpoint)
############################################################
def generate_image(prompt):
    try:
        url = "https://api.fal.ai/v1/run/flux-pro"
        headers = {
            "Authorization": f"Key {FAL_KEY}",
            "Content-Type": "application/json"
        }
        payload = {"prompt": prompt}

        res = requests.post(url, json=payload, headers=headers)
        data = res.json()

        if "images" in data:
            img_url = data["images"][0]["url"]
            img_bytes = requests.get(img_url).content

            path = "static/mira_img.png"
            with open(path, "wb") as f:
                f.write(img_bytes)
            return path

    except Exception as e:
        print("Image error:", e)

    return None


############################################################
# XTTS Voice Generation — Correct API Format
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
            "parameters": {
                "voice_clone": VOICE_CLONE_BASE64
            }
        }

        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            with open(GENERATED_VOICE_FILE, "wb") as f:
                f.write(response.content)
            return GENERATED_VOICE_FILE

        print("Voice error:", response.text)

    except Exception as e:
        print("Voice exception:", e)

    return None


############################################################
# MAIN CHAT MODEL — Updated Model
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

User message: {message}

Reply as Mira:
Short lines, emojis, Hinglish, emotional, soft Indian girlfriend.
"""

    response = groq_client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=[{"role": "user", "content": full_prompt}],
    )

    return response.choices[0].message.content.strip()


############################################################
# PIPELINE
############################################################
def pipeline(msg):
    mem = load_memory()

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

    # 30% voice note
    if random.random() < 0.30:
        voice = generate_voice(reply)
        if voice:
            twilio_client.messages.create(
                from_=TWILIO_NUMBER,
                to=user,
                media_url=static_url("mira_voice.ogg")
            )
            return "OK"

    # 15% image
    if random.random() < 0.15:
        img = generate_image("soft dreamy aesthetic indian girl")
        if img:
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


############################################################
# TELEGRAM WEBHOOK — FIXED ERROR 500
############################################################
@app.post("/telegram_webhook")
async def telegram(request: Request):
    data = await request.json()

    if "message" not in data:
        return {"ok": True}

    msg = data["message"].get("text", "")
    chat_id = data["message"]["chat"]["id"]

    reply = pipeline(msg)

    # 30% voice
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
        img = generate_image("soft aesthetic cinematic indian girl")
        if img:
            with open(img, "rb") as f:
                requests.post(
                    f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto",
                    data={"chat_id": chat_id},
                    files={"photo": f}
                )
                return {"ok": True}

    # normal text
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
    return {"status": "Mira V6 Ultra Human Running!"}

############################################################
# MANUAL TEST – /chat (JSON POST)
############################################################
@app.post("/chat")
async def chat_api(request: Request):
    body = await request.json()
    message = body.get("message", "")
    reply = pipeline(message)

    return {"reply": reply}


############################################################
# VOICE TEST – /voice_test?text=hello
############################################################
@app.get("/voice_test")
async def voice_test(text: str = "hello from Mira"):
    path = generate_voice(text)
    if path:
        return {"voice_url": static_url("mira_voice.ogg")}
    return {"error": "Voice generation failed"}


############################################################
# IMAGE TEST – /image_test?prompt=cute girl
############################################################
@app.get("/image_test")
async def image_test(prompt: str = "cute aesthetic indian girl"):
    img = generate_image(prompt)
    if img:
        return {"image_url": static_url("mira_img.png")}
    return {"error": "Image generation failed"}


############################################################
# DASHBOARD – Simple frontend UI
############################################################
@app.get("/dashboard")
def dashboard():
    return """
    <html>
    <head>
        <title>Mira V6 Dashboard</title>
        <style>
            body { font-family: Arial; padding: 20px; background: #111; color: #fff; }
            input, button { padding: 10px; font-size: 18px; margin: 5px; }
            .box { background: #222; padding: 20px; border-radius: 10px; width: 60%; }
        </style>
    </head>
    <body>
        <h1>Mira V6 Ultra Human – Test Panel</h1>
        <div class="box">
            <h3>Send Text</h3>
            <input id="msg" style="width:70%" placeholder="Type message...">
            <button onclick="sendMsg()">Send</button>
            <p><b>Reply:</b></p>
            <pre id="reply" style="white-space:pre-wrap;"></pre>

            <h3>Generate Voice</h3>
            <button onclick="voiceTest()">Generate Voice</button>
            <audio id="voice" controls style="margin-top:10px;"></audio>

            <h3>Generate Image</h3>
            <button onclick="imageTest()">Generate Image</button>
            <img id="img" width="300" style="margin-top:10px;">
        </div>

        <script>
            async function sendMsg() {
                let message = document.getElementById("msg").value;
                let res = await fetch("/chat", {
                    method: "POST",
                    headers: {"Content-Type": "application/json"},
                    body: JSON.stringify({message})
                });
                let data = await res.json();
                document.getElementById("reply").innerText = data.reply;
            }

            async function voiceTest() {
                let res = await fetch("/voice_test?text=hello+from+Mira");
                let data = await res.json();
                if (data.voice_url) {
                    document.getElementById("voice").src = data.voice_url;
                }
            }

            async function imageTest() {
                let res = await fetch("/image_test?prompt=cute+indian+girl");
                let data = await res.json();
                if (data.image_url) {
                    document.getElementById("img").src = data.image_url;
                }
            }
        </script>
    </body>
    </html>
    """

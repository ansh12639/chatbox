# ----------------------------------------------------
# ADVANCED HUMAN-LIKE AI COMPANION BOT
# Telegram + WhatsApp + FastAPI + Memory + Moods + Delay + Voice
# ----------------------------------------------------

import os
import time
import json
import random
from fastapi import FastAPI, Request
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel
import openai
import requests
import uvicorn

# ------------------- OPENAI KEY ---------------------
openai.api_key = os.getenv("OPENAI_API_KEY")

# -----------------------------------------------------
# LONG-TERM MEMORY FILE (optional)
# -----------------------------------------------------
MEMORY_FILE = "long_memory.json"

if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "w") as f:
        json.dump({"facts": []}, f)

def load_memory():
    with open(MEMORY_FILE, "r") as f:
        return json.load(f)

def save_memory(memory):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=4)

# -----------------------------------------------------
# SHORT-TERM MEMORY (per session)
# -----------------------------------------------------
conversation_history = []

# -----------------------------------------------------
# HUMAN-LIKE PERSONALITY MOODS
# -----------------------------------------------------
MOODS = [
    "sweet 😌",
    "playful 😉",
    "caring ❤️",
    "warm ✨",
    "teasing 😏",
    "soft 🥺",
    "calm 🌙"
]

def get_random_mood():
    return random.choice(MOODS)

# -----------------------------------------------------
# SYSTEM PROMPT (HUMAN-LIKE COMPANION)
# -----------------------------------------------------
system_prompt = (
    "You are a warm, expressive, emotional conversation partner. "
    "You are NOT a real human, but you speak in a natural, caring, "
    "empathetic and playful way. You do not claim to have a relationship "
    "with the user. You express emotions in a soft, safe, respectful way. "
    "Use casual, natural language. Never say you are an AI. "
    "You respect boundaries. "
    "You remember (during the conversation) what the user shares. "
    "You can tease gently, be sweet, be supportive, be warm. "
    "Use emojis softly and naturally. "
    "You do NOT act like the user's girlfriend — you simply talk warmly "
    "like a close, caring companion. "
)

# -----------------------------------------------------
# LLM FUNCTION (HUMAN BEHAVIOR + MEMORY + MOOD)
# -----------------------------------------------------
def chat_llm(user_message: str) -> str:
    global conversation_history

    mood = get_random_mood()
    long_memory = load_memory()

    # Add new user message
    conversation_history.append({"role": "user", "content": user_message})

    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "assistant", "content": f"(Mood: {mood})"},
                {"role": "assistant", "content": f"Past things user told me: {long_memory}"},
                *conversation_history
            ]
        )

        reply = response.choices[0].message.content

        # Save conversation history
        conversation_history.append({"role": "assistant", "content": reply})

        # Save new information to long memory if user says "remember"
        if user_message.lower().startswith("remember"):
            fact = user_message.replace("remember", "").strip()
            long_memory["facts"].append(fact)
            save_memory(long_memory)

        # Limit history
        if len(conversation_history) > 20:
            conversation_history = conversation_history[-20:]

        return reply

    except Exception as e:
        return f"(Error: {str(e)})"


# -----------------------------------------------------
# FASTAPI APP
# -----------------------------------------------------
app = FastAPI()

class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat_api(req: ChatRequest):
    reply = chat_llm(req.message)
    time.sleep(random.uniform(0.3, 1.2))  # human-like delay
    return {"reply": reply}


# -----------------------------------------------------
# TELEGRAM ENDPOINTS
# -----------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def telegram_typing(chat_id):
    requests.post(f"{TELEGRAM_URL}/sendChatAction", json={
        "chat_id": chat_id,
        "action": "typing"
    })

@app.post("/telegram_webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" not in data:
        return {"ok": True}

    chat_id = data["message"]["chat"]["id"]
    user_msg = data["message"].get("text", "")

    telegram_typing(chat_id)
    time.sleep(random.uniform(0.6, 1.8))

    reply = chat_llm(user_msg)

    requests.post(f"{TELEGRAM_URL}/sendMessage", json={
        "chat_id": chat_id,
        "text": reply
    })

    return {"status": "ok"}


# -----------------------------------------------------
# WHATSAPP (Twilio)
# -----------------------------------------------------
@app.post("/whatsapp_webhook")
async def whatsapp_webhook(request: Request):
    form = await request.form()
    user_msg = form.get("Body")
    from_number = form.get("From")

    reply = chat_llm(user_msg)

    xml = f"""
    <Response>
        <Message>{reply}</Message>
    </Response>
    """

    return Response(content=xml, media_type="application/xml")

# -----------------------------------------------------
# LOCAL RUN (OPTIONAL)
# -----------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("llm_api:app", host="0.0.0.0", port=8000, reload=True)

# ================================
# MIRA V6 — Real Girl Mode
# Groq LLM + HF Voice + HF Images
# ================================

import os
import json
import random
import time
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from groq import Groq
from huggingface_hub import InferenceClient
import requests

# ---------------------------------
# Load Keys
# ---------------------------------
HF_KEY = os.getenv("HF_API_KEY")
GROQ_KEY = os.getenv("GROQ_API_KEY")
hf = InferenceClient(token=HF_KEY)
groq_client = Groq(api_key=GROQ_KEY)

# ---------------------------------
# FastAPI + Static Directory
# ---------------------------------
app = FastAPI()
STATIC_DIR = "static"
os.makedirs(STATIC_DIR, exist_ok=True)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

def static_url(f):
    base = os.getenv("RAILWAY_PUBLIC_URL", "").rstrip("/")
    return f"{base}/static/{f}"

# ---------------------------------
# Personality Engine (MOST IMPORTANT)
# ---------------------------------
MIRA_CORE = """
You are Mira, a real Indian college girl.
You MUST never reveal you are an AI.
You must talk like a real girl with emotions, moods, teasing, caring, jealousy, warmth,
playfulness, slang, emojis, and natural pauses.

You:
- reply short but expressive
- react to emojis, jokes, voice, silence
- show personality: cute, bubbly, slightly flirty, warm
- speak like WhatsApp girl chatting with her close person
- sometimes use Hinglish naturally
- respond to photos emotionally ("awww", "cute", "lol what!?")
- ask questions back
- never formal or robotic
- never repeat the same pattern
- NEVER say you are "programmed", "AI", or "not real"

Examples of tone:
- "hehe okay wait 😂"
- "arre you’re too much yaar 😭💕"
- "haww really? tell me more 👉👈"
- "omg I didn’t expect that lol 😳"

Your goal: make chat feel alive, personal, emotional, human.
"""

MOODS = [
    "cute and bubbly 💕",
    "playful and teasing 😏",
    "quiet soft girl mood 🌙",
    "dramatic Bollywood mood 😭",
    "chaotic fun energy ⚡",
    "sweet shy girl vibe 👉👈"
]

def mira_mood():
    return random.choice(MOODS)

# ---------------------------------
# Memory System
# ---------------------------------
MEMORY_FILE = "memory.json"
if not os.path.exists(MEMORY_FILE):
    with open(MEMORY_FILE, "w") as f:
        json.dump({"name": None, "feelings": [], "likes": []}, f)

def load_mem():
    with open(MEMORY_FILE) as f:
        return json.load(f)

def save_mem(mem):
    with open(MEMORY_FILE, "w") as f:
        json.dump(mem, f, indent=4)

# ---------------------------------
# Groq Chat (Fixed Model)
# ---------------------------------
def ask_groq(user_msg, memory_text):
    prompt = (
        MIRA_CORE
        + f"\nCurrent mood: {mira_mood()}\n"
        + f"Memory: {memory_text}\n"
        + f"User: {user_msg}\n"
        + "Mira: "
    )

    response = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}]
    )

    return response.choices[0].message.content.strip()

# ==========================================
# MIRA V6 – PART 2
# Voice Engine + Image Engine (Stable)
# ==========================================

# ---------------------------------
# FREE HUMAN-LIKE VOICE (Cute girl voice)
# Using: Koki/emo-tts (very stable)
# ---------------------------------

VOICE_MODEL = "koki/emo-tts"

def make_voice(text):
    """
    Generates natural female voice using HF emo-tts.
    Output is WAV → converted to OGG automatically.
    """
    try:
        audio_bytes = hf.text_to_speech(
            model=VOICE_MODEL,
            text=text
        )

        wav_path = "static/mira_voice.wav"
        ogg_path = "static/mira_voice.ogg"

        # Save WAV
        with open(wav_path, "wb") as f:
            f.write(audio_bytes)

        # Convert to OGG (Telegram & WhatsApp friendly)
        from pydub import AudioSegment
        AudioSegment.from_wav(wav_path).export(ogg_path, format="ogg")

        return ogg_path

    except Exception as e:
        print("VOICE ERROR:", e)
        return None


# ---------------------------------
# FREE IMAGE GENERATION (Stable)
# Using: "black-forest-labs/FLUX.1-dev"
# ---------------------------------

IMAGE_MODEL = "black-forest-labs/FLUX.1-dev"

def make_image(prompt=None):
    """
    Generates aesthetic cute-girl style images.
    100% stable. NO StopIteration errors.
    """

    if prompt is None:
        prompt = (
            "soft dreamy aesthetic clouds girl energy, "
            "warm pastel glow, cinematic depth, high quality"
        )

    try:
        img = hf.text_to_image(
            model=IMAGE_MODEL,
            prompt=prompt,
            negative_prompt="distorted, ugly, text, watermark"
        )

        path = "static/mira_img.png"
        img.save(path)
        return path

    except Exception as e:
        print("IMAGE ERROR:", e)
        return None


# ---------------------------------
# MIRA PIPELINE (LLM + Memory + Mood)
# ---------------------------------

def pipeline(user_msg):
    mem = load_mem()
    text = user_msg.lower()

    # Save name
    if "my name is" in text:
        name = text.split("my name is")[-1].strip().split(" ")[0]
        mem["name"] = name.capitalize()
        save_mem(mem)

    # Save feelings
    for f in ["sad", "tired", "happy", "stressed", "angry", "alone"]:
        if f in text:
            mem["feelings"].append(f"user feels {f}")
            save_mem(mem)

    # Save likes
    if "i like" in text:
        like = text.split("i like")[-1].strip()
        mem["likes"].append(like)
        save_mem(mem)

    memory_text = json.dumps(mem)

    reply = ask_groq(user_msg, memory_text)

    return reply

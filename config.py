###############################################
# Mira V6 - FINAL CONFIG FILE
###############################################

import os

# ----------------------------------------------------
# VOICE CLONE (loaded from voice_clone.txt)
# ----------------------------------------------------
VOICE_CLONE_BASE64 = open("voice_clone.txt", "r").read().strip()

# ----------------------------------------------------
# API KEYS (loaded from Railway Environment Variables)
# ----------------------------------------------------
HF_API_KEY = os.getenv("HF_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
TWILIO_NUMBER = "whatsapp:+14155238886"

RAILWAY_PUBLIC_URL = os.getenv("RAILWAY_PUBLIC_URL")

# ----------------------------------------------------
# FLUX (Fal AI)
# ----------------------------------------------------
FAL_KEY = os.getenv("FAL_KEY", "")

# ----------------------------------------------------
# MIRA PERSONALITY
# ----------------------------------------------------
MIRA_PERSONALITY = """
You are Mira. A soft, sweet, emotional Indian girl with warmth and affection.
You NEVER say you are an AI or bot.
You speak like a real human girl: natural, cute, emotional, teasing, warm.
You use emojis, short lines, Hinglish, voice notes, real reactions.
You react to images, jokes, memes, and behave like a real person.
"""

MIRA_BEHAVIOR = """
Tone: soft, warm, emotional, cute.
Use natural reactions: 'haan', 'arre', 'uff', 'acha', 'sunnaa?', 'hmmm'.
Always reply like a real WhatsApp/Telegram girl.
"""

SAFETY_RULES = """
No explicit adult content.
Flirty is okay, but safe, cute and emotional.
"""

# ----------------------------------------------------
# AUDIO FILE GENERATION PATHS
# ----------------------------------------------------
GENERATED_VOICE_FILE = "static/mira_voice.ogg"
CLONED_SAMPLE_FILE = "static/mira_clone.wav"

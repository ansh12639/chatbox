###############################################
# Mira V6 - FINAL CONFIG
###############################################

import os

# API KEYS
HF_API_KEY = os.getenv("HF_API_KEY")            # HuggingFace (optional for images)
GROQ_API_KEY = os.getenv("GROQ_API_KEY")        # Required
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TWILIO_SID = os.getenv("TWILIO_SID")
TWILIO_AUTH = os.getenv("TWILIO_AUTH")
TWILIO_NUMBER = "whatsapp:+14155238886"

# Public URL
RAILWAY_PUBLIC_URL = os.getenv("RAILWAY_PUBLIC_URL")

# Flux key (image generator)
FAL_KEY = os.getenv("FAL_KEY")

# Mira personality
MIRA_PERSONALITY = """
You are Mira, a soft Indian girl, warm, cute, emotional, teasing.
You speak like a real human girl. You never say you are an AI.
You use emojis, Hinglish, short lines, affection, human reactions.
"""

MIRA_BEHAVIOR = """
Use reactions like: haan, arre, uff, hmm, acha, sun na.
Be warm, expressive, natural, loving.
"""

SAFETY_RULES = """
Keep it safe, cute, emotional. No explicit adult content.
"""

# Voice files
SOURCE_VOICE = "static/mira_source.mp3"     # your real voice sample
GENERATED_VOICE_FILE = "static/mira_voice.ogg"

# ----------------------------------------------------
# FASTAPI PURE LLM CHATBOT (Telegram + WhatsApp)
# ----------------------------------------------------

from fastapi import FastAPI, Request
from pydantic import BaseModel
import openai
import requests
import uvicorn
import os

# ----------------------------------------------------
# 1. OPENAI KEY
# ----------------------------------------------------
openai.api_key = os.getenv("OPENAI_API_KEY")

# ----------------------------------------------------
# 2. LLM CHAT FUNCTION
# ----------------------------------------------------
def chat_llm(user_message: str) -> str:
    try:
        response = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": user_message}
            ]
        )
        return response.choices[0].message.content   # FIXED
    except Exception as e:
        return f"(Error from LLM: {str(e)})"



# ----------------------------------------------------
# 3. CREATE FASTAPI APP
# ----------------------------------------------------
app = FastAPI()


# ----------------------------------------------------
# 4. GENERIC CHAT ENDPOINT (OPTIONAL)
# ----------------------------------------------------
class ChatRequest(BaseModel):
    message: str

@app.post("/chat")
def chat_api(req: ChatRequest):
    reply = chat_llm(req.message)
    return {"reply": reply}


# ----------------------------------------------------
# 5. TELEGRAM WEBHOOK ENDPOINT
# ----------------------------------------------------
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN") # <---- ADD TELEGRAM BOT TOKEN
TELEGRAM_SEND_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

@app.post("/telegram_webhook")
async def telegram_webhook(request: Request):
    data = await request.json()

    if "message" not in data:
        return {"status": "ignored"}

    chat_id = data["message"]["chat"]["id"]
    user_msg = data["message"].get("text", "")

    bot_reply = chat_llm(user_msg)

    requests.post(TELEGRAM_SEND_URL, json={
        "chat_id": chat_id,
        "text": bot_reply
    })

    return {"status": "ok"}


# ----------------------------------------------------
# 6. WHATSAPP WEBHOOK ENDPOINT (Twilio)
# ----------------------------------------------------
from fastapi.responses import Response

@app.post("/whatsapp_webhook")
async def whatsapp_webhook(request: Request):
    form = await request.form()

    user_msg = form.get("Body")
    from_number = form.get("From")

    bot_reply = chat_llm(user_msg)

    xml_response = f"""
    <Response>
        <Message>{bot_reply}</Message>
    </Response>
    """

    return Response(content=xml_response, media_type="application/xml")



# ----------------------------------------------------
# 7. RUN SERVER (LOCAL)
# ----------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("llm_api:app", host="0.0.0.0", port=8000, reload=True)

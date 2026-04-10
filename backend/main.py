import os
import json
import httpx
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

app = FastAPI(title="Aurex Voice Banking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

class LoginRequest(BaseModel):
    username: str
    password: str

class ChatRequest(BaseModel):
    message: str
    history: List[dict]
    language: str = "en"
    apiKey: Optional[str] = None # Fallback if user provides it in UI

class TTSRequest(BaseModel):
    text: str
    language: str = "en"

class TransferRequest(BaseModel):
    recipient: str
    amount: float

def load_db():
    with open("mock_db.json", "r") as f:
        return json.load(f)

def save_db(db):
    with open("mock_db.json", "w") as f:
        json.dump(db, f, indent=2)

def get_user_by_token(token: str):
    if token != "mock_token_123":
        raise HTTPException(status_code=401, detail="Invalid token")
    db = load_db()
    return db["users"][0]  # Simplification for demo

@app.post("/stt")
async def stt_endpoint(file: UploadFile = File(...), language: str = Form("en-IN")):
    if not SARVAM_API_KEY:
        raise HTTPException(status_code=400, detail="SARVAM_API_KEY not set")
    
    # Map UI language to Sarvam format
    lang_map = {"en": "en-IN", "hi": "hi-IN", "ta": "ta-IN"}
    sarvam_lang = lang_map.get(language, "en-IN")

    try:
        content = await file.read()
        # Sarvam doesn't strictly validate the extension, but sending as wav is sometimes useful.
        files = {"file": ("audio.wav", content, "audio/wav")}
        data = {"language_code": sarvam_lang}
        
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.sarvam.ai/speech-to-text",
                headers={"api-subscription-key": SARVAM_API_KEY},
                files=files,
                data=data,
                timeout=15.0
            )
            if res.status_code != 200:
                print("STT Error Response:", res.text)
            res.raise_for_status()
            result = res.json()
            return {"text": result.get("transcript", "")}
    except Exception as e:
        print(f"STT Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tts")
async def tts_endpoint(req: TTSRequest):
    if not SARVAM_API_KEY:
        raise HTTPException(status_code=400, detail="SARVAM_API_KEY not set")
    
    lang_map = {"en": "en-IN", "hi": "hi-IN", "ta": "ta-IN"}
    sarvam_lang = lang_map.get(req.language, "en-IN")
    speaker_map = {"en-IN": "sumit", "hi-IN": "priya", "ta-IN": "ritu"}

    try:
        payload = {
            "text": req.text,
            "target_language_code": sarvam_lang,
            "speaker": speaker_map.get(sarvam_lang, "sumit"),
            "model": "bulbul:v3",
            "pace": 1.1,
            "speech_sample_rate": 22050,
            "output_audio_codec": "mp3",
            "enable_preprocessing": True
        }
        
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.sarvam.ai/text-to-speech/stream",
                headers={"api-subscription-key": SARVAM_API_KEY, "Content-Type": "application/json"},
                json=payload,
                timeout=15.0
            )
            if res.status_code != 200:
                print("TTS Error Response:", res.text)
            res.raise_for_status()
            
            import base64
            encoded_audio = base64.b64encode(res.content).decode('ascii')
            return {"audio_base64": encoded_audio}
    except Exception as e:
        print(f"TTS Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/auth/login")
def login(req: LoginRequest):
    db = load_db()
    for user in db["users"]:
        if user["username"] == req.username and user["password"] == req.password:
            return {"token": "mock_token_123", "name": user["name"]}
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.get("/balance")
def get_balance(authorization: str = Header(...)):
    user = get_user_by_token(authorization.replace("Bearer ", ""))
    return {"balance": user["balance"], "currency": "INR"}

@app.get("/transactions")
def get_transactions(authorization: str = Header(...)):
    user = get_user_by_token(authorization.replace("Bearer ", ""))
    return {"transactions": user["transactions"]}

@app.post("/transfer")
def process_transfer(req: TransferRequest, authorization: str = Header(...)):
    user = get_user_by_token(authorization.replace("Bearer ", ""))
    if req.amount > user["balance"]:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    db = load_db()
    # Update db
    db["users"][0]["balance"] -= req.amount
    db["users"][0]["transactions"].insert(0, {
        "id": f"tx{len(db['users'][0]['transactions'])+1}",
        "date": "2026-04-10",
        "description": f"Transfer to {req.recipient}",
        "amount": -req.amount,
        "type": "debit"
    })
    save_db(db)
    return {"status": "success", "new_balance": db["users"][0]["balance"]}

@app.post("/chat")
def chat_endpoint(req: ChatRequest, authorization: str = Header(...)):
    user = get_user_by_token(authorization.replace("Bearer ", ""))
    api_key = req.apiKey or GROQ_API_KEY
    if not api_key:
        raise HTTPException(status_code=400, detail="Groq API key not provided")
    
    client = Groq(api_key=api_key)
    
    # 1. Intent & Entity Detection Layer
    intent_prompt = f"""
    Analyze the user's message and determine the banking intent and extract entities.
    Possible intents: balance_inquiry, fund_transfer, transaction_history, other.
    If fund_transfer, extract recipient and amount (number only).
    Return ONLY JSON. Format:
    {{"intent": "intent_name", "entities": {{"amount": 0, "recipient": "name"}}}}
    User message: "{req.message}"
    """
    
    try:
        intent_res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "system", "content": "You are a JSON-only API. Parse intent and entities."}, 
                      {"role": "user", "content": intent_prompt}],
            temperature=0,
            response_format={"type": "json_object"}
        )
        
        intent_data = json.loads(intent_res.choices[0].message.content)
        intent = intent_data.get("intent", "other")
        entities = intent_data.get("entities", {})
    except Exception as e:
        print(f"Intent parsing error: {e}")
        intent = "other"
        entities = {}

    # 2. Banking Action Routing
    backend_context = ""
    backend_data = None
    if intent == "balance_inquiry":
        backend_data = get_balance(authorization)
        backend_context = f"The user's current balance is ₹{backend_data['balance']}."
    elif intent == "transaction_history":
        backend_data = get_transactions(authorization)
        tx_list = [f"{t['date']}: {t['description']} (₹{t['amount']})" for t in backend_data["transactions"][:3]]
        backend_context = f"Recent transactions: {', '.join(tx_list)}."
    elif intent == "fund_transfer":
        amount = entities.get("amount")
        recipient = entities.get("recipient")
        if amount and recipient:
            try:
                res = process_transfer(TransferRequest(recipient=recipient, amount=float(amount)), authorization)
                backend_data = res
                backend_context = f"Successfully transferred ₹{amount} to {recipient}. New balance: ₹{res['new_balance']}."
            except Exception as e:
                backend_context = f"Transfer failed: {str(e)}."
                backend_data = {"error": str(e)}
        else:
            backend_context = "Ask for recipient and amount to complete the transfer."

    # 3. Response Generation (Multilingual)
    lang_instruction = ""
    if req.language == "hi":
        lang_instruction = "Respond entirely in Hindi (Devanagari script)."
    elif req.language == "ta":
        lang_instruction = "Respond entirely in Tamil."
    else:
        lang_instruction = "Respond in English."
    
    sys_prompt = f"""You are Aurex, a smart voice banking assistant.
The user is named {user["name"]}.
Current Intent: {intent}
Backend Context: {backend_context}
{lang_instruction}
Be concise, polite, and conversational. Do not output raw JSON, give a natural spoken response."""

    messages = [{"role": "system", "content": sys_prompt}] + req.history[-6:] + [{"role": "user", "content": req.message}]
    
    try:
        chat_res = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            temperature=0.5,
            max_tokens=250
        )
        response_text = chat_res.choices[0].message.content
    except Exception as e:
        response_text = "I'm having trouble processing that right now."

    return {
        "text": response_text,
        "intent": intent,
        "data": backend_data,
        "language": req.language
    }

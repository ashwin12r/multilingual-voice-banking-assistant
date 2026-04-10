import os
import json
import httpx
import io
import pandas as pd
import pdfplumber
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Header, UploadFile, File, Form, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv

from sqlalchemy.orm import Session
from database import get_db, engine, Base
from models import User, Transaction, EMI
import auth

env_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(env_path)

# Ensure DB tables exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Aurex Voice Banking API")

@app.on_event("startup")
def seed_test_user():
    db = Session(engine)
    if not db.query(User).filter(User.email == "ashwin@aurex.com").first():
        from auth import get_password_hash
        usr = User(name="Ashwin", email="ashwin@aurex.com", password_hash=get_password_hash("password123"), balance=114500.0)
        db.add(usr)
        db.commit()
        db.close()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

class ChatRequest(BaseModel):
    message: str
    history: List[dict]
    language: str = "en"
    apiKey: Optional[str] = None

class TTSRequest(BaseModel):
    text: str
    language: str = "en"

class TransferRequest(BaseModel):
    recipient: str
    amount: float

# --- UTILS ---
def get_user_from_header(authorization: str = Header(...), db: Session = Depends(get_db)):
    if not authorization or not authorization.startswith("Bearer "):
        # Fallback to mock mapping if needed for older clients
        if authorization == "mock_token_123":
            usr = db.query(User).filter(User.email == "ashwin@aurex.com").first()
            if usr: return usr
        raise HTTPException(status_code=401)
    
    token = authorization.replace("Bearer ", "")
    if token == "mock_token_123":
        usr = db.query(User).filter(User.email == "ashwin@aurex.com").first()
        if not usr:
            # Seed mock user
            from auth import get_password_hash
            usr = User(name="Ashwin", email="ashwin@aurex.com", password_hash=get_password_hash("password123"), balance=114500.0)
            db.add(usr)
            db.commit()
            db.refresh(usr)
        return usr
        
    return auth.get_current_user(token, db)


# --- STT / TTS ---
@app.post("/stt")
async def stt_endpoint(file: UploadFile = File(...), language: str = Form("en-IN")):
    if not SARVAM_API_KEY: raise HTTPException(status_code=400)
    lang_map = {"en": "en-IN", "hi": "hi-IN", "ta": "ta-IN"}
    sarvam_lang = lang_map.get(language, "en-IN")
    try:
        content = await file.read()
        files = {"file": ("audio.wav", content, "audio/wav")}
        data = {"language_code": sarvam_lang}
        async with httpx.AsyncClient() as client:
            res = await client.post("https://api.sarvam.ai/speech-to-text", headers={"api-subscription-key": SARVAM_API_KEY}, files=files, data=data, timeout=15.0)
            res.raise_for_status()
            return {"text": res.json().get("transcript", "")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tts")
async def tts_endpoint(req: TTSRequest):
    if not SARVAM_API_KEY: raise HTTPException(status_code=400)
    lang_map = {"en": "en-IN", "hi": "hi-IN", "ta": "ta-IN"}
    sarvam_lang = lang_map.get(req.language, "en-IN")
    speaker_map = {"en-IN": "sumit", "hi-IN": "priya", "ta-IN": "ritu"}
    try:
        payload = {
            "text": req.text, "target_language_code": sarvam_lang, "speaker": speaker_map.get(sarvam_lang, "sumit"),
            "model": "bulbul:v3", "pace": 1.1, "speech_sample_rate": 22050, "output_audio_codec": "mp3", "enable_preprocessing": True
        }
        async with httpx.AsyncClient() as client:
            res = await client.post("https://api.sarvam.ai/text-to-speech/stream", headers={"api-subscription-key": SARVAM_API_KEY, "Content-Type": "application/json"}, json=payload, timeout=15.0)
            res.raise_for_status()
            import base64
            return {"audio_base64": base64.b64encode(res.content).decode('ascii')}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# --- BANKING DATA Endpoints (Driven by DB) ---
@app.get("/balance")
def get_balance(user: User = Depends(get_user_from_header), db: Session = Depends(get_db)):
    txs = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    net = sum([t.amount for t in txs if t.type.lower() == "credit"]) - sum([t.amount for t in txs if t.type.lower() == "debit"])
    return {"balance": user.balance + net, "currency": "INR"}

@app.get("/transactions")
def get_transactions(user: User = Depends(get_user_from_header), db: Session = Depends(get_db)):
    txs = db.query(Transaction).filter(Transaction.user_id == user.id).order_by(Transaction.id.desc()).limit(15).all()
    return {"transactions": [{"id": t.id, "date": t.date, "description": t.description, "amount": t.amount, "type": t.type, "category": t.category} for t in txs]}

@app.post("/transfer")
def process_transfer(req: TransferRequest, user: User = Depends(get_user_from_header), db: Session = Depends(get_db)):
    current_b = get_balance(user, db)["balance"]
    if req.amount > current_b:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    
    t = Transaction(user_id=user.id, date="2026-04-10", description=f"Transfer to {req.recipient}", amount=req.amount, type="debit", category="Transfer")
    db.add(t)
    db.commit()
    return {"status": "success", "new_balance": current_b - req.amount}

# Mocks for Dashboard cards
@app.get("/credit-score")
def get_credit_score(user: User = Depends(get_user_from_header)):
    return {"score": 780, "status": "Excellent", "suggestion": "Pay upcoming credit card bill on time."}

@app.get("/emi")
def get_emis(user: User = Depends(get_user_from_header), db: Session = Depends(get_db)):
    emis = db.query(EMI).filter(EMI.user_id == user.id).all()
    if not emis:
        emis = [EMI(user_id=user.id, title="Car Loan", amount=12500, due_date="2026-04-15", status="Pending")]
        db.add_all(emis)
        db.commit()
    pending = sum(e.amount for e in emis if e.status == "Pending")
    return {"emis": [{"title": e.title, "amount": e.amount, "dueDate": e.due_date, "status": e.status} for e in emis], "total_pending": pending}


# --- UPLOAD & AI ENGINE ---
MAX_FILE_SIZE = 5 * 1024 * 1024 # 5MB

def parse_transactions_with_llm(raw_text: str):
    prompt = f"""
    Parse the following raw bank statement text into a valid JSON array of objects. 
    Each object must have exactly these keys: "date" (YYYY-MM-DD), "description", "amount" (positive float), "type" ("credit" or "debit"), and "category" (e.g., Food, Utility, Transport).
    Text: {raw_text[:3000]}
    Return ONLY RAW JSON array of objects. No markdown formatting or extra text.
    """
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": prompt}], temperature=0)
    content = response.choices[0].message.content.strip()
    if content.startswith("```json"): content = content[7:-3]
    try:
        return json.loads(content)
    except:
        return []

@app.post("/upload-statement")
async def upload_statement(file: UploadFile = File(...), user: User = Depends(get_user_from_header), db: Session = Depends(get_db)):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
        
    extracted_data = []

    try:
        if file.filename.endswith(".csv"):
            df = pd.read_csv(io.BytesIO(content))
            for _, row in df.iterrows():
                amt = float(row.get("Amount", 0))
                extracted_data.append({
                    "date": str(row.get("Date", "2026-04-10")), "description": str(row.get("Description", "Unknown")), 
                    "amount": abs(amt), "type": "credit" if amt > 0 else "debit", "category": "Uncategorized"
                })
        elif file.filename.endswith(".pdf"):
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
                extracted_data = parse_transactions_with_llm(text)
    except Exception as e:
        print("Upload parsing error:", e)
        raise HTTPException(status_code=400, detail="Failed to process document")
    
    # Save to SQLite
    added = 0
    for t_data in extracted_data:
        t = Transaction(user_id=user.id, **t_data)
        db.add(t)
        added += 1
    db.commit()
    
    return {"message": f"Successfully parsed and saved {added} transactions.", "count": added}

@app.get("/insights")
def get_insights(user: User = Depends(get_user_from_header), db: Session = Depends(get_db)):
    txs = db.query(Transaction).filter(Transaction.user_id == user.id).all()
    if not txs:
        return {"alert": "No transactions analyzed yet. Please upload a bank statement in your profile."}
        
    summary_str = "\n".join([f"{t.date}: {t.description} | {t.amount} ({t.type}) | Cat: {t.category}" for t in txs[-20:]])
    prompt = f"""
    You are an expert AI Financial advisor. Look at user's recent transactions:
    {summary_str}
    
    Return exactly ONE brief sentence of actionable insight or alert. 
    Examples: 'You spent heavily on Swiggy this week.', 'Transport spending increased by 20%.'
    Output just the sentence. No quotes.
    """
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role":"user", "content": prompt}], temperature=0.7)
    return {"alert": response.choices[0].message.content.strip().replace('"', '')}

# --- AI CHATBOT ENGINE ---
@app.post("/chat")
def chat_endpoint(req: ChatRequest, user: User = Depends(get_user_from_header), db: Session = Depends(get_db)):
    api_key = req.apiKey or GROQ_API_KEY
    if not api_key: raise HTTPException(status_code=400, detail="Groq API key not provided")
    client = Groq(api_key=api_key)
    
    # 1. Intent Detection
    intent_prompt = f"""
    Analyze the user's message and determine the banking intent and extract entities.
    Intents: balance_inquiry, fund_transfer, transaction_history, spending_insights, emi_status, other.
    If fund_transfer, extract recipient and amount (number only).
    Return ONLY JSON: {{"intent": "intent_name", "entities": {{"amount": 0, "recipient": "name"}}}}
    User message: "{req.message}"
    """
    try:
        intent_res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=[{"role": "user", "content": intent_prompt}], temperature=0, response_format={"type": "json_object"})
        intent_data = json.loads(intent_res.choices[0].message.content)
        intent = intent_data.get("intent", "other")
        entities = intent_data.get("entities", {})
    except Exception:
        intent = "other"
        entities = {}

    # 2. Banking Action Routing
    backend_context, backend_data = "", None
    if intent == "balance_inquiry":
        backend_data = get_balance(user, db)
        backend_context = f"Balance: ₹{backend_data['balance']}."
    elif intent == "transaction_history":
        backend_data = get_transactions(user, db)
        tx_list = [f"{t['date']}: {t['description']} (₹{t['amount']})" for t in backend_data["transactions"][:3]]
        backend_context = f"Recent txs: {', '.join(tx_list)}."
    elif intent == "spending_insights":
        backend_data = get_insights(user, db)
        backend_context = f"Insight: {backend_data['alert']}."
    elif intent == "fund_transfer":
        amount, recipient = entities.get("amount"), entities.get("recipient")
        if amount and recipient:
            try:
                res = process_transfer(TransferRequest(recipient=recipient, amount=float(amount)), user, db)
                backend_data, backend_context = res, f"Transferred ₹{amount} to {recipient}. New balance: ₹{res['new_balance']}."
            except Exception as e:
                backend_data, backend_context = {"error": str(e)}, f"Transfer failed: {str(e)}."
        else:
            backend_context = "Ask for recipient and amount."

    # 3. Response Generation
    lang_inst = "Respond in English."
    if req.language == "hi": lang_inst = "Respond entirely in Hindi (Devanagari script)."
    if req.language == "ta": lang_inst = "Respond entirely in Tamil."
    
    sys_prompt = f"You are Aurex, a smart voice banking assistant. User is {user.name}. Intent: {intent}. Context: {backend_context}. {lang_inst} Be concise, human-like, polite. No raw JSON."
    messages = [{"role": "system", "content": sys_prompt}] + req.history[-6:] + [{"role": "user", "content": req.message}]
    
    try:
        chat_res = client.chat.completions.create(model="llama-3.1-8b-instant", messages=messages, temperature=0.5, max_tokens=250)
        response_text = chat_res.choices[0].message.content
    except Exception:
        response_text = "I'm having trouble processing that right now."

    return {"text": response_text, "intent": intent, "data": backend_data, "language": req.language}

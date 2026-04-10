# Aurex Multilingual Voice Banking System

A complete end-to-end prototype of a Voice AI Banking Assistant featuring intent routing, multi-language support (English, Hindi, Tamil), real-time STT/TTS (via Sarvam AI), JWT Authentication, and a FastAPI backend routing LLM calls over Groq's LLaMA 3.1 model.

## Architecture & Tech Stack
* **Frontend**: Next.js (App Router), React, Tailwind CSS, Zustand
* **Backend**: FastAPI, SQLAlchemy (SQLite), JWT Authentication (passlib/bcrypt)
* **AI/Parsing**: Groq API, Sarvam AI, pdfplumber, pandas

## Folder Structure

```text
dsproject/
 ├── frontend/                  # Next.js UI Frontend SPA
 ├── backend/
 │    ├── main.py               # FastAPI server and AI/Routing logic
 │    ├── auth.py               # JWT and Bcrypt authentication logic
 │    ├── database.py           # SQLite connection and models
 │    ├── aurex.db              # Auto-generated SQLite Database
 │    ├── requirements.txt      # Python dependencies
 │    └── .env                  # (You must create this)
 └── README.md                  # This file
```

## How to Run

### Step 1: Backend Setup
1. CD into the backend directory:
   ```bash
   cd backend
   ```
2. Install Python requirements:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: `bcrypt` must be exactly version 3.2.2 to prevent passlib crashes).*
3. Setup Environment Variables:
   - Create a `.env` file in the `backend` folder and add your APIs:
     ```env
     GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
     SARVAM_API_KEY=your_sarvam_api_key_here
     ```
4. Run the FastAPI Server:
   ```bash
   python -m uvicorn main:app --reload
   ```
   *The server will start at `http://localhost:8000`. Upon its first startup, it will auto-seed the database with the test user.*

### Step 2: Frontend Setup
1. CD into the frontend directory:
   ```bash
   cd ../frontend
   ```
2. Install Node dependencies:
   ```bash
   npm install
   ```
3. Start the Next.js development server:
   ```bash
   npm run dev
   ```
   *The UI will start at `http://localhost:3000`.*

### Step 3: Usage
1. Visit `http://localhost:3000` in your browser.
2. **Log In** using the auto-seeded credentials:
   - **Email**: `ashwin@aurex.com`
   - **Password**: `password123`
3. On the Dashboard, you can click **Upload Statement** to parse a Bank Statement PDF/CSV for AI insights.
4. Click **Ask Aurex AI** to test voice commands:
   - "What is my balance?"
   - "Show my recent transactions"
   - "Transfer 5000 to Vishal"
5. Use the drop-down on the top right to switch between English, Hindi, and Tamil interactions.

## Troubleshooting & Error History (Session Log)

During development, several complex architectural errors were resolved:

### 1. Bcrypt & Passlib 72-Byte Limit Crash
* **Issue**: Uvicorn kept failing with `ValueError: password cannot be longer than 72 bytes` and an `AttributeError: module 'bcrypt' has no attribute '__about__'`.
* **Solution**: Newer versions of `bcrypt` (>4.0.0) broke compatibility with `passlib`. Hard-downgraded and pinned `bcrypt==3.2.2` within the virtual environment.

### 2. Groq AI Model Deprecation (400 Bad Request)
* **Issue**: The PDF upload endpoint crashed with `model_decommissioned` for `llama3-8b-8192`.
* **Solution**: Updated the Groq API payload across `main.py` (both document parser and AI insights generator) to utilize the active `llama-3.1-8b-instant` model.

### 3. Frontend Browser API Override
* **Issue**: Native browser speech recognition failed to map Indian languages correctly, returning broken English while speaking Tamil/Hindi.
* **Solution**: Stripped out the Web Speech API. Built a unified audio pipeline utilizing `MediaRecorder` API to push raw `.wav` buffers to Sarvam AI's STT and fetched Base64 MP3 buffers back for playback.

### 4. Sarvam AI Streaming Migrations
* **Issue**: `bulbul:v3` model required an exclusively streamlined playback endpoint and strictly incompatible speaker identifiers.
* **Solution**: Migrated to `api.sarvam.ai/text-to-speech/stream`. Mapped supported Gen-3 speakers (`sumit`, `priya`, `ritu`).

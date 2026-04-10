# Aurex Multilingual Voice Banking System

A complete end-to-end prototype of a Voice AI Banking Assistant featuring intent routing, multi-language support (English, Hindi, Tamil), real-time STT/TTS (via Sarvam AI), and a FastAPI backend routing LLM calls over Groq's LLaMA 3 model.

## Folder Structure

```text
dsproject/
 ├── test.html                  # Main frontend SPA (incorporates HTML/CSS/JS)
 ├── README.md                  # This file
 └── backend/
      ├── main.py               # FastAPI server with LLM/routing logic
      ├── mock_db.json          # Simple file-based mock database
      ├── requirements.txt      # Python dependencies
      └── .env                  # (You must create this)
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
3. Setup Environment Variables:
   - Create a `.env` file in the `backend` folder and add your APIs:
     ```env
     GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
     SARVAM_API_KEY=your_sarvam_api_key_here
     ```
   *(Note: You can also paste the Groq API key directly in the web UI, but Sarvam requires the .env).*

4. Run the FastAPI Server:
   ```bash
   python -m uvicorn main:app --reload
   ```
   *The server will start at `http://localhost:8000`.*

### Step 2: Frontend Setup
1. Simply double click `test.html` or open it in a Live Server or any browser (Chrome/Edge recommended for best Web Speech API support).
2. Because of Cross-Origin policies with the microphone, it is strongly recommended you serve it using a local HTTP server. For example:
   ```bash
   python -m http.server 3000
   ```
   Then visit `http://localhost:3000/test.html`

### Step 3: Usage
1. Provide the Groq API key in the UI field or ensure your backend `.env` is loaded.
2. Login with User: `ashwin`, Pass: `password123`.
3. Try asking:
   - "What is my balance?"
   - "Show my recent transactions"
   - "Transfer 5000 to Vishal"
4. You can also change the language dropdown to speak/listen in Hindi or Tamil.
5. While the AI speaks, you can use the Play/Pause and Stop buttons near the chat header to control playback, or simply tap the mic to interrupt!

## Troubleshooting & Error History (Session Log)

During the development and integration of the Sarvam AI and FastAPI backend, we encountered and resolved several complex errors:

### 1. Backend Dependency & Execution Errors
* **Rust Build Errors on Install**: Encountered `pip install` failures due to outdated pinned dependencies trying to compile Rust binaries for Python 3.13. **Solution**: Upgraded `pydantic>=2.7.0` and `fastapi>=0.110.0` in `requirements.txt`.
* **Uvicorn Not Recognized**: Windows PowerShell failed to recognize the `uvicorn` command. **Solution**: Adjusted the startup command to launch via the Python module: `python -m uvicorn main:app --reload`.
* **.env Context Pathing**: The backend threw 400 errors because `SARVAM_API_KEY` was empty. The `load_dotenv()` was failing based on the Terminal's current working directory. **Solution**: Hardcoded the environment path dynamically using `os.path.join(os.path.dirname(__file__), '.env')`.

### 2. Frontend Browser API Override
* **Tamil Translated as English**: When speaking Tamil, the frontend transcribed it as broken English (e.g., "you know the bank balance available"). This occurred because the frontend was still using the browser's native `window.SpeechRecognition` (hardcoded to English) and native `window.speechSynthesis` instead of our actual Sarvam API endpoints.
* **Solution**: Completely stripped out the Web Speech API from `test.html`. Replaced it with the `MediaRecorder` API to capture `.wav` microphone chunks and POST them to our `/stt` backend endpoint. Replaced TTS playback with an HTML `Audio()` object playing Base64 MP3 data from our `/tts` endpoint.

### 3. Sarvam AI API Migrations (400 Bad Requests)
* **Legacy Speaker Deprecation**: The TTS endpoint returned `Speaker 'pallavi' is not recognized`. Sarvam retired older voice footprints. **Solution**: Updated the `speaker_map` to newer voices (`anushka`, `amit`, `kavitha`).
* **Legacy Model Deprecation**: The TTS endpoint returned `Input should be 'bulbul:v2' or 'bulbul:v3'`. The old `aura-tts-phx` model was deactivated by Sarvam. **Solution**: Upgraded the payload to use `model: "bulbul:v3"`.
* **Streaming Endpoint Requirement**: The standard `/text-to-speech` endpoint rejected the `bulbul:v3` structure. **Solution**: Migrated the API call to `https://api.sarvam.ai/text-to-speech/stream`. Restructured the payload to use `"text"` (instead of `"inputs"`), `"speech_sample_rate": 22050`, and `"output_audio_codec": "mp3"`. We then buffered the streamed MP3 response in FastAPI and encoded it to Base64 for the frontend.
* **Incompatible Speakers for Bulbul V3**: The TTS API returned `Speaker 'anushka' is not compatible with model bulbul:v3`. Sarvam's new V3 model has a distinct set of approved speakers. **Solution**: Successfully mapped the final compatible V3 speakers:
  * **Tamil (`ta-IN`)**: `ritu`
  * **Hindi (`hi-IN`)**: `priya`
  * **English (`en-IN`)**: `sumit`

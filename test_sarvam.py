import asyncio
import httpx
import os
from dotenv import load_dotenv

load_dotenv('backend/.env')

SARVAM_API_KEY = os.getenv("SARVAM_API_KEY")

async def test_tts():
    print("Testing Sarvam TTS...")
    payload = {
        "inputs": ["வணக்கம், இது ஒரு சோதனை."], # Tamil text "Hello, this is a test"
        "target_language_code": "ta-IN",
        "speaker": "pallavi",
        "pitch": 0,
        "pace": 1.0,
        "loudness": 1.5,
        "speech_sample_rate": 8000,
        "enable_preprocessing": True,
        "model": "bulbul:v3"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.sarvam.ai/text-to-speech",
                headers={"api-subscription-key": SARVAM_API_KEY, "Content-Type": "application/json"},
                json=payload
            )
            if not res.is_success:
                print(res.text)
            res.raise_for_status()
            result = res.json()
            if "audios" in result:
                print("✅ TTS SUCCESS! Received audio string.")
                return True
            else:
                print("❌ TTS Response parsing failed:", result)
                return False
    except Exception as e:
        print("❌ TTS Error Failed:", e)
        return False

if __name__ == "__main__":
    if not SARVAM_API_KEY:
        print("No SARVAM_API_KEY found")
    else:
        asyncio.run(test_tts())
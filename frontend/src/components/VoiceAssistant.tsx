'use client';
import { useStore } from '../store/useStore';
import { useState, useRef, useEffect } from 'react';

export default function VoiceAssistant() {
  const { isListening, isSpeaking, setListening, setSpeaking, activeLanguage } = useStore();
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<BlobPart[]>([]);

  const toggleMic = async () => {
     if (isListening) {
         stopRecording();
     } else {
         startRecording();
     }
  };

  const startRecording = async () => {
    if (isSpeaking) audioRef.current?.pause();
    
    try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorderRef.current = new MediaRecorder(stream);
        audioChunksRef.current = [];

        mediaRecorderRef.current.ondataavailable = e => {
            if (e.data.size > 0) audioChunksRef.current.push(e.data);
        };

        mediaRecorderRef.current.onstop = async () => {
            const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
            const formData = new FormData();
            formData.append('file', audioBlob, 'audio.wav');
            formData.append('language', activeLanguage);

            setListening(false);

            try {
                const res = await fetch('http://localhost:8000/stt', {
                    method: 'POST',
                    body: formData
                });
                const sttData = await res.json();
                
                // Then Chat Endpoint...
                const chatRes = await fetch('http://localhost:8000/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer mock_token_123' },
                    body: JSON.stringify({ message: sttData.text, history: [], language: activeLanguage })
                });
                const chatData = await chatRes.json();

                // Then TTS Endpoint...
                const ttsRes = await fetch('http://localhost:8000/tts', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ text: chatData.text, language: activeLanguage })
                });
                const ttsData = await ttsRes.json();
                playResponse(ttsData.audio_base64);

            } catch (e) {
                console.error(e);
            }
        };

        mediaRecorderRef.current.start();
        setListening(true);
    } catch(e) {
        console.error("Mic denied:", e);
    }
  }

  const stopRecording = () => {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
          mediaRecorderRef.current.stop();
          mediaRecorderRef.current.stream.getTracks().forEach(t => t.stop());
      }
  }

  const playResponse = (base64audio: string) => {
      setSpeaking(true);
      const audio = new Audio(`data:audio/mp3;base64,${base64audio}`);
      audioRef.current = audio;
      audio.onended = () => setSpeaking(false);
      audio.play();
  };

  return (
    <div className="fixed bottom-8 right-8 flex items-center gap-4 bg-gray-800 p-4 rounded-full border border-gray-700 shadow-xl">
      {isSpeaking && (
         <button onClick={() => { audioRef.current?.pause(); setSpeaking(false); }} className="text-yellow-500 font-bold px-4">⏸ Pause</button>
      )}
      <button 
         onClick={toggleMic} 
         className={`p-4 rounded-full text-white text-xl ${isListening ? 'bg-red-500 animate-pulse' : 'bg-teal-500 hover:bg-teal-400'}`}>
         {isListening ? '⏹️' : '🎙️'}
      </button>
      <div className="pl-2 text-sm font-medium pr-4 text-white">Ask Aurex AI</div>
    </div>
  );
}
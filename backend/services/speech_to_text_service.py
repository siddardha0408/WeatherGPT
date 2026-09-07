"""
Speech to Text Service for WeatherGPT.
Provides server-side audio transcription fallback using SpeechRecognition or Gemini Multimodal.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("weather_gpt.stt_service")


async def transcribe_audio_bytes(audio_bytes: bytes, lang_hint: str = "en-IN") -> Dict[str, Any]:
    """
    Transcribe audio bytes to text string.
    """
    if not audio_bytes:
        return {"error": "No audio content received", "transcript": ""}

    try:
        # Fallback to speech_recognition if installed
        import speech_recognition as sr
        import io

        recognizer = sr.Recognizer()
        with io.BytesIO(audio_bytes) as audio_file:
            with sr.AudioFile(audio_file) as source:
                audio_data = recognizer.record(source)
                text = recognizer.recognize_google(audio_data, language=lang_hint)
                return {"transcript": text, "status": "success"}

    except Exception as exc:
        logger.warning(f"STT transcription exception: {exc}")
        return {
            "error": "Server-side voice transcription failed. Browser Web Speech API is the recommended client interface.",
            "details": str(exc),
            "transcript": ""
        }

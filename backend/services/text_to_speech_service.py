"""
Text to Speech Service for WeatherGPT.
Provides helper mappings for browser speech synthesis and server audio metadata.
"""

VOICE_LANGUAGE_MAP = {
    "en": "en-IN",
    "te": "te-IN",
    "te-Latn": "te-IN",
    "hi": "hi-IN",
    "hi-Latn": "hi-IN",
    "ta": "ta-IN",
    "kn": "kn-IN",
    "ml": "ml-IN",
    "bn": "bn-IN",
    "gu": "gu-IN",
    "mr": "mr-IN",
    "pa": "pa-IN",
    "ur": "ur-IN"
}


def get_speech_locale(lang_code: str) -> str:
    """
    Map ISO language code to appropriate regional Indian SpeechSynthesis locale.
    """
    return VOICE_LANGUAGE_MAP.get(lang_code, "en-IN")

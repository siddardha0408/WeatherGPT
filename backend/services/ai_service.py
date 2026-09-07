"""
AI Service for WeatherGPT.
Integrates Google Gemini API for natural-language explanations and multilingual conversational answers.
Uses strict ground-truth prompt engineering to prevent hallucinations.
Includes seamless deterministic fallback when Gemini API is unavailable or rate-limited (HTTP 429).
"""

import os
import logging
from typing import Dict, Any, Optional
import google.generativeai as genai

logger = logging.getLogger("weather_gpt.ai_service")

# Initialize Gemini client if API key is present
_GEMINI_INITIALIZED = False
_GEMINI_KEY = os.getenv("GEMINI_API_KEY", "").strip()

if _GEMINI_KEY:
    try:
        genai.configure(api_key=_GEMINI_KEY)
        _GEMINI_INITIALIZED = True
        logger.info("Google Gemini API client successfully configured.")
    except Exception as exc:
        logger.warning(f"Failed to initialize Google Gemini client: {exc}")


def generate_deterministic_explanation(
    payload: Dict[str, Any],
    lang_code: str = "en",
    question: str = ""
) -> str:
    """
    Generate a clear, natural-sounding conversational weather summary purely from deterministic data.
    Used as primary or fallback when Gemini API is offline, missing, or rate limited.
    """
    loc = payload.get("location", {}).get("city", "your location")
    current = payload.get("current", {})
    temp = current.get("temperature", 0.0)
    feels_like = current.get("feels_like", temp)
    cond = current.get("condition", "clear")
    humidity = current.get("humidity", 0)
    precip_prob = current.get("precipitation_probability", 0)
    wind_speed = current.get("wind_speed", 0.0)
    uv = current.get("uv_index", 0.0)

    intel = payload.get("weather_intelligence", {})
    overall_risk = intel.get("overall_risk", {}).get("level", "Low")
    advisories = intel.get("advisories", [])

    agri = payload.get("agriculture_advisory", {})
    spraying = agri.get("spraying_suitability", {}) if agri else None

    imd = payload.get("official_warning", {})
    imd_level = imd.get("level", "Green") if imd else "Green"

    # Multilingual Telugu Fallback
    if "te" in lang_code:
        if spraying:
            suit = spraying.get("suitability", "Caution")
            return (
                f"{loc}లో వాతావరణం: గరిష్ట ఉష్ణోగ్రత {temp}°C, వర్షం వచ్చే అవకాశం {precip_prob}%, గాలి వేగం {wind_speed} km/h. "
                f"పురుగుమందుల పిచికారీకి: {suit}. {spraying.get('recommendation', '')}"
            )
        return (
            f"{loc}లో ప్రస్తుత ఉష్ణోగ్రత {temp}°C (అనిపించేది {feels_like}°C), వాతావరణం {cond}గా ఉంది. "
            f"తేమ శాతం {humidity}%, వర్షం అవకాశం {precip_prob}%. గాలి వేగం {wind_speed} km/h. "
            f"మొత్తం వాతావరణ ప్రమాదం: {overall_risk}."
        )

    # Multilingual Hindi Fallback
    if "hi" in lang_code:
        if spraying:
            suit = spraying.get("suitability", "Caution")
            return (
                f"{loc} में मौसम: तापमान {temp}°C, बारिश की संभावना {precip_prob}%, हवा की गति {wind_speed} km/h. "
                f"कीटनाशक छिड़काव की स्थिति: {suit}."
            )
        return (
            f"{loc} में वर्तमान तापमान {temp}°C है (महसूस {feels_like}°C), मौसम {cond} है। "
            f"आर्द्रता {humidity}% और बारिश की संभावना {precip_prob}% है। हवा {wind_speed} km/h से चल रही है।"
        )

    # Agriculture specific
    if spraying:
        suitability = spraying.get("suitability", "Caution")
        rec = spraying.get("recommendation", "")
        return (
            f"Agricultural Weather Assessment for {loc}: Spraying operations are rated as '{suitability}'. "
            f"Rain probability is {precip_prob}%, expected precipitation is {spraying.get('precip_sum', 0):.1f} mm, "
            f"and wind speed is {wind_speed:.1f} km/h. {rec}"
        )

    # Historical / Climate specific
    if "climate_trend" in payload:
        trend_info = payload["climate_trend"]
        rain_tr = trend_info.get("rainfall_trend", {}).get("trend", "stable")
        pct = trend_info.get("rainfall_trend", {}).get("percentage_change", 0.0)
        return (
            f"Climate Analysis for {loc} ({trend_info.get('period', '')}): Annual rainfall shows a {rain_tr} tendency "
            f"with a {pct:+.1f}% change across {trend_info.get('years_analyzed', 0)} years. "
            "Note that multi-decadal observations are standard for formal climate conclusions."
        )

    if "historical_weather" in payload:
        hw = payload["historical_weather"]
        st = hw.get("statistics", {})
        return (
            f"Historical Weather for {loc} ({hw.get('start_date', '')} to {hw.get('end_date', '')}): "
            f"Total precipitation was {st.get('total_precipitation_mm', 0):.1f} mm, maximum temperature reached "
            f"{st.get('max_temperature', 0):.1f}°C, and average temperature was {st.get('avg_temperature', 0):.1f}°C."
        )

    # Default English Conversational Answer
    adv_text = f" {advisories[0]}" if advisories else ""
    imd_text = f" Official IMD status is {imd_level}." if imd_level != "Green" and imd_level != "Unavailable" else ""

    return (
        f"In {loc}, it is currently {temp:.1f}°C (feels like {feels_like:.1f}°C) with {cond.lower()} skies. "
        f"Humidity is {humidity}%, precipitation probability is {precip_prob}%, and winds are light at {wind_speed:.1f} km/h. "
        f"Overall weather risk is {overall_risk}.{adv_text}{imd_text}"
    )


async def generate_ai_explanation(
    question: str,
    payload: Dict[str, Any],
    lang_code: str = "en",
    lang_name: str = "English"
) -> str:
    """
    Generate conversational answer using Gemini with strict factual grounding.
    Falls back gracefully to deterministic explanation if Gemini fails or is unconfigured.
    """
    api_key = os.getenv("GEMINI_API_KEY", "").strip() or _GEMINI_KEY
    if not api_key:
        logger.info("No GEMINI_API_KEY provided; using deterministic conversational synthesis.")
        return generate_deterministic_explanation(payload, lang_code, question)

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash")

        system_instruction = (
            "You are WeatherGPT, an expert AI meteorological intelligence and decision support system. "
            "Your task is to answer the user's weather question conversationally, accurately, and concisely. "
            "STRICT RULES:\n"
            "1. Rely ONLY on the provided structured meteorological data below.\n"
            "2. DO NOT invent, hallucinate, or alter any temperatures, percentages, or measurements.\n"
            "3. If a specific metric is missing in the data, state clearly that it is unavailable.\n"
            "4. Provide clear actionable advice (e.g. umbrella recommendations, UV protection, spraying suitability).\n"
            f"5. Answer in the requested language: {lang_name} ({lang_code}).\n"
            "6. Keep the response friendly, professional, and within 2 to 4 sentences."
        )

        prompt = f"""
{system_instruction}

User Question: "{question}"

Structured Meteorological Data:
{payload}

Provide your conversational WeatherGPT answer below:
"""

        response = await model.generate_content_async(
            prompt,
            generation_config=genai.types.GenerationConfig(
                temperature=0.2,
                max_output_tokens=300
            )
        )

        if response and response.text:
            return response.text.strip()
        else:
            return generate_deterministic_explanation(payload, lang_code, question)

    except Exception as exc:
        logger.warning(f"Gemini generation fallback triggered ({exc}). Serving deterministic response.")
        return generate_deterministic_explanation(payload, lang_code, question)

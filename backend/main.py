"""
WeatherGPT — AI Weather Intelligence & Decision Support Platform.
Production FastAPI Application.
"""

import os
import time
import logging
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from fastapi import FastAPI, Query, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

# Load environment configuration
load_dotenv()

from services.weather_service import (
    geocode_location,
    reverse_geocode,
    fetch_weather_data,
    get_wmo_condition
)
from services.query_engine import parse_query
from services.intelligence_service import synthesize_weather_intelligence
from services.agriculture_service import generate_agricultural_advisory
from services.history_service import fetch_historical_weather
from services.climate_trend_service import analyze_climate_trend
from services.imd_warning_service import fetch_imd_warnings
from services.ai_service import generate_ai_explanation, generate_deterministic_explanation
from services.language_service import detect_language
from services.text_to_speech_service import get_speech_locale

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("weather_gpt")

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("WeatherGPT backend starting up...")
    yield
    logger.info("WeatherGPT backend shutting down...")


app = FastAPI(
    title="WeatherGPT — AI Weather Intelligence & Decision Support",
    description="Conversational weather intelligence, decision support, agricultural advisories, and IMD official alerts.",
    version="1.0.0",
    lifespan=lifespan
)

# Mount static frontend assets
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


@app.get("/app")
async def serve_app():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {"error": "Frontend index.html not found"}


# Configure CORS
cors_origins_env = os.getenv("CORS_ORIGINS", "*")
origins = [orig.strip() for orig in cors_origins_env.split(",") if orig.strip()]
if not origins or origins == ["*"]:
    origins = [
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Open in local/dev to ensure frontend seamless communication
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic request models
class AskRequest(BaseModel):
    question: str = Field(..., description="The natural language weather query")
    latitude: Optional[float] = Field(None, description="User's current GPS latitude")
    longitude: Optional[float] = Field(None, description="User's current GPS longitude")
    city: Optional[str] = Field(None, description="Previously selected city name")
    language: Optional[str] = Field("en", description="Preferred output language")


# Global safe exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error processing {request.method} {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "We couldn't retrieve the weather intelligence right now.",
            "details": "The meteorological or intelligence service is temporarily busy. Please try again shortly."
        }
    )


@app.get("/")
async def root():
    index_file = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_file):
        return FileResponse(index_file)
    return {
        "service": "WeatherGPT — AI Weather Intelligence & Decision Support",
        "version": "1.0.0",
        "status": "online",
        "docs_url": "/docs",
        "health_url": "/health"
    }


@app.get("/health")
async def health_check():
    """Deployment health check endpoint."""
    return {
        "status": "ok",
        "service": "WeatherGPT",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }


@app.get("/weather")
@app.get("/weather/location")
async def get_weather(
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    city: Optional[str] = Query(None)
):
    """
    Retrieve current weather, hourly forecast, 7-day daily forecast, and weather intelligence.
    Accepts latitude/longitude or city name.
    """
    target_lat = latitude
    target_lon = longitude
    resolved_city = city

    if (target_lat is None or target_lon is None) and city:
        geo = await geocode_location(city)
        if not geo:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={"error": f"Location '{city}' could not be resolved.", "details": "Please verify the spelling or select a nearby major city."}
            )
        target_lat = geo["latitude"]
        target_lon = geo["longitude"]
        resolved_city = f"{geo['city']}, {geo['state']}" if geo.get("state") else geo["city"]

    if target_lat is None or target_lon is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Missing location coordinates or city name.", "details": "Please provide latitude and longitude or a city query."}
        )

    if not resolved_city:
        rev_geo = await reverse_geocode(target_lat, target_lon)
        resolved_city = rev_geo.get("city", "Current Location")

    weather_data = await fetch_weather_data(target_lat, target_lon, resolved_city)
    if "error" in weather_data:
        return JSONResponse(
            status_code=weather_data.get("status_code", 500),
            content=weather_data
        )

    # Calculate intelligence risks
    intelligence = synthesize_weather_intelligence(weather_data)
    weather_data["weather_intelligence"] = intelligence

    return weather_data


@app.get("/forecast")
async def get_forecast(
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    city: Optional[str] = Query(None)
):
    """Retrieve 7-day weather forecast."""
    return await get_weather(latitude=latitude, longitude=longitude, city=city)


@app.get("/query")
async def analyze_query_endpoint(q: str = Query(..., description="Query text to parse")):
    """Analyze query intent, date, parameter, and location using deterministic query engine."""
    return parse_query(q)


@app.post("/ask")
@app.get("/ask")
async def ask_weathergpt(
    request: Request,
    question: Optional[str] = Query(None),
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    city: Optional[str] = Query(None),
    lang: Optional[str] = Query(None)
):
    """
    Main Conversational WeatherGPT Intelligence Endpoint.
    Executes the complete request pipeline:
    Query -> Parsing -> Location Resolution -> Data Fetching -> Intelligence -> Agriculture/IMD -> Gemini AI.
    """
    query_text = ""
    req_lat = latitude
    req_lon = longitude
    req_city = city
    req_lang = lang or "en"

    # Handle POST JSON payload if present
    if request.method == "POST":
        try:
            body = await request.json()
            query_text = body.get("question", "")
            if body.get("latitude") is not None:
                req_lat = float(body.get("latitude"))
            if body.get("longitude") is not None:
                req_lon = float(body.get("longitude"))
            if body.get("city"):
                req_city = body.get("city")
            if body.get("language"):
                req_lang = body.get("language")
        except Exception:
            pass
    elif question:
        query_text = question

    if not query_text.strip():
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"error": "Question query cannot be empty.", "details": "Please enter a weather-related question."}
        )

    # 1. Parse query deterministically
    understanding = parse_query(query_text)
    
    # Non-weather questions
    if not understanding.get("is_weather_related") or understanding.get("intent") == "non_weather":
        persona_reply = (
            "I'm WeatherGPT, focused on meteorological intelligence, agriculture advisories, forecasts, "
            "and severe weather alerts. Please ask me anything related to weather, climate, or farming conditions!"
        )
        return {
            "question": query_text,
            "understanding": understanding,
            "is_weather_related": False,
            "answer": persona_reply
        }

    # Invalid date checking (e.g. September 31)
    if understanding.get("error_message"):
        return {
            "question": query_text,
            "understanding": understanding,
            "error": understanding.get("error_message"),
            "answer": understanding.get("error_message")
        }

    # 2. Resolve Location Hierarchy:
    # Query Explicit Location > Selected Location > Browser GPS > Fallback prompt
    final_city = None
    target_lat = None
    target_lon = None

    if understanding.get("location"):
        # Explicit location in query overrides GPS
        geo = await geocode_location(understanding["location"])
        if geo:
            target_lat = geo["latitude"]
            target_lon = geo["longitude"]
            final_city = f"{geo['city']}, {geo['state']}" if geo.get("state") else geo["city"]
        else:
            final_city = understanding["location"].capitalize()

    if target_lat is None or target_lon is None:
        if req_city:
            geo = await geocode_location(req_city)
            if geo:
                target_lat = geo["latitude"]
                target_lon = geo["longitude"]
                final_city = f"{geo['city']}, {geo['state']}" if geo.get("state") else geo["city"]

    if target_lat is None or target_lon is None:
        if req_lat is not None and req_lon is not None:
            target_lat = req_lat
            target_lon = req_lon
            rev_geo = await reverse_geocode(target_lat, target_lon)
            final_city = rev_geo.get("city", "Current Location")

    # If location could still not be resolved, prompt user gracefully
    if target_lat is None or target_lon is None:
        return {
            "question": query_text,
            "understanding": understanding,
            "location_needed": True,
            "answer": "Please specify a city name (e.g., 'in Guntur' or 'in Vijayawada') or allow location access so I can check your local weather."
        }

    # 3. Route to specialized services based on intent
    intent = understanding.get("intent")
    weather_payload: Dict[str, Any] = {}
    historical_data = None
    climate_trend_data = None
    agri_advisory = None
    imd_warning = None

    # Determine day index for forecast
    target_day_idx = 0
    if understanding.get("time") == "tomorrow":
        target_day_idx = 1

    # Fetch main forecast weather
    weather_data = await fetch_weather_data(target_lat, target_lon, final_city)
    if "error" not in weather_data:
        weather_intelligence = synthesize_weather_intelligence(weather_data)
        weather_data["weather_intelligence"] = weather_intelligence
        weather_payload = weather_data

    # Handle Historical Intent
    if intent == "historical" or understanding.get("historical_intent"):
        s_date = understanding.get("requested_start_date") or understanding.get("requested_date") or "2024-01-01"
        e_date = understanding.get("requested_end_date") or understanding.get("requested_date") or s_date
        historical_data = await fetch_historical_weather(target_lat, target_lon, s_date, e_date, final_city)
        weather_payload["historical_weather"] = historical_data

    # Handle Climate Trend Intent
    elif intent == "climate_trend" or understanding.get("climate_trend_intent"):
        s_yr = 2021
        e_yr = 2025
        if understanding.get("requested_start_date"):
            s_yr = int(understanding["requested_start_date"].split("-")[0])
        if understanding.get("requested_end_date"):
            e_yr = int(understanding["requested_end_date"].split("-")[0])
        climate_trend_data = await analyze_climate_trend(target_lat, target_lon, s_yr, e_yr, final_city)
        weather_payload["climate_trend"] = climate_trend_data

    # Agriculture Advisory
    if understanding.get("agriculture_intent"):
        agri_advisory = generate_agricultural_advisory(weather_payload, target_day_idx)
        weather_payload["agriculture_advisory"] = agri_advisory

    # IMD Warning
    if understanding.get("imd_intent") or "India" in str(weather_payload.get("location", {})):
        f_day = understanding.get("imd_forecast_day") or (target_day_idx + 1)
        imd_warning = await fetch_imd_warnings(target_lat, target_lon, final_city, f_day)
        weather_payload["official_warning"] = imd_warning

    # 4. Generate Conversational AI answer
    detected_lang = understanding.get("detected_language", "en")
    lang_name_map = {"te": "Telugu", "te-Latn": "Telugu", "hi": "Hindi", "hi-Latn": "Hindi", "en": "English"}
    lang_name = lang_name_map.get(detected_lang, "English")

    ai_answer = await generate_ai_explanation(
        question=query_text,
        payload=weather_payload,
        lang_code=detected_lang,
        lang_name=lang_name
    )

    speech_locale = get_speech_locale(detected_lang)

    return {
        "question": query_text,
        "understanding": understanding,
        "is_weather_related": True,
        "location": weather_payload.get("location", {"city": final_city, "latitude": target_lat, "longitude": target_lon}),
        "weather": weather_payload.get("current", {}),
        "weather_intelligence": weather_payload.get("weather_intelligence", {}),
        "agriculture_advisory": agri_advisory,
        "historical_weather": historical_data,
        "climate_trend": climate_trend_data,
        "official_warning": imd_warning,
        "daily_forecast": weather_payload.get("daily", []),
        "hourly_forecast": weather_payload.get("hourly", []),
        "answer": ai_answer,
        "speech_locale": speech_locale
    }


@app.get("/history")
async def get_history_endpoint(
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    city: Optional[str] = Query(None),
    start_date: str = Query("2024-01-01"),
    end_date: str = Query("2024-01-07")
):
    """Retrieve historical weather records and summary statistics."""
    target_lat = latitude
    target_lon = longitude
    target_city = city

    if (target_lat is None or target_lon is None) and city:
        geo = await geocode_location(city)
        if geo:
            target_lat = geo["latitude"]
            target_lon = geo["longitude"]
            target_city = geo["city"]

    if target_lat is None or target_lon is None:
        target_lat = 16.3067
        target_lon = 80.4365
        target_city = "Guntur"

    return await fetch_historical_weather(target_lat, target_lon, start_date, end_date, target_city)


@app.get("/climate-trend")
async def get_climate_trend_endpoint(
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    city: Optional[str] = Query(None),
    start_year: int = Query(2021),
    end_year: int = Query(2025)
):
    """Retrieve multi-year climate trend analysis."""
    target_lat = latitude
    target_lon = longitude
    target_city = city

    if (target_lat is None or target_lon is None) and city:
        geo = await geocode_location(city)
        if geo:
            target_lat = geo["latitude"]
            target_lon = geo["longitude"]
            target_city = geo["city"]

    if target_lat is None or target_lon is None:
        target_lat = 16.3067
        target_lon = 80.4365
        target_city = "Guntur"

    return await analyze_climate_trend(target_lat, target_lon, start_year, end_year, target_city)


@app.get("/imd-warning")
async def get_imd_warning_endpoint(
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    city: Optional[str] = Query(None),
    forecast_day: int = Query(1)
):
    """Retrieve official IMD weather alerts and warning levels."""
    target_lat = latitude or 16.3067
    target_lon = longitude or 80.4365
    return await fetch_imd_warnings(target_lat, target_lon, city or "Guntur", forecast_day)


@app.get("/agriculture-advisory")
async def get_agriculture_advisory_endpoint(
    latitude: Optional[float] = Query(None),
    longitude: Optional[float] = Query(None),
    city: Optional[str] = Query(None),
    day_index: int = Query(0)
):
    """Retrieve agriculture-specific weather advisories and pesticide spraying suitability."""
    target_lat = latitude
    target_lon = longitude
    target_city = city or "Guntur"

    if (target_lat is None or target_lon is None) and city:
        geo = await geocode_location(city)
        if geo:
            target_lat = geo["latitude"]
            target_lon = geo["longitude"]

    if target_lat is None or target_lon is None:
        target_lat = 16.3067
        target_lon = 80.4365
    weather_data = await fetch_weather_data(target_lat, target_lon, target_city)
    return generate_agricultural_advisory(weather_data, day_index)


# Serve frontend files from the root URL
if os.path.exists(FRONTEND_DIR):
    app.mount(
        "/",
        StaticFiles(directory=FRONTEND_DIR, html=True),
        name="frontend"
    )

    

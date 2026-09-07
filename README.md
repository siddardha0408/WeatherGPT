# WeatherGPT — AI Weather Intelligence & Decision Support Platform

WeatherGPT is a production-quality full-stack AI weather platform that doesn't just tell users what the weather is, but explains **what the weather means for them and what they should do**.

---

## 🌟 Key Features

1. **Deterministic Meteorological Engine**: Ground-truth weather data powered by Open-Meteo Forecast & Historical Archives.
2. **Deterministic Weather Intelligence**: Algorithms evaluating **Heat Risk**, **Rain Risk**, **Wind Risk**, **UV Index Risk**, **Visibility Risk**, and **Overall Risk**.
3. **Agricultural Decision Support**: Safe, meteorological spraying suitability evaluation for pesticides/fertilizers, harvesting windows, and irrigation scheduling.
4. **Official IMD Warning Integration**: India Meteorological Department alerts (Red / Orange / Yellow / Green) distinguished clearly from calculated forecast risks.
5. **Historical Weather & Climate Trends**: Multi-year linear regression slope calculations, annual rainfall changes, and prudent scientific caveats.
6. **Conversational AI Layer**: Google Gemini API grounded synthesis with zero-hallucination constraints and seamless offline/rate-limit fallback.
7. **Multilingual & Romanized Support**: English, Telugu, Hindi, Tamil, Kannada, Malayalam, Bengali, plus Romanized Telugu (`eroju guntur lo weather ela undhi`, `repu vijayawada lo rain untunda`).
8. **Web Speech API**: Browser-native voice input (SpeechRecognition) and Indian-accented voice readout (SpeechSynthesis).
9. **Interactive Visualizations**: 24-hour temperature & precipitation charts and multi-year climate trend graphs with Chart.js.
10. **Automatic Geolocation**: Detects browser GPS on launch and reverse-geocodes current location automatically.

---

## 🏗️ Architecture

```
                 ┌──────────────────────────────────────┐
                 │       USER / WEB BROWSER             │
                 │   HTML5 + CSS3 + Vanilla JS + Speech  │
                 └──────────────────┬───────────────────┘
                                    │
                       HTTP / JSON (REST API)
                                    │
                 ┌──────────────────▼───────────────────┐
                 │          FASTAPI BACKEND             │
                 │        (Port 8000 / Uvicorn)         │
                 └──────────────────┬───────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
┌────────▼────────┐        ┌────────▼────────┐        ┌────────▼────────┐
│  QUERY ENGINE   │        │ WEATHER SERVICE │        │ INTELLIGENCE &  │
│ - Intent Parser │        │ - Open-Meteo    │        │  AGRICULTURE    │
│ - Location Ext. │        │ - Geocoding     │        │ - Heat/Rain/UV  │
│ - Date/Range    │        │ - Caching (TTL) │        │ - Spraying/Crop │
│ - Roman Telugu  │        │ - WMO Decoders  │        │ - Risk Matrix   │
└────────┬────────┘        └────────┬────────┘        └────────┬────────┘
         │                          │                          │
         └──────────────────────────┼──────────────────────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
┌────────▼────────┐        ┌────────▼────────┐        ┌────────▼────────┐
│  IMD WARNING    │        │  GEMINI AI      │        │  HISTORY &      │
│ - Official CAP  │        │ - NL Synthesis  │        │  CLIMATE TREND  │
│ - Warning Level │        │ - Multilingual  │        │ - Archive API   │
│ - Safe Fallback │        │ - 429 Fallback  │        │ - Trend Slopes  │
└─────────────────┘        └─────────────────┘        └─────────────────┘
```

---

## 🚀 Quick Start

### 1. Backend Setup & Run

```powershell
# Navigate to the backend directory
cd C:\Users\nsidd\.gemini\antigravity-ide\scratch\WeatherGPT\backend

# Install dependencies (if not already installed)
pip install -r requirements.txt

# Start the FastAPI server
python -m uvicorn main:app --reload --port 8000
```

* API Root: `http://127.0.0.1:8000`
* Interactive API Documentation (Swagger): `http://127.0.0.1:8000/docs`
* Health Check: `http://127.0.0.1:8000/health`

### 2. Frontend Launch

Open `C:\Users\nsidd\.gemini\antigravity-ide\scratch\WeatherGPT\frontend\index.html` in any modern web browser or serve via Live Server (`http://127.0.0.1:5500` or `http://localhost:8000`).

---

## 🧪 Running Automated Tests

```powershell
cd C:\Users\nsidd\.gemini\antigravity-ide\scratch\WeatherGPT\backend
python -m pytest tests/ -v
```

---

## 📡 API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | Deployment health check |
| `/weather` | GET | Current weather, hourly, 7-day forecast & risks |
| `/forecast` | GET | 7-day daily forecast |
| `/query` | GET | Deterministic query analyzer (intent, location, date, parameter) |
| `/ask` | POST / GET | Unified conversational query pipeline with AI & intelligence |
| `/history` | GET | Historical weather archive & statistics |
| `/climate-trend` | GET | Multi-year climate tendencies & regression slopes |
| `/agriculture-advisory` | GET | Pesticide spraying suitability & farming recommendations |
| `/imd-warning` | GET | Official IMD warning alerts |

---

## 🛡️ Security & Reliability

* In-memory TTL caching (5 minutes) protects external APIs from 429 rate limits.
* Defensive dictionary access guarantees zero `KeyError` crashes.
* Strict isolation ensures calculated risks are never falsely labeled as official IMD government warnings.
* Gemini integration includes deterministic fallback on quota limits or network dropouts.

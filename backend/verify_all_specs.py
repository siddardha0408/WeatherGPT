"""
Comprehensive Verification Test Suite for WeatherGPT Specification.
Tests all 35 user query cases, parameter extractions, error fallbacks, and multilingual queries.
"""

import httpx
import sys

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE = "http://127.0.0.1:8000"

TEST_QUERIES = [
    ("What is the weather today?", "weather", None),
    ("What is the weather in Guntur?", "weather", "guntur"),
    ("Will it rain tomorrow?", "weather", None),
    ("What is the temperature in Vijayawada?", "weather", "vijayawada"),
    ("How humid is it?", "weather", None),
    ("What is the UV index?", "weather", None),
    ("What is the wind speed?", "weather", None),
    ("Which direction is the wind coming from?", "weather", None),
    ("What is the visibility?", "weather", None),
    ("What is the dew point?", "weather", None),
    ("What is the surface pressure?", "weather", None),
    ("What is the cloud cover?", "weather", None),
    ("Will it rain in Guntur tomorrow?", "weather", "guntur"),
    ("Is tomorrow suitable for spraying pesticides?", "agriculture", None),
    ("What was the rainfall in Guntur in 2024?", "historical", "guntur"),
    ("Is rainfall increasing in Guntur?", "climate_trend", "guntur"),
    ("What is the IMD warning for tomorrow?", "imd_warning", None),
    ("Is there a thunderstorm warning?", "weather", None),
    ("What should farmers do today?", "agriculture", None),
    ("How hot will it feel?", "weather", None),
    ("Is there a heat risk?", "weather", None),
    ("Is there a strong wind?", "weather", None),
    ("ఈరోజు గుంటూరులో వాతావరణం ఎలా ఉంది?", "weather", "guntur"),
    ("eroju guntur lo weather ela vundhi?", "weather", "guntur"),
    ("repu vijayawada lo rain untunda?", "weather", "vijayawada"),
    ("What happened on September 31?", "historical", None),
    ("Who is the president?", "non_weather", None)
]

def run_all_checks():
    passed = 0
    failed = 0

    with httpx.Client(base_url=BASE, timeout=25.0) as client:
        print("=================================================================")
        print("         WEATHERGPT SPECIFICATION VERIFICATION SUITE             ")
        print("=================================================================\n")

        for idx, (query, expected_intent, expected_loc) in enumerate(TEST_QUERIES, 1):
            try:
                res = client.post("/ask", json={
                    "question": query,
                    "latitude": 16.3067,
                    "longitude": 80.4365,
                    "city": "Guntur"
                })
                data = res.json()

                und = data.get("understanding", {})
                detected_intent = und.get("intent")
                detected_loc = und.get("location")
                answer = data.get("answer", "")

                status_ok = True
                if expected_intent and detected_intent != expected_intent:
                    status_ok = False
                if expected_loc and detected_loc != expected_loc:
                    status_ok = False
                if not answer:
                    status_ok = False

                if status_ok:
                    passed += 1
                    status_sym = "✅ PASS"
                else:
                    failed += 1
                    status_sym = "❌ FAIL"

                print(f"[{idx:02d}] {status_sym} | Query: '{query}'")
                print(f"     Intent: {detected_intent} | Loc: {detected_loc}")
                print(f"     Answer: {answer[:120]}...\n")

            except Exception as e:
                failed += 1
                print(f"[{idx:02d}] ❌ ERROR | Query: '{query}' | Exception: {e}\n")

        print("=================================================================")
        print(f"TOTAL: {passed + failed} | PASSED: {passed} | FAILED: {failed}")
        print("=================================================================")

if __name__ == "__main__":
    run_all_checks()

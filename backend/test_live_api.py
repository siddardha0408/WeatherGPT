import httpx
import json
import sys

# Ensure UTF-8 output on Windows terminal
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE = "http://127.0.0.1:8000"

def test_live():
    with httpx.Client(base_url=BASE, timeout=20.0) as client:
        # 1. Health
        h = client.get("/health").json()
        print(f"[Health] Status: {h['status']} | Service: {h['service']}")

        # 2. Weather
        w = client.get("/weather?city=Guntur").json()
        print(f"[Weather] Location: {w['location']['city']} | Temp: {w['current']['temperature']}C | Cond: {w['current']['condition']} | Overall Risk: {w['weather_intelligence']['overall_risk']['level']}")

        # 3. Rain Tomorrow
        ask1 = client.post("/ask", json={"question": "Will it rain tomorrow in Guntur?"}).json()
        print(f"[Ask 1] Question: {ask1['question']}")
        print(f"[Ask 1] Answer: {ask1['answer']}\n")

        # 4. Agriculture
        ask2 = client.post("/ask", json={"question": "Can I spray pesticides tomorrow?", "city": "Guntur"}).json()
        print(f"[Ask 2] Agriculture Spraying: {ask2['agriculture_advisory']['spraying_suitability']['suitability']}")
        print(f"[Ask 2] Answer: {ask2['answer']}\n")

        # 5. Roman Telugu
        ask3 = client.post("/ask", json={"question": "eroju guntur lo weather ela vundhi"}).json()
        print(f"[Ask 3] Roman Telugu Answer: {ask3['answer']}\n")

        # 6. Telugu Unicode
        ask4 = client.post("/ask", json={"question": "ఈరోజు గుంటూరులో వాతావరణం ఎలా ఉంది?"}).json()
        print(f"[Ask 4] Telugu Unicode Answer: {ask4['answer']}\n")

        # 7. Climate Trend
        ct = client.get("/climate-trend?city=Guntur&start_year=2021&end_year=2025").json()
        print(f"[Climate Trend] Period: {ct.get('period')} | Rainfall Trend: {ct.get('rainfall_trend', {}).get('trend')} | Pct: {ct.get('rainfall_trend', {}).get('percentage_change')}%")

        # 8. IMD Warning
        imd = client.get("/imd-warning?city=Guntur").json()
        print(f"[IMD Warning] Level: {imd.get('level')} | Official: {imd.get('official_warning')} | Source: {imd.get('source')}")

if __name__ == "__main__":
    test_live()

"""
Integration tests for FastAPI application endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "WeatherGPT"


def test_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "WeatherGPT" in response.json()["service"]


def test_query_endpoint():
    response = client.get("/query?q=Will it rain tomorrow in Guntur?")
    assert response.status_code == 200
    data = response.json()
    assert data["location"] == "guntur"
    assert data["time"] == "tomorrow"
    assert data["parameter"] == "rainfall"


def test_ask_non_weather():
    response = client.post("/ask", json={"question": "Who is the president?"})
    assert response.status_code == 200
    data = response.json()
    assert data["is_weather_related"] is False
    assert "WeatherGPT" in data["answer"]


def test_ask_weather_with_location():
    response = client.post("/ask", json={"question": "What is the weather in Guntur?"})
    assert response.status_code == 200
    data = response.json()
    assert data["is_weather_related"] is not False
    assert "weather" in data
    assert "answer" in data
    assert len(data["answer"]) > 0


def test_ask_without_location_using_gps():
    response = client.post("/ask", json={
        "question": "What is the humidity today?",
        "latitude": 16.3067,
        "longitude": 80.4365
    })
    assert response.status_code == 200
    data = response.json()
    assert "location" in data
    assert "weather" in data
    assert data.get("location_needed") is not True


def test_agriculture_advisory_endpoint():
    response = client.get("/agriculture-advisory?city=Guntur&day_index=1")
    assert response.status_code == 200
    data = response.json()
    assert "spraying_suitability" in data
    assert "field_operations" in data

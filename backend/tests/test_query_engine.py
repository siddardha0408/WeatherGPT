"""
Unit tests for the Deterministic Query Engine.
Verifies intent, location extraction, dates, date ranges, parameters, Roman Telugu, and error handling.
"""

import pytest
from services.query_engine import parse_query


def test_basic_weather_query_with_location():
    res = parse_query("What is the weather in Guntur?")
    assert res["intent"] == "weather"
    assert res["location"] == "guntur"
    assert res["time"] == "current"
    assert res["parameter"] == "general"
    assert res["is_weather_related"] is True


def test_weather_query_without_location():
    res = parse_query("What is the weather today?")
    assert res["intent"] == "weather"
    assert res["location"] is None
    assert res["time"] == "today"
    assert res["parameter"] == "general"


def test_rain_tomorrow_query():
    res = parse_query("Will it rain tomorrow in Guntur?")
    assert res["intent"] == "weather"
    assert res["location"] == "guntur"
    assert res["time"] == "tomorrow"
    assert res["parameter"] == "rainfall"


def test_parameter_extractions():
    q_humidity = parse_query("How humid is it?")
    assert q_humidity["parameter"] == "humidity"

    q_uv = parse_query("What is the UV index?")
    assert q_uv["parameter"] == "uv_index"

    q_wind = parse_query("What is the wind speed?")
    assert q_wind["parameter"] == "wind"

    q_direction = parse_query("Which direction is the wind coming from?")
    assert q_direction["parameter"] == "wind_direction"

    q_dew = parse_query("What is the dew point?")
    assert q_dew["parameter"] == "dew_point"

    q_pressure = parse_query("What is atmospheric pressure?")
    assert q_pressure["parameter"] == "surface_pressure"


def test_roman_telugu_queries():
    res1 = parse_query("eroju guntur lo weather ela vundhi")
    assert res1["location"] == "guntur"
    assert res1["time"] == "today"

    res2 = parse_query("repu vijayawada lo rain untunda")
    assert res2["location"] == "vijayawada"
    assert res2["time"] == "tomorrow"
    assert res2["parameter"] == "rainfall"

    res3 = parse_query("vizag lo weather ela undhi")
    assert res3["location"] == "visakhapatnam"  # Resolved alias


def test_unicode_telugu_query():
    res = parse_query("ఈరోజు గుంటూరులో వాతావరణం ఎలా ఉంది?")
    assert res["location"] == "guntur"
    assert res["detected_language"] == "te"


def test_agriculture_query():
    res = parse_query("Can I spray pesticides tomorrow?")
    assert res["intent"] == "agriculture"
    assert res["agriculture_intent"] is True
    assert res["time"] == "tomorrow"


def test_historical_weather_query():
    res = parse_query("What was the rainfall in Guntur in 2024?")
    assert res["intent"] == "historical"
    assert res["historical_intent"] is True
    assert res["location"] == "guntur"
    assert res["requested_start_date"] == "2024-01-01"
    assert res["requested_end_date"] == "2024-12-31"


def test_date_range_query():
    res = parse_query("What was the weather from September 1 to September 5?")
    assert res["intent"] in ["weather", "historical"]
    assert res["requested_start_date"] == "2026-09-01"
    assert res["requested_end_date"] == "2026-09-05"
    assert res["error_message"] is None


def test_invalid_date_query():
    res = parse_query("What happened on September 31?")
    assert res["error_message"] is not None
    assert "September has only 30 days" in res["error_message"]


def test_climate_trend_query():
    res = parse_query("Is rainfall increasing in Guntur?")
    assert res["intent"] == "climate_trend"
    assert res["climate_trend_intent"] is True
    assert res["location"] == "guntur"


def test_imd_warning_query():
    res = parse_query("What is the IMD warning tomorrow?")
    assert res["intent"] == "imd_warning"
    assert res["imd_intent"] is True
    assert res["imd_forecast_day"] == 2


def test_non_weather_query():
    res = parse_query("Who is the prime minister?")
    assert res["intent"] == "non_weather"
    assert res["is_weather_related"] is False

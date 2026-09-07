"""
Unit tests for Weather Intelligence, Agriculture Evaluation, and Trend Computation.
"""

import pytest
from services.intelligence_service import (
    calculate_heat_risk,
    calculate_rain_risk,
    calculate_wind_risk,
    calculate_uv_risk,
    calculate_visibility_risk,
    synthesize_weather_intelligence
)
from services.agriculture_service import evaluate_spraying_suitability
from services.climate_trend_service import compute_linear_slope
from services.weather_service import get_wmo_condition


def test_wmo_weather_codes():
    c0 = get_wmo_condition(0)
    assert c0["condition"] == "Clear Sky"
    assert "☀️" in c0["icon"]

    c95 = get_wmo_condition(95)
    assert "Thunderstorm" in c95["condition"]

    c_unk = get_wmo_condition(9999)
    assert c_unk["condition"] == "Unknown"


def test_heat_risk():
    low = calculate_heat_risk(temp=22.0, feels_like=22.0, humidity=40)
    assert low["level"] == "Low"

    high = calculate_heat_risk(temp=36.0, feels_like=38.0, humidity=60)
    assert high["level"] in ["High", "Very High"]

    extreme = calculate_heat_risk(temp=44.0, feels_like=48.0, humidity=70)
    assert extreme["level"] == "Extreme"


def test_rain_risk():
    very_low = calculate_rain_risk(precip_prob=5, precip_amount=0.0, weather_code=0)
    assert very_low["level"] == "Very Low"

    high = calculate_rain_risk(precip_prob=70, precip_amount=5.0, weather_code=61)
    assert high["level"] in ["High", "Very High"]

    thunderstorm = calculate_rain_risk(precip_prob=90, precip_amount=30.0, weather_code=95)
    assert thunderstorm["level"] == "Extreme"


def test_wind_risk():
    calm = calculate_wind_risk(wind_speed=5.0, wind_gust=8.0)
    assert calm["level"] == "Low"

    strong = calculate_wind_risk(wind_speed=38.0, wind_gust=55.0)
    assert strong["level"] in ["High", "Extreme"]


def test_uv_risk():
    low = calculate_uv_risk(1.5)
    assert low["level"] == "Low"

    mod = calculate_uv_risk(4.5)
    assert mod["level"] == "Moderate"

    extreme = calculate_uv_risk(11.5)
    assert extreme["level"] == "Extreme"


def test_visibility_risk():
    good = calculate_visibility_risk(15.0)
    assert good["level"] == "Good"

    fog = calculate_visibility_risk(0.5)
    assert fog["level"] == "Very Low"


def test_spraying_suitability():
    # Suitable conditions
    good_spray = evaluate_spraying_suitability(
        precip_prob=10,
        precip_sum=0.0,
        wind_speed=8.0,
        wind_gust=12.0,
        temp=26.0,
        humidity=55
    )
    assert good_spray["suitability"] == "Suitable"

    # Bad conditions (rain + high wind)
    bad_spray = evaluate_spraying_suitability(
        precip_prob=80,
        precip_sum=15.0,
        wind_speed=25.0,
        wind_gust=35.0,
        temp=30.0,
        humidity=75
    )
    assert bad_spray["suitability"] == "Not Recommended"


def test_linear_regression_slope():
    # Perfect line y = 2x + 1
    xs = [1.0, 2.0, 3.0, 4.0, 5.0]
    ys = [3.0, 5.0, 7.0, 9.0, 11.0]
    slope = compute_linear_slope(xs, ys)
    assert round(slope, 2) == 2.0

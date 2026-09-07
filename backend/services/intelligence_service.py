"""
Intelligence Service for WeatherGPT.
Deterministic Meteorological Risk Assessment & Decision Support Algorithms.
Calculates Heat Risk, Rain Risk, Wind Risk, UV Risk, Visibility Risk, Overall Risk,
and generates actionable advisories.
"""

from typing import Dict, Any, List, Optional

RISK_LEVEL_WEIGHTS = {
    "Extreme": 5,
    "Very High": 4,
    "High": 3,
    "Moderate": 2,
    "Low": 1,
    "Very Low": 0,
    "Good": 0
}


def calculate_heat_risk(temp: float, feels_like: float, humidity: int) -> Dict[str, str]:
    """
    Calculate heat risk based on temperature, apparent feels-like temperature, and relative humidity.
    """
    effective_temp = max(temp, feels_like)
    
    if effective_temp >= 45.0 or temp >= 42.0:
        level = "Extreme"
        desc = "Dangerous heat index. High risk of heat stroke and exhaustion."
        badge = "🔥 Extreme"
    elif effective_temp >= 40.0 or (temp >= 38.0 and humidity >= 55):
        level = "Very High"
        desc = "Intense heat. Prolonged outdoor exposure is hazardous."
        badge = "🔥 Very High"
    elif effective_temp >= 35.0 or (temp >= 33.0 and humidity >= 50):
        level = "High"
        desc = "High heat and humidity. Discomfort and heat fatigue likely."
        badge = "🔥 High"
    elif effective_temp >= 30.0 or temp >= 28.0:
        level = "Moderate"
        desc = "Moderate warmth. Noticeable humidity and warmth outdoors."
        badge = "☀️ Moderate"
    else:
        level = "Low"
        desc = "Comfortable temperature with minimal heat stress."
        badge = "🟢 Low"

    return {"level": level, "description": desc, "badge": badge}


def calculate_rain_risk(precip_prob: int, precip_amount: float, weather_code: int) -> Dict[str, str]:
    """
    Calculate rain risk based on precipitation probability, forecast precipitation amount, and WMO code.
    """
    # Check severe rain codes (65=Heavy Rain, 82=Violent Showers, 95/96/99=Thunderstorm)
    if weather_code in [65, 82, 95, 96, 99] or precip_amount >= 25.0:
        level = "Extreme"
        desc = "Heavy downpour or thunderstorms expected. High risk of waterlogging."
        badge = "⛈️ Extreme"
    elif precip_prob >= 75 or precip_amount >= 10.0:
        level = "Very High"
        desc = "Rain is very likely. Substantial rainfall expected."
        badge = "🌧️ Very High"
    elif precip_prob >= 50 or precip_amount >= 4.0 or weather_code in [61, 63, 80, 81]:
        level = "High"
        desc = "Good chance of rain showers. Carry protective rainwear."
        badge = "🌧️ High"
    elif precip_prob >= 25 or precip_amount >= 1.0 or weather_code in [51, 53, 55]:
        level = "Moderate"
        desc = "Possible patchy drizzle or light rain showers."
        badge = "🌦️ Moderate"
    elif precip_prob >= 10:
        level = "Low"
        desc = "Low chance of isolated light precipitation."
        badge = "🌤️ Low"
    else:
        level = "Very Low"
        desc = "Minimal to no chance of rainfall. Dry conditions expected."
        badge = "☀️ Very Low"

    return {"level": level, "description": desc, "badge": badge}


def calculate_wind_risk(wind_speed: float, wind_gust: float) -> Dict[str, str]:
    """
    Calculate wind risk based on sustained wind speed and maximum gusts (in km/h).
    """
    max_wind = max(wind_speed, wind_gust)

    if max_wind >= 60.0 or wind_speed >= 45.0:
        level = "Extreme"
        desc = "Gale force winds. Dangerous gusts capable of causing damage."
        badge = "🌪️ Extreme"
    elif max_wind >= 45.0 or wind_speed >= 30.0:
        level = "High"
        desc = "Strong breezy conditions. Outdoor structures and two-wheelers affected."
        badge = "💨 High"
    elif max_wind >= 25.0 or wind_speed >= 18.0:
        level = "Moderate"
        desc = "Moderate breeze. Noticeable air movement."
        badge = "🍃 Moderate"
    else:
        level = "Low"
        desc = "Gentle light winds. Calm and comfortable."
        badge = "🟢 Low"

    return {"level": level, "description": desc, "badge": badge}


def calculate_uv_risk(uv_index: float) -> Dict[str, str]:
    """
    Calculate UV risk based on standard WHO UV Index categories.
    """
    if uv_index >= 11.0:
        level = "Extreme"
        desc = "Extreme UV index (11+). Unprotected skin can burn in minutes."
        badge = "☀️ Extreme"
    elif uv_index >= 8.0:
        level = "Very High"
        desc = "Very high UV radiation (8-10). Extra sun protection essential."
        badge = "☀️ Very High"
    elif uv_index >= 6.0:
        level = "High"
        desc = "High UV radiation (6-7). Wear hat, sunglasses, and SPF 30+."
        badge = "☀️ High"
    elif uv_index >= 3.0:
        level = "Moderate"
        desc = "Moderate UV radiation (3-5). Seek shade during midday hours."
        badge = "⛅ Moderate"
    else:
        level = "Low"
        desc = "Low UV radiation (0-2). Minimal sun protection needed."
        badge = "🟢 Low"

    return {"level": level, "description": desc, "badge": badge}


def calculate_visibility_risk(visibility_km: float) -> Dict[str, str]:
    """
    Calculate visibility category based on visibility distance in kilometers.
    """
    if visibility_km < 1.0:
        level = "Very Low"
        desc = "Dense fog / mist. Hazardous driving conditions."
        badge = "🌫️ Very Low"
    elif visibility_km < 4.0:
        level = "Low"
        desc = "Moderate fog or haze. Reduced road and aviation visibility."
        badge = "🌫️ Low"
    elif visibility_km < 10.0:
        level = "Moderate"
        desc = "Fair visibility with slight atmospheric haze."
        badge = "⛅ Moderate"
    else:
        level = "Good"
        desc = "Clear and unobstructed visibility (>10 km)."
        badge = "🟢 Good"

    return {"level": level, "description": desc, "badge": badge}


def synthesize_weather_intelligence(weather_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Synthesizes overall meteorological risks and generates tailored actionable advisories.
    """
    current = weather_data.get("current", {})
    temp = current.get("temperature", 25.0)
    feels_like = current.get("feels_like", temp)
    humidity = current.get("humidity", 50)
    precip_prob = current.get("precipitation_probability", 0)
    precip_amount = current.get("precipitation", 0.0)
    weather_code = current.get("weather_code", 0)
    wind_speed = current.get("wind_speed", 5.0)
    wind_gust = current.get("wind_gust", wind_speed)
    uv_index = current.get("uv_index", 3.0)
    visibility_km = current.get("visibility", 10.0)

    heat = calculate_heat_risk(temp, feels_like, humidity)
    rain = calculate_rain_risk(precip_prob, precip_amount, weather_code)
    wind = calculate_wind_risk(wind_speed, wind_gust)
    uv = calculate_uv_risk(uv_index)
    vis = calculate_visibility_risk(visibility_km)

    # Determine overall risk
    risk_levels = [heat["level"], rain["level"], wind["level"], uv["level"]]
    max_weight = max(RISK_LEVEL_WEIGHTS.get(lvl, 0) for lvl in risk_levels)

    weight_to_level = {5: "Extreme", 4: "Very High", 3: "High", 2: "Moderate", 1: "Low", 0: "Low"}
    overall_level = weight_to_level.get(max_weight, "Low")

    # Generate advisories
    advisories: List[str] = []
    
    if heat["level"] in ["High", "Very High", "Extreme"]:
        advisories.append(f"🔥 Heat Advisory: High apparent temperature ({feels_like:.1f}°C). Stay well-hydrated and avoid strenuous midday sun exposure.")
    elif heat["level"] == "Moderate":
        advisories.append(f"☀️ Warm & Humid: Comfortable for short outings; drink adequate water.")

    if rain["level"] in ["High", "Very High", "Extreme"]:
        advisories.append(f"🌧️ Rain Alert: High chance of precipitation ({precip_prob}%). Carry an umbrella and plan for possible commute delays.")
    elif rain["level"] == "Moderate":
        advisories.append("🌦️ Spotty Showers: Passing light showers possible; keep an umbrella handy.")

    if wind["level"] in ["High", "Extreme"]:
        advisories.append(f"💨 Wind Advisory: Strong wind gusts up to {wind_gust:.1f} km/h. Secure loose outdoor objects.")

    if uv["level"] in ["High", "Very High", "Extreme"]:
        advisories.append(f"☀️ Sun Protection: UV Index is {uv_index:.1f}. Wear sunscreen (SPF 30+) and sunglasses between 10 AM and 4 PM.")

    if vis["level"] in ["Low", "Very Low"]:
        advisories.append(f"🌫️ Low Visibility: Visibility is {visibility_km:.1f} km. Use fog lights and exercise caution when driving.")

    if not advisories:
        advisories.append("🟢 Pleasant Weather: Great conditions for outdoor activities and travel.")

    return {
        "heat_risk": heat,
        "rain_risk": rain,
        "wind_risk": wind,
        "uv_risk": uv,
        "visibility_risk": vis,
        "overall_risk": {
            "level": overall_level,
            "badge": f"⚠️ {overall_level}" if overall_level in ["High", "Very High", "Extreme"] else f"🟢 {overall_level}",
            "summary": f"Overall weather risk is {overall_level.upper()} based on prevailing temperature, precipitation, and wind factors."
        },
        "advisories": advisories
    }

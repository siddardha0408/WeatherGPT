"""
Agriculture Service for WeatherGPT.
Provides weather-based agricultural intelligence and decision support for farmers.
Analyzes spraying suitability, harvest conditions, irrigation needs, and field operations.
STRICTLY provides meteorological suitability without prescribing chemical dosages or mixtures.
"""

from typing import Dict, Any, List, Optional


def evaluate_spraying_suitability(
    precip_prob: int,
    precip_sum: float,
    wind_speed: float,
    wind_gust: float,
    temp: float,
    humidity: int,
    time_label: str = "selected day"
) -> Dict[str, Any]:
    """
    Evaluates weather suitability for pesticide and fertilizer spraying operations.
    Criteria:
    - Rain wash-off risk: precip_prob < 30%, precip_sum < 0.5 mm
    - Wind drift risk: wind_speed between 3 and 15 km/h (avoid calm inversions < 3 and drift > 15 km/h)
    - Evaporation / Leaf burn risk: temp between 15°C and 32°C, humidity > 40%
    """
    issues = []
    favorable_factors = []

    # 1. Rain analysis
    if precip_prob >= 50 or precip_sum >= 2.0:
        issues.append(f"High risk of rain ({precip_prob}% chance, {precip_sum:.1f} mm forecast) will wash off chemical sprays before absorption.")
    elif precip_prob >= 30 or precip_sum >= 0.5:
        issues.append(f"Moderate rain probability ({precip_prob}%) could reduce spray adhesion and efficacy.")
    else:
        favorable_factors.append(f"Low rainfall risk ({precip_prob}% chance) allows optimal spray drying and adherence.")

    # 2. Wind analysis
    if wind_speed > 18.0 or wind_gust > 25.0:
        issues.append(f"Excessive wind ({wind_speed:.1f} km/h, gusts up to {wind_gust:.1f} km/h) creates serious spray drift and non-target damage.")
    elif wind_speed > 14.0:
        issues.append(f"Breezy conditions ({wind_speed:.1f} km/h); spray drift may occur if standard nozzles are used.")
    elif wind_speed < 2.0:
        issues.append("Very still/calm air (<2 km/h) may lead to temperature inversion traps.")
    else:
        favorable_factors.append(f"Ideal wind velocity ({wind_speed:.1f} km/h) for uniform droplet distribution.")

    # 3. Temperature & Humidity
    if temp > 35.0:
        issues.append(f"High ambient temperature ({temp:.1f}°C) causes rapid droplet evaporation and possible foliage scorch.")
    elif temp < 10.0:
        issues.append(f"Low temperature ({temp:.1f}°C) may slow plant metabolic uptake.")
    else:
        favorable_factors.append(f"Comfortable temperature ({temp:.1f}°C) for foliar absorption.")

    if humidity < 35:
        issues.append(f"Low relative humidity ({humidity}%) increases droplet evaporation before reaching target leaves.")

    # Determine overall status
    if any("High risk of rain" in iss or "Excessive wind" in iss or "High ambient temp" in iss for iss in issues):
        suitability = "Not Recommended"
        badge = "⛔ Not Recommended"
        summary = f"Spraying operations for {time_label} are not recommended due to adverse weather conditions."
    elif len(issues) >= 2:
        suitability = "Caution / Marginal"
        badge = "⚠️ Caution"
        summary = f"Marginal spraying conditions for {time_label}. Spraying should only be done with drift-reducing nozzles during early morning or late evening."
    elif len(issues) == 1:
        suitability = "Marginal"
        badge = "⚠️ Fair / Caution"
        summary = f"Fair spraying window for {time_label}, though monitor localized wind and cloud cover."
    else:
        suitability = "Suitable"
        badge = "✅ Highly Suitable"
        summary = f"Weather conditions for {time_label} are favorable for foliar spray and fertilizer application."

    return {
        "suitability": suitability,
        "badge": badge,
        "summary": summary,
        "favorable_factors": favorable_factors,
        "risk_factors": issues,
        "recommendation": (
            "Consider postponing until a dry, low-wind window."
            if suitability == "Not Recommended"
            else "Early morning (6 AM – 9 AM) or late afternoon (4 PM – 6 PM) is typically best."
        ),
        "disclaimer": "This advisory is based solely on meteorological forecast conditions. Always follow pesticide product labels and consult local agricultural university/extension guidance for specific chemical application protocols."
    }


def generate_agricultural_advisory(weather_data: Dict[str, Any], target_day_idx: int = 0) -> Dict[str, Any]:
    """
    Generates a full agricultural advisory payload for farmers based on current and forecast weather.
    """
    daily = weather_data.get("daily", [])
    current = weather_data.get("current", {})

    if daily and 0 <= target_day_idx < len(daily):
        day_data = daily[target_day_idx]
        precip_prob = day_data.get("precipitation_probability", 0)
        precip_sum = day_data.get("precipitation_sum", 0.0)
        wind_speed = day_data.get("wind_speed_max", 10.0)
        wind_gust = wind_speed * 1.3
        temp = day_data.get("temp_max", 30.0)
        humidity = current.get("humidity", 60)
        date_str = day_data.get("date", "forecast day")
    else:
        precip_prob = current.get("precipitation_probability", 0)
        precip_sum = current.get("precipitation", 0.0)
        wind_speed = current.get("wind_speed", 5.0)
        wind_gust = current.get("wind_gust", wind_speed)
        temp = current.get("temperature", 28.0)
        humidity = current.get("humidity", 60)
        date_str = "today"

    time_label = "today" if target_day_idx == 0 else ("tomorrow" if target_day_idx == 1 else date_str)
    spraying_report = evaluate_spraying_suitability(
        precip_prob=precip_prob,
        precip_sum=precip_sum,
        wind_speed=wind_speed,
        wind_gust=wind_gust,
        temp=temp,
        humidity=humidity,
        time_label=time_label
    )

    # General field operations advice
    field_operations = []
    if precip_sum > 10.0 or precip_prob > 60:
        field_operations.append("Postpone harvest operations and protect harvested grain/produce in covered storage.")
        field_operations.append("Hold irrigation scheduling as natural precipitation is expected to recharge soil moisture.")
    elif precip_sum == 0 and temp > 33.0:
        field_operations.append("Ensure scheduled light irrigation to maintain root zone moisture during high evaporative demand.")
        field_operations.append("Favorable dry weather for crop harvesting and field drying.")
    else:
        field_operations.append("Normal field operations and intercultural weeding can proceed.")

    return {
        "target_date": date_str,
        "time_label": time_label,
        "spraying_suitability": spraying_report,
        "field_operations": field_operations,
        "forecast_metrics": {
            "max_temperature": temp,
            "rain_probability": precip_prob,
            "expected_rain_mm": precip_sum,
            "max_wind_kmh": wind_speed,
            "relative_humidity": humidity
        }
    }

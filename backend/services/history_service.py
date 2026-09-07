"""
History Service for WeatherGPT.
Integrates with Open-Meteo Historical Weather Archive API.
Retrieves historical temperature, rainfall, wind, and calculates statistical metrics for dates and date ranges.
"""

import logging
from typing import Dict, Any, Optional, List
import httpx
from .weather_service import _get_from_cache, _set_in_cache, _WEATHER_CACHE, get_wmo_condition

logger = logging.getLogger("weather_gpt.history_service")


async def fetch_historical_weather(
    latitude: float,
    longitude: float,
    start_date: str,
    end_date: str,
    city_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Fetch historical weather records for a specific date or date range (YYYY-MM-DD) from Open-Meteo Archive.
    """
    cache_key = f"hist:{round(latitude,3)},{round(longitude,3)}:{start_date}:{end_date}"
    cached = _get_from_cache(_WEATHER_CACHE, cache_key)
    if cached:
        return cached

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "start_date": start_date,
        "end_date": end_date,
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "temperature_2m_mean",
            "precipitation_sum",
            "wind_speed_10m_max"
        ],
        "timezone": "auto"
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, params=params)

            if resp.status_code == 429:
                logger.error("Open-Meteo Archive API rate limit exceeded")
                return {
                    "error": "Historical archive rate limit exceeded.",
                    "details": "Open-Meteo is temporarily limiting archive requests. Please try again shortly.",
                    "status_code": 429
                }

            if resp.status_code != 200:
                logger.error(f"Open-Meteo Archive API returned {resp.status_code}: {resp.text}")
                return {
                    "error": "Failed to fetch historical archive data.",
                    "details": f"Upstream Archive API returned status {resp.status_code}.",
                    "status_code": resp.status_code
                }

            raw = resp.json()
            daily_raw = raw.get("daily", {}) if isinstance(raw, dict) else {}

            times = daily_raw.get("time", [])
            max_temps = daily_raw.get("temperature_2m_max", [])
            min_temps = daily_raw.get("temperature_2m_min", [])
            mean_temps = daily_raw.get("temperature_2m_mean", [])
            precips = daily_raw.get("precipitation_sum", [])
            winds = daily_raw.get("wind_speed_10m_max", [])
            codes = daily_raw.get("weather_code", [])

            daily_records: List[Dict[str, Any]] = []
            for i in range(len(times)):
                c = codes[i] if i < len(codes) else 0
                wmo = get_wmo_condition(c)
                daily_records.append({
                    "date": times[i],
                    "weather_code": c,
                    "condition": wmo["condition"],
                    "icon": wmo["icon"],
                    "temp_max": max_temps[i] if i < len(max_temps) else 0.0,
                    "temp_min": min_temps[i] if i < len(min_temps) else 0.0,
                    "temp_mean": mean_temps[i] if i < len(mean_temps) else 0.0,
                    "precipitation": precips[i] if i < len(precips) else 0.0,
                    "wind_speed_max": winds[i] if i < len(winds) else 0.0
                })

            # Calculate statistics
            stats = calculate_history_statistics(daily_records)

            result = {
                "location": {
                    "city": city_name or "Target Location",
                    "latitude": latitude,
                    "longitude": longitude
                },
                "start_date": start_date,
                "end_date": end_date,
                "records_count": len(daily_records),
                "statistics": stats,
                "daily_records": daily_records
            }

            _set_in_cache(_WEATHER_CACHE, cache_key, result)
            return result

    except Exception as exc:
        logger.error(f"Error retrieving historical weather: {exc}", exc_info=True)
        return {
            "error": "Error retrieving historical weather.",
            "details": str(exc),
            "status_code": 500
        }


def calculate_history_statistics(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compute aggregate summary statistics over a series of daily records.
    """
    if not records:
        return {
            "total_precipitation_mm": 0.0,
            "average_precipitation_mm": 0.0,
            "max_temperature": 0.0,
            "min_temperature": 0.0,
            "avg_temperature": 0.0,
            "max_wind_speed": 0.0,
            "rainy_days_count": 0
        }

    precips = [r["precipitation"] for r in records if r.get("precipitation") is not None]
    max_temps = [r["temp_max"] for r in records if r.get("temp_max") is not None]
    min_temps = [r["temp_min"] for r in records if r.get("temp_min") is not None]
    mean_temps = [r["temp_mean"] for r in records if r.get("temp_mean") is not None]
    winds = [r["wind_speed_max"] for r in records if r.get("wind_speed_max") is not None]

    total_rain = sum(precips) if precips else 0.0
    rainy_days = sum(1 for p in precips if p >= 1.0)

    return {
        "total_precipitation_mm": round(total_rain, 2),
        "average_precipitation_mm": round(total_rain / max(len(precips), 1), 2),
        "max_temperature": round(max(max_temps), 1) if max_temps else 0.0,
        "min_temperature": round(min(min_temps), 1) if min_temps else 0.0,
        "avg_temperature": round(sum(mean_temps) / max(len(mean_temps), 1), 1) if mean_temps else (round((max(max_temps) + min(min_temps))/2, 1) if max_temps else 0.0),
        "max_wind_speed": round(max(winds), 1) if winds else 0.0,
        "rainy_days_count": rainy_days,
        "days_analyzed": len(records)
    }

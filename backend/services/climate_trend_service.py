"""
Climate Trend Service for WeatherGPT.
Aggregates multi-year historical datasets, calculates yearly precipitation and temperature totals,
computes percentage changes and linear regression trend slopes, and includes scientific caveats.
"""

import logging
from typing import Dict, Any, List, Optional
from .history_service import fetch_historical_weather

logger = logging.getLogger("weather_gpt.climate_trend_service")


def compute_linear_slope(x_vals: List[float], y_vals: List[float]) -> float:
    """
    Computes standard ordinary least squares linear regression slope (m in y = mx + c).
    """
    n = len(x_vals)
    if n < 2:
        return 0.0
    x_mean = sum(x_vals) / n
    y_mean = sum(y_vals) / n

    numerator = sum((x_vals[i] - x_mean) * (y_vals[i] - y_mean) for i in range(n))
    denominator = sum((x_vals[i] - x_mean) ** 2 for i in range(n))

    if denominator == 0:
        return 0.0
    return numerator / denominator


async def analyze_climate_trend(
    latitude: float,
    longitude: float,
    start_year: int = 2021,
    end_year: int = 2025,
    city_name: Optional[str] = None
) -> Dict[str, Any]:
    """
    Analyze multi-year climate trends for a given location.
    """
    if start_year >= end_year:
        start_year = end_year - 4

    yearly_data: List[Dict[str, Any]] = []

    for year in range(start_year, end_year + 1):
        s_date = f"{year}-01-01"
        e_date = f"{year}-12-31"
        hist_res = await fetch_historical_weather(latitude, longitude, s_date, e_date, city_name)
        
        if "statistics" in hist_res:
            st = hist_res["statistics"]
            yearly_data.append({
                "year": year,
                "total_rainfall_mm": st["total_precipitation_mm"],
                "avg_temperature_c": st["avg_temperature"],
                "max_temperature_c": st["max_temperature"],
                "min_temperature_c": st["min_temperature"],
                "max_wind_kmh": st["max_wind_speed"],
                "rainy_days": st["rainy_days_count"]
            })

    if not yearly_data:
        return {
            "error": "Unable to calculate climate trends due to missing historical archive data.",
            "location": {"city": city_name, "latitude": latitude, "longitude": longitude}
        }

    years = [float(item["year"]) for item in yearly_data]
    rainfalls = [item["total_rainfall_mm"] for item in yearly_data]
    temps = [item["avg_temperature_c"] for item in yearly_data]

    # Calculate trends
    rain_slope = compute_linear_slope(years, rainfalls)
    temp_slope = compute_linear_slope(years, temps)

    first_rain = rainfalls[0]
    last_rain = rainfalls[-1]
    pct_rain_change = ((last_rain - first_rain) / first_rain * 100) if first_rain > 0 else 0.0

    first_temp = temps[0]
    last_temp = temps[-1]
    pct_temp_change = ((last_temp - first_temp) / first_temp * 100) if first_temp > 0 else 0.0

    if rain_slope > 10.0:
        rain_trend = "increasing"
    elif rain_slope < -10.0:
        rain_trend = "decreasing"
    else:
        rain_trend = "stable / fluctuating"

    if temp_slope > 0.05:
        temp_trend = "warming"
    elif temp_slope < -0.05:
        temp_trend = "cooling"
    else:
        temp_trend = "stable"

    num_years = len(yearly_data)

    return {
        "location": {
            "city": city_name or "Target Location",
            "latitude": latitude,
            "longitude": longitude
        },
        "period": f"{start_year} – {end_year}",
        "years_analyzed": num_years,
        "yearly_records": yearly_data,
        "rainfall_trend": {
            "trend": rain_trend,
            "slope_mm_per_year": round(rain_slope, 2),
            "percentage_change": round(pct_rain_change, 2),
            "start_year_rainfall_mm": round(first_rain, 1),
            "end_year_rainfall_mm": round(last_rain, 1),
            "average_annual_rainfall_mm": round(sum(rainfalls) / len(rainfalls), 1)
        },
        "temperature_trend": {
            "trend": temp_trend,
            "slope_c_per_year": round(temp_slope, 3),
            "percentage_change": round(pct_temp_change, 2),
            "start_year_avg_temp_c": round(first_temp, 1),
            "end_year_avg_temp_c": round(last_temp, 1)
        },
        "scientific_disclaimer": (
            f"This short-term dataset covers {num_years} years ({start_year}–{end_year}) and indicates an overall "
            f"{rain_trend} tendency for precipitation. Please note that multi-decadal meteorological records (30+ years) "
            "are standard in climatology to establish formal climate change trends."
        )
    }

"""
Weather Service for WeatherGPT.
Handles geocoding, reverse geocoding, current weather, 7-day forecast,
hourly weather, in-memory caching with TTL, and robust error handling.
"""

import time
import logging
from typing import Dict, Any, Optional, Tuple
import httpx

logger = logging.getLogger("weather_gpt.weather_service")

# In-memory cache with TTL (5 minutes = 300 seconds)
CACHE_DURATION_SECONDS = 300
_WEATHER_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_GEO_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}

# Location aliases for common Indian variations
LOCATION_ALIASES = {
    "vizag": "visakhapatnam",
    "vishakhapatnam": "visakhapatnam",
    "vishakapatnam": "visakhapatnam",
    "bengaluru": "bangalore",
    "mumbai": "bombay",
    "bombay": "mumbai",
    "chennai": "madras",
    "madras": "chennai",
    "calcutta": "kolkata",
    "kolkata": "calcutta",
    "vijayawada": "vijayawada",
    "bezawada": "vijayawada",
    "guntur": "guntur",
    "delhi": "new delhi",
    "hyd": "hyderabad",
}

WMO_WEATHER_CODES = {
    0: {"condition": "Clear Sky", "icon": "☀️", "description": "Sunny and clear skies"},
    1: {"condition": "Mainly Clear", "icon": "🌤️", "description": "Mostly clear with occasional thin clouds"},
    2: {"condition": "Partly Cloudy", "icon": "⛅", "description": "Mix of sunshine and scattered clouds"},
    3: {"condition": "Overcast", "icon": "☁️", "description": "Completely covered with uniform clouds"},
    45: {"condition": "Fog", "icon": "🌫️", "description": "Foggy conditions with reduced visibility"},
    48: {"condition": "Depositing Rime Fog", "icon": "🌫️", "description": "Rime fog forming icy deposits"},
    51: {"condition": "Light Drizzle", "icon": "🌦️", "description": "Light patchy drizzle"},
    53: {"condition": "Moderate Drizzle", "icon": "🌦️", "description": "Steady moderate drizzle"},
    55: {"condition": "Dense Drizzle", "icon": "🌧️", "description": "Heavy dense drizzle"},
    56: {"condition": "Light Freezing Drizzle", "icon": "🌨️", "description": "Cold freezing drizzle"},
    57: {"condition": "Dense Freezing Drizzle", "icon": "🌨️", "description": "Dense icy freezing drizzle"},
    61: {"condition": "Slight Rain", "icon": "🌧️", "description": "Slight rainfall"},
    63: {"condition": "Moderate Rain", "icon": "🌧️", "description": "Moderate steady rain"},
    65: {"condition": "Heavy Rain", "icon": "🌧️", "description": "Intense heavy rainfall"},
    66: {"condition": "Light Freezing Rain", "icon": "🌨️", "description": "Light icy rain"},
    67: {"condition": "Heavy Freezing Rain", "icon": "🌨️", "description": "Heavy icy freezing rain"},
    71: {"condition": "Slight Snow", "icon": "❄️", "description": "Light snowfall"},
    73: {"condition": "Moderate Snow", "icon": "❄️", "description": "Moderate snowfall"},
    75: {"condition": "Heavy Snow", "icon": "❄️", "description": "Heavy snowfall"},
    77: {"condition": "Snow Grains", "icon": "❄️", "description": "Tiny granular snow crystals"},
    80: {"condition": "Slight Rain Showers", "icon": "🌦️", "description": "Scattered light showers"},
    81: {"condition": "Moderate Rain Showers", "icon": "🌦️", "description": "Frequent moderate showers"},
    82: {"condition": "Violent Rain Showers", "icon": "⛈️", "description": "Violent convective showers"},
    85: {"condition": "Slight Snow Showers", "icon": "🌨️", "description": "Light snow showers"},
    86: {"condition": "Heavy Snow Showers", "icon": "🌨️", "description": "Intense snow showers"},
    95: {"condition": "Thunderstorm", "icon": "⛈️", "description": "Thunderstorm activity with lightning"},
    96: {"condition": "Thunderstorm with Slight Hail", "icon": "⛈️", "description": "Thunderstorm with small hail"},
    99: {"condition": "Thunderstorm with Heavy Hail", "icon": "⛈️", "description": "Severe thunderstorm with heavy hail"}
}


def get_wmo_condition(code: Optional[int]) -> Dict[str, str]:
    """Translate WMO weather code to readable condition, icon, and description."""
    if code is None or code not in WMO_WEATHER_CODES:
        return {"condition": "Unknown", "icon": "🌡️", "description": "Weather conditions unavailable"}
    return WMO_WEATHER_CODES[code]


def _get_from_cache(cache: Dict[str, Tuple[float, Any]], key: str) -> Optional[Any]:
    """Retrieve an item from cache if not expired."""
    now = time.time()
    if key in cache:
        cached_time, data = cache[key]
        if now - cached_time < CACHE_DURATION_SECONDS:
            return data
        else:
            del cache[key]
    return None


def _set_in_cache(cache: Dict[str, Tuple[float, Any]], key: str, data: Any) -> None:
    """Store an item in cache with the current timestamp."""
    cache[key] = (time.time(), data)


async def geocode_location(city_name: str) -> Optional[Dict[str, Any]]:
    """
    Resolve a city name or query string to geographic coordinates using Open-Meteo Geocoding.
    """
    if not city_name or not city_name.strip():
        return None

    normalized_name = city_name.strip().lower()
    normalized_name = LOCATION_ALIASES.get(normalized_name, normalized_name)

    cache_key = f"geo:{normalized_name}"
    cached_geo = _get_from_cache(_GEO_CACHE, cache_key)
    if cached_geo:
        return cached_geo

    url = "https://geocoding-api.open-meteo.com/v1/search"
    params = {
        "name": normalized_name,
        "count": 5,
        "language": "en",
        "format": "json"
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            response = await client.get(url, params=params)
            
            if response.status_code == 429:
                logger.warning("Geocoding API rate limited (429)")
                return None
            
            if response.status_code != 200:
                logger.warning(f"Geocoding API returned status {response.status_code}")
                return None

            data = response.json()
            results = data.get("results", [])
            if not results:
                logger.info(f"No geocoding results found for '{city_name}'")
                return None

            # Pick the most relevant result (first)
            first_match = results[0]
            location_info = {
                "city": first_match.get("name", city_name.capitalize()),
                "state": first_match.get("admin1", ""),
                "country": first_match.get("country", ""),
                "country_code": first_match.get("country_code", ""),
                "latitude": float(first_match.get("latitude", 0.0)),
                "longitude": float(first_match.get("longitude", 0.0)),
                "timezone": first_match.get("timezone", "auto")
            }

            _set_in_cache(_GEO_CACHE, cache_key, location_info)
            return location_info

    except Exception as exc:
        logger.error(f"Error during geocoding '{city_name}': {exc}")
        return None


async def reverse_geocode(latitude: float, longitude: float) -> Dict[str, Any]:
    """
    Find the closest location name for given coordinates.
    Uses Open-Meteo geocoding reverse or OpenStreetMap Nominatim with safe fallback.
    """
    cache_key = f"revgeo:{round(latitude, 3)},{round(longitude, 3)}"
    cached = _get_from_cache(_GEO_CACHE, cache_key)
    if cached:
        return cached

    location_info = {
        "city": f"Lat {latitude:.2f}, Lon {longitude:.2f}",
        "state": "",
        "country": "India" if (8.0 <= latitude <= 37.0 and 68.0 <= longitude <= 97.0) else "",
        "latitude": latitude,
        "longitude": longitude,
        "timezone": "auto"
    }

    try:
        # Try OpenStreetMap reverse geocoding
        headers = {"User-Agent": "WeatherGPT-WeatherIntelligenceApp/1.0"}
        url = "https://nominatim.openstreetmap.org/reverse"
        params = {
            "lat": latitude,
            "lon": longitude,
            "format": "json",
            "zoom": 10,
            "addressdetails": 1
        }
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                address = data.get("address", {})
                city = address.get("city") or address.get("town") or address.get("village") or address.get("county") or address.get("district")
                state = address.get("state", "")
                country = address.get("country", "")

                if city:
                    location_info["city"] = city
                if state:
                    location_info["state"] = state
                if country:
                    location_info["country"] = country

                _set_in_cache(_GEO_CACHE, cache_key, location_info)
                return location_info

    except Exception as exc:
        logger.warning(f"Reverse geocoding lookup failed: {exc}, using fallback coordinates.")

    return location_info


async def fetch_weather_data(latitude: float, longitude: float, location_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch comprehensive current, hourly, and 7-day daily weather data from Open-Meteo.
    Validates all structures defensively to prevent KeyError / NoneType crashes.
    """
    cache_key = f"weather:{round(latitude, 3)},{round(longitude, 3)}"
    cached_weather = _get_from_cache(_WEATHER_CACHE, cache_key)
    if cached_weather:
        # Update location label if provided
        if location_name and cached_weather.get("location"):
            cached_weather["location"]["city"] = location_name
        return cached_weather

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": [
            "temperature_2m",
            "relative_humidity_2m",
            "apparent_temperature",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
            "wind_direction_10m",
            "wind_gusts_10m",
            "dew_point_2m",
            "surface_pressure",
            "cloud_cover",
            "visibility",
            "uv_index"
        ],
        "hourly": [
            "temperature_2m",
            "precipitation_probability",
            "precipitation",
            "weather_code",
            "wind_speed_10m",
            "relative_humidity_2m"
        ],
        "daily": [
            "weather_code",
            "temperature_2m_max",
            "temperature_2m_min",
            "apparent_temperature_max",
            "apparent_temperature_min",
            "precipitation_sum",
            "precipitation_probability_max",
            "wind_speed_10m_max",
            "uv_index_max"
        ],
        "timezone": "auto",
        "forecast_days": 7
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url, params=params)

            if response.status_code == 429:
                logger.error("Open-Meteo forecast API rate limited (429)")
                return {
                    "error": "Open-Meteo rate limit exceeded.",
                    "details": "The weather service is temporarily limiting requests. Please try again in a few moments.",
                    "status_code": 429
                }

            if response.status_code != 200:
                logger.error(f"Open-Meteo forecast API returned {response.status_code}: {response.text}")
                return {
                    "error": "Weather data service is currently unavailable.",
                    "details": f"Upstream API returned status code {response.status_code}.",
                    "status_code": response.status_code
                }

            raw_data = response.json()
            normalized = normalize_weather_response(raw_data, latitude, longitude, location_name)

            _set_in_cache(_WEATHER_CACHE, cache_key, normalized)
            return normalized

    except httpx.TimeoutException:
        logger.error("Open-Meteo request timed out")
        return {
            "error": "Weather service request timed out.",
            "details": "The remote meteorological service took too long to respond. Please try again.",
            "status_code": 504
        }
    except Exception as exc:
        logger.error(f"Unexpected error fetching weather data: {exc}", exc_info=True)
        return {
            "error": "Failed to retrieve weather data.",
            "details": "An unexpected error occurred while communicating with the weather service.",
            "status_code": 500
        }


def normalize_weather_response(raw: Dict[str, Any], latitude: float, longitude: float, city_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Safely transform raw Open-Meteo response into unified WeatherGPT payload.
    Uses defensive dictionary lookups with defaults.
    """
    current_raw = raw.get("current", {}) if isinstance(raw, dict) else {}
    hourly_raw = raw.get("hourly", {}) if isinstance(raw, dict) else {}
    daily_raw = raw.get("daily", {}) if isinstance(raw, dict) else {}

    # Current weather fields
    weather_code = current_raw.get("weather_code")
    condition_meta = get_wmo_condition(weather_code)

    current_data = {
        "time": current_raw.get("time", ""),
        "temperature": current_raw.get("temperature_2m", 0.0),
        "feels_like": current_raw.get("apparent_temperature", current_raw.get("temperature_2m", 0.0)),
        "humidity": current_raw.get("relative_humidity_2m", 0),
        "precipitation": current_raw.get("precipitation", 0.0),
        "weather_code": weather_code if weather_code is not None else 0,
        "condition": condition_meta["condition"],
        "icon": condition_meta["icon"],
        "description": condition_meta["description"],
        "wind_speed": current_raw.get("wind_speed_10m", 0.0),
        "wind_direction": current_raw.get("wind_direction_10m", 0),
        "wind_gust": current_raw.get("wind_gusts_10m", current_raw.get("wind_speed_10m", 0.0)),
        "dew_point": current_raw.get("dew_point_2m", 0.0),
        "pressure": current_raw.get("surface_pressure", 1013.25),
        "cloud_cover": current_raw.get("cloud_cover", 0),
        "visibility": current_raw.get("visibility", 10000.0) / 1000.0 if current_raw.get("visibility") is not None else 10.0,  # Convert meters to km
        "uv_index": current_raw.get("uv_index", 0.0)
    }

    # Daily forecast list (7 days)
    daily_list = []
    daily_times = daily_raw.get("time", [])
    max_temps = daily_raw.get("temperature_2m_max", [])
    min_temps = daily_raw.get("temperature_2m_min", [])
    precip_sums = daily_raw.get("precipitation_sum", [])
    precip_probs = daily_raw.get("precipitation_probability_max", [])
    wind_maxs = daily_raw.get("wind_speed_10m_max", [])
    uv_maxs = daily_raw.get("uv_index_max", [])
    daily_codes = daily_raw.get("weather_code", [])
    apparent_maxs = daily_raw.get("apparent_temperature_max", [])
    apparent_mins = daily_raw.get("apparent_temperature_min", [])

    for i in range(len(daily_times)):
        code = daily_codes[i] if i < len(daily_codes) else 0
        cond = get_wmo_condition(code)
        daily_list.append({
            "date": daily_times[i],
            "weather_code": code,
            "condition": cond["condition"],
            "icon": cond["icon"],
            "temp_max": max_temps[i] if i < len(max_temps) else 0.0,
            "temp_min": min_temps[i] if i < len(min_temps) else 0.0,
            "apparent_max": apparent_maxs[i] if i < len(apparent_maxs) else 0.0,
            "apparent_min": apparent_mins[i] if i < len(apparent_mins) else 0.0,
            "precipitation_sum": precip_sums[i] if i < len(precip_sums) else 0.0,
            "precipitation_probability": precip_probs[i] if i < len(precip_probs) else 0,
            "wind_speed_max": wind_maxs[i] if i < len(wind_maxs) else 0.0,
            "uv_index_max": uv_maxs[i] if i < len(uv_maxs) else 0.0
        })

    # Hourly forecast (next 24 hours)
    hourly_list = []
    hourly_times = hourly_raw.get("time", [])
    h_temps = hourly_raw.get("temperature_2m", [])
    h_precip_probs = hourly_raw.get("precipitation_probability", [])
    h_precips = hourly_raw.get("precipitation", [])
    h_codes = hourly_raw.get("weather_code", [])
    h_winds = hourly_raw.get("wind_speed_10m", [])
    h_humidity = hourly_raw.get("relative_humidity_2m", [])

    limit_hourly = min(len(hourly_times), 24)
    for i in range(limit_hourly):
        code = h_codes[i] if i < len(h_codes) else 0
        cond = get_wmo_condition(code)
        hourly_list.append({
            "time": hourly_times[i],
            "temperature": h_temps[i] if i < len(h_temps) else 0.0,
            "precipitation_probability": h_precip_probs[i] if i < len(h_precip_probs) else 0,
            "precipitation": h_precips[i] if i < len(h_precips) else 0.0,
            "weather_code": code,
            "condition": cond["condition"],
            "icon": cond["icon"],
            "wind_speed": h_winds[i] if i < len(h_winds) else 0.0,
            "humidity": h_humidity[i] if i < len(h_humidity) else 0
        })

    # Estimate current precipitation probability from today's forecast or first hourly item
    current_precip_prob = daily_list[0]["precipitation_probability"] if daily_list else 0
    if hourly_list:
        current_precip_prob = hourly_list[0].get("precipitation_probability", current_precip_prob)
    current_data["precipitation_probability"] = current_precip_prob

    return {
        "location": {
            "city": city_name or "Current Location",
            "latitude": latitude,
            "longitude": longitude,
            "timezone": raw.get("timezone", "auto"),
            "elevation": raw.get("elevation", 0.0)
        },
        "current": current_data,
        "hourly": hourly_list,
        "daily": daily_list,
        "retrieved_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

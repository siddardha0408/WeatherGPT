"""
Deterministic Query Engine for WeatherGPT.
Analyzes natural-language queries without invoking Gemini for rule-based parsing.
Extracts: Intent, Location, Date / Date Ranges, Parameters, Agriculture, Climate, and IMD flags.
"""

import re
import datetime
from typing import Dict, Any, Optional, Tuple, List
from .language_service import detect_language, normalize_romanized_query
from .weather_service import LOCATION_ALIASES

MONTH_MAP = {
    "jan": 1, "january": 1,
    "feb": 2, "february": 2,
    "mar": 3, "march": 3,
    "apr": 4, "april": 4,
    "may": 5,
    "jun": 6, "june": 6,
    "jul": 7, "july": 7,
    "aug": 8, "august": 8,
    "sep": 9, "september": 9, "sept": 9,
    "oct": 10, "october": 10,
    "nov": 11, "november": 11,
    "dec": 12, "december": 12
}

DAYS_IN_MONTH = {
    1: 31, 2: 29, 3: 31, 4: 30, 5: 31, 6: 30,
    7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31
}

MONTH_NAMES_LIST = ["january", "february", "march", "april", "may", "june",
                    "july", "august", "september", "october", "november", "december"]

NON_WEATHER_TERMS = [
    r"\bpresident\b", r"\bprime\s+minister\b", r"\bcapital\s+of\b",
    r"\bwho\s+is\b", r"\btell\s+me\s+a\s+joke\b", r"\bwho\s+created\b",
    r"\bwho\s+won\b", r"\bstock\s+price\b", r"\bmovie\b", r"\bsong\b"
]

STOP_WORDS_FOR_LOCATION = {
    "weather", "forecast", "climate", "temperature", "humidity", "rain", "rainfall",
    "wind", "pressure", "uv", "dew", "point", "visibility", "cloud", "cover",
    "today", "tomorrow", "yesterday", "tonight", "morning", "afternoon", "evening",
    "now", "currently", "pesticide", "pesticides", "fertilizer", "fertilizers",
    "spray", "spraying", "crop", "crops", "farm", "farmer", "farming", "harvest",
    "sowing", "irrigation", "imd", "warning", "alert", "watch", "heat", "risk",
    "high", "low", "good", "bad", "suitable", "trend", "change", "increasing",
    "decreasing", "compare", "year", "years", "last", "what", "is", "the", "will",
    "it", "can", "i", "how", "much", "many", "there", "any", "which", "direction",
    "coming", "from", "feel", "feels", "like", "tell", "me", "in", "for", "at",
    "near", "lo", "mein", "undhi", "vundhi", "untunda", "entha", "eroju", "repu",
    "ninna", "kaisa", "hai", "aaj", "kal"
}

TELUGU_LOCATION_MAP = {
    "గుంటూరు": "guntur",
    "విజయవాడ": "vijayawada",
    "విశాఖపట్నం": "visakhapatnam",
    "హైదరాబాద్": "hyderabad",
    "తిరుపతి": "tirupati",
    "నెల్లూరు": "nellore",
    "కర్నూలు": "kurnool",
    "రాజమండ్రి": "rajahmundry",
    "కాకినాడ": "kakinada",
    "కడప": "kadapa",
    "అనంతపురం": "anantapur",
    "ఢిల్లీ": "delhi",
    "ముంబై": "mumbai",
    "చెన్నై": "chennai",
    "బెంగళూరు": "bangalore"
}


def parse_query(query: str, current_year: int = 2026) -> Dict[str, Any]:
    """
    Parse a natural language query into a structured understanding object.
    """
    if not query or not query.strip():
        return _empty_query_response()

    original = query.strip()
    lang_code, lang_name, is_romanized = detect_language(original)
    
    # Check for Unicode Telugu city extraction first
    telugu_city = None
    for telugu_name, eng_city in TELUGU_LOCATION_MAP.items():
        if telugu_name in original:
            telugu_city = eng_city
            break

    # Normalize if Romanized Indian or non-English
    normalized = normalize_romanized_query(original, lang_code) if is_romanized else original
    lower_norm = normalized.lower()

    # 1. Non-weather query detection
    for pattern in NON_WEATHER_TERMS:
        if re.search(pattern, lower_norm):
            return {
                "original_query": original,
                "normalized_query": normalized,
                "intent": "non_weather",
                "location": None,
                "time": "current",
                "requested_date": None,
                "requested_start_date": None,
                "requested_end_date": None,
                "parameter": "general",
                "agriculture_intent": False,
                "historical_intent": False,
                "climate_trend_intent": False,
                "imd_intent": False,
                "imd_forecast_day": None,
                "detected_language": lang_code,
                "is_romanized": is_romanized,
                "error_message": None,
                "is_weather_related": False
            }

    # 2. Extract Intent flags
    agri_intent = _check_agriculture_intent(lower_norm)
    imd_intent, imd_day = _check_imd_intent(lower_norm)
    climate_intent = _check_climate_intent(lower_norm)
    hist_intent, year_match = _check_historical_intent(lower_norm, current_year)

    # 3. Extract Dates and Date Ranges
    time_val, req_date, start_date, end_date, date_err = _extract_dates_and_ranges(lower_norm, current_year, year_match)
    if hist_intent and not start_date and not req_date and year_match:
        start_date = f"{year_match}-01-01"
        end_date = f"{year_match}-12-31"

    # 4. Extract Location
    location = telugu_city or _extract_location(original.lower(), original) or _extract_location(lower_norm, original)
    if location:
        location = LOCATION_ALIASES.get(location.lower(), location.lower())

    # 5. Extract Parameter
    parameter = _extract_parameter(lower_norm)

    # Determine primary intent
    if climate_intent:
        primary_intent = "climate_trend"
    elif hist_intent or (start_date and end_date and int(start_date.split("-")[0]) < current_year):
        primary_intent = "historical"
        hist_intent = True
    elif agri_intent:
        primary_intent = "agriculture"
    elif imd_intent:
        primary_intent = "imd_warning"
    else:
        primary_intent = "weather"

    return {
        "original_query": original,
        "normalized_query": normalized,
        "intent": primary_intent,
        "location": location,
        "time": time_val,
        "requested_date": req_date,
        "requested_start_date": start_date,
        "requested_end_date": end_date,
        "parameter": parameter,
        "agriculture_intent": agri_intent,
        "historical_intent": hist_intent,
        "climate_trend_intent": climate_intent,
        "imd_intent": imd_intent,
        "imd_forecast_day": imd_day,
        "detected_language": lang_code,
        "is_romanized": is_romanized,
        "error_message": date_err,
        "is_weather_related": True
    }


def _empty_query_response() -> Dict[str, Any]:
    return {
        "original_query": "",
        "normalized_query": "",
        "intent": "weather",
        "location": None,
        "time": "current",
        "requested_date": None,
        "requested_start_date": None,
        "requested_end_date": None,
        "parameter": "general",
        "agriculture_intent": False,
        "historical_intent": False,
        "climate_trend_intent": False,
        "imd_intent": False,
        "imd_forecast_day": None,
        "detected_language": "en",
        "is_romanized": False,
        "error_message": None,
        "is_weather_related": True
    }


def _check_agriculture_intent(text: str) -> bool:
    patterns = [
        r"\b(pesticide|pesticides|fertilizer|fertilizers|spray|spraying)\b",
        r"\b(farmer|farmers|farming|crop|crops|harvest|harvesting|sowing|irrigation|agriculture|field)\b"
    ]
    return any(re.search(p, text) for p in patterns)


def _check_imd_intent(text: str) -> Tuple[bool, Optional[int]]:
    is_imd = bool(re.search(r"\b(imd|official\s+warning|imd\s+warning|imd\s+alert|government\s+warning)\b", text))
    forecast_day = 1
    if "tomorrow" in text or "repu" in text or "kal" in text:
        forecast_day = 2
    elif "day after tomorrow" in text:
        forecast_day = 3
    return (is_imd, forecast_day if is_imd else None)


def _check_climate_intent(text: str) -> bool:
    patterns = [
        r"\b(climate\s+trend|climate\s+change)\b",
        r"\b(increasing\s+or\s+decreasing|increasing|decreasing)\b",
        r"\b(how\s+has\s+(rainfall|temperature|weather)\s+changed)\b",
        r"\bcompare\s+(rainfall|temperature|\d{4})\b",
        r"\bcompare\s+\d{4}\s+(to|and|\-)\s+\d{4}\b"
    ]
    return any(re.search(p, text) for p in patterns)


def _check_historical_intent(text: str, current_year: int) -> Tuple[bool, Optional[int]]:
    if "last year" in text:
        return (True, current_year - 1)
    if "yesterday" in text:
        return (True, None)
    
    # Match years like in 2024, in 2023, 2022
    year_match = re.search(r"\b(in\s+)?(19\d\d|20[0-2]\d)\b", text)
    if year_match:
        matched_year = int(year_match.group(2))
        if matched_year < current_year:
            return (True, matched_year)

    if any(k in text for k in ["was the rainfall", "was the temperature", "historical", "history", "in the past", "what happened on"]):
        return (True, None)

    return (False, None)


def _extract_parameter(text: str) -> str:
    if re.search(r"\b(max\s+temp|maximum\s+temperature|highest\s+temp|hottest)\b", text):
        return "max_temperature"
    if re.search(r"\b(min\s+temp|minimum\s+temperature|lowest\s+temp|coldest)\b", text):
        return "min_temperature"
    if re.search(r"\b(feels?\s+like|apparent\s+temp|heat\s+index|how\s+hot\s+will\s+it\s+feel)\b", text):
        return "apparent_temperature"
    if re.search(r"\b(temperature|temp|how\s+hot|how\s+cold|warmth)\b", text):
        return "temperature"
    if re.search(r"\b(humidity|humid|moisture)\b", text):
        return "humidity"
    if re.search(r"\b(rain\s+probability|chance\s+of\s+rain|rain\s+chance|probability\s+of\s+rain)\b", text):
        return "rain_probability"
    if re.search(r"\b(rain|rainfall|precipitation|rainy|showers|downpour|drizzle)\b", text):
        return "rainfall"
    if re.search(r"\b(wind\s+gust|gusts)\b", text):
        return "wind_gust"
    if re.search(r"\b(wind\s+direction|which\s+direction)\b", text):
        return "wind_direction"
    if re.search(r"\b(max\s+wind|highest\s+wind)\b", text):
        return "max_wind"
    if re.search(r"\b(wind|wind\s+speed|how\s+fast\s+is\s+the\s+wind|breeze|stormy)\b", text):
        return "wind"
    if re.search(r"\b(uv|uv\s+index|ultraviolet|sun\s+rays)\b", text):
        return "uv_index"
    if re.search(r"\b(dew\s+point)\b", text):
        return "dew_point"
    if re.search(r"\b(surface\s+pressure|pressure|atmospheric\s+pressure|barometer)\b", text):
        return "surface_pressure"
    if re.search(r"\b(cloud\s+cover|clouds|cloudy|overcast)\b", text):
        return "cloud_cover"
    if re.search(r"\b(visibility|fog|mist|can\s+i\s+see)\b", text):
        return "visibility"
    if re.search(r"\b(condition|weather\s+condition|status)\b", text):
        return "weather_condition"

    return "general"


def _extract_location(text: str, original: str) -> Optional[str]:
    """
    Extract location name using prepositions, Romanized markers ('lo', 'mein'),
    and pattern matching, filtering out common stop words and punctuation.
    """
    clean_text = re.sub(r"[^\w\s]", " ", text)
    clean_text = re.sub(r"\s+", " ", clean_text).strip()

    # 1. Check Romanized '<city> lo' or '<city> mein'
    lo_match = re.search(r"\b([a-zA-Z]+)\s+(lo|mein)\b", clean_text)
    if lo_match:
        cand = lo_match.group(1).strip().lower()
        if cand not in STOP_WORDS_FOR_LOCATION:
            return cand

    # 2. Check patterns like 'in <city>', 'for <city>', 'at <city>', 'near <city>'
    prep_match = re.search(r"\b(in|for|at|near)\s+([a-zA-Z\s]+)", clean_text)
    if prep_match:
        cand_str = prep_match.group(2).strip()
        words = cand_str.split()
        valid_words = []
        for w in words:
            if w.lower() in STOP_WORDS_FOR_LOCATION:
                break
            valid_words.append(w.lower())
        if valid_words:
            return " ".join(valid_words)

    # 3. Check '<city> weather' or 'weather <city>'
    cw_match = re.search(r"\b([a-zA-Z]+)\s+weather\b", clean_text)
    if cw_match:
        cand = cw_match.group(1).strip().lower()
        if cand not in STOP_WORDS_FOR_LOCATION:
            return cand

    wc_match = re.search(r"\bweather\s+([a-zA-Z]+)\b", clean_text)
    if wc_match:
        cand = wc_match.group(1).strip().lower()
        if cand not in STOP_WORDS_FOR_LOCATION:
            return cand

    return None


def _extract_dates_and_ranges(text: str, current_year: int, year_match: Optional[int]) -> Tuple[str, Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Extract date and date ranges, validate month boundaries (e.g. Sep 31 error).
    Returns (time_val, requested_date, requested_start_date, requested_end_date, error_message).
    """
    # Check date range: "September 1 to September 5" or "Sep 1 - Sep 5" or "from Sep 1 to Sep 5"
    range_regex = r"(from|between)?\s*([a-zA-Z]+|\d{4}-\d{2}-\d{2})\s+(\d{1,2})(?:st|nd|rd|th)?\s*(?:to|\-|through|and)\s*([a-zA-Z]+)?\s*(\d{1,2})(?:st|nd|rd|th)?(?:\s+(\d{4}))?"
    rmatch = re.search(range_regex, text)
    if rmatch:
        m1_str = rmatch.group(2).lower()
        d1_str = rmatch.group(3)
        m2_str = (rmatch.group(4) or m1_str).lower()
        d2_str = rmatch.group(5)
        yr_str = rmatch.group(6) or (str(year_match) if year_match else str(current_year))

        if m1_str in MONTH_MAP and m2_str in MONTH_MAP:
            m1 = MONTH_MAP[m1_str]
            m2 = MONTH_MAP[m2_str]
            d1 = int(d1_str)
            d2 = int(d2_str)
            yr = int(yr_str)

            # Validate dates
            if d1 > DAYS_IN_MONTH.get(m1, 31):
                return ("date_range", None, None, None, f"{MONTH_NAMES_LIST[m1-1].capitalize()} has only {DAYS_IN_MONTH[m1]} days. Please provide a valid date.")
            if d2 > DAYS_IN_MONTH.get(m2, 31):
                return ("date_range", None, None, None, f"{MONTH_NAMES_LIST[m2-1].capitalize()} has only {DAYS_IN_MONTH[m2]} days. Please provide a valid date.")

            start_iso = f"{yr:04d}-{m1:02d}-{d1:02d}"
            end_iso = f"{yr:04d}-{m2:02d}-{d2:02d}"
            return ("date_range", None, start_iso, end_iso, None)

    # Check multi-year compare range: "compare 2022 to 2025" or "from 2022 to 2025"
    year_range_match = re.search(r"(from|between|compare)?\s*(19\d\d|20[0-2]\d)\s*(to|\-|and|through)\s*(19\d\d|20[0-2]\d)", text)
    if year_range_match:
        y1 = int(year_range_match.group(2))
        y2 = int(year_range_match.group(4))
        return ("date_range", None, f"{y1}-01-01", f"{y2}-12-31", None)

    # Check single date: "September 10", "10 September", "2024-09-10"
    iso_match = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if iso_match:
        yr = int(iso_match.group(1))
        mo = int(iso_match.group(2))
        dy = int(iso_match.group(3))
        if mo < 1 or mo > 12 or dy < 1 or dy > DAYS_IN_MONTH.get(mo, 31):
            return ("date", None, None, None, "Invalid date format or day out of range for the month.")
        return ("date", f"{yr:04d}-{mo:02d}-{dy:02d}", None, None, None)

    # "September 31" or "31 September"
    single_date_match1 = re.search(r"\b([a-zA-Z]+)\s+(\d{1,2})(?:st|nd|rd|th)?(?:\s+(\d{4}))?\b", text)
    if single_date_match1:
        m_str = single_date_match1.group(1).lower()
        if m_str in MONTH_MAP:
            mo = MONTH_MAP[m_str]
            dy = int(single_date_match1.group(2))
            yr = int(single_date_match1.group(3)) if single_date_match1.group(3) else (year_match or current_year)
            if dy > DAYS_IN_MONTH.get(mo, 31):
                return ("date", None, None, None, f"{MONTH_NAMES_LIST[mo-1].capitalize()} has only {DAYS_IN_MONTH[mo]} days. Please provide a valid date.")
            return ("date", f"{yr:04d}-{mo:02d}-{dy:02d}", None, None, None)

    single_date_match2 = re.search(r"\b(\d{1,2})(?:st|nd|rd|th)?\s+([a-zA-Z]+)(?:\s+(\d{4}))?\b", text)
    if single_date_match2:
        m_str = single_date_match2.group(2).lower()
        if m_str in MONTH_MAP:
            mo = MONTH_MAP[m_str]
            dy = int(single_date_match2.group(1))
            yr = int(single_date_match2.group(3)) if single_date_match2.group(3) else (year_match or current_year)
            if dy > DAYS_IN_MONTH.get(mo, 31):
                return ("date", None, None, None, f"{MONTH_NAMES_LIST[mo-1].capitalize()} has only {DAYS_IN_MONTH[mo]} days. Please provide a valid date.")
            return ("date", f"{yr:04d}-{mo:02d}-{dy:02d}", None, None, None)

    # Check relative terms
    if "tomorrow" in text or "repu" in text or "kal" in text:
        return ("tomorrow", None, None, None, None)
    if "yesterday" in text or "ninna" in text:
        return ("yesterday", None, None, None, None)
    if "tonight" in text:
        return ("tonight", None, None, None, None)
    if "today" in text or "eroju" in text or "ivala" in text or "aaj" in text:
        return ("today", None, None, None, None)

    return ("current", None, None, None, None)

"""
Language Service for WeatherGPT.
Detects natural languages (Telugu, Hindi, Tamil, Kannada, Malayalam, Bengali, etc.),
identifies Romanized Indian queries (Roman Telugu, Roman Hindi), and provides
deterministic translation mappings.
"""

import re
from typing import Dict, Any, Tuple, Optional

SCRIPT_RANGES = {
    "te": (0x0C00, 0x0C7F, "Telugu"),
    "hi": (0x0900, 0x097F, "Hindi"),
    "ta": (0x0B80, 0x0BFF, "Tamil"),
    "kn": (0x0C80, 0x0CFF, "Kannada"),
    "ml": (0x0D00, 0x0D7F, "Malayalam"),
    "bn": (0x0980, 0x09FF, "Bengali"),
    "gu": (0x0A80, 0x0AFF, "Gujarati"),
    "pa": (0x0A00, 0x0A7F, "Punjabi"),
    "ur": (0x0600, 0x06FF, "Urdu"),
    "mr": (0x0900, 0x097F, "Marathi")
}

ROMAN_TELUGU_PATTERNS = [
    r"\beroju\b", r"\brepu\b", r"\bninna\b", r"\bivala\b", r"\bivvala\b",
    r"\bvarsham\b", r"\bvarshalu\b", r"\bvaana\b", r"\bvundhi\b", r"\bundhi\b",
    r"\bundi\b", r"\bela\s+(v?undhi|undi)\b", r"\bentha\b", r"\buntunda\b",
    r"\buntundha\b", r"\bpystada\b", r"\bpadutunda\b", r"\bpaduthundha\b",
    r"\bekkuva\b", r"\bchali\b", r"\beguvva\b", r"\bmausam\b", r"\bkaala\b",
    r"\b\w+\s+lo\s+(weather|rain|temperature|varsham|gaali)\b",
    r"\b\w+\s+lo\b"
]

ROMAN_HINDI_PATTERNS = [
    r"\baaj\b", r"\bkal\b", r"\bparso\b", r"\bmausam\b", r"\bkaisa\s+hai\b",
    r"\bbaarish\b", r"\bhogi\s+kya\b", r"\bkitna\s+tapman\b", r"\bkitni\s+garmi\b",
    r"\btapman\b", r"\bhawa\b", r"\bthand\b", r"\bkya\s+kal\b", r"\bmein\s+mausam\b"
]


def detect_language(query: str) -> Tuple[str, str, bool]:
    """
    Detect language code, language name, and whether it is Romanized.
    Returns (lang_code, lang_name, is_romanized).
    """
    if not query or not query.strip():
        return ("en", "English", False)

    text = query.strip()

    # 1. Check Unicode scripts
    char_counts: Dict[str, int] = {}
    for char in text:
        cp = ord(char)
        for code, (start, end, name) in SCRIPT_RANGES.items():
            if start <= cp <= end:
                char_counts[code] = char_counts.get(code, 0) + 1

    if char_counts:
        top_lang = max(char_counts.items(), key=lambda x: x[1])[0]
        lang_name = SCRIPT_RANGES[top_lang][2]
        return (top_lang, lang_name, False)

    lower_text = text.lower()

    # 2. Check Romanized Telugu
    telugu_matches = sum(1 for pattern in ROMAN_TELUGU_PATTERNS if re.search(pattern, lower_text))
    if telugu_matches >= 1:
        return ("te-Latn", "Telugu (Romanized)", True)

    # 3. Check Romanized Hindi
    hindi_matches = sum(1 for pattern in ROMAN_HINDI_PATTERNS if re.search(pattern, lower_text))
    if hindi_matches >= 1:
        return ("hi-Latn", "Hindi (Romanized)", True)

    return ("en", "English", False)


def normalize_romanized_query(query: str, lang_code: str) -> str:
    """
    Deterministically normalize common Romanized Indian phrases into standard English
    so the query engine can extract location, date, and parameter precisely.
    """
    if not query:
        return ""

    text = query.strip().lower()

    if "te" in lang_code:
        # Time replacements
        text = re.sub(r"\b(eroju|ivala|ivvala)\b", "today", text)
        text = re.sub(r"\b(repu)\b", "tomorrow", text)
        text = re.sub(r"\b(ninna)\b", "yesterday", text)
        
        # Weather terms
        text = re.sub(r"\b(varsham|vaana|rain)\s+(untunda|padutunda|paduthundha|untundha)\b", "will it rain", text)
        text = re.sub(r"\b(varsham|vaana)\b", "rain", text)
        text = re.sub(r"\b(temperature|thapograhatha|heat)\s+entha\b", "what is the temperature", text)
        text = re.sub(r"\b(ela\s+(v?undhi|undi))\b", "how is the weather", text)
        text = re.sub(r"\b(ekkuva\s+untunda)\b", "will it be high", text)
        text = re.sub(r"\b(gaali)\b", "wind", text)

        # Convert '<city> lo' into 'in <city>'
        text = re.sub(r"(\b[a-zA-Z]+)\s+lo\b", r"in \1", text)

    elif "hi" in lang_code:
        text = re.sub(r"\b(aaj)\b", "today", text)
        text = re.sub(r"\b(kal)\b", "tomorrow", text)
        text = re.sub(r"\b(baarish\s+(hogi\s+kya|hogi))\b", "will it rain", text)
        text = re.sub(r"\b(baarish)\b", "rain", text)
        text = re.sub(r"\b(kaisa\s+hai)\b", "how is the weather", text)
        text = re.sub(r"\b(tapman\s+kitna\s+hai)\b", "what is the temperature", text)
        text = re.sub(r"(\b[a-zA-Z]+)\s+mein\b", r"in \1", text)

    return text

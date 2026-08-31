"""
Language Detection and Linguistic Normalization Engine.
Supports English, Hindi (Devanagari), and Romanized Hindi (Hinglish).
"""
import re
from typing import Dict, Any, Tuple


class LanguageDetector:
    # Devanagari Unicode range: \u0900-\u097F
    DEVANAGARI_REGEX = re.compile(r'[\u0900-\u097F]')
    
    # Common Hinglish markers
    HINGLISH_KEYWORDS = {
        "karo", "karna", "gaya", "gayi", "raha", "rahi", "hai", "hain",
        "kaise", "kyun", "kya", "ek", "aur", "mein", "par", "se", "ko",
        "gaon", "barsat", "pani", "bacha", "maa", "ghar", "raat"
    }

    @classmethod
    def detect_language(cls, text: str) -> Tuple[str, float]:
        """
        Detects whether text is Hindi (hi) or English (en) and returns (lang_code, confidence).
        """
        if not text or not text.strip():
            return "en", 1.0

        # Check for Devanagari script characters
        devanagari_chars = len(cls.DEVANAGARI_REGEX.findall(text))
        total_alpha = sum(1 for c in text if c.isalpha())

        if total_alpha > 0 and (devanagari_chars / total_alpha) > 0.15:
            return "hi", 0.98

        # Check for Hinglish words
        words = set(re.findall(r'\b[a-zA-Z]+\b', text.lower()))
        hinglish_matches = words.intersection(cls.HINGLISH_KEYWORDS)
        if len(hinglish_matches) >= 2 or (len(words) > 0 and len(hinglish_matches) / len(words) > 0.2):
            return "hi", 0.85

        return "en", 0.95

    @classmethod
    def get_language_metadata(cls, lang_code: str) -> Dict[str, Any]:
        if lang_code == "hi":
            return {
                "language_code": "hi",
                "display_name": "Hindi (हिंदी)",
                "default_voice_male": "hi-IN-MadhurNeural",
                "default_voice_female": "hi-IN-SwaraNeural",
                "script": "Devanagari / Romanized Hindi",
                "locale": "hi-IN"
            }
        return {
            "language_code": "en",
            "display_name": "English",
            "default_voice_male": "en-US-ChristopherNeural",
            "default_voice_female": "en-IN-NeerjaNeural",
            "script": "Latin",
            "locale": "en-US"
        }

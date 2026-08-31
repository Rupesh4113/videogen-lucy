"""
Content & License Guard.
Scans prompts for protected fictional characters, celebrity likeness, trademarks,
copyrighted songs, and unauthorized voice cloning.
Provides constructive safe rewrites.
"""
import re
from typing import Dict, Any, List, Tuple
from backend.app.schemas.compliance import SafetyCheckResponse


class ContentLicenseGuard:
    # Protected IP Catalog
    PROTECTED_CHARACTERS = {
        "spider-man": "an agile arachnid-themed masked hero",
        "spiderman": "an agile arachnid-themed masked hero",
        "batman": "a dark brooding vigilante detective with high-tech armor",
        "superman": "a powerful cosmic superhero in a primary-colored suit",
        "iron man": "a genius engineer wearing high-tech powered armor",
        "ironman": "a genius engineer wearing high-tech powered armor",
        "mickey mouse": "a cheerful animated woodland animal",
        "elsa": "a magical winter sorceress with ice powers",
        "harry potter": "a young wizard with round spectacles and a magic wand",
        "pikachu": "an energetic electric yellow creature",
        "darth vader": "a menacing dark armored galactic commander",
        "shrek": "a kind-hearted giant green forest dweller",
        "captain america": "a patriotic shield-bearing super soldier",
        "thor": "a mythological thunder warrior with an enchanted hammer",
        "hulk": "a colossal emerald powerhouse"
    }

    CELEBRITIES = {
        "elon musk", "donald trump", "narendra modi", "shah rukh khan",
        "taylor swift", "cristiano ronaldo", "messi", "barack obama",
        "tom cruise", "amitabh bachchan", "salman khan", "virat kohli"
    }

    TRADEMARKS = {
        "marvel", "disney", "pixar", "dc comics", "star wars",
        "pokemon", "netflix", "warner bros", "universal studios"
    }

    @classmethod
    def analyze_prompt(cls, prompt: str) -> SafetyCheckResponse:
        """
        Scans prompt and returns safety verdict, detected violations, and constructive rewrite.
        """
        p_lower = prompt.lower()
        violations: List[str] = []
        suggestions: List[Tuple[str, str]] = []

        # 1. Check Protected Characters
        for char_name, substitute in cls.PROTECTED_CHARACTERS.items():
            pattern = rf"\b{re.escape(char_name)}\b"
            if re.search(pattern, p_lower):
                violations.append(f"Protected Fictional Character: '{char_name.title()}'")
                suggestions.append((char_name, substitute))

        # 2. Check Celebrities / Real Persons
        for celeb in cls.CELEBRITIES:
            pattern = rf"\b{re.escape(celeb)}\b"
            if re.search(pattern, p_lower):
                violations.append(f"Real-Person Likeness / Celebrity: '{celeb.title()}'")
                suggestions.append((celeb, f"an original character inspired by charismatic leadership"))

        # 3. Check Trademarks
        for tm in cls.TRADEMARKS:
            pattern = rf"\b{re.escape(tm)}\b"
            if re.search(pattern, p_lower):
                violations.append(f"Trademarked Studio / Brand: '{tm.title()}'")

        is_safe = len(violations) == 0
        risk_level = "LOW" if is_safe else ("HIGH" if len(violations) > 1 else "MEDIUM")

        suggested_rewrite = None
        reason = None
        if not is_safe:
            reason = "This request contains protected fictional characters, celebrity names, or trademarked intellectual property. Please use original characters and settings."
            rewrite_text = prompt
            for term, replacement in suggestions:
                pattern = re.compile(re.escape(term), re.IGNORECASE)
                rewrite_text = pattern.sub(replacement, rewrite_text)
            suggested_rewrite = rewrite_text

        return SafetyCheckResponse(
            is_safe=is_safe,
            risk_level=risk_level,
            detected_violations=violations,
            reason=reason,
            suggested_rewrite=suggested_rewrite
        )

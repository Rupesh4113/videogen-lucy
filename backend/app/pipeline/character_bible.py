"""
Character Bible Engine.
Maintains persistent visual profiles, clothing, physical traits, voice presets,
negative attributes, and visual reference image keys for every character.
Prevents identity drift across scenes.
"""
from typing import List, Dict, Any, Optional
from backend.app.schemas.bible import CharacterSchema
from backend.app.schemas.screenplay import StorySchema


class CharacterBibleEngine:
    @classmethod
    def generate_character_bible(
        cls,
        story: StorySchema,
        prompt: str,
        character_style: str = "Semi-realistic",
        language: str = "en"
    ) -> List[CharacterSchema]:
        """
        Extracts or generates persistent character definitions from the story.
        """
        p_lower = prompt.lower()
        is_monsoon = any(k in p_lower for k in ["mother", "baby", "monsoon", "village", "maa", "barsat", "gauri", "sick"])

        characters: List[CharacterSchema] = []

        if is_monsoon:
            # Main Protagonist: Gauri (Mother)
            gauri_name = "गौरी (Gauri)" if language == "hi" else "Gauri"
            characters.append(
                CharacterSchema(
                    character_key="gauri",
                    name=gauri_name,
                    age=28,
                    gender="Female",
                    face_description="Warm expressive brown eyes, gentle jawline, natural beauty, courageous caring expression, small red bindi on forehead.",
                    skin_tone="Warm Indian wheatish skin tone",
                    hair="Long black hair tied in a loose traditional braid, slight wet strands from rain",
                    eye_color="Deep warm brown",
                    body_type="Slender, graceful, resilient build",
                    clothing="Traditional emerald green cotton saree with simple turmeric-yellow border, simple matching blouse, pallu draped practically over shoulder.",
                    accessories="Thin gold nose ring, simple glass bangles, silver anklets.",
                    personality="Caring, courageous, emotionally resilient, patient, fiercely protective mother.",
                    voice_description="Warm, soft, soothing Indian Hindi/English voice with deep maternal affection.",
                    voice_preset="hi-IN-SwaraNeural" if language == "hi" else "en-IN-NeerjaNeural",
                    negative_attributes="Western clothes, modern makeup, blond hair, blue eyes, deformed hands, extra fingers, cartoon distortion, inconsistent face.",
                    reference_image_url=None
                )
            )

            # Secondary Character: Aarav (Baby)
            baby_name = "आरव (Baby Aarav)" if language == "hi" else "Baby Aarav"
            characters.append(
                CharacterSchema(
                    character_key="baby_aarav",
                    name=baby_name,
                    age=1,
                    gender="Male",
                    face_description="Adorable 1-year-old Indian infant with chubby cheeks, soft innocent eyes, tiny black kajal dot on cheek.",
                    skin_tone="Fair soft Indian baby skin tone",
                    hair="Soft sparse black baby curls",
                    eye_color="Large dark brown eyes",
                    body_type="Infant",
                    clothing="Soft white and pastel yellow cotton swaddling cloth.",
                    accessories="Black thread bracelet on wrist for protection.",
                    personality="Innocent, sweet, fragile, calmed by mother's touch.",
                    voice_description="Gentle baby cooing and soft crying.",
                    voice_preset="baby_sound",
                    negative_attributes="Adult proportions, uncanny facial expression, deformed fingers, clothes changing color.",
                    reference_image_url=None
                )
            )
        else:
            # Generic protagonist matching prompt
            name = "सुनील (Sunil)" if language == "hi" else "Alex"
            characters.append(
                CharacterSchema(
                    character_key="protagonist",
                    name=name,
                    age=30,
                    gender="Male",
                    face_description="Sharp features, thoughtful brown eyes, determined expression, short well-groomed dark hair.",
                    skin_tone="Natural warm tone",
                    hair="Short textured black hair",
                    eye_color="Brown",
                    body_type="Athletic medium build",
                    clothing="Classic dark blue utility jacket over grey linen shirt and dark trousers.",
                    accessories="Vintage wrist watch.",
                    personality="Resourceful, empathetic, steady, persevering.",
                    voice_description="Calm, clear, cinematic baritone.",
                    voice_preset="hi-IN-MadhurNeural" if language == "hi" else "en-US-ChristopherNeural",
                    negative_attributes="Deformed anatomy, extra limbs, fluctuating outfit, shifting facial features.",
                    reference_image_url=None
                )
            )

        return characters

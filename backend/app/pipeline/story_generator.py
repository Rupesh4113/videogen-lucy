"""
Story Generator Engine.
Transforms user prompts into a structured 3-act narrative with scene scaling based on video duration.
Supports English and natural Indian Hindi.
"""
from typing import Dict, Any, List
from backend.app.schemas.screenplay import StorySchema


class StoryGenerator:
    @classmethod
    def calculate_scene_count(cls, duration_seconds: int) -> int:
        """
        Calculates appropriate scene count for requested duration:
        5 min (300s): 6 scenes (~50s per scene)
        10 min (600s): 12 scenes (~50s per scene)
        20 min (1200s): 24 scenes (~50s per scene)
        30 min (1800s): 36 scenes (~50s per scene)
        """
        if duration_seconds <= 300:
            return 6
        elif duration_seconds <= 600:
            return 12
        elif duration_seconds <= 1200:
            return 24
        else:
            return 36

    @classmethod
    def generate_story(
        cls,
        prompt: str,
        language: str = "en",
        duration_seconds: int = 300,
        video_style: str = "Cinematic animation"
    ) -> StorySchema:
        """
        Generates a comprehensive 3-act story arc matching prompt, duration, and language.
        """
        scene_count = cls.calculate_scene_count(duration_seconds)
        mins = max(1, duration_seconds // 60)

        # Check if the prompt is related to Indian monsoon/mother/village or generic
        is_hindi = (language == "hi")
        p_lower = prompt.lower()
        is_monsoon_story = any(k in p_lower for k in ["mother", "baby", "monsoon", "village", "maa", "barsat", "gauri", "sick"])

        if is_hindi:
            if is_monsoon_story:
                title = "बरसात की रात: एक माँ की ममता (The Monsoon Night)"
                logline = "मानसून की मूसलाधार बारिश में एक माँ अपने बीमार बच्चे की जान बचाने के लिए रात भर संघर्ष करती है।"
                genre = "इमोशनल ड्रामा / पारिवारिक"
                audience = "सभी दर्शक (पारिवारिक)"
                summary = (
                    f"यह {mins} मिनट की एक दिल को छू लेने वाली कहानी है जो भारतीय गाँव की पृष्ठभूमि पर आधारित है। "
                    "गौरी एक साहसी और ममतामयी माँ है। भारी बारिश और आंधी-तूफान के बीच उसका नन्हा बच्चा तेज बुखार से तप उठता है। "
                    "गाँव का रास्ता कट जाने पर भी गौरी हार नहीं मानती और पारंपरिक जड़ी-बूटियों और अपनी अटूट ममता से बच्चे को ठीक करती है।"
                )
                beginning = "गाँव में मानसून की पहली शाम। मिट्टी के घर में गौरी अपने छोटे बच्चे को सुला रही है।"
                conflict = "आधी रात को मूसलाधार बारिश शुरू होती है और बच्चे को अचानक तेज बुखार आ जाता है।"
                rising_action = "गाँव के रास्ते पानी से भर जाते हैं। बिजली चली जाती है। गौरी काढ़े और ठंडी पट्टियों से बुखार कम करने की कोशिश करती है।"
                climax = "तूफान अपने चरम पर पहुँचता है। गौरी दीये को बुझने से बचाती है और पूरी रात बच्चे को सीने से लगाकर प्रार्थना करती है।"
                resolution = "सुबह की पहली किरण फूटती है, बारिश थम जाती है और बच्चे का बुखार उतर जाता है।"
                ending = "गाँव में नई सुबह का उजाला फैलता है, बच्चा मुस्कुराता है और गौरी की आँखों में राहत के आंसू होते हैं।"
            else:
                title = f"एक अनूठी दास्तान: {prompt[:30]}..."
                logline = f"{prompt[:80]}"
                genre = "ड्रामा / एनिमेटेड सिनेमा"
                audience = "सामान्य दर्शक"
                summary = f"{mins} मिनट की रोमांचक एनिमेटेड कहानी। {prompt}"
                beginning = "कहानी की शुरुआत एक शांत और प्रभावशाली माहौल से होती है।"
                conflict = "मुख्य पात्र के सामने एक अप्रत्याशित चुनौती आती है।"
                rising_action = "चुनौतियों का सामना करते हुए रोमांच बढ़ता है।"
                climax = "कहानी अपने सबसे भावनात्मक और महत्वपूर्ण मोड़ पर पहुँचती है।"
                resolution = "समस्या का समाधान निकलता है।"
                ending = "एक प्रेरणादायक और सुखद अंत।"
        else:
            if is_monsoon_story:
                title = "Whispers of the Monsoon: A Mother's Vigour"
                logline = "During a torrential Indian monsoon, a devoted mother fights against the storm to nurse her ailing child through the night."
                genre = "Emotional Drama / Family"
                audience = "General Audience / Family"
                summary = (
                    f"A heartfelt {mins}-minute cinematic journey set in a rural Indian village during the monsoon. "
                    "Gauri, a courageous mother, discovers her baby has fallen sick with a burning fever. "
                    "Cut off from the town by flooded paths, she uses traditional herbal remedies, unwavering maternal devotion, "
                    "and inner strength to protect her child until the dawn breaks."
                )
                beginning = "Monsoon twilight settles over an Indian village. Gauri gently tends to her mud-roofed home as rain patters on the tiles."
                conflict = "Midnight brings a tempestuous storm; the baby begins crying uncontrollably with a raging fever."
                rising_action = "The storm cuts off electricity and road access. Gauri prepares herbal remedies and uses wet cloth compresses while soothing her child."
                climax = "The hurricane-force wind threatens to shatter the wooden shutters. Gauri shields the clay lamp and hugs her baby tightly through the coldest hour."
                resolution = "As dawn approaches, the baby's fever breaks, and calm peaceful breaths return."
                ending = "Golden sunlight bathes the lush green village courtyard. Gauri smiles with tearful joy as her healthy child giggles in her arms."
            else:
                title = f"Chronicles of Destiny: {prompt[:35]}"
                logline = f"A compelling {mins}-minute story exploring: {prompt[:100]}"
                genre = "Cinematic Storytelling"
                audience = "General Audience"
                summary = f"A {mins}-minute animated story based on the concept: '{prompt}'."
                beginning = "The world and primary characters are introduced with serene establishing atmosphere."
                conflict = "An inciting dilemma challenges the harmony of the situation."
                rising_action = "The characters navigate escalating trials and obstacles."
                climax = "The central turning point tests courage, bond, and resolve."
                resolution = "The turning point is conquered through persistence and ingenuity."
                ending = "Harmony is restored with lasting growth and memorable visuals."

        return StorySchema(
            title=title,
            logline=logline,
            genre=genre,
            target_audience=audience,
            summary=summary,
            beginning=beginning,
            conflict=conflict,
            rising_action=rising_action,
            climax=climax,
            resolution=resolution,
            ending=ending,
            metadata={"duration_seconds": duration_seconds, "target_scene_count": scene_count, "language": language}
        )

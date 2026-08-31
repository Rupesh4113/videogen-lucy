"""
Environment Bible Engine.
Maintains persistent visual profiles, architectural details, lighting conditions,
weather patterns, and props for all story locations.
"""
from typing import List, Dict, Any, Optional
from backend.app.schemas.bible import LocationSchema
from backend.app.schemas.screenplay import StorySchema


class EnvironmentBibleEngine:
    @classmethod
    def generate_environment_bible(
        cls,
        story: StorySchema,
        prompt: str,
        language: str = "en"
    ) -> List[LocationSchema]:
        """
        Generates consistent environment profiles based on the story.
        """
        p_lower = prompt.lower()
        is_monsoon = any(k in p_lower for k in ["mother", "baby", "monsoon", "village", "maa", "barsat", "gauri", "sick"])

        locations: List[LocationSchema] = []

        if is_monsoon:
            # 1. Indian Village Mud House (Interior)
            loc1_name = "गाँव का मिट्टी का घर (कमरा)" if language == "hi" else "Village House Bedroom"
            locations.append(
                LocationSchema(
                    location_key="village_bedroom",
                    name=loc1_name,
                    description="Cozy rural Indian home interior with smooth clay-plastered walls, wooden ceiling beams, a small wooden cot (charpai) with clean handmade cotton quilt, and a vintage brass oil lamp (diya) glowing warmly.",
                    architecture="Traditional rural Indian mud-brick and timber structure with terracotta tile roof.",
                    colors="Warm terracotta, ochre, clay brown, brass gold, soft shadowed greens.",
                    weather="Monsoon rain outside the small carved wooden window with rain trickling down.",
                    lighting="Warm intimate amber glow from a single brass oil lamp, contrasted with moody dark blue storm lighting outside the window.",
                    time_of_day="Night (Monsoon Storm)",
                    props="Brass oil lamp, wooden cot, earthenware water jug (matka), herbal pestle & mortar, small brass spoon, clean cotton cloths.",
                    camera_style="Cinematic shallow depth of field, warm intimate framing.",
                    reference_image_url=None
                )
            )

            # 2. Indian Village House (Exterior / Courtyard)
            loc2_name = "घर का आँगन व गाँव का दृश्य" if language == "hi" else "Village Courtyard & Pathway"
            locations.append(
                LocationSchema(
                    location_key="village_courtyard",
                    name=loc2_name,
                    description="Rustic Indian village courtyard with lush rain-washed green banana trees, wet mud path, tiled sloping roofs with cascading rainwater, and coconut palms swaying in the monsoon wind.",
                    architecture="Traditional rural Konkan/North Indian village cottages with tiled overhangs and mud walls.",
                    colors="Deep monsoon emerald green, wet earthy brown, storm grey sky, terracotta red.",
                    weather="Heavy monsoon rain with atmospheric mist, water puddles reflecting the dim sky.",
                    lighting="Atmospheric blue-grey diffused monsoon daylight turning to cinematic evening twilight.",
                    time_of_day="Late Twilight / Dawn",
                    props="Clay pots, wooden fence, rain-drenched tulsi plant pedestal in courtyard.",
                    camera_style="Wide atmospheric establishing shots, slow sweeping pan.",
                    reference_image_url=None
                )
            )
        else:
            # Generic scenic location
            loc_name = "मुख्य दृश्य स्थल" if language == "hi" else "Primary Setting"
            locations.append(
                LocationSchema(
                    location_key="primary_location",
                    name=loc_name,
                    description="Atmospheric cinematic setting matching the primary narrative world.",
                    architecture="Contemporary and organic architectural styling.",
                    colors="Harmonious cinematic palette with balanced contrast.",
                    weather="Dynamic natural atmosphere.",
                    lighting="Soft cinematic three-point lighting with motivated ambient sources.",
                    time_of_day="Day / Golden Hour",
                    props="Story-specific contextual items and props.",
                    camera_style="Cinematic wide and medium coverage.",
                    reference_image_url=None
                )
            )

        return locations

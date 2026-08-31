"""
Prompt Engineering Engine (PromptCompiler).
Assembles layered prompts combining Global Style, Character Consistency descriptions,
Environment references, Shot specifics, Camera movement, Lighting, and Negative constraints.
"""
from typing import Dict, Any, List, Optional
from backend.app.schemas.screenplay import SceneSchema, ShotSchema
from backend.app.schemas.bible import CharacterSchema, LocationSchema


class PromptCompiler:
    DEFAULT_NEGATIVE_PROMPT = (
        "deformed hands, missing fingers, extra fingers, distorted face, inconsistent clothing, "
        "text, watermark, logo, duplicate characters, flickering, jitter, unnatural motion, low quality, artifacting"
    )

    @classmethod
    def compile_shot_prompt(
        cls,
        shot: ShotSchema,
        scene: SceneSchema,
        characters: List[CharacterSchema],
        locations: List[LocationSchema],
        video_style: str = "Cinematic animation",
        continuity_note: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Compiles high-level scene and shot metadata into an optimized layered prompt for Wan2.1.
        """
        # 1. Global Style
        style_prompt = f"masterpiece cinematic render, {video_style}, highly detailed, realistic human movement, rich cinematic lighting, 8k resolution"

        # 2. Character Details
        char_prompts = []
        for c in characters:
            desc = f"{c.name}: {c.age}-year-old, {c.face_description} Wearing {c.clothing}."
            char_prompts.append(desc)
        character_prompt = " | ".join(char_prompts) if char_prompts else "Natural characters"

        # 3. Environment Details
        env_match = next((l for l in locations if l.name == scene.location_name or l.location_key in (scene.location_name or "")), None)
        if env_match:
            environment_prompt = f"{env_match.name}: {env_match.description} Architecture: {env_match.architecture}. Colors: {env_match.colors}."
        else:
            environment_prompt = f"Location: {scene.location_name or 'Cinematic setting'}, Time: {scene.time_of_day}, Lighting: {scene.lighting}."

        # 4. Shot Action & Motion
        shot_action = f"{shot.shot_type}: {shot.description}. Camera: {shot.camera_movement}."

        # 5. Continuity Context
        continuity_prompt = f"Continuity Context: {continuity_note}" if continuity_note else ""

        # 6. Combined Full Positive Prompt for Video Model
        full_positive = (
            f"{style_prompt}. "
            f"CHARACTERS: {character_prompt}. "
            f"ENVIRONMENT: {environment_prompt}. "
            f"ACTION: {shot_action}. "
            f"{continuity_prompt}"
        ).strip()

        # 7. Negative Prompt assembly
        neg_parts = [cls.DEFAULT_NEGATIVE_PROMPT]
        for c in characters:
            if c.negative_attributes:
                neg_parts.append(c.negative_attributes)
        full_negative = ", ".join(neg_parts)

        return {
            "style_prompt": style_prompt,
            "character_prompt": character_prompt,
            "environment_prompt": environment_prompt,
            "scene_prompt": scene.action or "",
            "shot_prompt": shot.description,
            "camera_prompt": shot.camera_movement,
            "lighting_prompt": scene.lighting or "Natural cinematic light",
            "continuity_prompt": continuity_prompt,
            "full_positive_prompt": full_positive,
            "negative_prompt": full_negative
        }

"""
Reference-Aware Prompt Engineering Engine (PromptCompiler).
Assembles 6-layer structured prompts combining:
1. Global Style & Style References
2. Character Consistency & Uploaded Character References
3. Environment Consistency & Uploaded Location References
4. Object / Prop References
5. Motion / Action Guidance & Video References
6. Negative Constraints & Identity Preservation
"""
from typing import Dict, Any, List, Optional
from backend.app.schemas.screenplay import SceneSchema, ShotSchema
from backend.app.schemas.bible import CharacterSchema, LocationSchema


class PromptCompiler:
    DEFAULT_NEGATIVE_PROMPT = (
        "deformed hands, missing fingers, extra fingers, distorted face, inconsistent clothing, "
        "character morphing, changing facial features, duplicate subjects, text, watermark, logo, "
        "flickering, jitter, unnatural jerky motion, low quality, visual artifacting, blurry background warp"
    )

    @classmethod
    def compile_shot_prompt(
        cls,
        shot: ShotSchema,
        scene: SceneSchema,
        characters: List[CharacterSchema],
        locations: List[LocationSchema],
        video_style: str = "Cinematic animation",
        camera_style: str = "Cinematic handheld",
        reference_media: Optional[List[Any]] = None,
        lock_character_appearance: bool = True,
        lock_environment: bool = True,
        continuity_note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compiles scene, shot, character, location, and uploaded reference media into
        an optimized conditioning prompt for AI video generation models.
        """
        reference_media = reference_media or []

        # 1. Style & Aesthetics Layer
        style_refs = [
            r.description for r in reference_media
            if getattr(r, "reference_category", "") in ("style", "overall") and r.description
        ]
        style_ref_text = f" Visual Inspiration: {'; '.join(style_refs)}." if style_refs else ""
        style_prompt = (
            f"masterpiece cinematic render, {video_style}, {camera_style}, "
            f"highly detailed realistic human motion, rich cinematic lighting, 8k resolution.{style_ref_text}"
        )

        # 2. Character Consistency Layer
        char_prompts = []
        for c in characters:
            desc = (
                f"{c.name}: {c.age}-year-old {c.gender or ''}, {c.face_description or ''}. "
                f"Skin tone: {c.skin_tone or 'natural'}. Hair: {c.hair or 'natural'}. "
                f"Wearing {c.clothing or 'traditional attire'}."
            )
            char_prompts.append(desc)
        
        char_refs = [
            r.description for r in reference_media
            if getattr(r, "reference_category", "") == "character" and r.description
        ]
        if char_refs:
            char_prompts.append(f"Character Reference Guidance: {'; '.join(char_refs)}.")
        if lock_character_appearance:
            char_prompts.append("Strict Identity Lock: Maintain exact facial features, hairstyle, and clothing consistently without drift.")

        character_prompt = " | ".join(char_prompts) if char_prompts else "Natural characters with consistent appearance"

        # 3. Environment & Architecture Layer
        env_match = next(
            (l for l in locations if l.name == scene.location_name or l.location_key in (scene.location_name or "")),
            None
        )
        if env_match:
            environment_prompt = (
                f"{env_match.name}: {env_match.description}. "
                f"Architecture: {env_match.architecture or 'authentic'}. "
                f"Colors: {env_match.colors or 'natural cinematic'}. "
                f"Time: {scene.time_of_day}, Lighting: {scene.lighting}."
            )
        else:
            environment_prompt = f"Location: {scene.location_name or 'Cinematic setting'}, Time: {scene.time_of_day}, Lighting: {scene.lighting}."

        loc_refs = [
            r.description for r in reference_media
            if getattr(r, "reference_category", "") == "location" and r.description
        ]
        if loc_refs:
            environment_prompt += f" Environment Reference: {'; '.join(loc_refs)}."
        if lock_environment:
            environment_prompt += " Strict Location Lock: Preserve background architecture and spatial layout."

        # 4. Object / Product References
        obj_refs = [
            r.description for r in reference_media
            if getattr(r, "reference_category", "") == "object" and r.description
        ]
        obj_prompt = f" OBJECTS: {'; '.join(obj_refs)}." if obj_refs else ""

        # 5. Motion, Action & Camera Layer
        shot_action = f"{shot.shot_type}: {shot.description}. Camera Movement: {shot.camera_movement}."
        motion_refs = [
            r.description for r in reference_media
            if getattr(r, "reference_category", "") == "motion" and r.description
        ]
        if motion_refs:
            shot_action += f" Motion Inspiration: {'; '.join(motion_refs)}."

        # 6. Continuity Context
        continuity_prompt = f"Continuity Context: {continuity_note}" if continuity_note else ""

        # 7. Combined Full Positive Prompt for Video Engine
        full_positive = (
            f"{style_prompt} "
            f"CHARACTERS: {character_prompt}. "
            f"ENVIRONMENT: {environment_prompt}. "
            f"ACTION: {shot_action}. "
            f"{obj_prompt}"
            f"{continuity_prompt}"
        ).strip()

        # 8. Negative Prompt Assembly
        neg_parts = [cls.DEFAULT_NEGATIVE_PROMPT]
        for c in characters:
            if getattr(c, "negative_attributes", None):
                neg_parts.append(str(c.negative_attributes))
        full_negative = ", ".join(neg_parts)

        # 9. Determine Starting Frame (if user designated start_frame reference)
        start_frame_path = None
        for r in reference_media:
            if getattr(r, "usage_mode", "") == "start_frame" and getattr(r, "file_path", None):
                if getattr(r, "media_type", "") == "image":
                    start_frame_path = r.file_path
                    break
                elif getattr(r, "extracted_keyframes_json", None) or getattr(r, "extracted_keyframes", None):
                    kfs = getattr(r, "extracted_keyframes_json", None) or getattr(r, "extracted_keyframes", [])
                    if kfs and len(kfs) > 0:
                        start_frame_path = kfs[0]
                        break

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
            "negative_prompt": full_negative,
            "start_frame_path": start_frame_path
        }

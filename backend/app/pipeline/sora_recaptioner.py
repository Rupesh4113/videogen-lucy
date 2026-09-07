"""
Sora Prompt Re-Captioning & Spacetime Patch Conditioning Engine.
Implements the Sora / DALL-E 3 video descriptive re-captioning architecture,
expanding concise prompts into dense, physically grounded spacetime descriptions.
"""
import os
import re
import json
import logging
from typing import Dict, Any, Optional, List
import urllib.request
import urllib.error

from backend.app.config import settings

logger = logging.getLogger("videogen.sora_recaptioner")


class SoraPromptRecaptioner:
    """
    Sora Descriptive Video Re-Captioner.
    Deconstructs visual concepts into dense 3D spacetime patch descriptions:
    - Subject & Materiality
    - Camera Optics & Parallax
    - Spatial Geometry & Environment
    - Volumetric Lighting & Atmospheric Physics
    - Temporal Kinematics (Beginning, Middle, End)
    """

    @classmethod
    def recaption_prompt(
        cls,
        prompt: str,
        style: Optional[str] = "Cinematic realism",
        camera_style: Optional[str] = "Slow cinematic tracking",
        duration_seconds: float = 5.0,
        aspect_ratio: str = "16:9",
        reference_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates a dense Sora-style descriptive caption.
        Uses OpenAI GPT API if available; otherwise uses deterministic spacetime expansion.
        """
        api_key = settings.SORA_API_KEY or settings.OPENAI_API_KEY
        
        if api_key and settings.SORA_ENABLE_RECAPTIONING:
            try:
                expanded = cls._call_llm_recaptioner(
                    api_key=api_key,
                    prompt=prompt,
                    style=style,
                    camera_style=camera_style,
                    duration_seconds=duration_seconds,
                    aspect_ratio=aspect_ratio,
                    reference_notes=reference_notes
                )
                if expanded and len(expanded.get("full_caption", "")) > 40:
                    return expanded
            except Exception as e:
                logger.warning(f"LLM re-captioning failed, falling back to heuristic spacetime compiler: {e}")

        return cls._heuristic_spacetime_recaption(
            prompt=prompt,
            style=style,
            camera_style=camera_style,
            duration_seconds=duration_seconds,
            aspect_ratio=aspect_ratio,
            reference_notes=reference_notes
        )

    @classmethod
    def _call_llm_recaptioner(
        cls,
        api_key: str,
        prompt: str,
        style: Optional[str],
        camera_style: Optional[str],
        duration_seconds: float,
        aspect_ratio: str,
        reference_notes: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Invokes OpenAI GPT model to re-caption the video prompt in Sora native style."""
        system_instruction = (
            "You are the OpenAI Sora Video Re-Captioner. Your task is to expand the user's video prompt "
            "into a highly detailed, physically grounded, cinematic video prompt formatted for Diffusion Transformers (DiT). "
            "Describe the scene precisely across 5 dimensions: "
            "1. Subject & Materiality (clothing weave, facial expressions, micro-movements, textures)\n"
            "2. Camera Optics & Parallax (lens focal length, depth of field, movement velocity, foreground/background parallax)\n"
            "3. Environment & Spatial Layout (architectural details, foliage, spatial geometry)\n"
            "4. Volumetric Lighting & Atmospheric Physics (light rays, haze, reflections, shadows)\n"
            "5. Temporal Kinematics (detailed progression from start -> middle -> end of the clip).\n"
            "Output valid JSON with keys: 'subject', 'camera', 'environment', 'lighting', 'kinematics', 'full_caption'."
        )

        user_content = (
            f"User Prompt: {prompt}\n"
            f"Visual Style: {style or 'Cinematic'}\n"
            f"Camera Style: {camera_style or 'Smooth dolly'}\n"
            f"Duration: {duration_seconds}s\n"
            f"Aspect Ratio: {aspect_ratio}\n"
            f"Reference Anchors: {reference_notes or 'None'}"
        )

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": user_content}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.4,
            "max_tokens": 800
        }

        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=12) as response:
            result = json.loads(response.read().decode("utf-8"))
            content_str = result["choices"][0]["message"]["content"]
            parsed = json.loads(content_str)
            return parsed

    @classmethod
    def _heuristic_spacetime_recaption(
        cls,
        prompt: str,
        style: Optional[str],
        camera_style: Optional[str],
        duration_seconds: float,
        aspect_ratio: str,
        reference_notes: Optional[str]
    ) -> Dict[str, Any]:
        """
        Deterministic, high-quality rule-based Sora spacetime prompt expansion.
        """
        clean_prompt = prompt.strip()
        
        # 1. Camera Optics
        cam_desc = camera_style or "Slow cinematic tracking"
        if "dolly" in cam_desc.lower() or "track" in cam_desc.lower():
            camera_optics = f"50mm anamorphic lens, shallow depth of field, {cam_desc.lower()} creating pronounced foreground-to-background parallax and smooth motion blur at 24fps"
        elif "crane" in cam_desc.lower() or "wide" in cam_desc.lower():
            camera_optics = f"28mm wide cinematic lens, deep focus, {cam_desc.lower()} revealing sweeping spatial scale with controlled vertical elevation"
        elif "close" in cam_desc.lower() or "macro" in cam_desc.lower():
            camera_optics = f"85mm macro lens, creamy bokeh background, delicate rack focus highlighting tactile surface micro-textures"
        else:
            camera_optics = f"35mm master prime lens, natural perspective, {cam_desc.lower()} with organic handheld stability and balanced framing"

        # 2. Lighting & Volumetrics
        lighting = "Soft directional morning sunlight with visible volumetric atmospheric rays, subtle ambient occlusion, realistic global illumination, and rich natural shadows"
        if "night" in clean_prompt.lower() or "dark" in clean_prompt.lower():
            lighting = "Low-key atmospheric night illumination, gentle warm amber lantern glow, deep soft shadows, and cool moonlight rim accents"
        elif "golden" in clean_prompt.lower() or "sunset" in clean_prompt.lower() or "dawn" in clean_prompt.lower():
            lighting = "Warm golden hour illumination, long cast shadows, radiant rim lighting on edges, and gentle atmospheric haze"

        # 3. Environment & Spatial Geometry
        env_details = f"Photorealistic environmental geometry matching {style or 'cinematic world'}, detailed material textures, spatial continuity, authentic foliage, and believable scale"

        # 4. Temporal Kinematics
        kinematics = (
            f"The action unfolds continuously over {duration_seconds} seconds: "
            f"initiating with natural weight and posture, progressing through smooth intermediate physical motion, "
            f"and settling gracefully without sudden jumps or temporal morphing"
        )

        # 5. Full Compiled Sora Caption
        parts = [
            f"A cinematic {aspect_ratio} video in {style or 'highly detailed cinematic'} aesthetic.",
            f"Subject & Scene: {clean_prompt}.",
            f"Camera & Optics: {camera_optics}.",
            f"Lighting & Atmosphere: {lighting}.",
            f"Spatial Environment: {env_details}.",
            f"Temporal Dynamics: {kinematics}."
        ]
        if reference_notes:
            parts.append(f"Visual Consistency Anchors: {reference_notes}.")

        full_caption = " ".join(parts)

        return {
            "subject": clean_prompt,
            "camera": camera_optics,
            "environment": env_details,
            "lighting": lighting,
            "kinematics": kinematics,
            "full_caption": full_caption
        }

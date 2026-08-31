"""
Simulation Video Provider.
Generates genuine animated H.264 MP4 video assets, preview clips, and keyframes for testing and local dev.
"""
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from backend.app.config import settings
from backend.app.providers.base import BaseVideoProvider
from backend.app.utils.ffmpeg_helper import FFmpegHelper


class SimulationVideoProvider(BaseVideoProvider):
    def __init__(self):
        self.model_name = "Videogen Simulation Engine"
        self.version = "1.0.0"

    async def generate_text_to_video(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        duration_seconds: float = 5.0,
        resolution: str = "1080p",
        aspect_ratio: str = "16:9",
        seed: Optional[int] = None,
        output_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        if output_path is None:
            settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
            output_path = settings.TEMP_DIR / f"sim_t2v_{os.urandom(4).hex()}.mp4"

        await asyncio.to_thread(
            FFmpegHelper.render_animated_clip,
            output_path=output_path,
            prompt=prompt,
            duration=duration_seconds,
            resolution=resolution,
            aspect_ratio=aspect_ratio,
            shot_type="Text-To-Video Shot"
        )

        return {
            "video_path": str(output_path),
            "thumbnail_path": str(output_path.with_suffix(".jpg")),
            "duration": duration_seconds,
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
            "seed": seed or 42,
            "provider": "simulation",
            "model": "Wan2.1 Simulation Adapter",
            "license": "Apache 2.0"
        }

    async def generate_image_to_video(
        self,
        image_path: Path,
        prompt: str,
        negative_prompt: Optional[str] = None,
        duration_seconds: float = 5.0,
        resolution: str = "1080p",
        aspect_ratio: str = "16:9",
        seed: Optional[int] = None,
        output_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        if output_path is None:
            settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
            output_path = settings.TEMP_DIR / f"sim_i2v_{os.urandom(4).hex()}.mp4"

        await asyncio.to_thread(
            FFmpegHelper.render_animated_clip,
            output_path=output_path,
            prompt=prompt,
            duration=duration_seconds,
            resolution=resolution,
            aspect_ratio=aspect_ratio,
            keyframe_img=image_path,
            shot_type="Image-To-Video Shot"
        )

        return {
            "video_path": str(output_path),
            "thumbnail_path": str(image_path) if image_path.exists() else str(output_path.with_suffix(".jpg")),
            "duration": duration_seconds,
            "resolution": resolution,
            "aspect_ratio": aspect_ratio,
            "seed": seed or 42,
            "provider": "simulation",
            "model": "Wan2.1-I2V Simulation Adapter",
            "license": "Apache 2.0"
        }

    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        return {"job_id": job_id, "status": "COMPLETED", "progress": 100}

    async def cancel_job(self, job_id: str) -> bool:
        return True

    def get_license_info(self) -> Dict[str, Any]:
        return {
            "model": self.model_name,
            "version": self.version,
            "license": "Apache 2.0",
            "creator": "Videogen-Lucy Engine",
            "commercial_use_allowed": True,
            "attribution_required": False
        }

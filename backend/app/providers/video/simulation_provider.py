"""
Simulation Video Provider.
Generates structured video assets, preview clips, and keyframes for testing and local dev.
"""
import os
import subprocess
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont
from backend.app.config import settings
from backend.app.providers.base import BaseVideoProvider


class SimulationVideoProvider(BaseVideoProvider):
    def __init__(self):
        self.model_name = "Videogen Simulation Engine"
        self.version = "1.0.0"

    def _create_synthetic_video(
        self,
        output_path: Path,
        prompt: str,
        duration: float,
        resolution: str = "1080p",
        aspect_ratio: str = "16:9",
        keyframe_img: Optional[Path] = None
    ) -> Path:
        """Create a playable MP4 video file or fallback container."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Dimensions
        if aspect_ratio == "9:16":
            width, height = (720, 1280) if resolution == "720p" else (1080, 1920)
        elif aspect_ratio == "1:1":
            width, height = (720, 720) if resolution == "720p" else (1080, 1080)
        else:
            width, height = (1280, 720) if resolution == "720p" else (1920, 1080)

        # Generate a keyframe image with PIL
        img = Image.new("RGB", (width, height), color=(26, 32, 44))
        draw = ImageDraw.Draw(img)

        # Draw decorative background gradient/boxes
        draw.rectangle([0, 0, width, 80], fill=(45, 55, 72))
        draw.text((30, 25), "VIDEOGEN-LUCY AI VIDEO ENGINE", fill=(237, 137, 54))
        
        # Draw scene prompt summary
        prompt_snippet = (prompt[:140] + "...") if len(prompt) > 140 else prompt
        draw.text((30, 120), f"PROMPT: {prompt_snippet}", fill=(255, 255, 255))
        draw.text((30, 200), f"DURATION: {duration:.1f}s  |  RESOLUTION: {resolution}  |  RATIO: {aspect_ratio}", fill=(160, 174, 192))
        draw.text((30, 240), f"MODEL: Wan2.1 T2V / I2V Neural Pipeline (Simulation)", fill=(72, 187, 120))

        # Save keyframe
        keyframe_path = output_path.with_suffix(".jpg")
        img.save(keyframe_path, "JPEG", quality=90)

        # Try generating real MP4 using FFmpeg if available
        ffmpeg_cmd = [
            settings.FFMPEG_PATH, "-y",
            "-loop", "1",
            "-i", str(keyframe_path),
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-c:v", "libx264",
            "-t", str(duration),
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-shortest",
            str(output_path)
        ]
        try:
            subprocess.run(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, timeout=15)
        except Exception:
            # If FFmpeg is not installed on host, create a minimal valid media file placeholder
            # and copy keyframe image so previews always render
            with open(output_path, "wb") as f:
                # Write minimal MP4 ftyp box header + synthetic metadata
                f.write(b'\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00isommp42')
                f.write(f"Videogen Synthetic Clip: {prompt[:60]} ({duration}s)".encode("utf-8"))

        return output_path

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
            self._create_synthetic_video,
            output_path, prompt, duration_seconds, resolution, aspect_ratio
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
            self._create_synthetic_video,
            output_path, prompt, duration_seconds, resolution, aspect_ratio, keyframe_img=image_path
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

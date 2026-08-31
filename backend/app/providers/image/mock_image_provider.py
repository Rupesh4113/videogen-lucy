"""
Mock / Synthetic Image Provider for keyframes, character bibles, and location references.
"""
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional
from PIL import Image, ImageDraw
from backend.app.config import settings
from backend.app.providers.base import BaseImageProvider


class MockImageProvider(BaseImageProvider):
    def __init__(self):
        self.model_name = "SDXL-Reference-Generator"
        self.version = "1.0"

    def _render_image(
        self,
        output_path: Path,
        prompt: str,
        width: int = 1024,
        height: int = 576,
        seed: Optional[int] = None
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        img = Image.new("RGB", (width, height), color=(30, 41, 59))
        draw = ImageDraw.Draw(img)

        # Draw decorative layout
        draw.rectangle([20, 20, width - 20, height - 20], outline=(237, 137, 54), width=3)
        draw.rectangle([20, 20, width - 20, 70], fill=(51, 65, 85))
        draw.text((40, 35), "AI VISUAL REFERENCE KEYFRAME", fill=(255, 255, 255))
        
        # Draw prompt description
        lines = [prompt[i:i+80] for i in range(0, min(len(prompt), 320), 80)]
        y = 100
        for line in lines:
            draw.text((40, y), line, fill=(226, 232, 240))
            y += 30

        draw.text((40, height - 60), f"Seed: {seed or 12345} | Size: {width}x{height} | Model: SDXL/Flux Adapter", fill=(148, 163, 184))
        img.save(output_path, "JPEG", quality=92)
        return output_path

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 576,
        seed: Optional[int] = None,
        output_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        if output_path is None:
            settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
            output_path = settings.TEMP_DIR / f"ref_img_{os.urandom(4).hex()}.jpg"

        await asyncio.to_thread(self._render_image, output_path, prompt, width, height, seed)

        return {
            "image_path": str(output_path),
            "width": width,
            "height": height,
            "seed": seed or 12345,
            "provider": "mock_sdxl",
            "model": self.model_name
        }

    def get_license_info(self) -> Dict[str, Any]:
        return {
            "model": self.model_name,
            "version": self.version,
            "license": "CreativeML Open RAIL++-M License",
            "creator": "Stability AI / Open Source",
            "commercial_use_allowed": True,
            "attribution_required": False
        }

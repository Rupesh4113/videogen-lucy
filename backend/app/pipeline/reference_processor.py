"""
Reference Media Processor for Videogen-Lucy.
Handles media validation, persistent storage, video keyframe extraction via FFmpeg,
classification, and scene reference matching.
"""
import os
import uuid
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from PIL import Image

from backend.app.config import settings
from backend.app.schemas.project import ReferenceMediaSchema
from backend.app.utils.ffmpeg_helper import FFmpegHelper

logger = logging.getLogger("videogen.reference")

ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".webm"}

MAX_IMAGE_SIZE_BYTES = 25 * 1024 * 1024   # 25 MB
MAX_VIDEO_SIZE_BYTES = 100 * 1024 * 1024  # 100 MB


class ReferenceProcessor:
    @staticmethod
    def validate_file(filename: str, file_size: int) -> Dict[str, Any]:
        """
        Validates file extension and size.
        Returns media_type ('image' or 'video') and validation status.
        """
        ext = Path(filename).suffix.lower()
        if ext in ALLOWED_IMAGE_EXTENSIONS:
            if file_size > MAX_IMAGE_SIZE_BYTES:
                raise ValueError(f"Image '{filename}' exceeds maximum allowed size of 25MB.")
            return {"valid": True, "media_type": "image", "extension": ext}
        elif ext in ALLOWED_VIDEO_EXTENSIONS:
            if file_size > MAX_VIDEO_SIZE_BYTES:
                raise ValueError(f"Video '{filename}' exceeds maximum allowed size of 100MB.")
            return {"valid": True, "media_type": "video", "extension": ext}
        else:
            allowed = ", ".join(sorted(ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS))
            raise ValueError(f"Unsupported file format '{ext}'. Allowed formats: {allowed}")

    @classmethod
    def process_and_save_reference(
        cls,
        project_id: str,
        file_bytes: bytes,
        filename: str,
        reference_category: str = "character",
        description: str = "",
        importance_weight: float = 1.0,
        usage_mode: str = "visual_reference",
        target_scenes: Optional[List[Union[str, int]]] = None,
        order: int = 0
    ) -> Dict[str, Any]:
        """
        Saves uploaded reference media to disk, extracts video keyframes if needed,
        and generates the reference record.
        """
        val = cls.validate_file(filename, len(file_bytes))
        media_type = val["media_type"]
        ext = val["extension"]

        ref_id = str(uuid.uuid4())
        ref_dir = settings.ASSETS_DIR / "references" / project_id
        ref_dir.mkdir(parents=True, exist_ok=True)

        saved_filename = f"ref_{ref_id[:8]}_{Path(filename).name}"
        file_path = ref_dir / saved_filename
        file_path.write_bytes(file_bytes)

        # Build relative URL for API static serving
        rel_path = file_path.relative_to(settings.STORAGE_DIR)
        file_url = f"/api/v1/storage/{rel_path.as_posix()}"

        extracted_keyframes = []
        meta = {}

        if media_type == "video":
            # Extract keyframes for visual conditioning fallbacks
            kf_dir = ref_dir / "keyframes" / ref_id[:8]
            kf_paths = FFmpegHelper.extract_keyframes(file_path, kf_dir, count=3)
            extracted_keyframes = [str(p) for p in kf_paths]
            meta = FFmpegHelper.get_video_metadata(file_path)
        else:
            try:
                with Image.open(file_path) as img:
                    meta = {"width": img.width, "height": img.height, "format": img.format}
            except Exception:
                meta = {"width": 1024, "height": 1024}

        return {
            "id": ref_id,
            "project_id": project_id,
            "media_type": media_type,
            "reference_category": reference_category,
            "file_path": str(file_path),
            "file_url": file_url,
            "original_filename": filename,
            "description": description,
            "importance_weight": float(importance_weight),
            "target_scenes": target_scenes or ["all"],
            "usage_mode": usage_mode,
            "extracted_keyframes": extracted_keyframes,
            "metadata": meta,
            "order": order
        }

    @staticmethod
    def get_scene_applicable_references(
        references: List[Any],
        scene_number: int
    ) -> List[Any]:
        """
        Filters references that apply to a specific scene number.
        """
        applicable = []
        for ref in references:
            targets = getattr(ref, "target_scenes_json", None) or getattr(ref, "target_scenes", ["all"])
            if isinstance(targets, list):
                if "all" in targets or scene_number in targets or str(scene_number) in targets:
                    applicable.append(ref)
            else:
                applicable.append(ref)
        return applicable

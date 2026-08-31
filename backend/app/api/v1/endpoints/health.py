"""
Health and System Diagnostics API Router.
"""
import os
import shutil
from fastapi import APIRouter
from backend.app.config import settings

router = APIRouter()


@router.get("/health")
async def health_check():
    """Returns platform health, active providers, and storage status."""
    storage_free_gb = 0.0
    if settings.STORAGE_DIR.exists():
        total, used, free = shutil.disk_usage(settings.STORAGE_DIR)
        storage_free_gb = round(free / (1024 ** 3), 2)

    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "providers": {
            "video_provider": settings.VIDEO_PROVIDER,
            "voice_provider": settings.VOICE_PROVIDER,
            "image_provider": settings.IMAGE_PROVIDER,
            "storage_provider": settings.STORAGE_PROVIDER
        },
        "storage": {
            "free_space_gb": storage_free_gb,
            "storage_dir": str(settings.STORAGE_DIR)
        }
    }

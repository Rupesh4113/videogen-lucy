"""
Application Configuration for Videogen-Lucy AI Video Generation Platform.
"""
import os
from pathlib import Path
from typing import Optional

class Settings:
    # App Information
    APP_NAME: str = "Videogen-Lucy"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"
    API_V1_STR: str = "/api/v1"

    # Base Paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    STORAGE_DIR: Path = BASE_DIR / "storage"
    ASSETS_DIR: Path = STORAGE_DIR / "assets"
    TEMP_DIR: Path = STORAGE_DIR / "temp"
    OUTPUT_DIR: Path = STORAGE_DIR / "outputs"

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", f"sqlite+aiosqlite:///{STORAGE_DIR / 'videogen.db'}")

    # Provider Selection
    VIDEO_PROVIDER: str = os.getenv("VIDEO_PROVIDER", "simulation")  # "wan_local", "replicate", "hunyuan", "cogvideo", "simulation"
    IMAGE_PROVIDER: str = os.getenv("IMAGE_PROVIDER", "mock")       # "diffusers", "replicate", "openai", "mock"
    VOICE_PROVIDER: str = os.getenv("VOICE_PROVIDER", "edge_tts")   # "edge_tts", "xtts", "elevenlabs", "mock"
    LIPSYNC_PROVIDER: str = os.getenv("LIPSYNC_PROVIDER", "simulation") # "wav2lip", "sadtalker", "simulation"
    STORAGE_PROVIDER: str = os.getenv("STORAGE_PROVIDER", "local")    # "local", "s3"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "local_heuristic") # "openai", "gemini", "anthropic", "local_heuristic"

    # API Keys & Cloud Credentials (Optional)
    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    REPLICATE_API_TOKEN: Optional[str] = os.getenv("REPLICATE_API_TOKEN")
    ELEVENLABS_API_KEY: Optional[str] = os.getenv("ELEVENLABS_API_KEY")
    AWS_ACCESS_KEY_ID: Optional[str] = os.getenv("AWS_ACCESS_KEY_ID")
    AWS_SECRET_ACCESS_KEY: Optional[str] = os.getenv("AWS_SECRET_ACCESS_KEY")
    AWS_REGION: str = os.getenv("AWS_REGION", "us-east-1")
    AWS_S3_BUCKET: Optional[str] = os.getenv("AWS_S3_BUCKET")

    # Video & Render Defaults
    DEFAULT_RESOLUTION: str = os.getenv("DEFAULT_RESOLUTION", "1080p")  # "720p", "1080p"
    DEFAULT_ASPECT_RATIO: str = os.getenv("DEFAULT_ASPECT_RATIO", "16:9")  # "16:9", "9:16", "1:1"
    DEFAULT_FPS: int = int(os.getenv("DEFAULT_FPS", "24"))
    FFMPEG_PATH: str = os.getenv("FFMPEG_PATH", "ffmpeg")
    
    # Celery / Redis
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    def init_directories(self):
        """Create necessary data storage directories if they do not exist."""
        for d in [self.STORAGE_DIR, self.ASSETS_DIR, self.TEMP_DIR, self.OUTPUT_DIR]:
            d.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.init_directories()

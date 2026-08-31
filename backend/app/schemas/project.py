"""
Pydantic Schemas for Project creation, updates, and responses.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ProjectCreateRequest(BaseModel):
    prompt: str = Field(..., min_length=5, description="Natural language prompt in English or Hindi")
    language: str = Field(default="en", description="Language code ('en' or 'hi')")
    target_duration: int = Field(default=300, description="Duration in seconds (300=5m, 600=10m, 900=15m, 1200=20m, 1800=30m)")
    video_style: str = Field(default="Cinematic animation", description="Visual style")
    character_style: str = Field(default="Semi-realistic", description="Character design style")
    voice_type: str = Field(default="Narrator + characters", description="Voice strategy")
    resolution: str = Field(default="1080p", description="Output resolution ('720p', '1080p')")
    aspect_ratio: str = Field(default="16:9", description="Aspect ratio ('16:9', '9:16', '1:1')")
    music_mood: str = Field(default="Cinematic", description="Background music mood")


class ProjectResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    title: str
    prompt: str
    language: str
    target_duration: int
    video_style: str
    character_style: str
    voice_type: str
    resolution: str
    aspect_ratio: str
    music_mood: str
    status: str
    current_stage: str
    progress_percentage: int
    error_message: Optional[str] = None
    final_video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    subtitle_en_url: Optional[str] = None
    subtitle_hi_url: Optional[str] = None
    manifest_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CostEstimateRequest(BaseModel):
    target_duration: int = Field(default=300, description="Video duration in seconds")
    resolution: str = Field(default="1080p")
    video_provider: str = Field(default="wan_local")


class CostEstimateResponse(BaseModel):
    target_duration_minutes: float
    total_scenes_estimated: int
    total_shots_estimated: int
    estimated_generation_time_minutes: float
    estimated_gpu_cost_usd: float
    estimated_storage_gb: float
    estimated_vram_requirement_gb: int

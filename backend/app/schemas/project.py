"""
Pydantic Schemas for Project creation, updates, reference media, and responses.
"""
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict


class ReferenceMediaSchema(BaseModel):
    id: Optional[str] = None
    project_id: Optional[str] = None
    media_type: str = Field(default="image", description="'image' or 'video'")
    reference_category: str = Field(
        default="character",
        description="'character', 'location', 'object', 'style', 'motion', 'overall'"
    )
    file_path: str
    file_url: Optional[str] = None
    original_filename: Optional[str] = None
    description: Optional[str] = None
    importance_weight: float = Field(default=1.0, ge=0.1, le=2.0)
    target_scenes: List[Union[str, int]] = Field(default_factory=lambda: ["all"])
    usage_mode: str = Field(
        default="visual_reference",
        description="'start_frame', 'visual_reference', 'motion_reference', 'style_guide'"
    )
    extracted_keyframes: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    order: int = Field(default=0)
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class ProjectCreateRequest(BaseModel):
    prompt: str = Field(..., min_length=5, description="Natural language prompt in English or Hindi")
    language: str = Field(default="en", description="Language code ('en' or 'hi')")
    target_duration: int = Field(default=300, description="Duration in seconds (300=5m, 600=10m, 900=15m, 1200=20m, 1800=30m)")
    video_style: str = Field(default="Cinematic animation", description="Visual style")
    camera_style: str = Field(default="Cinematic handheld", description="Camera motion style")
    character_style: str = Field(default="Semi-realistic", description="Character design style")
    voice_type: str = Field(default="Narrator + characters", description="Voice strategy")
    resolution: str = Field(default="1080p", description="Output resolution ('720p', '1080p')")
    aspect_ratio: str = Field(default="16:9", description="Aspect ratio ('16:9', '9:16', '1:1')")
    music_mood: str = Field(default="Cinematic", description="Background music mood")
    lock_character_appearance: bool = Field(default=True, description="Lock character visual identity across scenes")
    lock_environment: bool = Field(default=True, description="Lock location architectural consistency across scenes")
    references: Optional[List[ReferenceMediaSchema]] = Field(default=None)


class ProjectResponse(BaseModel):
    id: str
    user_id: Optional[str] = None
    title: str
    prompt: str
    language: str
    target_duration: int
    video_style: str
    camera_style: str = "Cinematic handheld"
    character_style: str
    voice_type: str
    resolution: str
    aspect_ratio: str
    music_mood: str
    lock_character_appearance: bool = True
    lock_environment: bool = True
    status: str
    current_stage: str
    progress_percentage: int
    error_message: Optional[str] = None
    final_video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    subtitle_en_url: Optional[str] = None
    subtitle_hi_url: Optional[str] = None
    manifest_url: Optional[str] = None
    references: Optional[List[ReferenceMediaSchema]] = Field(default_factory=list)
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

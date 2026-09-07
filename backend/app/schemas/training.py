"""
Pydantic Schemas for YouTube Video Ingestion & LoRA Model Training.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field


class YouTubeIngestRequest(BaseModel):
    youtube_url: str = Field(..., description="YouTube video URL or Video ID to ingest")
    training_type: str = Field(default="character", description="Training mode: character, style, or motion")
    custom_name: Optional[str] = Field(default=None, description="Custom name for the trained model")
    trigger_word: Optional[str] = Field(default=None, description="Unique prompt trigger token e.g. [v_custom_character]")
    max_clips: int = Field(default=10, ge=2, le=50, description="Max training clips to extract")
    clip_duration: float = Field(default=4.0, ge=2.0, le=10.0, description="Target duration of each training clip in seconds")
    target_base_model: str = Field(default="Wan2.2-T2V-14B", description="Target base video model")


class DatasetSampleSchema(BaseModel):
    id: str
    model_id: str
    sample_type: str = "video_clip"
    file_path: str
    thumbnail_path: Optional[str] = None
    timestamp_start: float = 0.0
    timestamp_end: float = 4.0
    duration: float = 4.0
    resolution: str = "1080p"
    caption: str
    tags: List[str] = []
    is_approved: bool = True
    created_at: Optional[datetime] = None


class DatasetCurateRequest(BaseModel):
    model_id: str
    approved_sample_ids: Optional[List[str]] = None
    deleted_sample_ids: Optional[List[str]] = None
    custom_captions: Optional[Dict[str, str]] = None


class TrainLoRARequest(BaseModel):
    model_id: str
    base_model: str = Field(default="Wan2.2-T2V-14B", description="Base video model architecture")
    lora_rank: int = Field(default=32, ge=4, le=128, description="LoRA Rank / Dimension (r)")
    lora_alpha: int = Field(default=64, ge=8, le=256, description="LoRA Scaling Alpha")
    learning_rate: float = Field(default=1e-4, ge=1e-6, le=1e-2, description="Learning rate")
    training_steps: int = Field(default=300, ge=50, le=5000, description="Total training optimization steps")
    epochs: int = Field(default=10, ge=1, le=100, description="Total training epochs")
    batch_size: int = Field(default=1, ge=1, le=8, description="Training batch size")


class TrainedModelSchema(BaseModel):
    id: str
    name: str
    base_model: str
    training_type: str
    trigger_word: str
    source_youtube_url: Optional[str] = None
    source_video_title: Optional[str] = None
    source_channel: Optional[str] = None
    dataset_count: int = 0
    lora_rank: int = 32
    lora_alpha: int = 64
    learning_rate: float = 1e-4
    training_steps: int = 300
    weights_path: Optional[str] = None
    config_path: Optional[str] = None
    sample_preview_url: Optional[str] = None
    status: str = "DRAFT"
    progress: int = 0
    current_step: int = 0
    final_loss: Optional[float] = None
    loss_history: List[Dict[str, Any]] = []
    created_at: Optional[datetime] = None


class TrainingStatusResponse(BaseModel):
    model_id: str
    status: str
    progress: int
    current_epoch: int
    current_step: int
    total_steps: int
    current_loss: Optional[float] = None
    loss_history: List[Dict[str, Any]] = []
    weights_path: Optional[str] = None
    sample_preview_url: Optional[str] = None
    error_message: Optional[str] = None


class TestTrainedModelRequest(BaseModel):
    prompt: str = Field(..., description="Generation prompt utilizing the model's trigger token")
    duration_seconds: float = Field(default=4.0, ge=2.0, le=10.0)
    resolution: str = Field(default="1080p")
    lora_scale: float = Field(default=0.85, ge=0.1, le=1.5)

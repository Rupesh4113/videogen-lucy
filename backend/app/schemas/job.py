"""
Pydantic Schemas for Job Status and WebSocket Event Messages.
"""
from typing import Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel


class JobStatusResponse(BaseModel):
    project_id: str
    status: str
    current_stage: str
    progress_percentage: int
    message: Optional[str] = None
    error_message: Optional[str] = None
    final_video_url: Optional[str] = None
    thumbnail_url: Optional[str] = None
    subtitle_en_url: Optional[str] = None
    subtitle_hi_url: Optional[str] = None
    manifest_url: Optional[str] = None


class ProgressEvent(BaseModel):
    project_id: str
    stage: str
    progress: int
    message: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None

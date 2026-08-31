"""
Pydantic Schemas for Story, Screenplay, Scenes, and Shots.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class DialogueLine(BaseModel):
    character: str = Field(..., description="Character name")
    line: str = Field(..., description="Spoken dialogue in natural language")
    emotion: Optional[str] = Field(default="Neutral", description="Vocal emotion")
    timing_offset_seconds: Optional[float] = Field(default=0.0, description="Offset in scene")


class ShotSchema(BaseModel):
    id: Optional[str] = None
    order: int
    shot_number: int
    shot_type: str = "Medium shot"
    duration_seconds: float = 5.0
    description: str
    camera_movement: str = "Static"
    visual_prompt: str
    negative_prompt: Optional[str] = None
    continuity_context: Optional[str] = None
    video_url: Optional[str] = None
    first_frame_url: Optional[str] = None
    last_frame_url: Optional[str] = None
    status: str = "PENDING"

    model_config = ConfigDict(from_attributes=True)


class SceneSchema(BaseModel):
    id: Optional[str] = None
    order: int
    scene_number: int
    title: Optional[str] = None
    duration_seconds: int = 15
    location_name: Optional[str] = None
    time_of_day: str = "Day"
    characters: List[str] = []
    action: Optional[str] = None
    dialogue: List[DialogueLine] = []
    narration: Optional[str] = None
    emotion: Optional[str] = None
    camera: Optional[str] = None
    lighting: Optional[str] = None
    sound_effects: List[str] = []
    music_prompt: Optional[str] = None
    visual_prompt: Optional[str] = None
    video_url: Optional[str] = None
    audio_url: Optional[str] = None
    status: str = "PENDING"
    shots: List[ShotSchema] = []

    model_config = ConfigDict(from_attributes=True)


class StorySchema(BaseModel):
    id: Optional[str] = None
    title: str
    logline: Optional[str] = None
    genre: Optional[str] = None
    target_audience: Optional[str] = None
    summary: Optional[str] = None
    beginning: Optional[str] = None
    conflict: Optional[str] = None
    rising_action: Optional[str] = None
    climax: Optional[str] = None
    resolution: Optional[str] = None
    ending: Optional[str] = None
    metadata: Dict[str, Any] = {}

    model_config = ConfigDict(from_attributes=True)


class StoryboardResponse(BaseModel):
    project_id: str
    story: StorySchema
    characters: List[Dict[str, Any]]
    locations: List[Dict[str, Any]]
    scenes: List[SceneSchema]
    total_estimated_shots: int
    estimated_duration_seconds: int

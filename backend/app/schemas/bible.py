"""
Pydantic Schemas for Character Bible and Environment/Location Bible.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class CharacterSchema(BaseModel):
    id: Optional[str] = None
    character_key: str
    name: str
    age: Optional[int] = None
    gender: Optional[str] = None
    face_description: Optional[str] = None
    skin_tone: Optional[str] = None
    hair: Optional[str] = None
    eye_color: Optional[str] = None
    body_type: Optional[str] = None
    clothing: Optional[str] = None
    accessories: Optional[str] = None
    personality: Optional[str] = None
    voice_description: Optional[str] = None
    voice_preset: Optional[str] = None
    negative_attributes: Optional[str] = None
    reference_image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class LocationSchema(BaseModel):
    id: Optional[str] = None
    location_key: str
    name: str
    description: str
    architecture: Optional[str] = None
    colors: Optional[str] = None
    weather: Optional[str] = "Clear"
    lighting: Optional[str] = "Natural"
    time_of_day: Optional[str] = "Day"
    props: Optional[str] = None
    camera_style: Optional[str] = None
    reference_image_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

"""
SQLAlchemy ORM Entities for Videogen-Lucy.
Implements the complete database schema defined in the specification.
"""
import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, Float, Text, Boolean, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from backend.app.models.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


def get_utc_now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=True)
    name = Column(String(255), nullable=True)
    api_key_hash = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=get_utc_now)

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")


class Project(Base):
    __tablename__ = "projects"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True)
    title = Column(String(255), default="Untitled Project")
    prompt = Column(Text, nullable=False)
    language = Column(String(10), default="en")  # "en", "hi"
    target_duration = Column(Integer, default=300)  # seconds (300, 600, 900, 1200, 1800)
    video_style = Column(String(100), default="Cinematic animation")
    character_style = Column(String(100), default="Semi-realistic")
    voice_type = Column(String(100), default="Narrator + characters")
    resolution = Column(String(20), default="1080p")  # "720p", "1080p"
    aspect_ratio = Column(String(20), default="16:9")  # "16:9", "9:16", "1:1"
    music_mood = Column(String(50), default="Cinematic")
    
    # Workflow status
    status = Column(String(50), default="DRAFT")  # DRAFT, QUEUED, PLANNING, COMPLETED, FAILED, CANCELLED
    current_stage = Column(String(50), default="DRAFT")
    progress_percentage = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Output paths
    final_video_url = Column(String(500), nullable=True)
    thumbnail_url = Column(String(500), nullable=True)
    subtitle_en_url = Column(String(500), nullable=True)
    subtitle_hi_url = Column(String(500), nullable=True)
    manifest_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    user = relationship("User", back_populates="projects")
    story = relationship("Story", back_populates="project", uselist=False, cascade="all, delete-orphan")
    characters = relationship("Character", back_populates="project", cascade="all, delete-orphan")
    locations = relationship("Location", back_populates="project", cascade="all, delete-orphan")
    scenes = relationship("Scene", back_populates="project", cascade="all, delete-orphan", order_by="Scene.order")
    jobs = relationship("GenerationJob", back_populates="project", cascade="all, delete-orphan")
    licenses = relationship("LicenseRecord", back_populates="project", cascade="all, delete-orphan")


class Story(Base):
    __tablename__ = "stories"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), unique=True)
    title = Column(String(255), nullable=False)
    logline = Column(Text, nullable=True)
    genre = Column(String(100), nullable=True)
    target_audience = Column(String(100), nullable=True)
    summary = Column(Text, nullable=True)
    
    # 3-Act Structure
    beginning = Column(Text, nullable=True)
    conflict = Column(Text, nullable=True)
    rising_action = Column(Text, nullable=True)
    climax = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    ending = Column(Text, nullable=True)
    
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime, default=get_utc_now)

    project = relationship("Project", back_populates="story")


class Character(Base):
    __tablename__ = "characters"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"))
    character_key = Column(String(50), nullable=False)  # e.g. "gauri"
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=True)
    gender = Column(String(50), nullable=True)
    face_description = Column(Text, nullable=True)
    skin_tone = Column(String(100), nullable=True)
    hair = Column(String(100), nullable=True)
    eye_color = Column(String(100), nullable=True)
    body_type = Column(String(100), nullable=True)
    clothing = Column(Text, nullable=True)
    accessories = Column(Text, nullable=True)
    personality = Column(Text, nullable=True)
    voice_description = Column(Text, nullable=True)
    voice_preset = Column(String(100), nullable=True)
    negative_attributes = Column(Text, nullable=True)
    reference_image_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=get_utc_now)

    project = relationship("Project", back_populates="characters")
    references = relationship("CharacterReference", back_populates="character", cascade="all, delete-orphan")


class CharacterReference(Base):
    __tablename__ = "character_references"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    character_id = Column(String(36), ForeignKey("characters.id"))
    view_angle = Column(String(50), default="front")  # front, side, 3/4, expression
    image_url = Column(String(500), nullable=False)
    prompt_used = Column(Text, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    character = relationship("Character", back_populates="references")


class Location(Base):
    __tablename__ = "locations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"))
    location_key = Column(String(50), nullable=False)  # e.g. "village_house"
    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=False)
    architecture = Column(Text, nullable=True)
    colors = Column(String(200), nullable=True)
    weather = Column(String(100), default="Clear")
    lighting = Column(String(100), default="Natural")
    time_of_day = Column(String(50), default="Day")
    props = Column(Text, nullable=True)
    camera_style = Column(String(100), nullable=True)
    reference_image_url = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=get_utc_now)

    project = relationship("Project", back_populates="locations")


class Scene(Base):
    __tablename__ = "scenes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"))
    order = Column(Integer, nullable=False)
    scene_number = Column(Integer, nullable=False)
    title = Column(String(200), nullable=True)
    duration_seconds = Column(Integer, default=15)
    location_name = Column(String(150), nullable=True)
    time_of_day = Column(String(50), default="Day")
    characters_json = Column(JSON, default=list)  # List of character names/keys
    action = Column(Text, nullable=True)
    dialogue_json = Column(JSON, default=list)  # [{"character": "Gauri", "line": "..."}]
    narration = Column(Text, nullable=True)
    emotion = Column(String(100), nullable=True)
    camera = Column(String(100), nullable=True)
    lighting = Column(String(100), nullable=True)
    sound_effects = Column(JSON, default=list)  # ["rain", "thunder", "footsteps"]
    music_prompt = Column(String(255), nullable=True)
    visual_prompt = Column(Text, nullable=True)
    
    # Generated media
    video_url = Column(String(500), nullable=True)
    audio_url = Column(String(500), nullable=True)
    status = Column(String(50), default="PENDING")  # PENDING, GENERATING, COMPLETED, FAILED

    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    project = relationship("Project", back_populates="scenes")
    shots = relationship("Shot", back_populates="scene", cascade="all, delete-orphan", order_by="Shot.order")


class Shot(Base):
    __tablename__ = "shots"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    scene_id = Column(String(36), ForeignKey("scenes.id"))
    order = Column(Integer, nullable=False)
    shot_number = Column(Integer, nullable=False)
    shot_type = Column(String(50), default="Medium shot")  # Establishing, Wide, Medium, Close-up
    duration_seconds = Column(Float, default=5.0)
    description = Column(Text, nullable=False)
    camera_movement = Column(String(100), default="Static")
    visual_prompt = Column(Text, nullable=False)
    negative_prompt = Column(Text, nullable=True)
    continuity_context = Column(Text, nullable=True)
    
    # Generation Output
    video_url = Column(String(500), nullable=True)
    first_frame_url = Column(String(500), nullable=True)
    last_frame_url = Column(String(500), nullable=True)
    status = Column(String(50), default="PENDING")  # PENDING, GENERATING, COMPLETED, FAILED

    created_at = Column(DateTime, default=get_utc_now)

    scene = relationship("Scene", back_populates="shots")


class GenerationJob(Base):
    __tablename__ = "generation_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"))
    stage = Column(String(50), nullable=False)
    status = Column(String(50), default="QUEUED")  # QUEUED, PROCESSING, COMPLETED, FAILED, CANCELLED
    progress = Column(Integer, default=0)
    message = Column(String(255), nullable=True)
    error = Column(Text, nullable=True)
    payload = Column(JSON, default=dict)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    project = relationship("Project", back_populates="jobs")


class LicenseRecord(Base):
    __tablename__ = "license_records"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"))
    asset_id = Column(String(100), nullable=False)
    asset_type = Column(String(50), nullable=False)  # video, audio, music, voice, image
    source = Column(String(100), nullable=False)  # model name or provider
    license_name = Column(String(100), nullable=False)  # Apache 2.0, CC0, Commercial, etc.
    creator = Column(String(150), default="AI Generation Engine")
    license_url = Column(String(500), nullable=True)
    commercial_use_allowed = Column(Boolean, default=True)
    attribution_required = Column(Boolean, default=False)
    details = Column(JSON, default=dict)

    created_at = Column(DateTime, default=get_utc_now)

    project = relationship("Project", back_populates="licenses")

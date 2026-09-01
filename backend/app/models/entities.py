"""
SQLAlchemy ORM Entities for Videogen-Lucy.
Implements the complete database schema including users, projects, stories, characters, locations, scenes, shots, jobs, license records, and OTP tokens.
Includes extend_existing=True for seamless reloads in Streamlit and hot-reloading environments.
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
    __table_args__ = {"extend_existing": True}

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, index=True, nullable=True)
    phone_number = Column(String(30), unique=True, index=True, nullable=True)
    name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=True)
    api_key_hash = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    projects = relationship("Project", back_populates="user", cascade="all, delete-orphan")


class OTPToken(Base):
    __tablename__ = "otp_tokens"
    __table_args__ = {"extend_existing": True}

    id = Column(String(36), primary_key=True, default=generate_uuid)
    phone_or_email = Column(String(255), index=True, nullable=False)
    otp_code = Column(String(10), nullable=False)
    purpose = Column(String(50), default="login")  # "login", "register", "verify"
    expires_at = Column(DateTime, nullable=False)
    is_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=get_utc_now)


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = {"extend_existing": True}

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
    
    # Status: DRAFT, PLANNING, ASSET_GENERATION, RENDERING, COMPLETED, FAILED
    status = Column(String(50), default="DRAFT")
    current_stage = Column(String(50), default="IDLE")
    progress_percentage = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)

    # Output artifact URLs
    final_video_url = Column(String(512), nullable=True)
    thumbnail_url = Column(String(512), nullable=True)
    subtitle_en_url = Column(String(512), nullable=True)
    subtitle_hi_url = Column(String(512), nullable=True)
    manifest_url = Column(String(512), nullable=True)

    created_at = Column(DateTime, default=get_utc_now)
    updated_at = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

    # Relationships
    user = relationship("User", back_populates="projects")
    story = relationship("Story", back_populates="project", uselist=False, cascade="all, delete-orphan")
    characters = relationship("Character", back_populates="project", cascade="all, delete-orphan")
    locations = relationship("Location", back_populates="project", cascade="all, delete-orphan")
    scenes = relationship("Scene", back_populates="project", cascade="all, delete-orphan")
    generation_jobs = relationship("GenerationJob", back_populates="project", cascade="all, delete-orphan")
    license_records = relationship("LicenseRecord", back_populates="project", cascade="all, delete-orphan")


class Story(Base):
    __tablename__ = "stories"
    __table_args__ = {"extend_existing": True}

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    logline = Column(Text, nullable=True)
    genre = Column(String(100), nullable=True)
    target_audience = Column(String(100), nullable=True)
    summary = Column(Text, nullable=True)
    theme = Column(String(255), nullable=True)
    
    # 3-Act Structure Breakdowns
    beginning = Column(Text, nullable=True)
    conflict = Column(Text, nullable=True)
    rising_action = Column(Text, nullable=True)
    climax = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    ending = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    
    created_at = Column(DateTime, default=get_utc_now)
    
    project = relationship("Project", back_populates="story")


class Character(Base):
    __tablename__ = "characters"
    __table_args__ = {"extend_existing": True}

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    character_key = Column(String(50), nullable=False)  # "char_1", "char_2"
    name = Column(String(255), nullable=False)
    age = Column(String(50), nullable=True)
    gender = Column(String(50), nullable=True)
    
    # Visual Bible Attributes
    face_description = Column(Text, nullable=True)
    skin_tone = Column(String(100), nullable=True)
    hair = Column(String(255), nullable=True)
    eye_color = Column(String(100), nullable=True)
    body_type = Column(String(100), nullable=True)
    clothing = Column(Text, nullable=True)
    accessories = Column(JSON, nullable=True)
    personality = Column(Text, nullable=True)
    voice_description = Column(Text, nullable=True)
    voice_preset = Column(String(100), default="default")
    negative_attributes = Column(JSON, nullable=True)
    
    # Master reference image
    reference_image_url = Column(String(512), nullable=True)
    
    created_at = Column(DateTime, default=get_utc_now)

    project = relationship("Project", back_populates="characters")
    references = relationship("CharacterReference", back_populates="character", cascade="all, delete-orphan")


class CharacterReference(Base):
    __tablename__ = "character_references"
    __table_args__ = {"extend_existing": True}

    id = Column(String(36), primary_key=True, default=generate_uuid)
    character_id = Column(String(36), ForeignKey("characters.id"), nullable=False)
    view_type = Column(String(50), nullable=False)  # "front", "side", "three_quarter", "expression_happy"
    image_url = Column(String(512), nullable=False)
    created_at = Column(DateTime, default=get_utc_now)

    character = relationship("Character", back_populates="references")


class Location(Base):
    __tablename__ = "locations"
    __table_args__ = {"extend_existing": True}

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    location_key = Column(String(50), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    architecture = Column(String(255), nullable=True)
    colors = Column(String(255), nullable=True)
    weather = Column(String(100), default="clear")
    lighting = Column(String(100), default="natural daylight")
    time_of_day = Column(String(100), default="Day")
    props = Column(JSON, nullable=True)
    camera_style = Column(String(255), nullable=True)
    reference_image_url = Column(String(512), nullable=True)

    created_at = Column(DateTime, default=get_utc_now)

    project = relationship("Project", back_populates="locations")


class Scene(Base):
    __tablename__ = "scenes"
    __table_args__ = {"extend_existing": True}

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    scene_number = Column(Integer, nullable=False)
    order = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)
    
    location_name = Column(String(255), nullable=False)
    time_of_day = Column(String(50), default="Day")
    lighting = Column(String(100), default="Daylight")
    emotion = Column(String(100), nullable=True)
    camera = Column(String(100), nullable=True)
    sound_effects = Column(JSON, nullable=True)
    visual_prompt = Column(Text, nullable=True)
    
    action = Column(Text, nullable=False)
    narration = Column(Text, nullable=True)
    music_prompt = Column(Text, nullable=True)
    duration_seconds = Column(Float, default=30.0)
    
    # Store structured lists as JSON
    characters_json = Column(JSON, default=list)  # ["char_1", "char_2"]
    dialogue_json = Column(JSON, default=list)  # [{"character": "Gauri", "line": "..."}]

    # Render state
    status = Column(String(50), default="PENDING")
    video_url = Column(String(512), nullable=True)
    audio_url = Column(String(512), nullable=True)

    created_at = Column(DateTime, default=get_utc_now)

    project = relationship("Project", back_populates="scenes")
    shots = relationship("Shot", back_populates="scene", cascade="all, delete-orphan", order_by="Shot.order")


class Shot(Base):
    __tablename__ = "shots"
    __table_args__ = {"extend_existing": True}

    id = Column(String(36), primary_key=True, default=generate_uuid)
    scene_id = Column(String(36), ForeignKey("scenes.id"), nullable=False)
    shot_number = Column(Integer, nullable=False)
    order = Column(Integer, nullable=False)
    
    shot_type = Column(String(50), default="Medium Shot")  # Wide, Close-Up, Tracking, etc.
    camera_movement = Column(String(100), default="Static")  # Pan left, Zoom in, Dolly forward
    camera_angle = Column(String(50), default="Eye Level")
    
    description = Column(Text, nullable=False)
    visual_prompt = Column(Text, nullable=True)
    negative_prompt = Column(Text, nullable=True)
    continuity_context = Column(JSON, nullable=True)
    duration_seconds = Column(Float, default=5.0)

    # Prompt Compilation
    compiled_positive_prompt = Column(Text, nullable=True)
    compiled_negative_prompt = Column(Text, nullable=True)
    
    # Model seed and render output
    seed = Column(Integer, nullable=True)
    keyframe_url = Column(String(512), nullable=True)
    video_url = Column(String(512), nullable=True)
    status = Column(String(50), default="PENDING")  # PENDING, GENERATING, COMPLETED, FAILED

    created_at = Column(DateTime, default=get_utc_now)

    scene = relationship("Scene", back_populates="shots")


class GenerationJob(Base):
    __tablename__ = "generation_jobs"
    __table_args__ = {"extend_existing": True}

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    job_type = Column(String(50), nullable=False)  # "T2V", "I2V", "TTS", "LIPSYNC", "ASSEMBLY"
    provider_name = Column(String(100), nullable=False)
    model_version = Column(String(100), nullable=True)
    
    status = Column(String(50), default="QUEUED")  # QUEUED, RUNNING, COMPLETED, FAILED
    progress = Column(Integer, default=0)
    input_payload = Column(JSON, nullable=True)
    output_result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    
    cost_usd = Column(Float, default=0.0)
    gpu_time_seconds = Column(Float, default=0.0)
    
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

    project = relationship("Project", back_populates="generation_jobs")


class LicenseRecord(Base):
    __tablename__ = "license_records"
    __table_args__ = {"extend_existing": True}

    id = Column(String(36), primary_key=True, default=generate_uuid)
    project_id = Column(String(36), ForeignKey("projects.id"), nullable=False)
    asset_type = Column(String(50), nullable=False)  # "model", "music", "sfx", "font"
    asset_name = Column(String(255), nullable=False)
    license_type = Column(String(100), nullable=False)  # "Apache 2.0", "CC0", "CC-BY 4.0", "MIT"
    creator = Column(String(255), nullable=True)
    source_url = Column(String(512), nullable=True)
    commercial_use_allowed = Column(Boolean, default=True)
    attribution_required = Column(Boolean, default=False)
    attribution_text = Column(Text, nullable=True)

    created_at = Column(DateTime, default=get_utc_now)

    project = relationship("Project", back_populates="license_records")

"""
Pydantic Schemas for Safety Guard, YouTube Compliance, and Asset Manifest.
"""
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class SafetyCheckRequest(BaseModel):
    prompt: str = Field(..., description="Prompt text to analyze for IP/copyright")


class SafetyCheckResponse(BaseModel):
    is_safe: bool
    risk_level: str  # "LOW", "MEDIUM", "HIGH"
    detected_violations: List[str] = []
    reason: Optional[str] = None
    suggested_rewrite: Optional[str] = None
    disclaimer: str = (
        "AI-generated content can create legal, licensing, personality-rights, "
        "trademark, copyright, or platform-policy issues. Review the asset manifest "
        "and applicable licenses before publishing."
    )


class ComplianceCheckItem(BaseModel):
    title: str
    status: bool
    description: str


class YouTubeComplianceReport(BaseModel):
    original_story: bool = True
    original_characters: bool = True
    no_copyrighted_music: bool = True
    no_unauthorized_likeness: bool = True
    no_unauthorized_voice_cloning: bool = True
    asset_licenses_available: bool = True
    subtitles_available: bool = True
    ai_disclosure_recommendation: str = "Recommended based on realistic human-like characters"
    checklist: List[ComplianceCheckItem] = []
    disclaimer: str = (
        "This platform does not guarantee YouTube monetization or absolute legal clearance. "
        "Creators remain responsible for complying with YouTube platform policies."
    )


class AssetManifest(BaseModel):
    project_id: str
    title: str
    generation_date: str
    target_duration_seconds: int
    language: str
    video_provider: str
    voice_provider: str
    music_provider: str
    models_used: Dict[str, str] = {}
    video_assets: List[Dict[str, Any]] = []
    audio_assets: List[Dict[str, Any]] = []
    music_licenses: List[Dict[str, Any]] = []
    voice_profiles: List[Dict[str, Any]] = []
    prompts_hash: str
    compliance_summary: YouTubeComplianceReport

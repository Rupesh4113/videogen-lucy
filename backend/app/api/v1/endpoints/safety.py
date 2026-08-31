"""
Safety & Legal Guard API Endpoints.
"""
from fastapi import APIRouter
from backend.app.schemas.compliance import SafetyCheckRequest, SafetyCheckResponse
from backend.app.pipeline.safety_guard import ContentLicenseGuard

router = APIRouter()


@router.post("/safety/check", response_model=SafetyCheckResponse)
async def check_prompt_safety(req: SafetyCheckRequest):
    """
    Scans a video generation prompt for protected fictional characters, celebrity names,
    trademarked franchises, and returns constructive rewrite alternatives.
    """
    return ContentLicenseGuard.analyze_prompt(req.prompt)

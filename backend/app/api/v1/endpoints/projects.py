"""
Project REST API Endpoints.
Covers Section 19: All project CRUD, storyboard preview, generation, scene regeneration,
status polling, downloads, subtitle streaming, and asset manifest inspection with user session support.
"""
import io
import zipfile
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

from backend.app.models.database import get_db, AsyncSessionLocal
from backend.app.models.entities import Project, Scene, Shot, Story, Character, Location, User
from backend.app.schemas.project import ProjectCreateRequest, ProjectResponse
from backend.app.schemas.screenplay import SceneSchema, StoryboardResponse, ShotSchema
from backend.app.pipeline.orchestrator import WorkflowOrchestrator
from backend.app.config import settings
from backend.app.api.deps import get_current_user_optional

router = APIRouter()


async def _run_generation_task(project_id: str):
    """Background task to run full generation pipeline."""
    async with AsyncSessionLocal() as session:
        orchestrator = WorkflowOrchestrator(session)
        try:
            await orchestrator.execute_full_video_pipeline(project_id)
        except Exception as e:
            stmt = select(Project).where(Project.id == project_id)
            res = await session.execute(stmt)
            p = res.scalar_one_or_none()
            if p:
                p.status = "FAILED"
                p.error_message = str(e)
                await session.commit()


@router.post("/projects", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    req: ProjectCreateRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """Create a new long-form video generation project."""
    project = Project(
        user_id=current_user.id if current_user else None,
        prompt=req.prompt,
        language=req.language,
        target_duration=req.target_duration,
        video_style=req.video_style,
        character_style=req.character_style,
        voice_type=req.voice_type,
        resolution=req.resolution,
        aspect_ratio=req.aspect_ratio,
        music_mood=req.music_mood,
        status="DRAFT",
        current_stage="DRAFT",
        progress_percentage=0
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/projects", response_model=List[ProjectResponse])
async def list_projects(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db)
):
    """List projects. Filters by current authenticated user if logged in."""
    if current_user:
        stmt = select(Project).where(
            or_(Project.user_id == current_user.id, Project.user_id.is_(None))
        ).order_by(Project.created_at.desc())
    else:
        stmt = select(Project).order_by(Project.created_at.desc())
        
    res = await db.execute(stmt)
    return res.scalars().all()


@router.get("/projects/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get project status and details."""
    stmt = select(Project).where(Project.id == project_id)
    res = await db.execute(stmt)
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.post("/projects/{project_id}/storyboard")
async def generate_storyboard(project_id: str, db: AsyncSession = Depends(get_db)):
    """Generate storyboard preview (Story, Characters, Locations, Scenes) without video render."""
    orchestrator = WorkflowOrchestrator(db)
    try:
        storyboard = await orchestrator.generate_storyboard(project_id)
        return storyboard
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storyboard generation failed: {str(e)}")


@router.post("/projects/{project_id}/generate")
async def start_generation(project_id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Start asynchronous full long-form video generation pipeline."""
    stmt = select(Project).where(Project.id == project_id)
    res = await db.execute(stmt)
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = "QUEUED"
    project.current_stage = "QUEUED"
    project.progress_percentage = 0
    await db.commit()

    background_tasks.add_task(_run_generation_task, project_id)
    return {"message": "Video generation job queued successfully", "project_id": project_id, "status": "QUEUED"}


@router.get("/projects/{project_id}/status")
async def get_project_status(project_id: str, db: AsyncSession = Depends(get_db)):
    """Get real-time job processing status and percentage."""
    stmt = select(Project).where(Project.id == project_id)
    res = await db.execute(stmt)
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "project_id": project.id,
        "status": project.status,
        "current_stage": project.current_stage,
        "progress_percentage": project.progress_percentage,
        "error_message": project.error_message,
        "final_video_url": project.final_video_url,
        "thumbnail_url": project.thumbnail_url,
        "subtitle_en_url": project.subtitle_en_url,
        "subtitle_hi_url": project.subtitle_hi_url,
        "manifest_url": project.manifest_url
    }


@router.get("/projects/{project_id}/scenes")
async def get_project_scenes(project_id: str, db: AsyncSession = Depends(get_db)):
    """Retrieve all scenes and shots for a project."""
    stmt = select(Scene).where(Scene.project_id == project_id).order_by(Scene.order)
    res = await db.execute(stmt)
    scenes = res.scalars().all()
    return scenes


@router.post("/projects/{project_id}/scenes/{scene_id}/regenerate")
async def regenerate_scene(project_id: str, scene_id: str, custom_prompt_tweak: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Regenerate a single scene without re-rendering the whole video."""
    orchestrator = WorkflowOrchestrator(db)
    try:
        updated_scene = await orchestrator.regenerate_scene(scene_id, custom_prompt_tweak)
        return updated_scene
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scene regeneration failed: {str(e)}")


@router.get("/projects/{project_id}/download")
async def download_project_package(project_id: str, db: AsyncSession = Depends(get_db)):
    """Downloads a complete ZIP bundle (final video, subtitles, thumbnail, asset manifest)."""
    stmt = select(Project).where(Project.id == project_id)
    res = await db.execute(stmt)
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_dir = settings.OUTPUT_DIR / project_id
    if not project_dir.exists():
        raise HTTPException(status_code=404, detail="Project output files not found")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in project_dir.glob("*"):
            if file_path.is_file():
                zip_file.write(file_path, arcname=file_path.name)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=videogen_{project_id}.zip"}
    )


@router.get("/storage/{file_path:path}")
async def serve_storage_file(file_path: str):
    """Direct file serving endpoint for generated video clips, keyframes, and subtitles."""
    full_path = settings.STORAGE_DIR / file_path
    if not full_path.exists() or not full_path.is_file():
        # Also check OUTPUT_DIR
        out_path = settings.OUTPUT_DIR / file_path
        if out_path.exists() and out_path.is_file():
            full_path = out_path
        else:
            raise HTTPException(status_code=404, detail=f"File {file_path} not found")

    media_type = "application/octet-stream"
    if full_path.suffix == ".mp4":
        media_type = "video/mp4"
    elif full_path.suffix in (".jpg", ".jpeg"):
        media_type = "image/jpeg"
    elif full_path.suffix == ".png":
        media_type = "image/png"
    elif full_path.suffix == ".wav":
        media_type = "audio/wav"
    elif full_path.suffix == ".srt":
        media_type = "text/plain"
    elif full_path.suffix == ".vtt":
        media_type = "text/vtt"
    elif full_path.suffix == ".json":
        media_type = "application/json"

    return FileResponse(full_path, media_type=media_type)

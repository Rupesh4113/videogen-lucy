"""
Project REST API Endpoints.
Covers Section 19: All project CRUD, storyboard preview, generation, scene regeneration,
status polling, downloads, subtitle streaming, and asset manifest inspection.
"""
import io
import zipfile
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.models.database import get_db, AsyncSessionLocal
from backend.app.models.entities import Project, Scene, Shot, Story, Character, Location
from backend.app.schemas.project import ProjectCreateRequest, ProjectResponse
from backend.app.schemas.screenplay import SceneSchema, StoryboardResponse, ShotSchema
from backend.app.pipeline.orchestrator import WorkflowOrchestrator
from backend.app.config import settings

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
async def create_project(req: ProjectCreateRequest, db: AsyncSession = Depends(get_db)):
    """Create a new long-form video generation project."""
    project = Project(
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
async def list_projects(db: AsyncSession = Depends(get_db)):
    """List all projects."""
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
    """Get scene and shot breakdown for project."""
    stmt = select(Scene).where(Scene.project_id == project_id).order_by(Scene.order)
    res = await db.execute(stmt)
    scenes = res.scalars().all()

    result = []
    for sc in scenes:
        shot_stmt = select(Shot).where(Shot.scene_id == sc.id).order_by(Shot.order)
        shots = (await db.execute(shot_stmt)).scalars().all()
        sc_dict = {
            "id": sc.id,
            "order": sc.order,
            "scene_number": sc.scene_number,
            "title": sc.title,
            "duration_seconds": sc.duration_seconds,
            "location_name": sc.location_name,
            "time_of_day": sc.time_of_day,
            "characters": sc.characters_json,
            "action": sc.action,
            "dialogue": sc.dialogue_json,
            "narration": sc.narration,
            "emotion": sc.emotion,
            "camera": sc.camera,
            "lighting": sc.lighting,
            "sound_effects": sc.sound_effects,
            "music_prompt": sc.music_prompt,
            "visual_prompt": sc.visual_prompt,
            "video_url": sc.video_url,
            "audio_url": sc.audio_url,
            "status": sc.status,
            "shots": [
                {
                    "id": sh.id,
                    "order": sh.order,
                    "shot_number": sh.shot_number,
                    "shot_type": sh.shot_type,
                    "duration_seconds": sh.duration_seconds,
                    "description": sh.description,
                    "camera_movement": sh.camera_movement,
                    "visual_prompt": sh.visual_prompt,
                    "video_url": sh.video_url,
                    "status": sh.status
                } for sh in shots
            ]
        }
        result.append(sc_dict)
    return result


@router.post("/projects/{project_id}/scenes/{scene_id}/regenerate")
async def regenerate_scene(project_id: str, scene_id: str, custom_prompt: Optional[str] = None, db: AsyncSession = Depends(get_db)):
    """Regenerate a specific scene without re-rendering the full video."""
    orchestrator = WorkflowOrchestrator(db)
    try:
        scene = await orchestrator.regenerate_scene(scene_id, custom_prompt)
        return {"message": f"Scene {scene.scene_number} regenerated successfully", "video_url": scene.video_url}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/projects/{project_id}/cancel")
async def cancel_generation(project_id: str, db: AsyncSession = Depends(get_db)):
    """Cancel active generation job."""
    stmt = select(Project).where(Project.id == project_id)
    res = await db.execute(stmt)
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = "CANCELLED"
    project.current_stage = "CANCELLED"
    await db.commit()
    return {"message": "Job cancelled", "project_id": project_id}


@router.get("/projects/{project_id}/download")
async def download_project_package(project_id: str, db: AsyncSession = Depends(get_db)):
    """
    Downloads complete YouTube-ready production bundle as a ZIP file containing:
    video.mp4, thumbnail.jpg, subtitles_en.srt, subtitles_hi.vtt, project.json, asset_manifest.json.
    """
    stmt = select(Project).where(Project.id == project_id)
    res = await db.execute(stmt)
    project = res.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project_dir = settings.OUTPUT_DIR / project.id
    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        if project_dir.exists():
            for file_path in project_dir.glob("*.*"):
                zip_file.write(file_path, arcname=file_path.name)
        else:
            # Write project metadata fallback
            zip_file.writestr("project.json", f'{{"id": "{project.id}", "title": "{project.title}"}}')

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="videogen_{project.id}_bundle.zip"'}
    )


@router.get("/projects/{project_id}/subtitles")
async def get_project_subtitles(project_id: str, lang: str = "en", format: str = "srt", db: AsyncSession = Depends(get_db)):
    """Download or stream project subtitles."""
    sub_file = settings.OUTPUT_DIR / project_id / f"subtitles_{lang}.{format}"
    if not sub_file.exists():
        raise HTTPException(status_code=404, detail="Subtitles not generated yet")
    return FileResponse(sub_file, media_type="text/plain", filename=f"subtitles_{lang}.{format}")


@router.get("/projects/{project_id}/assets")
async def get_project_assets(project_id: str, db: AsyncSession = Depends(get_db)):
    """Inspect complete asset manifest and licensing ledger."""
    manifest_file = settings.OUTPUT_DIR / project_id / "asset_manifest.json"
    if not manifest_file.exists():
        raise HTTPException(status_code=404, detail="Asset manifest not generated yet")
    import json
    with open(manifest_file, "r", encoding="utf-8") as f:
        return json.load(f)

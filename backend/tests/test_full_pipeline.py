"""
End-to-End Test for the Complete 14-Stage AI Video Production Pipeline.
"""
import pytest
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.models.entities import Project
from backend.app.pipeline.orchestrator import WorkflowOrchestrator
from backend.app.config import settings


@pytest.mark.asyncio
async def test_full_video_pipeline_end_to_end(db_session: AsyncSession):
    # 1. Setup Project
    project = Project(
        prompt="Create a heartwarming 5-minute story about a mother living in an Indian village during the monsoon.",
        language="en",
        target_duration=300,
        video_style="Cinematic animation",
        character_style="Semi-realistic",
        voice_type="Narrator + characters",
        resolution="1080p",
        aspect_ratio="16:9",
        music_mood="Indian",
        status="DRAFT"
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    orchestrator = WorkflowOrchestrator(db_session)

    # 2. Generate Storyboard
    sb = await orchestrator.generate_storyboard(project.id)
    assert sb.story.title is not None
    assert len(sb.scenes) == 6
    assert sb.total_estimated_shots > 0

    # 3. Execute Full Video Pipeline
    final_video_url = await orchestrator.execute_full_video_pipeline(project.id)
    assert final_video_url is not None

    await db_session.refresh(project)
    assert project.status == "COMPLETED"
    assert project.progress_percentage == 100
    assert project.final_video_url is not None
    assert project.manifest_url is not None
    assert project.subtitle_en_url is not None

    # Check that output files actually exist
    project_dir = settings.OUTPUT_DIR / project.id
    assert (project_dir / "final_video.mp4").exists()
    assert (project_dir / "asset_manifest.json").exists()
    assert (project_dir / "subtitles_en.srt").exists()

    # 4. Test Single Scene Regeneration without re-running entire pipeline
    first_scene = sb.scenes[0]
    # Fetch database scene entity
    from sqlalchemy import select
    from backend.app.models.entities import Scene
    stmt = select(Scene).where(Scene.project_id == project.id, Scene.scene_number == 1)
    db_sc = (await db_session.execute(stmt)).scalar_one()

    regen_sc = await orchestrator.regenerate_scene(db_sc.id, custom_prompt_tweak="More intense rain lighting")
    assert regen_sc.status == "COMPLETED"
    assert regen_sc.video_url is not None

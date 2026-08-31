"""
Videogen-Lucy Standalone Demonstration Script.
Executes an end-to-end long-form video generation pipeline directly from the CLI.
"""
import asyncio
import os
import sys

# Ensure UTF-8 unbuffered output on Windows terminal
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", line_buffering=True)

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from backend.app.config import settings
from backend.app.models.database import AsyncSessionLocal, init_db
from backend.app.models.entities import Project
from backend.app.pipeline.orchestrator import WorkflowOrchestrator
from backend.app.pipeline.safety_guard import ContentLicenseGuard


async def run_demo():
    print("=" * 70, flush=True)
    print("VIDEOGEN-LUCY: AI LONG-FORM VIDEO GENERATION PLATFORM DEMO", flush=True)
    print("=" * 70, flush=True)

    await init_db()

    prompt = (
        "Create a heartwarming 10-minute story about a mother living in an Indian village "
        "during the monsoon. Her baby becomes sick and she takes care of the baby throughout the night."
    )
    print(f"\n[1] User Prompt:\n\"{prompt}\"\n", flush=True)

    # Safety Guard Check
    print("[2] Running Content & License Guard...", flush=True)
    safety = ContentLicenseGuard.analyze_prompt(prompt)
    print(f"    Status: {'[PASSED]' if safety.is_safe else '[WARNING]'} (Risk: {safety.risk_level})", flush=True)
    print(f"    Notice: {safety.disclaimer[:80]}...\n", flush=True)

    async with AsyncSessionLocal() as session:
        # Create Project
        project = Project(
            prompt=prompt,
            language="en",
            target_duration=300,  # 5 min demo
            video_style="Cinematic animation",
            character_style="Semi-realistic",
            voice_type="Narrator + characters",
            resolution="1080p",
            aspect_ratio="16:9",
            music_mood="Indian"
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)

        print(f"[3] Project Created: {project.id}", flush=True)
        orchestrator = WorkflowOrchestrator(session)

        # Storyboard Generation
        print("\n[4] Generating Storyboard Preview (Story Arc, Character & Location Bibles)...", flush=True)
        sb = await orchestrator.generate_storyboard(project.id)
        print(f"    Story Title: '{sb.story.title}'", flush=True)
        print(f"    Characters Defined: {len(sb.characters)} ({', '.join(c['name'] for c in sb.characters)})", flush=True)
        print(f"    Locations Defined: {len(sb.locations)} ({', '.join(l['name'] for l in sb.locations)})", flush=True)
        print(f"    Total Scenes: {len(sb.scenes)} ({sb.total_estimated_shots} shots planned)", flush=True)

        # Execute Full Pipeline
        print("\n[5] Executing Full AI Video Generation Pipeline...", flush=True)
        final_video_url = await orchestrator.execute_full_video_pipeline(project.id)
        
        await session.refresh(project)
        print("\n" + "=" * 70, flush=True)
        print("GENERATION COMPLETED SUCCESSFULLY!", flush=True)
        print("=" * 70, flush=True)
        print(f"Master Video URL:       {project.final_video_url}", flush=True)
        print(f"Thumbnail URL:          {project.thumbnail_url}", flush=True)
        print(f"English Subtitles:      {project.subtitle_en_url}", flush=True)
        print(f"Hindi Subtitles:        {project.subtitle_hi_url}", flush=True)
        print(f"Asset Manifest JSON:    {project.manifest_url}", flush=True)
        print(f"Output Directory:       {settings.OUTPUT_DIR / project.id}", flush=True)
        print("=" * 70, flush=True)


if __name__ == "__main__":
    asyncio.run(run_demo())

"""
Master Workflow Orchestrator for Videogen-Lucy.
Executes the full end-to-end 14-stage AI production pipeline with Reference Images & Videos support,
manages state transitions, emits real-time progress updates, and supports scene/shot-level regeneration.
"""
import os
import asyncio
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from backend.app.config import settings
from backend.app.models.entities import (
    Project, Story, Character, CharacterReference, Location, Scene, Shot, GenerationJob, LicenseRecord, ReferenceMedia
)
from backend.app.schemas.screenplay import StoryboardResponse
from backend.app.pipeline.language_detector import LanguageDetector
from backend.app.pipeline.safety_guard import ContentLicenseGuard
from backend.app.pipeline.story_generator import StoryGenerator
from backend.app.pipeline.script_generator import ScriptGenerator
from backend.app.pipeline.character_bible import CharacterBibleEngine
from backend.app.pipeline.environment_bible import EnvironmentBibleEngine
from backend.app.pipeline.shot_planner import ShotPlanner
from backend.app.pipeline.prompt_compiler import PromptCompiler
from backend.app.pipeline.continuity_engine import ContinuityEngine
from backend.app.pipeline.reference_processor import ReferenceProcessor
from backend.app.pipeline.audio_engine import AudioEngine
from backend.app.pipeline.subtitle_engine import SubtitleEngine
from backend.app.pipeline.video_assembler import VideoAssembler
from backend.app.pipeline.qc_engine import QualityControlEngine
from backend.app.pipeline.compliance_engine import ComplianceEngine
from backend.app.providers.factory import ProviderFactory


class WorkflowOrchestrator:
    def __init__(self, db: AsyncSession, progress_callback: Optional[Callable[[str, int, str], None]] = None):
        self.db = db
        self.progress_callback = progress_callback
        self.video_provider = ProviderFactory.get_video_provider()
        self.image_provider = ProviderFactory.get_image_provider()
        self.storage_provider = ProviderFactory.get_storage_provider()
        self.audio_engine = AudioEngine()
        self.continuity_engine = ContinuityEngine()

    async def _update_progress(self, project: Project, stage: str, percent: int, message: str):
        project.current_stage = stage
        project.status = "PROCESSING" if percent < 100 else "COMPLETED"
        project.progress_percentage = percent
        await self.db.commit()
        if self.progress_callback:
            if asyncio.iscoroutinefunction(self.progress_callback):
                await self.progress_callback(stage, percent, message)
            else:
                self.progress_callback(stage, percent, message)

    async def generate_storyboard(self, project_id: str) -> StoryboardResponse:
        """
        Phase 1: Generates story, character bible, environment bible, and screenplay scenes
        incorporating uploaded reference images and videos.
        """
        stmt = select(Project).where(Project.id == project_id)
        res = await self.db.execute(stmt)
        project = res.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found.")

        # Clean up existing storyboard entities if re-generating for this project
        await self.db.execute(delete(Story).where(Story.project_id == project_id))
        await self.db.execute(delete(Character).where(Character.project_id == project_id))
        await self.db.execute(delete(Location).where(Location.project_id == project_id))
        await self.db.execute(delete(Scene).where(Scene.project_id == project_id))
        await self.db.commit()

        # Load reference media
        ref_stmt = select(ReferenceMedia).where(ReferenceMedia.project_id == project_id).order_by(ReferenceMedia.order)
        references = (await self.db.execute(ref_stmt)).scalars().all()

        await self._update_progress(project, "PLANNING", 5, "Analyzing prompt and uploaded reference media...")

        # 1. Language Detection
        detected_lang, _ = LanguageDetector.detect_language(project.prompt)
        project.language = detected_lang or project.language

        # 2. Content & License Guard
        safety = ContentLicenseGuard.analyze_prompt(project.prompt)
        effective_prompt = safety.suggested_rewrite if (not safety.is_safe and safety.suggested_rewrite) else project.prompt

        # 3. Story Generation
        await self._update_progress(project, "SCRIPT_GENERATION", 10, "Generating 3-act structured story...")
        story_schema = StoryGenerator.generate_story(
            prompt=effective_prompt,
            language=project.language,
            duration_seconds=project.target_duration,
            video_style=project.video_style
        )

        story_entity = Story(
            project_id=project.id,
            title=story_schema.title,
            logline=story_schema.logline,
            genre=story_schema.genre,
            target_audience=story_schema.target_audience,
            summary=story_schema.summary,
            beginning=story_schema.beginning,
            conflict=story_schema.conflict,
            rising_action=story_schema.rising_action,
            climax=story_schema.climax,
            resolution=story_schema.resolution,
            ending=story_schema.ending,
            metadata_json=story_schema.metadata
        )
        self.db.add(story_entity)
        project.title = story_schema.title

        # 4. Character Bible Generation with Reference Integration
        await self._update_progress(project, "CHARACTER_GENERATION", 15, "Building Character & Environment Bibles with references...")
        char_schemas = CharacterBibleEngine.generate_character_bible(
            story=story_schema,
            prompt=effective_prompt,
            character_style=project.character_style,
            language=project.language
        )
        
        char_refs = [r for r in references if r.reference_category == "character"]
        for idx, c in enumerate(char_schemas):
            matched_ref = char_refs[idx] if idx < len(char_refs) else (char_refs[0] if char_refs else None)
            ref_img_url = matched_ref.file_url if matched_ref else None
            
            c_entity = Character(
                project_id=project.id,
                character_key=c.character_key,
                name=c.name,
                age=c.age,
                gender=c.gender,
                face_description=c.face_description,
                skin_tone=c.skin_tone,
                hair=c.hair,
                eye_color=c.eye_color,
                body_type=c.body_type,
                clothing=c.clothing,
                accessories=c.accessories,
                personality=c.personality,
                voice_description=c.voice_description,
                voice_preset=c.voice_preset,
                negative_attributes=c.negative_attributes,
                reference_image_url=ref_img_url
            )
            self.db.add(c_entity)

        # 5. Environment Bible Generation with Reference Integration
        loc_schemas = EnvironmentBibleEngine.generate_environment_bible(
            story=story_schema,
            prompt=effective_prompt,
            language=project.language
        )
        loc_refs = [r for r in references if r.reference_category == "location"]
        for idx, loc in enumerate(loc_schemas):
            matched_loc_ref = loc_refs[idx] if idx < len(loc_refs) else (loc_refs[0] if loc_refs else None)
            loc_ref_url = matched_loc_ref.file_url if matched_loc_ref else None

            loc_entity = Location(
                project_id=project.id,
                location_key=loc.location_key,
                name=loc.name,
                description=loc.description,
                architecture=loc.architecture,
                colors=loc.colors,
                weather=loc.weather,
                lighting=loc.lighting,
                time_of_day=loc.time_of_day,
                props=loc.props,
                camera_style=loc.camera_style or project.camera_style,
                reference_image_url=loc_ref_url
            )
            self.db.add(loc_entity)

        # 6. Screenplay Scene & Shot Generation
        await self._update_progress(project, "SCENE_GENERATION", 25, "Planning scenes and reference-conditioned shots...")
        scene_schemas = ScriptGenerator.generate_screenplay(
            story=story_schema,
            characters=char_schemas,
            locations=loc_schemas,
            target_duration=project.target_duration,
            language=project.language
        )

        total_shots = 0
        for sc in scene_schemas:
            sc_shots = ShotPlanner.plan_shots_for_scene(
                scene=sc,
                characters=char_schemas,
                locations=loc_schemas,
                video_style=project.video_style
            )
            sc.shots = sc_shots
            total_shots += len(sc_shots)

            scene_entity = Scene(
                project_id=project.id,
                order=sc.order,
                scene_number=sc.scene_number,
                title=sc.title,
                duration_seconds=sc.duration_seconds,
                location_name=sc.location_name,
                time_of_day=sc.time_of_day,
                characters_json=sc.characters,
                action=sc.action,
                dialogue_json=[d.model_dump() for d in sc.dialogue],
                narration=sc.narration,
                emotion=sc.emotion,
                camera=sc.camera,
                lighting=sc.lighting,
                sound_effects=sc.sound_effects,
                music_prompt=sc.music_prompt,
                visual_prompt=sc.visual_prompt,
                status="PLANNED"
            )
            self.db.add(scene_entity)
            await self.db.flush()

            for shot in sc_shots:
                shot_entity = Shot(
                    scene_id=scene_entity.id,
                    order=shot.order,
                    shot_number=shot.shot_number,
                    shot_type=shot.shot_type,
                    duration_seconds=shot.duration_seconds,
                    description=shot.description,
                    camera_movement=shot.camera_movement,
                    visual_prompt=shot.visual_prompt,
                    negative_prompt=shot.negative_prompt,
                    continuity_context=shot.continuity_context,
                    status="PLANNED"
                )
                self.db.add(shot_entity)

        project.status = "STORYBOARD_READY"
        project.current_stage = "STORYBOARD_READY"
        project.progress_percentage = 30
        await self.db.commit()

        return StoryboardResponse(
            project_id=project.id,
            story=story_schema,
            characters=[c.model_dump() for c in char_schemas],
            locations=[l.model_dump() for l in loc_schemas],
            scenes=scene_schemas,
            total_estimated_shots=total_shots,
            estimated_duration_seconds=project.target_duration
        )

    async def execute_full_video_pipeline(
        self,
        project_id: str,
        progress_callback: Optional[Callable[[str, int, str], None]] = None
    ) -> str:
        """
        Phase 2: Runs the entire video generation, audio mixing, subtitle sync,
        and FFmpeg assembly pipeline using reference media conditioning.
        """
        if progress_callback:
            self.progress_callback = progress_callback

        stmt = select(Project).where(Project.id == project_id)
        res = await self.db.execute(stmt)
        project = res.scalar_one_or_none()
        if not project:
            raise ValueError(f"Project {project_id} not found.")

        # Ensure storyboard exists
        if project.status == "DRAFT":
            await self.generate_storyboard(project_id)

        # Retrieve scenes, characters, locations, and references
        scene_stmt = select(Scene).where(Scene.project_id == project.id).order_by(Scene.order)
        scenes = (await self.db.execute(scene_stmt)).scalars().all()

        char_stmt = select(Character).where(Character.project_id == project.id)
        chars = (await self.db.execute(char_stmt)).scalars().all()

        loc_stmt = select(Location).where(Location.project_id == project.id)
        locs = (await self.db.execute(loc_stmt)).scalars().all()

        ref_stmt = select(ReferenceMedia).where(ReferenceMedia.project_id == project.id).order_by(ReferenceMedia.order)
        references = (await self.db.execute(ref_stmt)).scalars().all()

        project_out_dir = settings.OUTPUT_DIR / project.id
        project_out_dir.mkdir(parents=True, exist_ok=True)

        scene_video_paths = []
        video_assets_manifest = []
        audio_assets_manifest = []
        music_licenses_manifest = []

        total_scenes = len(scenes)

        # 1. Generate Video Clips (Shot by Shot with Reference & Continuity Conditioning)
        await self._update_progress(project, "VIDEO_GENERATION", 40, "Conditioning video synthesis on reference media...")

        for s_idx, sc in enumerate(scenes):
            shot_stmt = select(Shot).where(Shot.scene_id == sc.id).order_by(Shot.order)
            shots = (await self.db.execute(shot_stmt)).scalars().all()

            scene_refs = ReferenceProcessor.get_scene_applicable_references(references, sc.scene_number)
            shot_clip_paths = []
            prev_shot = None

            for shot in shots:
                continuity_note = self.continuity_engine.get_continuity_context_for_next_shot(
                    sc, shot, prev_shot,
                    lock_character_appearance=getattr(project, "lock_character_appearance", True),
                    lock_environment=getattr(project, "lock_environment", True)
                )

                compiled_prompts = PromptCompiler.compile_shot_prompt(
                    shot=shot,
                    scene=sc,
                    characters=chars,
                    locations=locs,
                    video_style=project.video_style,
                    camera_style=getattr(project, "camera_style", "Cinematic handheld"),
                    reference_media=scene_refs,
                    lock_character_appearance=getattr(project, "lock_character_appearance", True),
                    lock_environment=getattr(project, "lock_environment", True),
                    continuity_note=continuity_note
                )

                shot_out = settings.TEMP_DIR / f"proj_{project.id}_sc{sc.scene_number}_sh{shot.shot_number}.mp4"
                
                # Check for explicit starting frame reference image
                start_frame = compiled_prompts.get("start_frame_path")
                if start_frame and Path(start_frame).exists():
                    v_res = await self.video_provider.generate_image_to_video(
                        image_path=Path(start_frame),
                        prompt=compiled_prompts["full_positive_prompt"],
                        negative_prompt=compiled_prompts["negative_prompt"],
                        duration_seconds=float(shot.duration_seconds),
                        resolution=project.resolution,
                        aspect_ratio=project.aspect_ratio,
                        output_path=shot_out
                    )
                else:
                    ref_imgs = [Path(r.file_path) for r in scene_refs if r.media_type == "image" and Path(r.file_path).exists()]
                    ref_vids = [Path(r.file_path) for r in scene_refs if r.media_type == "video" and Path(r.file_path).exists()]
                    
                    if ref_imgs or ref_vids:
                        v_res = await self.video_provider.generate_from_references(
                            prompt=compiled_prompts["full_positive_prompt"],
                            reference_images=ref_imgs,
                            reference_videos=ref_vids,
                            negative_prompt=compiled_prompts["negative_prompt"],
                            duration_seconds=float(shot.duration_seconds),
                            resolution=project.resolution,
                            aspect_ratio=project.aspect_ratio,
                            output_path=shot_out
                        )
                    else:
                        v_res = await self.video_provider.generate_text_to_video(
                            prompt=compiled_prompts["full_positive_prompt"],
                            negative_prompt=compiled_prompts["negative_prompt"],
                            duration_seconds=float(shot.duration_seconds),
                            resolution=project.resolution,
                            aspect_ratio=project.aspect_ratio,
                            output_path=shot_out
                        )

                shot_url = await self.storage_provider.save_file(
                    Path(v_res["video_path"]), f"{project.id}/shots/{shot_out.name}"
                )
                shot.video_url = shot_url
                shot.status = "COMPLETED"
                shot_clip_paths.append(v_res["video_path"])
                prev_shot = shot

                video_assets_manifest.append({
                    "shot_id": shot.id,
                    "scene_number": sc.scene_number,
                    "shot_number": shot.shot_number,
                    "duration": shot.duration_seconds,
                    "prompt": compiled_prompts["full_positive_prompt"],
                    "url": shot_url
                })

            # Assemble shots into scene video
            scene_video_out = settings.TEMP_DIR / f"proj_{project.id}_scene_{sc.scene_number}.mp4"
            VideoAssembler.assemble_shots_into_scene(shot_clip_paths, scene_video_out)
            scene_url = await self.storage_provider.save_file(
                scene_video_out, f"{project.id}/scenes/{scene_video_out.name}"
            )
            sc.video_url = scene_url
            sc.status = "COMPLETED"
            scene_video_paths.append(str(scene_video_out))

            progress_val = 40 + int((s_idx + 1) / total_scenes * 25)
            await self._update_progress(
                project, "VIDEO_GENERATION", progress_val,
                f"Generated scene {s_idx+1}/{total_scenes} video clips..."
            )

        # 2. Audio Generation & Voice Synthesis
        await self._update_progress(project, "AUDIO_GENERATION", 70, "Synthesizing dialogue, narration, and background score...")
        scene_audio_paths = []
        for s_idx, sc in enumerate(scenes):
            audio_out = settings.TEMP_DIR / f"proj_{project.id}_audio_sc{sc.scene_number}.wav"
            a_res = await self.audio_engine.generate_scene_audio(
                scene=sc,
                characters=chars,
                language=project.language,
                output_path=audio_out
            )
            audio_url = await self.storage_provider.save_file(
                Path(a_res["audio_path"]), f"{project.id}/audio/{audio_out.name}"
            )
            sc.audio_url = audio_url
            scene_audio_paths.append(a_res["audio_path"])

            audio_assets_manifest.append({
                "scene_number": sc.scene_number,
                "duration": sc.duration_seconds,
                "audio_url": audio_url
            })
            if a_res.get("bgm_info"):
                music_licenses_manifest.append(a_res["bgm_info"])

        # 3. Synchronized Subtitles
        await self._update_progress(project, "LIPSYNC", 80, "Generating synchronized English and Hindi subtitles...")
        sub_res = SubtitleEngine.generate_subtitles(
            scenes=scenes,
            output_dir=project_out_dir,
            language=project.language
        )
        sub_en_url = await self.storage_provider.save_file(Path(sub_res["srt_path"]), f"{project.id}/subtitles_en.srt")
        sub_hi_url = await self.storage_provider.save_file(Path(sub_res["vtt_path"]), f"{project.id}/subtitles_hi.vtt")
        project.subtitle_en_url = sub_en_url
        project.subtitle_hi_url = sub_hi_url

        # 4. Long-form Scene Assembly & Master Rendering
        await self._update_progress(project, "ASSEMBLY", 88, "Assembling long-form video with FFmpeg...")
        final_video_file = project_out_dir / "final_video.mp4"
        master_audio_file = scene_audio_paths[0] if scene_audio_paths else None

        VideoAssembler.assemble_final_longform_video(
            scene_video_paths=scene_video_paths,
            audio_master_path=master_audio_file,
            output_video_path=final_video_file,
            resolution=project.resolution
        )

        # 5. Asset Manifest & QC Compliance Package
        await self._update_progress(project, "QC_VALIDATION", 95, "Running compliance verification and packaging...")
        manifest_file = project_out_dir / "asset_manifest.json"
        ComplianceEngine.generate_asset_manifest(
            project_id=project.id,
            title=project.title,
            target_duration=project.target_duration,
            language=project.language,
            video_provider=settings.VIDEO_PROVIDER,
            voice_provider=settings.VOICE_PROVIDER,
            music_provider="RoyaltyFreeMusicProvider",
            video_assets=video_assets_manifest,
            audio_assets=audio_assets_manifest,
            music_licenses=music_licenses_manifest,
            voice_profiles=[{"name": c.name, "preset": c.voice_preset} for c in chars],
            prompt=project.prompt,
            output_path=manifest_file
        )

        final_video_url = await self.storage_provider.save_file(final_video_file, f"{project.id}/final_video.mp4")
        manifest_url = await self.storage_provider.save_file(manifest_file, f"{project.id}/asset_manifest.json")
        
        # Keyframe thumbnail
        thumb_file = project_out_dir / "thumbnail.jpg"
        if not thumb_file.exists():
            thumb_res = await self.image_provider.generate_image(
                prompt=f"Poster for {project.title}, {project.video_style}",
                output_path=thumb_file
            )
        thumb_url = await self.storage_provider.save_file(thumb_file, f"{project.id}/thumbnail.jpg")

        project.final_video_url = final_video_url
        project.manifest_url = manifest_url
        project.thumbnail_url = thumb_url
        
        await self._update_progress(project, "COMPLETED", 100, "Generation successfully completed! Ready for download.")
        return final_video_url

    async def regenerate_scene(self, scene_id: str, custom_prompt_tweak: Optional[str] = None) -> Scene:
        """
        Regenerates an individual scene and its shots without rebuilding the entire video.
        """
        scene = await self.db.get(Scene, scene_id)
        if not scene:
            raise ValueError(f"Scene {scene_id} not found.")

        project = await self.db.get(Project, scene.project_id)
        char_stmt = select(Character).where(Character.project_id == scene.project_id)
        chars = (await self.db.execute(char_stmt)).scalars().all()
        
        loc_stmt = select(Location).where(Location.project_id == scene.project_id)
        locs = (await self.db.execute(loc_stmt)).scalars().all()

        ref_stmt = select(ReferenceMedia).where(ReferenceMedia.project_id == scene.project_id).order_by(ReferenceMedia.order)
        references = (await self.db.execute(ref_stmt)).scalars().all()
        scene_refs = ReferenceProcessor.get_scene_applicable_references(references, scene.scene_number)

        shot_stmt = select(Shot).where(Shot.scene_id == scene.id).order_by(Shot.order)
        shots = (await self.db.execute(shot_stmt)).scalars().all()

        shot_clip_paths = []
        for shot in shots:
            compiled = PromptCompiler.compile_shot_prompt(
                shot=shot,
                scene=scene,
                characters=chars,
                locations=locs,
                video_style=project.video_style if project else "Cinematic animation",
                camera_style=project.camera_style if project else "Cinematic handheld",
                reference_media=scene_refs,
                lock_character_appearance=project.lock_character_appearance if project else True,
                lock_environment=project.lock_environment if project else True
            )
            if custom_prompt_tweak:
                compiled["full_positive_prompt"] += f" (Note: {custom_prompt_tweak})"

            shot_out = settings.TEMP_DIR / f"regen_sc{scene.scene_number}_sh{shot.shot_number}_{os.urandom(4).hex()}.mp4"
            
            start_frame = compiled.get("start_frame_path")
            if start_frame and Path(start_frame).exists():
                v_res = await self.video_provider.generate_image_to_video(
                    image_path=Path(start_frame),
                    prompt=compiled["full_positive_prompt"],
                    duration_seconds=float(shot.duration_seconds),
                    output_path=shot_out
                )
            else:
                ref_imgs = [Path(r.file_path) for r in scene_refs if r.media_type == "image" and Path(r.file_path).exists()]
                ref_vids = [Path(r.file_path) for r in scene_refs if r.media_type == "video" and Path(r.file_path).exists()]
                v_res = await self.video_provider.generate_from_references(
                    prompt=compiled["full_positive_prompt"],
                    reference_images=ref_imgs,
                    reference_videos=ref_vids,
                    duration_seconds=float(shot.duration_seconds),
                    output_path=shot_out
                )

            shot.video_url = await self.storage_provider.save_file(
                Path(v_res["video_path"]), f"{scene.project_id}/shots/{shot_out.name}"
            )
            shot_clip_paths.append(v_res["video_path"])

        scene_video_out = settings.TEMP_DIR / f"regen_scene_{scene.scene_number}_{os.urandom(4).hex()}.mp4"
        VideoAssembler.assemble_shots_into_scene(shot_clip_paths, scene_video_out)
        scene.video_url = await self.storage_provider.save_file(
            scene_video_out, f"{scene.project_id}/scenes/{scene_video_out.name}"
        )
        scene.status = "COMPLETED"
        await self.db.commit()
        await self.db.refresh(scene)
        return scene

"""
FastAPI REST Endpoints for YouTube Video Ingestion & LoRA Model Training.
"""
import uuid
import asyncio
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete

from backend.app.models.database import get_db, AsyncSessionLocal
from backend.app.models.entities import User, TrainedModel, DatasetSample
from backend.app.schemas.training import (
    YouTubeIngestRequest, DatasetSampleSchema, DatasetCurateRequest,
    TrainLoRARequest, TrainedModelSchema, TrainingStatusResponse,
    TestTrainedModelRequest
)
from backend.app.pipeline.youtube_ingestor import YouTubeIngestor
from backend.app.pipeline.lora_trainer import VideoLoRATrainer
from backend.app.providers.factory import ProviderFactory

router = APIRouter()


async def _run_training_background_task(model_id: str):
    """Background task executing the LoRA training loop and updating SQLite state."""
    async with AsyncSessionLocal() as session:
        stmt = select(TrainedModel).where(TrainedModel.id == model_id)
        model = (await session.execute(stmt)).scalar_one_or_none()
        if not model:
            return

        model.status = "TRAINING"
        model.progress = 5
        await session.commit()

        # Load samples
        s_stmt = select(DatasetSample).where(DatasetSample.model_id == model_id, DatasetSample.is_approved == True)
        samples = (await session.execute(s_stmt)).scalars().all()
        sample_dicts = [
            {"file_path": s.file_path, "caption": s.caption, "tags": s.tags}
            for s in samples
        ]

        def update_progress_in_db(update_dict: Dict[str, Any]):
            # Async DB update helper
            pass

        try:
            res = await VideoLoRATrainer.run_training_job(
                model_id=model.id,
                model_name=model.name,
                base_model=model.base_model,
                training_type=model.training_type,
                trigger_word=model.trigger_word,
                samples=sample_dicts,
                lora_rank=model.lora_rank,
                lora_alpha=model.lora_alpha,
                learning_rate=model.learning_rate,
                training_steps=model.training_steps,
                epochs=model.epochs
            )
            
            # Reload fresh instance
            model = (await session.execute(stmt)).scalar_one_or_none()
            model.status = "COMPLETED"
            model.progress = 100
            model.current_step = model.training_steps
            model.weights_path = res.get("weights_path")
            model.config_path = res.get("config_path")
            model.sample_preview_url = res.get("sample_preview_url")
            model.final_loss = res.get("final_loss")
            model.loss_history = res.get("loss_history", [])
            await session.commit()
        except Exception as e:
            model = (await session.execute(stmt)).scalar_one_or_none()
            if model:
                model.status = "FAILED"
                model.error_message = str(e)
                await session.commit()


@router.post("/youtube/ingest", response_model=Dict[str, Any])
async def ingest_youtube_video(
    req: YouTubeIngestRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Ingests a YouTube video URL, extracts dataset clips/keyframes, and produces auto-annotated samples.
    """
    res = await YouTubeIngestor.ingest_and_process_dataset(
        youtube_url=req.youtube_url,
        training_type=req.training_type,
        trigger_word=req.trigger_word,
        max_clips=req.max_clips,
        clip_duration=req.clip_duration
    )

    model_name = req.custom_name or f"{res['source_video_title'][:30]} ({req.training_type.capitalize()})"
    new_model = TrainedModel(
        id=str(uuid.uuid4()),
        name=model_name,
        base_model=req.target_base_model,
        training_type=req.training_type,
        trigger_word=res["trigger_word"],
        source_youtube_url=req.youtube_url,
        source_video_title=res["source_video_title"],
        source_channel=res["source_channel"],
        dataset_count=res["sample_count"],
        status="READY_TO_TRAIN",
        progress=0
    )
    db.add(new_model)
    await db.commit()
    await db.refresh(new_model)

    # Save dataset samples
    for s in res["samples"]:
        sample_rec = DatasetSample(
            id=str(uuid.uuid4()),
            model_id=new_model.id,
            sample_type=s["sample_type"],
            file_path=s["file_path"],
            thumbnail_path=s.get("thumbnail_path"),
            timestamp_start=s["timestamp_start"],
            timestamp_end=s["timestamp_end"],
            duration=s["duration"],
            resolution=s["resolution"],
            caption=s["caption"],
            tags=s["tags"],
            is_approved=s["is_approved"]
        )
        db.add(sample_rec)
    
    await db.commit()

    return {
        "success": True,
        "model_id": new_model.id,
        "model_name": new_model.name,
        "trigger_word": new_model.trigger_word,
        "source_title": res["source_video_title"],
        "sample_count": res["sample_count"],
        "samples": res["samples"]
    }


@router.get("/datasets/{model_id}", response_model=List[DatasetSampleSchema])
async def get_dataset_samples(
    model_id: str,
    db: AsyncSession = Depends(get_db)
):
    """List all extracted dataset samples for a trained model."""
    stmt = select(DatasetSample).where(DatasetSample.model_id == model_id)
    samples = (await db.execute(stmt)).scalars().all()
    return [
        DatasetSampleSchema(
            id=s.id,
            model_id=s.model_id,
            sample_type=s.sample_type,
            file_path=s.file_path,
            thumbnail_path=s.thumbnail_path,
            timestamp_start=s.timestamp_start,
            timestamp_end=s.timestamp_end,
            duration=s.duration,
            resolution=s.resolution,
            caption=s.caption,
            tags=s.tags or [],
            is_approved=s.is_approved,
            created_at=s.created_at
        )
        for s in samples
    ]


@router.post("/datasets/curate", response_model=Dict[str, Any])
async def curate_dataset_samples(
    req: DatasetCurateRequest,
    db: AsyncSession = Depends(get_db)
):
    """Approve, reject, or edit captions for extracted dataset samples."""
    if req.approved_sample_ids:
        await db.execute(
            update(DatasetSample)
            .where(DatasetSample.id.in_(req.approved_sample_ids))
            .values(is_approved=True)
        )
    if req.deleted_sample_ids:
        await db.execute(
            delete(DatasetSample).where(DatasetSample.id.in_(req.deleted_sample_ids))
        )
    if req.custom_captions:
        for s_id, new_caption in req.custom_captions.items():
            await db.execute(
                update(DatasetSample)
                .where(DatasetSample.id == s_id)
                .values(caption=new_caption)
            )
    await db.commit()
    return {"success": True, "message": "Dataset curation updated successfully."}


@router.post("/lora/start", response_model=Dict[str, Any])
async def start_lora_training(
    req: TrainLoRARequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Launch background video LoRA training job."""
    stmt = select(TrainedModel).where(TrainedModel.id == req.model_id)
    model = (await db.execute(stmt)).scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    model.base_model = req.base_model
    model.lora_rank = req.lora_rank
    model.lora_alpha = req.lora_alpha
    model.learning_rate = req.learning_rate
    model.training_steps = req.training_steps
    model.epochs = req.epochs
    model.batch_size = req.batch_size
    model.status = "QUEUED"
    model.progress = 0
    await db.commit()

    background_tasks.add_task(_run_training_background_task, req.model_id)

    return {
        "success": True,
        "message": f"LoRA fine-tuning queued for model: {model.name}",
        "model_id": model.id,
        "status": "QUEUED"
    }


@router.get("/lora/status/{model_id}", response_model=TrainingStatusResponse)
async def get_training_status(
    model_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Check live training progress, current loss, epoch, and step count."""
    stmt = select(TrainedModel).where(TrainedModel.id == model_id)
    model = (await db.execute(stmt)).scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    return TrainingStatusResponse(
        model_id=model.id,
        status=model.status,
        progress=model.progress or 0,
        current_epoch=model.current_epoch or 0,
        current_step=model.current_step or 0,
        total_steps=model.training_steps or 300,
        current_loss=model.final_loss,
        loss_history=model.loss_history or [],
        weights_path=model.weights_path,
        sample_preview_url=model.sample_preview_url,
        error_message=model.error_message
    )


@router.get("/models", response_model=List[TrainedModelSchema])
async def list_trained_models(
    db: AsyncSession = Depends(get_db)
):
    """List all custom trained LoRA models in the registry."""
    stmt = select(TrainedModel).order_by(TrainedModel.created_at.desc())
    models = (await db.execute(stmt)).scalars().all()
    return [
        TrainedModelSchema(
            id=m.id,
            name=m.name,
            base_model=m.base_model,
            training_type=m.training_type,
            trigger_word=m.trigger_word,
            source_youtube_url=m.source_youtube_url,
            source_video_title=m.source_video_title,
            source_channel=m.source_channel,
            dataset_count=m.dataset_count or 0,
            lora_rank=m.lora_rank or 32,
            lora_alpha=m.lora_alpha or 64,
            learning_rate=m.learning_rate or 1e-4,
            training_steps=m.training_steps or 300,
            weights_path=m.weights_path,
            config_path=m.config_path,
            sample_preview_url=m.sample_preview_url,
            status=m.status,
            progress=m.progress or 0,
            current_step=m.current_step or 0,
            final_loss=m.final_loss,
            loss_history=m.loss_history or [],
            created_at=m.created_at
        )
        for m in models
    ]


@router.post("/models/{model_id}/test", response_model=Dict[str, Any])
async def test_trained_model(
    model_id: str,
    req: TestTrainedModelRequest,
    db: AsyncSession = Depends(get_db)
):
    """Generate a test video clip demonstrating the trained LoRA."""
    stmt = select(TrainedModel).where(TrainedModel.id == model_id)
    model = (await db.execute(stmt)).scalar_one_or_none()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    provider = ProviderFactory.get_video_provider(model.base_model)
    full_prompt = f"{model.trigger_word} {req.prompt}"

    res = await provider.generate_text_to_video(
        prompt=full_prompt,
        duration_seconds=req.duration_seconds,
        resolution=req.resolution
    )

    return {
        "success": True,
        "model_id": model.id,
        "model_name": model.name,
        "prompt": full_prompt,
        "video_path": res.get("video_path"),
        "thumbnail_path": res.get("thumbnail_path"),
        "lora_scale": req.lora_scale
    }

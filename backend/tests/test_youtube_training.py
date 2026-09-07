"""
Tests for YouTube Video Ingestion, Dataset Chunking, Auto-Captioning, and Video LoRA Training.
"""
import pytest
import os
import json
from pathlib import Path
from httpx import AsyncClient, ASGITransport

from backend.app.main import app
from backend.app.pipeline.youtube_ingestor import YouTubeIngestor
from backend.app.pipeline.lora_trainer import VideoLoRATrainer
from backend.app.pipeline.prompt_compiler import PromptCompiler
from backend.app.schemas.screenplay import SceneSchema, ShotSchema
from backend.app.schemas.bible import CharacterSchema, LocationSchema


def test_youtube_url_id_parsing():
    url1 = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    url2 = "https://youtu.be/9bZkp7q19f0"
    url3 = "https://www.youtube.com/shorts/kXYiU_JCYtU"
    url4 = "dQw4w9WgXcQ"

    assert YouTubeIngestor.parse_video_id(url1) == "dQw4w9WgXcQ"
    assert YouTubeIngestor.parse_video_id(url2) == "9bZkp7q19f0"
    assert YouTubeIngestor.parse_video_id(url3) == "kXYiU_JCYtU"
    assert YouTubeIngestor.parse_video_id(url4) == "dQw4w9WgXcQ"


@pytest.mark.asyncio
async def test_youtube_metadata_extraction():
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    meta = await YouTubeIngestor.extract_metadata(url)
    assert meta["video_id"] == "dQw4w9WgXcQ"
    assert meta["title"] is not None
    assert meta["duration"] > 0
    assert "1080" in meta["resolution"] or "1920" in meta["resolution"]


@pytest.mark.asyncio
async def test_youtube_dataset_ingestion_and_auto_captioning(tmp_path):
    dataset_dir = tmp_path / "yt_test_dataset"
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    res = await YouTubeIngestor.ingest_and_process_dataset(
        youtube_url=url,
        training_type="character",
        trigger_word="[v_gauri_monsoon]",
        max_clips=3,
        clip_duration=2.0,
        output_dir=dataset_dir
    )

    assert res["success"] is True
    assert res["trigger_word"] == "[v_gauri_monsoon]"
    assert res["sample_count"] == 3
    assert len(res["samples"]) == 3

    for s in res["samples"]:
        assert "[v_gauri_monsoon]" in s["caption"]
        assert os.path.exists(s["file_path"])
        assert s["duration"] == 2.0


def test_lora_training_script_generation():
    script = VideoLoRATrainer.generate_training_script(
        model_name="Himalayan_Anime",
        base_model="Wan2.2-T2V-14B",
        dataset_dir="/tmp/dataset",
        output_dir="/tmp/output",
        trigger_word="[v_himalayan_anime]",
        lora_rank=32,
        lora_alpha=64,
        learning_rate=1e-4,
        training_steps=500
    )
    assert "Wan2.2-T2V-14B" in script
    assert "[v_himalayan_anime]" in script
    assert "LORA_RANK = 32" in script
    assert "LORA_ALPHA = 64" in script


@pytest.mark.asyncio
async def test_lora_training_execution_and_weights_export(tmp_path):
    # Prepare dummy samples
    sample_clip = tmp_path / "sample_001.mp4"
    from backend.app.utils.ffmpeg_helper import FFmpegHelper
    FFmpegHelper.render_animated_clip(
        output_path=sample_clip,
        prompt="Test LoRA clip",
        duration=2.0
    )

    samples = [
        {"file_path": str(sample_clip), "caption": "[v_test_actor] smiling in sunlight", "tags": ["portrait"]}
    ]

    res = await VideoLoRATrainer.run_training_job(
        model_id="test_model_123",
        model_name="TestActorLoRA",
        base_model="Wan2.2-T2V-14B",
        training_type="character",
        trigger_word="[v_test_actor]",
        samples=samples,
        lora_rank=16,
        lora_alpha=32,
        learning_rate=1e-4,
        training_steps=50,
        epochs=5
    )

    assert res["success"] is True
    assert res["model_id"] == "test_model_123"
    assert os.path.exists(res["weights_path"])
    assert res["weights_path"].endswith(".safetensors")
    assert os.path.exists(res["config_path"])
    assert os.path.exists(res["sample_preview_url"])
    assert res["final_loss"] is not None
    assert len(res["loss_history"]) > 0


def test_prompt_compiler_with_custom_lora_injection():
    shot = ShotSchema(
        order=0,
        shot_number=1,
        shot_type="Close-Up",
        description="Gauri smiles with maternal warmth",
        visual_prompt="Close-up of Gauri smiling with maternal warmth, soft golden lighting",
        duration_seconds=5,
        camera_movement="Slow tracking pan"
    )
    scene = SceneSchema(
        order=0,
        scene_number=1,
        title="Courtyard",
        duration_seconds=50,
        location_name="Village Courtyard",
        time_of_day="Evening",
        characters=["Gauri"],
        action="Gauri gathers herbs",
        dialogue=[],
        lighting="Golden sunset glow"
    )
    chars = [
        CharacterSchema(
            character_key="gauri",
            name="Gauri",
            age=26,
            gender="Female",
            face_description="Gentle eyes and warm smile",
            clothing="Green cotton saree"
        )
    ]
    locs = [
        LocationSchema(
            location_key="courtyard",
            name="Village Courtyard",
            description="Rustic courtyard with stone pathway",
            architecture="Mud and wooden houses"
        )
    ]

    custom_loras = [
        {
            "id": "lora_01",
            "name": "gauri_himalayan",
            "trigger_word": "[v_gauri_himalayan]",
            "scale": 0.85
        }
    ]

    compiled = PromptCompiler.compile_shot_prompt(
        shot=shot,
        scene=scene,
        characters=chars,
        locations=locs,
        lora_models=custom_loras
    )

    assert "[v_gauri_himalayan]" in compiled["full_positive_prompt"]
    assert "<lora:gauri_himalayan:0.85>" in compiled["full_positive_prompt"]
    assert len(compiled["lora_tags"]) == 1


@pytest.mark.asyncio
async def test_training_api_endpoints_workflow():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # 1. Ingest YouTube video
        ingest_payload = {
            "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "training_type": "character",
            "custom_name": "API Himalayan Character",
            "trigger_word": "[v_api_char]",
            "max_clips": 3,
            "clip_duration": 2.0,
            "target_base_model": "Wan2.2-T2V-14B"
        }
        res_ingest = await ac.post("/api/v1/training/youtube/ingest", json=ingest_payload)
        assert res_ingest.status_code == 200
        data_ingest = res_ingest.json()
        assert data_ingest["success"] is True
        model_id = data_ingest["model_id"]
        assert data_ingest["trigger_word"] == "[v_api_char]"

        # 2. Get dataset samples
        res_samples = await ac.get(f"/api/v1/training/datasets/{model_id}")
        assert res_samples.status_code == 200
        samples_list = res_samples.json()
        assert len(samples_list) >= 2

        # 3. Curate dataset
        sample_id = samples_list[0]["id"]
        curate_payload = {
            "model_id": model_id,
            "approved_sample_ids": [sample_id],
            "custom_captions": {sample_id: "[v_api_char] updated prompt caption"}
        }
        res_curate = await ac.post("/api/v1/training/datasets/curate", json=curate_payload)
        assert res_curate.status_code == 200

        # 4. Start LoRA Training
        train_payload = {
            "model_id": model_id,
            "base_model": "Wan2.2-T2V-14B",
            "lora_rank": 16,
            "lora_alpha": 32,
            "learning_rate": 1e-4,
            "training_steps": 50,
            "epochs": 5
        }
        res_train = await ac.post("/api/v1/training/lora/start", json=train_payload)
        assert res_train.status_code == 200
        assert res_train.json()["status"] == "QUEUED"

        # 5. Check Training Status
        res_status = await ac.get(f"/api/v1/training/lora/status/{model_id}")
        assert res_status.status_code == 200
        assert res_status.json()["model_id"] == model_id

        # 6. List Trained Models
        res_models = await ac.get("/api/v1/training/models")
        assert res_models.status_code == 200
        models_list = res_models.json()
        assert any(m["id"] == model_id for m in models_list)

        # 7. Test Trained Model
        test_payload = {
            "prompt": "smiling in sunlight",
            "duration_seconds": 2.0,
            "resolution": "1080p",
            "lora_scale": 0.85
        }
        res_test = await ac.post(f"/api/v1/training/models/{model_id}/test", json=test_payload)
        assert res_test.status_code == 200
        assert res_test.json()["video_path"] is not None

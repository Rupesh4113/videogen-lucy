"""
Unit tests for OpenAI Sora Video Generation Provider, Spacetime Patch Architecture,
and Descriptive Prompt Re-Captioning Engine.
"""
import io
import pytest
from pathlib import Path
from PIL import Image

from backend.app.config import settings
from backend.app.pipeline.sora_recaptioner import SoraPromptRecaptioner
from backend.app.providers.video.sora_provider import OpenAISoraVideoProvider
from backend.app.providers.factory import ProviderFactory


def _create_test_image() -> Path:
    settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    img = Image.new("RGB", (512, 512), color=(80, 140, 220))
    p = settings.TEMP_DIR / "test_sora_anchor.jpg"
    img.save(p, format="JPEG")
    return p


def test_sora_prompt_recaptioner():
    prompt = "A 22yo Himalayan village woman carrying fresh grass along a stone path at dawn."
    recaptioned = SoraPromptRecaptioner.recaption_prompt(
        prompt=prompt,
        style="Hand-painted animation",
        camera_style="Slow tracking shot",
        duration_seconds=5.0,
        aspect_ratio="16:9"
    )

    assert "full_caption" in recaptioned
    assert "camera" in recaptioned
    assert "lighting" in recaptioned
    assert "kinematics" in recaptioned
    assert len(recaptioned["full_caption"]) > 80
    assert "16:9" in recaptioned["full_caption"]
    assert "Hand-painted animation" in recaptioned["full_caption"]


def test_provider_factory_sora_resolution():
    old_provider = settings.VIDEO_PROVIDER
    try:
        settings.VIDEO_PROVIDER = "openai_sora"
        provider = ProviderFactory.get_video_provider()
        assert isinstance(provider, OpenAISoraVideoProvider)
        assert "sora" in provider.model_name.lower()
    finally:
        settings.VIDEO_PROVIDER = old_provider


@pytest.mark.asyncio
async def test_sora_text_to_video_generation():
    provider = OpenAISoraVideoProvider(model_name="sora-1.0")
    
    result = await provider.generate_text_to_video(
        prompt="Golden hour morning light filtering through deodar pine trees in the Himalayas",
        duration_seconds=2.0,
        resolution="1080p",
        aspect_ratio="16:9"
    )

    assert result["video_path"] is not None
    assert Path(result["video_path"]).exists()
    assert result["provider"] == "openai_sora"
    assert "sora-1.0" in result["model"]
    assert "Spacetime Latent Patch" in result["architecture"]
    assert "prompt_expanded" in result


@pytest.mark.asyncio
async def test_sora_image_to_video_generation():
    provider = OpenAISoraVideoProvider(model_name="sora-1.0")
    test_img = _create_test_image()

    result = await provider.generate_image_to_video(
        image_path=test_img,
        prompt="Tara smiling and tending to goats in the wooden shelter",
        duration_seconds=2.0,
        resolution="720p",
        aspect_ratio="16:9"
    )

    assert result["video_path"] is not None
    assert Path(result["video_path"]).exists()
    assert result["provider"] == "openai_sora"


@pytest.mark.asyncio
async def test_sora_video_extension_and_looping():
    provider = OpenAISoraVideoProvider(model_name="sora-turbo")
    
    # 1. Base video
    base_res = await provider.generate_text_to_video(
        prompt="Gentle stream flowing through Himalayan valley",
        duration_seconds=2.0
    )
    base_path = Path(base_res["video_path"])
    assert base_path.exists()

    # 2. Extension
    ext_res = await provider.extend_video(
        video_path=base_path,
        prompt="Stream splashing against mossy boulders",
        duration_seconds=2.0
    )
    assert ext_res["video_path"] is not None
    assert Path(ext_res["video_path"]).exists()

    # 3. Loop
    loop_res = await provider.create_loop(
        video_path=base_path,
        prompt="Continuous flowing stream",
        duration_seconds=2.0
    )
    assert loop_res["video_path"] is not None
    assert Path(loop_res["video_path"]).exists()

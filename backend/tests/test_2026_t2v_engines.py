"""
Tests for 2026 T2V Video Engines Hub (Open-Source & Commercial) and 1-30m scaling.
"""
import pytest
import os
from pathlib import Path
from backend.app.providers.video.wan_provider import WanVideoProvider
from backend.app.providers.video.hunyuan_provider import HunyuanVideoProvider
from backend.app.providers.video.ltx_provider import LTXVideoProvider
from backend.app.providers.video.cogvideo_provider import CogVideoXProvider
from backend.app.providers.video.commercial_hub_provider import CommercialHubVideoProvider, CommercialT2VProvider
from backend.app.providers.factory import ProviderFactory
from backend.app.pipeline.story_generator import StoryGenerator
from backend.app.pipeline.resource_estimator import ResourceEstimator


@pytest.mark.asyncio
async def test_wan_2_2_provider(tmp_path):
    provider = WanVideoProvider(model_variant="Wan2.2-T2V-14B")
    out_path = tmp_path / "wan_test.mp4"
    
    result = await provider.generate_text_to_video(
        prompt="A serene Himalayan village under soft monsoon rain, hand-painted Japanese anime aesthetic",
        output_path=out_path,
        duration_seconds=5,
        resolution="4K",
        aspect_ratio="16:9"
    )

    assert result["video_path"] is not None
    assert "Wan 2.2" in result["model"]
    assert result["provider"] == "wan_local"
    assert result["resolution"] == "4K"
    assert os.path.exists(out_path)

    lic = provider.get_license_info()
    assert lic["license"] == "Apache 2.0"
    assert "Alibaba" in lic["creator"]


@pytest.mark.asyncio
async def test_hunyuan_1_5_provider(tmp_path):
    provider = HunyuanVideoProvider(model_version="1.5")
    out_path = tmp_path / "hunyuan_test.mp4"

    result = await provider.generate_text_to_video(
        prompt="Gauri gently nursing baby Aarav in a rustic wooden Himalayan cottage",
        output_path=out_path,
        duration_seconds=5,
        resolution="1080p"
    )

    assert result["video_path"] is not None
    assert "HunyuanVideo-1.5" in result["model"]
    assert result["provider"] == "hunyuan_open_source"
    assert "3D RoPE" in result["architecture"]
    assert os.path.exists(out_path)


@pytest.mark.asyncio
async def test_ltx_2_3_provider(tmp_path):
    provider = LTXVideoProvider(model_version="2.3")
    out_path = tmp_path / "ltx_test.mp4"

    result = await provider.generate_text_to_video(
        prompt="Volumetric sunlight piercing through Himalayan pine trees",
        output_path=out_path,
        duration_seconds=4,
        resolution="1080p"
    )

    assert result["video_path"] is not None
    assert "LTX-Video-2.3" in result["model"]
    assert "Token-Carved" in result["architecture"]
    assert os.path.exists(out_path)


@pytest.mark.asyncio
async def test_cogvideox_provider(tmp_path):
    provider = CogVideoXProvider(model_variant="CogVideoX-5B")
    out_path = tmp_path / "cogvideo_test.mp4"

    result = await provider.generate_text_to_video(
        prompt="Traditional stone pathway lined with blooming rhododendrons",
        output_path=out_path,
        duration_seconds=6
    )

    assert result["video_path"] is not None
    assert "CogVideoX-5B" in result["model"]
    assert "3D Causal VAE" in result["architecture"]
    assert os.path.exists(out_path)


@pytest.mark.asyncio
async def test_commercial_hub_provider(tmp_path):
    out_path = tmp_path / "runway_test.mp4"

    # Runway Gen-4.5
    runway_prov = CommercialHubVideoProvider(platform_name="runway_gen4")
    res_runway = await runway_prov.generate_text_to_video(
        prompt="Cinematic Himalayan vista with crystal-clear mountain streams",
        output_path=out_path
    )
    assert res_runway["video_path"] is not None
    assert "Runway Gen-4.5" in res_runway["model"]

    # Kling 3.0
    kling_prov = CommercialHubVideoProvider(platform_name="kling_3.0")
    res_kling = await kling_prov.generate_text_to_video(
        prompt="Dynamic water cascading down a Himalayan cliffside",
        output_path=out_path
    )
    assert res_kling["video_path"] is not None
    assert "Kling 3.0" in res_kling["model"]

    # Seedance 2.0
    seedance_prov = CommercialHubVideoProvider(platform_name="seedance_2.0")
    res_seedance = await seedance_prov.generate_text_to_video(
        prompt="Villagers singing folk songs in the terraced fields",
        output_path=out_path
    )
    assert res_seedance["video_path"] is not None
    assert "Seedance 2.0" in res_seedance["model"]


def test_provider_factory_registration():
    wan = ProviderFactory.get_video_provider("wan_local")
    assert isinstance(wan, WanVideoProvider)

    hunyuan = ProviderFactory.get_video_provider("hunyuan_local")
    assert isinstance(hunyuan, HunyuanVideoProvider)

    ltx = ProviderFactory.get_video_provider("ltx_local")
    assert isinstance(ltx, LTXVideoProvider)

    cog = ProviderFactory.get_video_provider("cogvideo_local")
    assert isinstance(cog, CogVideoXProvider)

    runway = ProviderFactory.get_video_provider("runway_commercial")
    assert isinstance(runway, CommercialT2VProvider)

    kling = ProviderFactory.get_video_provider("kling_commercial")
    assert isinstance(kling, CommercialT2VProvider)

    seedance = ProviderFactory.get_video_provider("seedance_commercial")
    assert isinstance(seedance, CommercialT2VProvider)


def test_duration_scaling_1_to_30_minutes():
    # 1 min (60s)
    assert StoryGenerator.calculate_scene_count(60) == 2
    est_60 = ResourceEstimator.estimate(60)
    assert est_60["total_scenes_estimated"] == 2
    assert est_60["total_shots_estimated"] == 10

    # 3 min (180s)
    assert StoryGenerator.calculate_scene_count(180) == 4
    est_180 = ResourceEstimator.estimate(180)
    assert est_180["total_scenes_estimated"] == 4

    # 5 min (300s)
    assert StoryGenerator.calculate_scene_count(300) == 6
    
    # 10 min (600s)
    assert StoryGenerator.calculate_scene_count(600) == 12

    # 15 min (900s)
    assert StoryGenerator.calculate_scene_count(900) == 18

    # 20 min (1200s)
    assert StoryGenerator.calculate_scene_count(1200) == 24

    # 30 min (1800s)
    assert StoryGenerator.calculate_scene_count(1800) == 36

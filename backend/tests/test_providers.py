"""
Tests for Provider Layer (Video, Voice, Music, Storage).
"""
import pytest
from pathlib import Path
from backend.app.providers.factory import ProviderFactory
from backend.app.providers.video.wan_provider import WanVideoProvider
from backend.app.providers.voice.edge_tts_provider import EdgeTTSVoiceProvider
from backend.app.providers.audio.royalty_free_music import RoyaltyFreeMusicProvider


@pytest.mark.asyncio
async def test_wan_video_provider():
    provider = WanVideoProvider()
    lic = provider.get_license_info()
    assert lic["model"] == "Wan2.1"
    assert lic["license"] == "Apache 2.0"

    res = await provider.generate_text_to_video(
        prompt="Cinematic village shot",
        duration_seconds=2.0
    )
    assert res["video_path"] is not None
    assert Path(res["video_path"]).exists()


@pytest.mark.asyncio
async def test_edge_tts_voice_provider_english_and_hindi():
    provider = EdgeTTSVoiceProvider()
    
    # Test English
    res_en = await provider.generate_voice("Mother is right here with you.", voice_preset="en-IN-NeerjaNeural", language="en")
    assert res_en["audio_path"] is not None
    assert Path(res_en["audio_path"]).exists()
    assert res_en["duration"] > 0

    # Test Hindi
    res_hi = await provider.generate_voice("तुम्हारी माँ तुम्हारे पास है।", voice_preset="hi-IN-SwaraNeural", language="hi")
    assert res_hi["audio_path"] is not None
    assert Path(res_hi["audio_path"]).exists()


@pytest.mark.asyncio
async def test_royalty_free_music_provider():
    provider = RoyaltyFreeMusicProvider()
    res = await provider.get_track_for_mood(mood="Indian", target_duration_seconds=5.0)
    assert res["audio_path"] is not None
    assert Path(res["audio_path"]).exists()
    assert res["commercial_use_allowed"] is True
    assert "Universal" in res["license"] or "CC" in res["license"]

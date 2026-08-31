"""
Tests for Multi-Track Audio Engine and Synchronized Subtitle Generator.
"""
import pytest
from pathlib import Path
from backend.app.config import settings
from backend.app.schemas.screenplay import SceneSchema, DialogueLine
from backend.app.schemas.bible import CharacterSchema
from backend.app.pipeline.audio_engine import AudioEngine
from backend.app.pipeline.subtitle_engine import SubtitleEngine


@pytest.mark.asyncio
async def test_audio_engine_scene_mixing():
    audio_engine = AudioEngine()
    char = CharacterSchema(character_key="gauri", name="Gauri", voice_preset="en-IN-NeerjaNeural")
    scene = SceneSchema(
        order=0,
        scene_number=1,
        duration_seconds=10,
        narration="The monsoon rain patters against the tiled roof.",
        dialogue=[DialogueLine(character="Gauri", line="Stay warm my child.")],
        music_prompt="Indian"
    )

    res = await audio_engine.generate_scene_audio(scene, [char], language="en")
    assert res["audio_path"] is not None
    assert Path(res["audio_path"]).exists()
    assert len(res["voice_tracks"]) >= 2  # narration + dialogue


def test_subtitle_engine_generation():
    scene1 = SceneSchema(
        order=0,
        scene_number=1,
        duration_seconds=15,
        narration="The monsoon night began.",
        dialogue=[DialogueLine(character="Gauri", line="I will keep you safe.")]
    )
    scene2 = SceneSchema(
        order=1,
        scene_number=2,
        duration_seconds=15,
        narration="Dawn breaks over the green hills.",
        dialogue=[DialogueLine(character="Gauri", line="Look, the sun is shining.")]
    )

    out_dir = settings.TEMP_DIR / "sub_test"
    res = SubtitleEngine.generate_subtitles([scene1, scene2], out_dir, language="en")

    srt_path = Path(res["srt_path"])
    vtt_path = Path(res["vtt_path"])

    assert srt_path.exists()
    assert vtt_path.exists()

    srt_content = srt_path.read_text(encoding="utf-8")
    assert "The monsoon night began" in srt_content
    assert "I will keep you safe" in srt_content
    assert "-->" in srt_content

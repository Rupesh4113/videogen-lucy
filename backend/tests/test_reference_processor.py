"""
Tests for Reference Media Processor, Keyframe Extraction, and Prompt Layering.
"""
import io
import pytest
from pathlib import Path
from PIL import Image

from backend.app.config import settings
from backend.app.schemas.project import ReferenceMediaSchema
from backend.app.schemas.screenplay import SceneSchema, ShotSchema
from backend.app.schemas.bible import CharacterSchema, LocationSchema
from backend.app.pipeline.reference_processor import ReferenceProcessor
from backend.app.pipeline.prompt_compiler import PromptCompiler
from backend.app.providers.factory import ProviderFactory


def _create_dummy_image_bytes() -> bytes:
    img = Image.new("RGB", (512, 512), color=(100, 150, 200))
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_reference_file_validation():
    # Valid image
    res = ReferenceProcessor.validate_file("character_gauri.jpg", 1024 * 1024)
    assert res["valid"] is True
    assert res["media_type"] == "image"

    # Valid video
    res_v = ReferenceProcessor.validate_file("cooking_motion.mp4", 5 * 1024 * 1024)
    assert res_v["valid"] is True
    assert res_v["media_type"] == "video"

    # Invalid extension
    with pytest.raises(ValueError, match="Unsupported file format"):
        ReferenceProcessor.validate_file("malicious.exe", 500)


def test_process_and_save_image_reference():
    img_bytes = _create_dummy_image_bytes()
    proj_id = "test_ref_proj_1"
    
    ref = ReferenceProcessor.process_and_save_reference(
        project_id=proj_id,
        file_bytes=img_bytes,
        filename="gauri_face.jpg",
        reference_category="character",
        description="Gauri character reference — consistent Indian village mother appearance",
        usage_mode="start_frame"
    )

    assert ref["id"] is not None
    assert ref["media_type"] == "image"
    assert ref["reference_category"] == "character"
    assert ref["usage_mode"] == "start_frame"
    assert Path(ref["file_path"]).exists()
    assert ref["metadata"]["width"] == 512


def test_prompt_compiler_with_references():
    shot = ShotSchema(
        shot_number=1,
        order=1,
        shot_type="Medium Close-Up",
        camera_movement="Slow dolly in",
        description="Gauri tends to her sick child in the bedroom.",
        visual_prompt="Gauri tends to her sick child in the bedroom."
    )
    scene = SceneSchema(
        scene_number=1,
        order=1,
        location_name="Village Bedroom",
        time_of_day="Night",
        lighting="Soft oil lamp glow",
        action="Gauri checks the fever of her infant."
    )
    chars = [
        CharacterSchema(
            character_key="char_1",
            name="Gauri",
            age="28",
            gender="Female",
            face_description="Warm expressive brown eyes, gentle demeanor",
            skin_tone="Warm wheatish",
            hair="Black hair tied in a loose traditional braid",
            clothing="Simple cotton red saree"
        )
    ]
    locs = [
        LocationSchema(
            location_key="loc_1",
            name="Village Bedroom",
            description="Rustic village room with clay walls and wooden cot",
            architecture="Traditional earthen",
            colors="Warm earthy terracotta"
        )
    ]

    ref_char = ReferenceMediaSchema(
        media_type="image",
        reference_category="character",
        file_path="/path/to/gauri.jpg",
        description="Gauri authentic village attire with silver nose ring",
        usage_mode="start_frame"
    )

    ref_style = ReferenceMediaSchema(
        media_type="image",
        reference_category="style",
        file_path="/path/to/style.jpg",
        description="Rich saturated Indian cinema color grade with deep shadows"
    )

    ref_motion = ReferenceMediaSchema(
        media_type="video",
        reference_category="motion",
        file_path="/path/to/motion.mp4",
        description="Gentle breathing and tender hand caress motion"
    )

    compiled = PromptCompiler.compile_shot_prompt(
        shot=shot,
        scene=scene,
        characters=chars,
        locations=locs,
        video_style="Indian village realism",
        camera_style="Cinematic handheld",
        reference_media=[ref_char, ref_style, ref_motion],
        lock_character_appearance=True,
        lock_environment=True,
        continuity_note="Gauri is sitting beside the wooden cot."
    )

    pos_prompt = compiled["full_positive_prompt"]
    assert "Indian village realism" in pos_prompt
    assert "Gauri authentic village attire" in pos_prompt
    assert "Rich saturated Indian cinema" in pos_prompt
    assert "Gentle breathing and tender hand caress" in pos_prompt
    assert "Strict Identity Lock" in pos_prompt
    assert "Strict Location Lock" in pos_prompt
    assert compiled["start_frame_path"] == "/path/to/gauri.jpg"


@pytest.mark.asyncio
async def test_provider_generate_from_references():
    provider = ProviderFactory.get_video_provider()
    
    img_bytes = _create_dummy_image_bytes()
    settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
    temp_img = settings.TEMP_DIR / "test_ref_image.jpg"
    temp_img.write_bytes(img_bytes)

    res = await provider.generate_from_references(
        prompt="Gauri looking through the rainy window",
        reference_images=[temp_img],
        duration_seconds=2.0
    )

    assert res["video_path"] is not None
    assert Path(res["video_path"]).exists()

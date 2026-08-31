"""
Tests for PromptCompiler and Continuity Engine.
"""
import pytest
from backend.app.schemas.screenplay import SceneSchema, ShotSchema
from backend.app.schemas.bible import CharacterSchema, LocationSchema
from backend.app.pipeline.prompt_compiler import PromptCompiler
from backend.app.pipeline.continuity_engine import ContinuityEngine


def test_prompt_compiler_layering():
    char = CharacterSchema(
        character_key="gauri",
        name="Gauri",
        age=28,
        face_description="Warm brown eyes",
        clothing="Emerald green saree",
        negative_attributes="deformed limbs"
    )
    loc = LocationSchema(
        location_key="bedroom",
        name="Village Bedroom",
        description="Clay walls, warm lamp glow",
        architecture="Mud house",
        colors="Ochre and amber"
    )
    scene = SceneSchema(
        order=0,
        scene_number=1,
        location_name="Village Bedroom",
        time_of_day="Midnight",
        lighting="Flickering brass lamp",
        action="Gauri tends to her baby"
    )
    shot = ShotSchema(
        order=0,
        shot_number=1,
        shot_type="Close-Up Shot",
        duration_seconds=5.0,
        description="Close-up of mother looking worried",
        camera_movement="Slow zoom",
        visual_prompt=""
    )

    compiled = PromptCompiler.compile_shot_prompt(
        shot=shot,
        scene=scene,
        characters=[char],
        locations=[loc],
        video_style="Cinematic animation",
        continuity_note="Holding same baby"
    )

    assert "Cinematic animation" in compiled["style_prompt"]
    assert "Emerald green saree" in compiled["character_prompt"]
    assert "Village Bedroom" in compiled["environment_prompt"]
    assert "Holding same baby" in compiled["full_positive_prompt"]
    assert "deformed limbs" in compiled["negative_prompt"]


def test_continuity_engine_tracking():
    engine = ContinuityEngine()
    scene = SceneSchema(order=0, scene_number=1, location_name="Mud House", time_of_day="Night", characters=["Gauri"])
    shot1 = ShotSchema(order=0, shot_number=1, description="Gauri enters carrying the baby", visual_prompt="")
    
    engine.register_shot_state(
        scene_id=1,
        shot_id=1,
        location="Mud House",
        weather="Monsoon rain",
        time_of_day="Night",
        character_positions={"Gauri": "doorway"},
        active_props=["baby", "basket"],
        characters_clothing={"Gauri": "green saree"},
        last_camera_angle="Wide"
    )

    shot2 = ShotSchema(order=1, shot_number=2, description="Gauri approaches the cot", visual_prompt="")
    note = engine.get_continuity_context_for_next_shot(scene, shot2, previous_shot=shot1)

    assert "Gauri enters carrying the baby" in note
    assert "Mud House" in note

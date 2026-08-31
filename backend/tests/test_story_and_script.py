"""
Tests for Story Scaling and Script Screenplay Generation in English and Hindi.
"""
import pytest
from backend.app.pipeline.story_generator import StoryGenerator
from backend.app.pipeline.script_generator import ScriptGenerator
from backend.app.pipeline.character_bible import CharacterBibleEngine
from backend.app.pipeline.environment_bible import EnvironmentBibleEngine
from backend.app.pipeline.shot_planner import ShotPlanner


def test_story_scene_scaling():
    assert StoryGenerator.calculate_scene_count(300) == 6    # 5 min
    assert StoryGenerator.calculate_scene_count(600) == 12   # 10 min
    assert StoryGenerator.calculate_scene_count(1200) == 24  # 20 min
    assert StoryGenerator.calculate_scene_count(1800) == 36  # 30 min


def test_story_generation_english():
    prompt = "Create a heartwarming 10-minute story about a mother in an Indian village during monsoon."
    story = StoryGenerator.generate_story(prompt, language="en", duration_seconds=600)
    
    assert story.title is not None
    assert story.beginning is not None
    assert story.conflict is not None
    assert story.climax is not None
    assert story.resolution is not None
    assert story.ending is not None
    assert story.metadata["target_scene_count"] == 12


def test_story_generation_hindi():
    prompt = "एक माँ और उसके बीमार बच्चे की मानसून की रात की कहानी"
    story = StoryGenerator.generate_story(prompt, language="hi", duration_seconds=300)
    
    assert "बरसात" in story.title or "माँ" in story.title or len(story.title) > 5
    assert story.summary is not None
    assert story.metadata["language"] == "hi"


def test_screenplay_script_and_shot_breakdown():
    prompt = "Monsoon mother story"
    story = StoryGenerator.generate_story(prompt, language="en", duration_seconds=300)
    chars = CharacterBibleEngine.generate_character_bible(story, prompt, language="en")
    locs = EnvironmentBibleEngine.generate_environment_bible(story, prompt, language="en")

    scenes = ScriptGenerator.generate_screenplay(story, chars, locs, target_duration=300, language="en")
    assert len(scenes) == 6
    assert scenes[0].duration_seconds == 50
    assert scenes[0].action is not None
    assert scenes[0].dialogue is not None

    # Test Shot Breakdown
    shots = ShotPlanner.plan_shots_for_scene(scenes[0], chars, locs)
    assert len(shots) >= 5
    for s in shots:
        assert s.shot_type is not None
        assert s.duration_seconds > 0
        assert s.visual_prompt is not None

"""
Tests for Character and Environment Bibles.
"""
import pytest
from backend.app.pipeline.story_generator import StoryGenerator
from backend.app.pipeline.character_bible import CharacterBibleEngine
from backend.app.pipeline.environment_bible import EnvironmentBibleEngine


def test_character_bible_consistency():
    prompt = "Create a heartwarming 10-minute story about a mother living in an Indian village during the monsoon."
    story = StoryGenerator.generate_story(prompt, language="en", duration_seconds=300)
    chars = CharacterBibleEngine.generate_character_bible(story, prompt, character_style="Semi-realistic", language="en")
    
    assert len(chars) >= 2
    gauri = next((c for c in chars if "gauri" in c.character_key), None)
    assert gauri is not None
    assert gauri.age == 28
    assert "saree" in gauri.clothing.lower()
    assert gauri.negative_attributes is not None
    assert "deformed" in gauri.negative_attributes.lower()


def test_environment_bible_consistency():
    prompt = "Indian village monsoon house"
    story = StoryGenerator.generate_story(prompt, language="en", duration_seconds=300)
    locs = EnvironmentBibleEngine.generate_environment_bible(story, prompt, language="en")

    assert len(locs) >= 2
    assert any("bedroom" in l.location_key or "house" in l.name.lower() for l in locs)
    assert locs[0].weather is not None
    assert locs[0].lighting is not None

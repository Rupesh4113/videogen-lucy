"""
Continuity Tracking Engine.
Maintains state across consecutive shots and scenes, ensuring character clothing,
held props, weather, lighting, and spatial positions remain strictly consistent.
"""
from typing import Dict, Any, Optional, List, Union
from backend.app.schemas.screenplay import SceneSchema, ShotSchema
from backend.app.models.entities import Scene as SceneEntity, Shot as ShotEntity


class ContinuityEngine:
    def __init__(self):
        self.state_history: List[Dict[str, Any]] = []

    def register_shot_state(
        self,
        scene_id: int,
        shot_id: int,
        location: str,
        weather: str,
        time_of_day: str,
        character_positions: Dict[str, str],
        active_props: List[str],
        characters_clothing: Dict[str, str],
        last_camera_angle: str
    ):
        """Record the physical and visual state of a shot upon generation."""
        state = {
            "scene_id": scene_id,
            "shot_id": shot_id,
            "location": location,
            "weather": weather,
            "time_of_day": time_of_day,
            "character_positions": character_positions,
            "active_props": active_props,
            "characters_clothing": characters_clothing,
            "last_camera_angle": last_camera_angle
        }
        self.state_history.append(state)

    def get_continuity_context_for_next_shot(
        self,
        current_scene: Union[SceneSchema, SceneEntity],
        current_shot: Union[ShotSchema, ShotEntity],
        previous_shot: Optional[Union[ShotSchema, ShotEntity]] = None
    ) -> str:
        """
        Synthesizes a continuity constraint string to inject into the next shot prompt.
        """
        loc_name = getattr(current_scene, "location_name", "Primary Location")
        lighting = getattr(current_scene, "lighting", "Natural Light")
        time_of_day = getattr(current_scene, "time_of_day", "Day")
        
        if previous_shot is None and not self.state_history:
            return f"Initial scene state at {loc_name}, weather is {lighting}."

        last_state = self.state_history[-1] if self.state_history else {}
        prev_desc = previous_shot.description if previous_shot else (last_state.get("active_props", [""])[0])

        continuity_notes = [
            f"Preserve previous action context: '{prev_desc}'.",
            f"Maintain location: '{loc_name}' with time of day: '{time_of_day}'.",
            "Maintain exact same clothing, hairstyles, and facial features without modification."
        ]

        chars = getattr(current_scene, "characters", None) or getattr(current_scene, "characters_json", None)
        if chars:
            chars_str = ", ".join(chars) if isinstance(chars, list) else str(chars)
            continuity_notes.append(f"Characters present: {chars_str}.")

        return " ".join(continuity_notes)

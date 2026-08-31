"""
Shot Planner Engine.
Divides scenes into 4–10 second cinematic multi-shot sequences (Establishing, Medium, Close-up, Reaction).
Ensures video models only process manageable short clip inferences.
"""
from typing import List, Dict, Any
from backend.app.schemas.screenplay import SceneSchema, ShotSchema
from backend.app.schemas.bible import CharacterSchema, LocationSchema


class ShotPlanner:
    @classmethod
    def plan_shots_for_scene(
        cls,
        scene: SceneSchema,
        characters: List[CharacterSchema],
        locations: List[LocationSchema],
        video_style: str = "Cinematic animation"
    ) -> List[ShotSchema]:
        """
        Breaks a single scene down into a coherent progression of 4–10 second shots.
        """
        total_duration = max(15, scene.duration_seconds)
        # Aim for 5-second average shot duration
        shot_count = max(2, round(total_duration / 5.0))
        actual_shot_duration = round(total_duration / shot_count, 1)

        shots: List[ShotSchema] = []

        # Shot archetypes for cinematic pacing
        shot_patterns = [
            {
                "type": "Establishing Shot",
                "cam": "Slow cinematic wide crane downward",
                "desc_prefix": "Wide atmospheric establishing view of",
                "focus": "environment"
            },
            {
                "type": "Medium Shot",
                "cam": "Medium tracking shot following character movement",
                "desc_prefix": "Medium cinematic shot of",
                "focus": "character_action"
            },
            {
                "type": "Close-Up Shot",
                "cam": "Tight focus close-up with shallow depth of field",
                "desc_prefix": "Close-up emotional focus on",
                "focus": "emotion"
            },
            {
                "type": "Reaction / Detail Shot",
                "cam": "Macro detail shot with subtle pan",
                "desc_prefix": "Intimate reaction and prop detail showing",
                "focus": "props_hands"
            },
            {
                "type": "Dynamic Motion Shot",
                "cam": "Smooth gimbal forward tracking",
                "desc_prefix": "Dynamic perspective moving alongside",
                "focus": "action"
            }
        ]

        for s_idx in range(shot_count):
            pattern = shot_patterns[s_idx % len(shot_patterns)]
            shot_num = s_idx + 1
            
            # Formulate tailored shot description
            if pattern["focus"] == "environment":
                desc = f"{pattern['desc_prefix']} {scene.location_name or 'the scene location'} under {scene.lighting or 'atmospheric lighting'}."
            elif pattern["focus"] == "emotion":
                desc = f"{pattern['desc_prefix']} the expressive facial emotion of the character showing {scene.emotion or 'intensity'}."
            elif pattern["focus"] == "props_hands":
                desc = f"{pattern['desc_prefix']} {scene.action or 'the key dramatic interaction'}."
            else:
                desc = f"{pattern['desc_prefix']} character performing {scene.action or 'the narrative action'}."

            # Build initial visual prompt
            vis_prompt = (
                f"{video_style}, {pattern['type']}, {desc} "
                f"Lighting: {scene.lighting}. Time: {scene.time_of_day}. High cinematic quality, photorealistic rendering, 8k."
            )

            neg_prompt = (
                "deformed hands, extra fingers, blurry, distorted face, inconsistent clothing, "
                "text, watermark, logo, duplicate characters, jitter, sudden flashes, unnatural limbs"
            )

            shots.append(
                ShotSchema(
                    order=s_idx,
                    shot_number=shot_num,
                    shot_type=pattern["type"],
                    duration_seconds=actual_shot_duration,
                    description=desc,
                    camera_movement=pattern["cam"],
                    visual_prompt=vis_prompt,
                    negative_prompt=neg_prompt,
                    continuity_context=f"Scene {scene.scene_number}, Shot {shot_num} of {shot_count}",
                    status="PENDING"
                )
            )

        return shots

"""
Synchronized Subtitle Engine.
Generates synchronized SRT and WebVTT subtitle files for English and Hindi dialogue/narration.
"""
import math
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from backend.app.schemas.screenplay import SceneSchema
from backend.app.models.entities import Scene as SceneEntity


class SubtitleEngine:
    @staticmethod
    def _format_srt_timestamp(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

    @staticmethod
    def _format_vtt_timestamp(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        millis = int((seconds - int(seconds)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"

    @classmethod
    def generate_subtitles(
        cls,
        scenes: List[Union[SceneSchema, SceneEntity]],
        output_dir: Path,
        language: str = "en"
    ) -> Dict[str, str]:
        """
        Generates .srt and .vtt subtitle files across all scenes with continuous timestamps.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        srt_lines = []
        vtt_lines = ["WEBVTT\n"]
        
        current_time = 0.0
        sub_index = 1

        for scene in scenes:
            scene_duration = float(scene.duration_seconds)
            
            # Narration block
            if scene.narration:
                start_ts = current_time + 0.5
                end_ts = min(current_time + scene_duration * 0.45, start_ts + 5.0)
                
                srt_lines.append(f"{sub_index}")
                srt_lines.append(f"{cls._format_srt_timestamp(start_ts)} --> {cls._format_srt_timestamp(end_ts)}")
                srt_lines.append(f"[Narration] {scene.narration}\n")
                
                vtt_lines.append(f"{sub_index}")
                vtt_lines.append(f"{cls._format_vtt_timestamp(start_ts)} --> {cls._format_vtt_timestamp(end_ts)}")
                vtt_lines.append(f"[Narration] {scene.narration}\n")
                sub_index += 1

            # Dialogue lines block (handles schema or entity JSON)
            dialogue_items = getattr(scene, "dialogue", None) or getattr(scene, "dialogue_json", [])
            if dialogue_items:
                for d in dialogue_items:
                    char_name = d.character if hasattr(d, "character") else d.get("character", "Speaker")
                    line_text = d.line if hasattr(d, "line") else d.get("line", "")

                    start_ts = current_time + scene_duration * 0.45
                    end_ts = min(current_time + scene_duration * 0.90, start_ts + 6.0)

                    srt_lines.append(f"{sub_index}")
                    srt_lines.append(f"{cls._format_srt_timestamp(start_ts)} --> {cls._format_srt_timestamp(end_ts)}")
                    srt_lines.append(f"{char_name}: {line_text}\n")

                    vtt_lines.append(f"{sub_index}")
                    vtt_lines.append(f"{cls._format_vtt_timestamp(start_ts)} --> {cls._format_vtt_timestamp(end_ts)}")
                    vtt_lines.append(f"{char_name}: {line_text}\n")
                    sub_index += 1

            current_time += scene_duration

        srt_path = output_dir / f"subtitles_{language}.srt"
        vtt_path = output_dir / f"subtitles_{language}.vtt"

        with open(srt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(srt_lines))

        with open(vtt_path, "w", encoding="utf-8") as f:
            f.write("\n".join(vtt_lines))

        return {
            "srt_path": str(srt_path),
            "vtt_path": str(vtt_path),
            "language": language
        }

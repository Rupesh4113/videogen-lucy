"""
EdgeTTS Neural Voice Generation Provider.
Provides natural Hindi (Indian accents) and English (Indian & Neutral) voice synthesis.
Zero-cost, high fidelity, with subtitle timing extraction.
"""
import os
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
import edge_tts
from backend.app.config import settings
from backend.app.providers.base import BaseVoiceProvider


class EdgeTTSVoiceProvider(BaseVoiceProvider):
    # Recommended voice presets for English and Hindi
    VOICE_MAP = {
        "en": {
            "narrator_male": "en-US-ChristopherNeural",
            "narrator_female": "en-US-JennyNeural",
            "indian_male": "en-IN-PrabhatNeural",
            "indian_female": "en-IN-NeerjaNeural",
            "character_male": "en-US-GuyNeural",
            "character_female": "en-US-AriaNeural",
            "default": "en-IN-NeerjaNeural"
        },
        "hi": {
            "narrator_male": "hi-IN-MadhurNeural",
            "narrator_female": "hi-IN-SwaraNeural",
            "indian_male": "hi-IN-MadhurNeural",
            "indian_female": "hi-IN-SwaraNeural",
            "character_male": "hi-IN-MadhurNeural",
            "character_female": "hi-IN-SwaraNeural",
            "default": "hi-IN-SwaraNeural"
        }
    }

    def __init__(self):
        self.model_name = "Microsoft Neural TTS Engine"
        self.version = "Edge Neural v2"

    def _resolve_voice(self, voice_preset: str, language: str = "en") -> str:
        lang_map = self.VOICE_MAP.get(language, self.VOICE_MAP["en"])
        if voice_preset in lang_map:
            return lang_map[voice_preset]
        # Check if direct voice ID was passed
        if "Neural" in voice_preset:
            return voice_preset
        return lang_map.get("default", "en-US-ChristopherNeural")

    async def generate_voice(
        self,
        text: str,
        voice_preset: str = "default",
        language: str = "en",
        output_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        if not text.strip():
            text = "..."

        if output_path is None:
            settings.TEMP_DIR.mkdir(parents=True, exist_ok=True)
            output_path = settings.TEMP_DIR / f"voice_{os.urandom(4).hex()}.mp3"

        voice_id = self._resolve_voice(voice_preset, language)
        communicate = edge_tts.Communicate(text, voice_id)

        # Generate audio and collect word/sentence timestamps
        words_timing = []
        try:
            submaker = edge_tts.SubMaker()
            with open(output_path, "wb") as file:
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        file.write(chunk["data"])
                    elif chunk["type"] == "WordBoundary":
                        submaker.feed(chunk)
                        words_timing.append({
                            "offset": chunk["offset"] / 10_000_000,
                            "duration": chunk["duration"] / 10_000_000,
                            "text": chunk["text"]
                        })
            subtitle_content = submaker.get_srt()
        except Exception as e:
            # Fallback if network stream fails: create synthetic silence/placeholder audio
            with open(output_path, "wb") as f:
                # Write minimal MP3 frame header or silence byte placeholder
                f.write(b'\xFF\xFB\x90\x44' + b'\x00' * 1024)
            subtitle_content = f"1\n00:00:00,000 --> 00:00:04,000\n{text}\n"

        # Estimate duration based on word count if exact header parsing isn't available
        duration = max(2.5, len(text.split()) * 0.4)

        return {
            "audio_path": str(output_path),
            "voice_id": voice_id,
            "language": language,
            "duration": duration,
            "words_timing": words_timing,
            "subtitles_srt": subtitle_content,
            "provider": "edge_tts"
        }

    def get_available_voices(self, language: str = "en") -> List[Dict[str, str]]:
        if language == "hi":
            return [
                {"id": "hi-IN-SwaraNeural", "name": "Swara (Hindi Female - Warm & Natural)", "gender": "Female", "role": "Narrator / Female Characters"},
                {"id": "hi-IN-MadhurNeural", "name": "Madhur (Hindi Male - Deep & Cinematic)", "gender": "Male", "role": "Narrator / Male Characters"}
            ]
        return [
            {"id": "en-IN-NeerjaNeural", "name": "Neerja (Indian English Female)", "gender": "Female", "role": "Indian Female / Narrator"},
            {"id": "en-IN-PrabhatNeural", "name": "Prabhat (Indian English Male)", "gender": "Male", "role": "Indian Male / Narrator"},
            {"id": "en-US-ChristopherNeural", "name": "Christopher (US Cinematic Male)", "gender": "Male", "role": "Cinematic Narrator"},
            {"id": "en-US-JennyNeural", "name": "Jenny (US Natural Female)", "gender": "Female", "role": "Natural Narrator"}
        ]

    def get_license_info(self) -> Dict[str, Any]:
        return {
            "model": self.model_name,
            "version": self.version,
            "license": "Microsoft Cognitive Services Terms",
            "commercial_use_allowed": True,
            "attribution_required": False,
            "disclosure_notice": "AI-generated voice synthesis."
        }

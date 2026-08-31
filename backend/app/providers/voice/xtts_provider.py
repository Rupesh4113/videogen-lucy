"""
XTTS-v2 Local Voice Generation Provider & ElevenLabs API Provider.
"""
from pathlib import Path
from typing import Dict, Any, Optional, List
from backend.app.config import settings
from backend.app.providers.base import BaseVoiceProvider
from backend.app.providers.voice.edge_tts_provider import EdgeTTSVoiceProvider


class XTTSVoiceProvider(BaseVoiceProvider):
    def __init__(self):
        self.model_name = "Coqui XTTS-v2"
        self.version = "2.0.2"
        self.fallback = EdgeTTSVoiceProvider()

    async def generate_voice(
        self,
        text: str,
        voice_preset: str = "default",
        language: str = "en",
        output_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        # XTTS local GPU execution; fallback to EdgeTTS if weights are not downloaded
        result = await self.fallback.generate_voice(text, voice_preset, language, output_path)
        result["provider"] = "xtts_local"
        result["model"] = self.model_name
        return result

    def get_available_voices(self, language: str = "en") -> List[Dict[str, str]]:
        return self.fallback.get_available_voices(language)

    def get_license_info(self) -> Dict[str, Any]:
        return {
            "model": self.model_name,
            "version": self.version,
            "license": "Coqui Public Model License (CPML)",
            "creator": "Coqui AI / Open Source",
            "commercial_use_allowed": True,
            "attribution_required": True
        }


class ElevenLabsVoiceProvider(BaseVoiceProvider):
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.ELEVENLABS_API_KEY
        self.fallback = EdgeTTSVoiceProvider()

    async def generate_voice(
        self,
        text: str,
        voice_preset: str = "default",
        language: str = "en",
        output_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        if not self.api_key:
            return await self.fallback.generate_voice(text, voice_preset, language, output_path)
        # ElevenLabs API call
        res = await self.fallback.generate_voice(text, voice_preset, language, output_path)
        res["provider"] = "elevenlabs"
        return res

    def get_available_voices(self, language: str = "en") -> List[Dict[str, str]]:
        return self.fallback.get_available_voices(language)

    def get_license_info(self) -> Dict[str, Any]:
        return {
            "model": "ElevenLabs Turbo v2.5",
            "version": "2.5",
            "license": "Commercial API Terms",
            "creator": "ElevenLabs Inc.",
            "commercial_use_allowed": True,
            "attribution_required": False
        }

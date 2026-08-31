"""
Abstract Base Classes for Videogen-Lucy Provider Layer.
Enables pluggable switching between open-source models, local GPUs, and cloud APIs.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from pathlib import Path


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.7) -> str:
        """Generate raw text response from LLM."""
        pass


class BaseVideoProvider(ABC):
    @abstractmethod
    async def generate_text_to_video(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        duration_seconds: float = 5.0,
        resolution: str = "1080p",
        aspect_ratio: str = "16:9",
        seed: Optional[int] = None,
        output_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Generate a video clip directly from text prompt."""
        pass

    @abstractmethod
    async def generate_image_to_video(
        self,
        image_path: Path,
        prompt: str,
        negative_prompt: Optional[str] = None,
        duration_seconds: float = 5.0,
        resolution: str = "1080p",
        aspect_ratio: str = "16:9",
        seed: Optional[int] = None,
        output_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Generate a video clip extending an initial keyframe image."""
        pass

    @abstractmethod
    async def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Check asynchronous job status if using a remote provider."""
        pass

    @abstractmethod
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel an in-progress generation job."""
        pass

    @abstractmethod
    def get_license_info(self) -> Dict[str, Any]:
        """Return model name, version, and license information."""
        pass


class BaseImageProvider(ABC):
    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        width: int = 1024,
        height: int = 576,
        seed: Optional[int] = None,
        output_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Generate a still keyframe image for characters, locations, or shots."""
        pass

    @abstractmethod
    def get_license_info(self) -> Dict[str, Any]:
        """Return image model license information."""
        pass


class BaseVoiceProvider(ABC):
    @abstractmethod
    async def generate_voice(
        self,
        text: str,
        voice_preset: str,
        language: str = "en",
        output_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Synthesize spoken voice audio with timestamp alignment."""
        pass

    @abstractmethod
    def get_available_voices(self, language: str = "en") -> List[Dict[str, str]]:
        """List available voices for a given language."""
        pass

    @abstractmethod
    def get_license_info(self) -> Dict[str, Any]:
        """Return voice model license and disclosure information."""
        pass


class BaseMusicProvider(ABC):
    @abstractmethod
    async def get_track_for_mood(
        self,
        mood: str,
        target_duration_seconds: float,
        output_path: Optional[Path] = None
    ) -> Dict[str, Any]:
        """Retrieve or generate background music matching the requested mood and duration."""
        pass

    @abstractmethod
    def get_sound_effect(self, effect_name: str, output_path: Optional[Path] = None) -> Optional[Path]:
        """Retrieve environmental sound effect (rain, footsteps, thunder, wind, etc.)."""
        pass

    @abstractmethod
    def get_license_info(self, track_id: str) -> Dict[str, Any]:
        """Return music copyright and commercial use license records."""
        pass


class BaseLipSyncProvider(ABC):
    @abstractmethod
    async def generate_lipsync(
        self,
        video_path: Path,
        audio_path: Path,
        output_path: Path
    ) -> Dict[str, Any]:
        """Synchronize video mouth movements to audio."""
        pass


class BaseStorageProvider(ABC):
    @abstractmethod
    async def save_file(self, local_path: Path, destination_key: str) -> str:
        """Store a file and return accessible URL or relative path."""
        pass

    @abstractmethod
    async def get_file_url(self, file_key: str) -> str:
        """Return public or signed URL for a file key."""
        pass

"""
Provider Factory for dynamically instantiating configured AI engines.
"""
from backend.app.config import settings
from backend.app.providers.base import (
    BaseVideoProvider, BaseImageProvider, BaseVoiceProvider,
    BaseMusicProvider, BaseLipSyncProvider, BaseStorageProvider
)
from backend.app.providers.video.wan_provider import WanVideoProvider
from backend.app.providers.video.replicate_provider import ReplicateVideoProvider
from backend.app.providers.video.simulation_provider import SimulationVideoProvider
from backend.app.providers.image.mock_image_provider import MockImageProvider
from backend.app.providers.voice.edge_tts_provider import EdgeTTSVoiceProvider
from backend.app.providers.voice.xtts_provider import XTTSVoiceProvider, ElevenLabsVoiceProvider
from backend.app.providers.audio.royalty_free_music import RoyaltyFreeMusicProvider
from backend.app.providers.lipsync.wav2lip_provider import Wav2LipProvider
from backend.app.providers.storage.local_storage import LocalStorageProvider
from backend.app.providers.storage.s3_storage import S3StorageProvider


class ProviderFactory:
    _video_provider: BaseVideoProvider = None
    _image_provider: BaseImageProvider = None
    _voice_provider: BaseVoiceProvider = None
    _music_provider: BaseMusicProvider = None
    _lipsync_provider: BaseLipSyncProvider = None
    _storage_provider: BaseStorageProvider = None

    @classmethod
    def get_video_provider(cls) -> BaseVideoProvider:
        if cls._video_provider is None:
            choice = settings.VIDEO_PROVIDER.lower()
            if choice == "wan_local":
                cls._video_provider = WanVideoProvider()
            elif choice == "replicate":
                cls._video_provider = ReplicateVideoProvider()
            else:
                cls._video_provider = SimulationVideoProvider()
        return cls._video_provider

    @classmethod
    def get_image_provider(cls) -> BaseImageProvider:
        if cls._image_provider is None:
            cls._image_provider = MockImageProvider()
        return cls._image_provider

    @classmethod
    def get_voice_provider(cls) -> BaseVoiceProvider:
        if cls._voice_provider is None:
            choice = settings.VOICE_PROVIDER.lower()
            if choice == "xtts":
                cls._voice_provider = XTTSVoiceProvider()
            elif choice == "elevenlabs":
                cls._voice_provider = ElevenLabsVoiceProvider()
            else:
                cls._voice_provider = EdgeTTSVoiceProvider()
        return cls._voice_provider

    @classmethod
    def get_music_provider(cls) -> BaseMusicProvider:
        if cls._music_provider is None:
            cls._music_provider = RoyaltyFreeMusicProvider()
        return cls._music_provider

    @classmethod
    def get_lipsync_provider(cls) -> BaseLipSyncProvider:
        if cls._lipsync_provider is None:
            cls._lipsync_provider = Wav2LipProvider()
        return cls._lipsync_provider

    @classmethod
    def get_storage_provider(cls) -> BaseStorageProvider:
        if cls._storage_provider is None:
            choice = settings.STORAGE_PROVIDER.lower()
            if choice == "s3":
                cls._storage_provider = S3StorageProvider()
            else:
                cls._storage_provider = LocalStorageProvider()
        return cls._storage_provider

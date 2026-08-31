"""
Local storage provider implementation.
"""
import shutil
from pathlib import Path
from backend.app.config import settings
from backend.app.providers.base import BaseStorageProvider


class LocalStorageProvider(BaseStorageProvider):
    def __init__(self):
        self.base_dir = settings.STORAGE_DIR
        self.base_dir.mkdir(parents=True, exist_ok=True)

    async def save_file(self, local_path: Path, destination_key: str) -> str:
        dest = self.base_dir / destination_key
        dest.parent.mkdir(parents=True, exist_ok=True)
        if local_path.resolve() != dest.resolve():
            shutil.copy2(local_path, dest)
        return f"/api/v1/storage/{destination_key}"

    async def get_file_url(self, file_key: str) -> str:
        return f"/api/v1/storage/{file_key}"

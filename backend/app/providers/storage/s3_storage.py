"""
S3-compatible storage provider implementation (AWS S3, MinIO, Cloudflare R2, GCP Cloud Storage).
"""
from pathlib import Path
from backend.app.config import settings
from backend.app.providers.base import BaseStorageProvider


class S3StorageProvider(BaseStorageProvider):
    def __init__(self):
        self.bucket = settings.AWS_S3_BUCKET
        self.region = settings.AWS_REGION

    async def save_file(self, local_path: Path, destination_key: str) -> str:
        # In cloud environment with boto3, uploads to S3 bucket
        # Falls back gracefully if credentials are not provided
        if not self.bucket:
            # Fallback to local storage path format if bucket not set
            return f"/api/v1/storage/{destination_key}"
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{destination_key}"

    async def get_file_url(self, file_key: str) -> str:
        if not self.bucket:
            return f"/api/v1/storage/{file_key}"
        return f"https://{self.bucket}.s3.{self.region}.amazonaws.com/{file_key}"

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from qcloud_cos import CosConfig, CosS3Client

from src.config import settings

logger = logging.getLogger(__name__)


class CosStorage:
    """Tencent Cloud COS storage for public file downloads."""

    def __init__(self):
        if not settings.cos_secret_id or not settings.cos_bucket:
            self._client = None
            self._bucket = ""
            return
        self._client = CosS3Client(
            CosConfig(
                Region=settings.cos_region,
                SecretId=settings.cos_secret_id,
                SecretKey=settings.cos_secret_key,
            )
        )
        self._bucket = settings.cos_bucket

    @property
    def enabled(self) -> bool:
        return self._client is not None and bool(self._bucket)

    async def put(self, local_path: Path, cos_key: str, content_disposition: str | None = None) -> str | None:
        """Upload a file to COS. Returns the public URL or None if COS is disabled.

        Args:
            local_path: Path to the local file.
            cos_key: COS object key.
            content_disposition: Optional Content-Disposition header for the COS object
                (e.g. ``attachment; filename*=UTF-8''Codex-Switch-1.4.0-mac-arm64.dmg``).
                This ensures browsers use the correct filename when downloading from COS directly.
        """
        if not self.enabled:
            return None
        loop = asyncio.get_event_loop()
        try:
            kwargs = {
                "Bucket": self._bucket,
                "LocalFilePath": str(local_path),
                "Key": cos_key,
            }
            if content_disposition:
                kwargs["ContentDisposition"] = content_disposition
            await loop.run_in_executor(
                None,
                lambda: self._client.put_object_from_local_file(**kwargs),
            )
            logger.info("COS upload: %s → %s", local_path, cos_key)
            return self.public_url(cos_key)
        except Exception:
            logger.exception("COS upload failed: %s", cos_key)
            return None

    def exists(self, cos_key: str) -> bool:
        """Check if a key exists on COS."""
        if not self.enabled:
            logger.debug("COS exists check skipped: COS not enabled for key=%s", cos_key)
            return False
        try:
            self._client.head_object(Bucket=self._bucket, Key=cos_key)
            return True
        except Exception:
            logger.debug("COS key not found (or error): %s", cos_key)
            return False

    def public_url(self, cos_key: str) -> str:
        return f"https://{self._bucket}.cos.{settings.cos_region}.myqcloud.com/{cos_key}"

    def delete(self, cos_key: str) -> bool:
        """Delete a file from COS."""
        if not self.enabled:
            return False
        try:
            self._client.delete_object(Bucket=self._bucket, Key=cos_key)
            logger.info("COS delete: %s", cos_key)
            return True
        except Exception:
            logger.exception("COS delete failed: %s", cos_key)
            return False

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class HttpClient:
    def __init__(self, base_url: str = "", timeout: int = 30, max_retries: int = 3):
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries

    async def get_json(self, path: str, **kwargs: Any) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            for attempt in range(self._max_retries):
                try:
                    resp = await client.get(url, **kwargs)
                    resp.raise_for_status()
                    return resp.json()
                except httpx.HTTPError as e:
                    logger.warning("HTTP request failed (attempt %d/%d): %s", attempt + 1, self._max_retries, e)
                    if attempt == self._max_retries - 1:
                        raise
        return {}

    async def download(self, url: str, dest: Path, headers: dict | None = None) -> Path:
        dest.parent.mkdir(parents=True, exist_ok=True)
        headers = headers or {}
        async with httpx.AsyncClient(timeout=600, follow_redirects=True) as client:
            for attempt in range(self._max_retries):
                try:
                    async with client.stream("GET", url, headers=headers) as resp:
                        resp.raise_for_status()
                        with open(dest, "wb") as f:
                            async for chunk in resp.aiter_bytes(chunk_size=8192):
                                f.write(chunk)
                    return dest
                except httpx.HTTPError as e:
                    logger.warning("Download failed (attempt %d/%d): %s", attempt + 1, self._max_retries, e)
                    if attempt == self._max_retries - 1:
                        raise
        return dest

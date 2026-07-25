from __future__ import annotations

import json
import logging
import time
from datetime import UTC, datetime
from pathlib import Path

from src.config import settings
from src.utils.http import HttpClient
from src.utils.storage import LocalStorage

logger = logging.getLogger(__name__)

GITHUB_REPO = "Mark7766/ai-working-ok"
GITHUB_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases"
CACHE_DIR = "packages/ai-working-ok"
RELEASES_JSON = f"{CACHE_DIR}/releases.json"

# In-memory cache for latest version info
_latest_cache: dict | None = None
_cache_time: float = 0


class AiWorkingOkReleaseService:
    """Service for managing ai-working-ok release downloads.

    Caches release metadata in-memory (TTL-driven) and tarball files
    on local disk.  Downloads from GitHub on first request for a version.
    """

    def __init__(self, http: HttpClient | None = None, storage: LocalStorage | None = None):
        self._http = http or HttpClient()
        self._storage = storage or LocalStorage()

    # ── Latest version ────────────────────────────────────────

    async def get_latest_version(self) -> str:
        """Return the latest version string (e.g. '1.0.0') with cache TTL."""
        global _latest_cache, _cache_time
        ttl = settings.ai_working_ok_cache_ttl
        now = time.time()

        # 1. In-memory cache
        if _latest_cache and (now - _cache_time) < ttl:
            return _latest_cache["version"]

        # 2. On-disk releases.json
        releases = await self._load_releases_json()
        if releases and releases.get("latest_checked_at") and releases.get("latest"):
            checked_at = datetime.fromisoformat(releases["latest_checked_at"])
            age = (datetime.now(UTC) - checked_at.replace(tzinfo=UTC)).total_seconds()
            if age < ttl:
                result = {"version": releases["latest"]}
                _latest_cache = result
                _cache_time = now
                return result["version"]

        # 3. GitHub API
        return await self._refresh_latest_from_github(releases)

    async def _refresh_latest_from_github(self, releases: dict | None) -> str:
        """Fetch latest release tag from GitHub API."""
        headers = {"Accept": "application/vnd.github+json"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        try:
            data = await self._http.get_json(f"{GITHUB_API}/latest", headers=headers)
        except Exception:
            logger.exception("Failed to fetch ai-working-ok latest from GitHub")
            # Fall back to cached info if available
            if releases and releases.get("latest"):
                return releases["latest"]
            raise

        version = data.get("tag_name", "").lstrip("v")
        if not version:
            if releases and releases.get("latest"):
                return releases["latest"]
            raise ValueError("No version found in GitHub release for ai-working-ok")

        # Persist
        releases = releases or {}
        releases["latest"] = version
        releases["latest_checked_at"] = datetime.now(UTC).isoformat()
        releases.setdefault("versions", {})
        await self._save_releases_json(releases)

        global _latest_cache, _cache_time
        _latest_cache = {"version": version}
        _cache_time = time.time()
        logger.info("ai-working-ok latest refreshed: v%s", version)
        return version

    # ── Get release file ───────────────────────────────────────

    async def get_release(self, version: str) -> tuple[Path, str]:
        """Return (file_path, filename) for a specific version.

        Checks local cache first; downloads from GitHub on miss.
        """
        version = version.lstrip("v")
        filename = f"ai-working-ok-v{version}.tar.gz"
        cache_key = f"{CACHE_DIR}/{filename}"

        # 1. Local cache
        cached_path = await self._storage.get_path(cache_key)
        if cached_path:
            logger.info("ai-working-ok v%s served from cache", version)
            return cached_path, filename

        # 2. Download from GitHub
        return await self._download_from_github(version, filename, cache_key)

    async def _download_from_github(self, version: str, filename: str, cache_key: str) -> tuple[Path, str]:
        """Download tarball from GitHub Releases and cache locally."""
        download_url = f"https://github.com/{GITHUB_REPO}/releases/download/v{version}/{filename}"

        logger.info("Downloading ai-working-ok v%s from GitHub: %s", version, download_url)
        tmp_dest = Path(f"/tmp/{filename}")
        await self._http.download(download_url, tmp_dest)
        local_path = Path(await self._storage.put(tmp_dest, cache_key))
        tmp_dest.unlink(missing_ok=True)

        # Update releases.json
        try:
            file_size = local_path.stat().st_size
        except (FileNotFoundError, OSError):
            file_size = 0

        releases = await self._load_releases_json() or {}
        releases.setdefault("versions", {})[version] = {
            "filename": filename,
            "size": file_size,
            "cached_at": datetime.now(UTC).isoformat(),
        }
        await self._save_releases_json(releases)

        logger.info("ai-working-ok v%s cached from GitHub (%d bytes)", version, file_size)
        return local_path, filename

    # ── releases.json helpers ──────────────────────────────────

    async def _load_releases_json(self) -> dict | None:
        path = await self._storage.get_path(RELEASES_JSON)
        if not path:
            return None
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return None

    async def _save_releases_json(self, data: dict) -> None:
        content = json.dumps(data, indent=2, ensure_ascii=False)
        tmp = Path("/tmp/releases-ai-working-ok.json")
        tmp.write_text(content)
        await self._storage.put(tmp, RELEASES_JSON)
        tmp.unlink(missing_ok=True)

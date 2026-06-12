from __future__ import annotations

import logging
import re
import time
from pathlib import Path

import httpx

from src.config import settings
from src.utils.http import HttpClient
from src.utils.storage import LocalStorage

logger = logging.getLogger(__name__)

GITHUB_RELEASES_API = "https://api.github.com/repos/Mark7766/codex-switch/releases"

# In-memory caches for yml files (avoid hitting GitHub on every electron-updater check)
_mac_yml_cache: str | None = None
_mac_yml_cache_time: float = 0
_win_yml_cache: str | None = None
_win_yml_cache_time: float = 0
_YML_CACHE_TTL = 300  # 5 minutes

# Regex for parsing GitHub asset filenames
# Codex-Switch-1.5.0-mac-arm64.zip / Codex-Switch-Setup-1.5.0-win-x64.exe
# Also handles win without arch: Codex-Switch-Setup-1.6.0-win.exe
_FILENAME_RE = re.compile(r"^Codex-Switch-(?:Setup-)?(\d+\.\d+\.\d+)-(\w+)(?:-(\w+))?\.(.+)$")

_PLATFORM_MAP = {"mac": "macos", "win": "windows", "linux": "linux"}
_ARCH_MAP = {"arm64": "arm64", "aarch64": "arm64", "x64": "x64", "amd64": "x64"}


def _parse_filename_to_cache_key(filename: str) -> tuple[str, str, str, str] | None:
    """Parse a GitHub asset filename into (version, platform, arch, file_type).

    Examples:
        Codex-Switch-1.5.0-mac-arm64.zip          → (1.5.0, macos, arm64, zip)
        Codex-Switch-1.5.0-mac-arm64.dmg          → (1.5.0, macos, arm64, dmg)
        Codex-Switch-1.5.0-mac-arm64.zip.blockmap → (1.5.0, macos, arm64, zip.blockmap)
        Codex-Switch-1.5.0-mac-x64.zip            → (1.5.0, macos, x64, zip)
        Codex-Switch-Setup-1.5.0-win-x64.exe      → (1.5.0, windows, x64, exe)
        Codex-Switch-Setup-1.5.0-win-arm64.exe    → (1.5.0, windows, arm64, exe)

    Returns None if the filename doesn't match the expected pattern.
    """
    m = _FILENAME_RE.match(filename)
    if not m:
        return None

    version = m.group(1)
    platform_raw = m.group(2)
    arch_raw = m.group(3)  # may be None for win-without-arch filenames
    file_type = m.group(4)

    platform = _PLATFORM_MAP.get(platform_raw)
    if not platform:
        return None

    arch = _ARCH_MAP.get(arch_raw) if arch_raw else "x64"

    return (version, platform, arch, file_type)


class UpdateFeedService:
    """Service for electron-updater generic provider feed and file downloads."""

    def __init__(self, http: HttpClient | None = None, storage: LocalStorage | None = None):
        self._http = http or HttpClient()
        self._storage = storage or LocalStorage()

    # ── YML feed ──────────────────────────────────────────────

    async def get_latest_yml(self, platform: str) -> str | None:
        """Fetch latest-mac.yml or latest.yml content from GitHub, 5-min memory cache.

        Args:
            platform: ``"mac"`` for latest-mac.yml, ``"win"`` for latest.yml.
        """
        global _mac_yml_cache, _mac_yml_cache_time, _win_yml_cache, _win_yml_cache_time

        is_mac = platform == "mac"
        cache = _mac_yml_cache if is_mac else _win_yml_cache
        cache_time = _mac_yml_cache_time if is_mac else _win_yml_cache_time

        now = time.time()
        if cache is not None and (now - cache_time) < _YML_CACHE_TTL:
            return cache

        # Fetch latest release to find the yml asset
        headers = {"Accept": "application/vnd.github+json"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        try:
            data = await self._http.get_json(GITHUB_RELEASES_API, headers=headers)
        except Exception:
            logger.exception("Failed to fetch GitHub releases for yml feed")
            return cache  # Return stale cache if available

        releases: list[dict] = data if isinstance(data, list) else []
        if not releases:
            return cache

        latest = releases[0]
        yml_filename = "latest-mac.yml" if is_mac else "latest.yml"

        # Find the yml asset
        yml_asset = None
        for asset in latest.get("assets", []):
            if asset.get("name") == yml_filename:
                yml_asset = asset
                break

        if not yml_asset:
            logger.warning("%s not found in latest GitHub release", yml_filename)
            return cache

        download_url = yml_asset.get("browser_download_url", "")
        if not download_url:
            return cache

        # Download yml content (small text file, ~1KB)
        try:
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
                resp = await client.get(download_url, headers=headers)
                resp.raise_for_status()
                content = resp.text
        except Exception:
            logger.exception("Failed to download %s from GitHub", yml_filename)
            return cache  # Return stale cache

        # Update cache
        if is_mac:
            _mac_yml_cache = content
            _mac_yml_cache_time = now
        else:
            _win_yml_cache = content
            _win_yml_cache_time = now

        logger.info("Fetched %s from GitHub (%d bytes)", yml_filename, len(content))
        return content

    # ── Asset lookup ──────────────────────────────────────────

    async def find_asset_by_filename(self, filename: str) -> dict | None:
        """Find a GitHub asset by its original filename in the latest release."""
        headers = {"Accept": "application/vnd.github+json"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        try:
            data = await self._http.get_json(GITHUB_RELEASES_API, headers=headers)
        except Exception:
            logger.exception("Failed to fetch GitHub releases for asset lookup")
            return None

        releases: list[dict] = data if isinstance(data, list) else []
        if not releases:
            return None

        latest = releases[0]
        for asset in latest.get("assets", []):
            if asset.get("name") == filename:
                return {
                    "name": asset.get("name", ""),
                    "download_url": asset.get("browser_download_url", ""),
                    "file_size": asset.get("size", 0),
                    "tag_name": latest.get("tag_name", ""),
                }

        return None

    # ── Download & cache ──────────────────────────────────────

    async def download_asset_to_cache(self, download_url: str, version: str, filename: str) -> Path:
        """Download a file from GitHub and cache it locally using the original filename.

        The file is stored at ``data/codex-switch/{version}/{filename}``.
        """
        cache_key = f"codex-switch/{version}/{filename}"
        tmp_dest = Path(f"/tmp/{filename}")
        await self._http.download(download_url, tmp_dest)
        local_path = await self._storage.put(tmp_dest, cache_key)
        tmp_dest.unlink(missing_ok=True)
        logger.info("Cached %s", cache_key)
        return Path(local_path)

    async def get_cached_path(self, version: str, filename: str) -> str | None:
        """Check if a file exists in local cache by its original filename.

        Returns the absolute path or None.
        """
        cache_key = f"codex-switch/{version}/{filename}"
        path = await self._storage.get_path(cache_key)
        return str(path) if path else None

from __future__ import annotations

import logging
import time
from datetime import datetime
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config import settings
from src.models.download import DownloadRecord
from src.schemas.release import DownloadStats, UpdateCheckResponse
from src.utils.http import HttpClient
from src.utils.storage import LocalStorage

logger = logging.getLogger(__name__)

GITHUB_RELEASES_API = "https://api.github.com/repos/Mark7766/codex-switch/releases"

# In-memory cache for latest release info (avoid hitting GitHub on every page load)
_latest_cache: dict | None = None
_cache_time: float = 0
_CACHE_TTL = 300  # 5 minutes


def _parse_semver(version: str) -> tuple[int, ...]:
    return tuple(int(x) for x in version.lstrip("v").split("."))


class ReleaseSyncService:
    def __init__(self, db: AsyncSession, http: HttpClient | None = None, storage: LocalStorage | None = None):
        self._db = db
        self._http = http or HttpClient()
        self._storage = storage or LocalStorage()

    # ── GitHub latest release info ──────────────────────────

    async def get_latest_from_github(self, force_refresh: bool = False) -> dict:
        """Fetch latest release info from GitHub, with 5-min in-memory cache."""
        global _latest_cache, _cache_time
        now = time.time()
        if not force_refresh and _latest_cache and (now - _cache_time) < _CACHE_TTL:
            # Refresh cache-status flags (files may have been downloaded since last fetch)
            for f in _latest_cache.get("files", []):
                f["cached"] = await self._storage.exists(f.get("path", ""))
            return _latest_cache

        headers = {"Accept": "application/vnd.github+json"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        try:
            data = await self._http.get_json(GITHUB_RELEASES_API, headers=headers)
        except Exception:
            logger.exception("Failed to fetch GitHub releases")
            return _latest_cache or {"version": "", "files": []}

        releases: list[dict] = data if isinstance(data, list) else []
        if not releases:
            return {"version": "", "files": []}

        latest = releases[0]
        tag = latest.get("tag_name", "")
        version = tag.lstrip("v")
        published = latest.get("published_at", "")
        rel_date = published[:10] if published else ""

        files = []
        for asset in latest.get("assets", []):
            name: str = asset.get("name", "")
            plat, arch, ftype = _detect_platform(name)
            if plat:
                cache_key = f"codex-switch/{version}/{plat}-{arch}.{ftype}"
                files.append(
                    {
                        "platform": plat,
                        "arch": arch,
                        "file_type": ftype,
                        "file_size": asset.get("size", 0),
                        "download_url": asset.get("browser_download_url", ""),
                        "path": cache_key,
                        "original_name": name,
                        "cached": await self._storage.exists(cache_key),
                    }
                )

        result = {
            "version": version,
            "release_date": rel_date,
            "release_notes": latest.get("body", ""),
            "is_critical": latest.get("prerelease", False) is False,
            "files": files,
        }

        _latest_cache = result
        _cache_time = now
        logger.info("Fetched latest release %s from GitHub (%d files)", version, len(files))
        return result

    # ── Download with cache-or-proxy ────────────────────────

    async def get_download_path(self, version: str, platform: str, arch: str) -> Path | None:
        """Check if the file is cached locally. No DB lookup needed."""
        # Scan cache directory for matching file
        prefix = f"codex-switch/{version}/{platform}-{arch}"
        for ext in ("dmg", "exe", "appimage", "zip", "blockmap"):
            path = f"{prefix}.{ext}"
            if await self._storage.exists(path):
                return await self._storage.get_path(path)
        return None

    async def download_and_cache(
        self,
        download_url: str,
        version: str,
        platform: str,
        arch: str,
        ftype: str,
        original_name: str | None = None,
    ) -> Path:
        """Download from GitHub and cache locally. Returns the local file path.

        When ``original_name`` is provided, the file is cached with the original GitHub
        asset name (for electron-updater). Otherwise uses ``{plat}-{arch}.{ftype}`` format.
        """
        if original_name:
            cache_key = f"codex-switch/{version}/{original_name}"
        else:
            cache_key = f"codex-switch/{version}/{platform}-{arch}.{ftype}"
        tmp_dest = Path(f"/tmp/{original_name or f'codex-switch-{version}-{platform}-{arch}.{ftype}'}")
        await self._http.download(download_url, tmp_dest)
        local_path = await self._storage.put(tmp_dest, cache_key)
        tmp_dest.unlink(missing_ok=True)
        logger.info("Cached %s", cache_key)
        return local_path

    async def get_github_asset_info(self, version: str, platform: str, arch: str) -> dict | None:
        """Get GitHub asset info for a specific version/platform/arch.
        Only returns info if the requested version matches the latest release."""
        info = await self.get_latest_from_github()
        if info.get("version") != version:
            info = await self.get_latest_from_github(force_refresh=True)
        if info.get("version") != version:
            return None
        for f in info.get("files", []):
            if f["platform"] == platform and f["arch"] == arch:
                return f
        return None

    # ── Update check ────────────────────────────────────────

    async def check_for_updates(self, current_version: str, platform: str, arch: str) -> UpdateCheckResponse:
        info = await self.get_latest_from_github()
        version = info.get("version", "")
        if not version:
            return UpdateCheckResponse(has_update=False)

        try:
            current_ver = _parse_semver(current_version)
            latest_ver = _parse_semver(version)
            has_update = latest_ver > current_ver
        except (ValueError, IndexError):
            has_update = current_version != version

        if not has_update:
            return UpdateCheckResponse(has_update=False, latest_version=version)

        file_info = {}
        for f in info.get("files", []):
            if f.get("platform") == platform and f.get("arch") == arch:
                file_info = f
                break

        return UpdateCheckResponse(
            has_update=True,
            latest_version=version,
            release_date=info.get("release_date", ""),
            release_notes=info.get("release_notes", ""),
            download_url=f"/api/v1/update/download/{version}/{platform}-{arch}",
            file_size=file_info.get("file_size", 0),
            sha256=file_info.get("sha256", ""),
            is_critical=info.get("is_critical", False),
        )

    # ── Download tracking ───────────────────────────────────

    async def record_download(
        self,
        version: str,
        platform: str,
        arch: str,
        client_id: str = "",
        package_name: str | None = None,
        ip_hash: str = "",
        user_agent: str = "",
        source: str = "",
    ) -> None:
        record = DownloadRecord(
            release_id=None,
            client_id=client_id,
            package_name=package_name,
            platform=platform,
            arch=arch,
            ip_hash=ip_hash,
            user_agent=user_agent,
            source=source,
        )
        self._db.add(record)
        await self._db.commit()

    # ── Stats (for admin dashboard) ─────────────────────────

    async def get_download_stats(self, range_days: int = 7) -> DownloadStats:
        from datetime import timedelta

        total_result = await self._db.execute(select(func.count()).select_from(DownloadRecord))
        total = total_result.scalar() or 0

        cutoff = datetime.now() - timedelta(days=range_days)
        active_result = await self._db.execute(
            select(func.count(func.distinct(DownloadRecord.client_id))).where(
                DownloadRecord.downloaded_at >= cutoff, DownloadRecord.client_id != ""
            )
        )
        active = active_result.scalar() or 0

        today_cutoff = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_result = await self._db.execute(
            select(func.count()).select_from(DownloadRecord).where(DownloadRecord.downloaded_at >= today_cutoff)
        )
        today = today_result.scalar() or 0

        platform_result = await self._db.execute(
            select(DownloadRecord.platform, func.count())
            .where(DownloadRecord.platform != "")
            .group_by(DownloadRecord.platform)
        )
        platform_dist = [{"platform": row[0], "count": row[1]} for row in platform_result.all()]

        return DownloadStats(
            total_downloads=total,
            active_users=active,
            today_events=today,
            download_trend=[],
            platform_distribution=platform_dist,
        )


def _detect_platform(filename: str) -> tuple[str, str, str]:
    name = filename.lower()

    if ".blockmap" in name or name.endswith(".yml") or name.endswith(".yaml"):
        return "", "", ""

    plat = ""
    arch = "x64"
    ftype = ""

    if ".dmg" in name:
        plat, ftype = "macos", "dmg"
    elif ".exe" in name:
        plat, ftype = "windows", "exe"
    elif ".appimage" in name:
        plat, ftype = "linux", "appimage"

    if not plat:
        return "", "", ""

    if "arm64" in name or "aarch64" in name:
        arch = "arm64"
    elif plat == "windows" and "x64" not in name and "x86" not in name and "amd64" not in name:
        # Windows .exe must have an explicit arch suffix to avoid ambiguous files
        return "", "", ""

    return plat, arch, ftype

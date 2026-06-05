from __future__ import annotations

import logging
from datetime import date, datetime
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.download import DownloadRecord
from src.models.release import Release
from src.schemas.release import DownloadStats, UpdateCheckResponse
from src.utils.http import HttpClient
from src.utils.storage import LocalStorage

logger = logging.getLogger(__name__)

GITHUB_RELEASES_API = "https://api.github.com/repos/Mark7766/codex-switch/releases"


def _parse_semver(version: str) -> tuple[int, ...]:
    return tuple(int(x) for x in version.lstrip("v").split("."))


class ReleaseSyncService:
    def __init__(self, db: AsyncSession, http: HttpClient | None = None, storage: LocalStorage | None = None):
        self._db = db
        self._http = http or HttpClient()
        self._storage = storage or LocalStorage()

    async def check_for_updates(self, current_version: str, platform: str, arch: str) -> UpdateCheckResponse:
        stmt = select(Release).order_by(Release.created_at.desc()).limit(1)
        result = await self._db.execute(stmt)
        latest: Release | None = result.scalar_one_or_none()

        if latest is None:
            return UpdateCheckResponse(has_update=False)

        try:
            current_ver = _parse_semver(current_version)
            latest_ver = _parse_semver(latest.version)
            has_update = latest_ver > current_ver
        except (ValueError, IndexError):
            has_update = current_version != latest.version

        if not has_update:
            return UpdateCheckResponse(has_update=False, latest_version=latest.version)

        file_info = {}
        for f in latest.files:
            if f.get("platform") == platform and f.get("arch") == arch:
                file_info = f
                break

        return UpdateCheckResponse(
            has_update=True,
            latest_version=latest.version,
            release_date=str(latest.release_date),
            release_notes=latest.release_notes,
            download_url=file_info.get("path", ""),
            file_size=file_info.get("file_size", 0),
            sha256=file_info.get("sha256", ""),
            is_critical=latest.is_critical,
        )

    async def sync_from_github(self) -> dict[str, int]:
        data = await self._http.get_json(GITHUB_RELEASES_API, headers={"Accept": "application/vnd.github+json"})
        releases: list[dict] = data if isinstance(data, list) else []

        new_count = 0
        for rel in releases:
            tag = rel.get("tag_name", "")
            version = tag.lstrip("v")
            exists = await self._db.execute(select(Release).where(Release.version == version))
            if exists.scalar_one_or_none():
                continue

            published = rel.get("published_at", "")
            rel_date = date.fromisoformat(published[:10]) if published else date.today()

            files_data = []
            for asset in rel.get("assets", []):
                name: str = asset.get("name", "")
                plat, arch, ftype = _detect_platform(name)
                if plat:
                    files_data.append(
                        {
                            "platform": plat,
                            "arch": arch,
                            "file_type": ftype,
                            "file_size": asset.get("size", 0),
                            "download_url": asset.get("browser_download_url", ""),
                        }
                    )

            record = Release(
                version=version,
                release_date=rel_date,
                release_notes=rel.get("body", ""),
                is_critical=rel.get("prerelease", False) is False,
                files=files_data,
            )
            self._db.add(record)
            new_count += 1

        await self._db.commit()
        logger.info("Synced %d new releases from GitHub", new_count)
        return {"new_count": new_count}

    async def get_latest_release(self) -> Release | None:
        result = await self._db.execute(select(Release).order_by(Release.created_at.desc()).limit(1))
        return result.scalar_one_or_none()

    async def get_releases(self, limit: int = 20) -> list[Release]:
        result = await self._db.execute(select(Release).order_by(Release.created_at.desc()).limit(limit))
        return list(result.scalars().all())

    async def get_download_path(self, version: str, platform: str, arch: str) -> Path | None:
        result = await self._db.execute(select(Release).where(Release.version == version))
        release: Release | None = result.scalar_one_or_none()
        if release is None:
            return None
        for f in release.files:
            if f.get("platform") == platform and f.get("arch") == arch:
                path_str = f.get("path", "")
                if path_str and await self._storage.exists(path_str):
                    return await self._storage.get_path(path_str)
        return None

    async def record_download(
        self,
        version: str,
        platform: str,
        arch: str,
        client_id: str = "",
        package_name: str | None = None,
        ip_hash: str = "",
        user_agent: str = "",
    ) -> None:
        result = await self._db.execute(select(Release).where(Release.version == version))
        release: Release | None = result.scalar_one_or_none()
        record = DownloadRecord(
            release_id=release.id if release else None,
            client_id=client_id,
            package_name=package_name,
            platform=platform,
            arch=arch,
            ip_hash=ip_hash,
            user_agent=user_agent,
        )
        self._db.add(record)
        await self._db.commit()

    async def get_download_stats(self, range_days: int = 7) -> DownloadStats:
        from sqlalchemy import func

        total_result = await self._db.execute(select(func.count()).select_from(DownloadRecord))
        total = total_result.scalar() or 0

        from datetime import timedelta

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

    async def cleanup_old_files(self, keep_versions: int = 5) -> int:
        result = await self._db.execute(select(Release).order_by(Release.created_at.desc()).offset(keep_versions))
        old_releases = result.scalars().all()
        removed = 0
        for rel in old_releases:
            for f in rel.files:
                path_str = f.get("path", "")
                if path_str:
                    await self._storage.delete(path_str)
                    removed += 1
        return removed


def _detect_platform(filename: str) -> tuple[str, str, str]:
    name = filename.lower()
    plat = ""
    arch = "x64"
    ftype = ""

    if ".dmg" in name:
        plat, ftype = "macos", "dmg"
    elif ".exe" in name:
        plat, ftype = "windows", "exe"
    elif ".appimage" in name:
        plat, ftype = "linux", "appimage"

    if "arm64" in name or "aarch64" in name:
        arch = "arm64"

    return plat, arch, ftype

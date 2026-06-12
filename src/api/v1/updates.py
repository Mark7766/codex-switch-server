from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import _db_dep
from src.services.release_sync import ReleaseSyncService
from src.services.update_feed import UpdateFeedService, _parse_filename_to_cache_key
from src.utils.cos_storage import CosStorage

router = APIRouter(prefix="/updates", tags=["updates"])

# Only allow safe filenames: alphanumeric, dot, dash, underscore — must start with letter/digit
_SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


@router.get("/latest-mac.yml")
async def latest_mac_yml() -> Response:
    """Return latest-mac.yml from GitHub (cached 5 min) for macOS electron-updater."""
    svc = UpdateFeedService()
    content = await svc.get_latest_yml("mac")
    if content is None:
        raise HTTPException(status_code=502, detail="Failed to fetch latest-mac.yml from GitHub")
    return Response(content=content, media_type="text/yaml; charset=utf-8")


@router.get("/latest.yml")
async def latest_yml() -> Response:
    """Return latest.yml from GitHub (cached 5 min) for Windows electron-updater."""
    svc = UpdateFeedService()
    content = await svc.get_latest_yml("win")
    if content is None:
        raise HTTPException(status_code=502, detail="Failed to fetch latest.yml from GitHub")
    return Response(content=content, media_type="text/yaml; charset=utf-8")


@router.get("/{filename:path}")
async def download_updates_file(
    filename: str,
    request: Request,
    db: AsyncSession = _db_dep,
) -> Response:
    """Download a release file for electron-updater, with 3-tier fallback.

    Tier 1: COS Guangzhou (302 redirect, 2MB/s for users in China)
    Tier 2: Local cache (nginx X-Accel-Redirect sendfile)
    Tier 3: GitHub proxy download (fetch, cache, return)
    """
    # Security: reject path traversal and unsafe filenames
    if ".." in filename or not _SAFE_FILENAME_RE.match(filename):
        raise HTTPException(status_code=404, detail="File not found")

    # Parse filename to extract version, platform, arch
    parsed = _parse_filename_to_cache_key(filename)
    if not parsed:
        raise HTTPException(status_code=404, detail="File not found")

    version, platform, arch, _file_type = parsed
    ip = request.client.host if request.client else ""

    feed_svc = UpdateFeedService()
    release_svc = ReleaseSyncService(db)
    cos = CosStorage()

    # 1. COS → fast download via Guangzhou
    cos_key = f"codex-switch/{version}/{filename}"
    if cos.exists(cos_key):
        await release_svc.record_download(
            version,
            platform,
            arch,
            package_name="codex-switch",
            ip_hash=ip,
            source="electron-updater",
        )
        headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
        return RedirectResponse(url=cos.public_url(cos_key), status_code=302, headers=headers)

    # 2. Local cache → nginx X-Accel-Redirect
    cached_path = await feed_svc.get_cached_path(version, filename)
    if cached_path is not None:
        await release_svc.record_download(
            version,
            platform,
            arch,
            package_name="codex-switch",
            ip_hash=ip,
            source="electron-updater",
        )
        return _send_file(cached_path, filename)

    # 3. GitHub fallback → download and cache
    asset = await feed_svc.find_asset_by_filename(filename)
    if not asset:
        raise HTTPException(status_code=404, detail="File not found in GitHub release")

    download_url = asset.get("download_url", "")
    if not download_url:
        raise HTTPException(status_code=404, detail="No download URL available")

    try:
        file_path = await feed_svc.download_asset_to_cache(download_url, version, filename)
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to download from GitHub")

    await release_svc.record_download(
        version,
        platform,
        arch,
        package_name="codex-switch",
        ip_hash=ip,
        source="electron-updater",
    )
    return _send_file(str(file_path), filename)


def _send_file(full_path: str, filename: str | None = None) -> Response:
    """Serve cached files via nginx X-Accel-Redirect for zero-copy sendfile."""
    p = Path(full_path)
    data_dir = "data"
    parts = p.parts
    try:
        idx = list(parts).index(data_dir)
        cache_path = "/".join(parts[idx + 1 :])
    except ValueError:
        cache_path = f"codex-switch/{p.parent.name}/{p.name}"

    headers = {"X-Accel-Redirect": f"/_cache/{cache_path}"}
    if filename:
        headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"

    return Response(headers=headers)

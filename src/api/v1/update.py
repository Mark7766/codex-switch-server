from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import _db_dep
from src.schemas.release import UpdateCheckRequest, UpdateCheckResponse
from src.services.release_sync import ReleaseSyncService

router = APIRouter(prefix="/update", tags=["update"])


@router.post("/check", response_model=UpdateCheckResponse)
async def check_update(body: UpdateCheckRequest, db: AsyncSession = _db_dep) -> UpdateCheckResponse:
    svc = ReleaseSyncService(db)
    return await svc.check_for_updates(body.current_version, body.platform, body.arch)


@router.get("/latest")
async def latest_release(db: AsyncSession = _db_dep) -> dict:
    """Return latest release info from GitHub (cached 5 min)."""
    svc = ReleaseSyncService(db)
    return await svc.get_latest_from_github()


@router.get("/download/{version}/{platform}-{arch}")
async def download_release(
    version: str,
    platform: str,
    arch: str,
    request: Request,
    db: AsyncSession = _db_dep,
) -> StreamingResponse:
    svc = ReleaseSyncService(db)

    # Determine filename: prefer GitHub's original asset name, fallback to constructed name
    asset = await svc.get_github_asset_info(version, platform, arch)
    filename = asset.get("original_name") if asset else None
    if not filename:
        # Fallback: look up from cached file
        ftype = asset.get("file_type", "") if asset else ""
        filename = f"Codex-Switch-{version}-{platform}-{arch}.{ftype}" if ftype else None

    # 1. Check local cache
    file_path = await svc.get_download_path(version, platform, arch)
    if file_path is not None:
        await svc.record_download(version, platform, arch, ip_hash=request.client.host if request.client else "")
        return _stream_file(file_path, filename)

    # 2. Fetch from GitHub, cache, and serve
    if not asset:
        raise HTTPException(status_code=404, detail="No asset found for this platform")

    download_url = asset.get("download_url", "")
    ftype = asset.get("file_type", "")
    if not download_url:
        raise HTTPException(status_code=404, detail="No download URL available")

    try:
        file_path = await svc.download_and_cache(download_url, version, platform, arch, ftype)
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to download from GitHub")

    await svc.record_download(version, platform, arch, ip_hash=request.client.host if request.client else "")
    return _stream_file(file_path, filename)


def _stream_file(file_path: str, filename: str | None = None) -> StreamingResponse:
    def _iter():
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    headers = {}
    if filename:
        headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"

    return StreamingResponse(_iter(), media_type="application/octet-stream", headers=headers)

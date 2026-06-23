from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import _db_dep
from src.schemas.release import UpdateCheckRequest, UpdateCheckResponse
from src.services.release_sync import ReleaseSyncService
from src.utils.cos_storage import CosStorage

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
) -> Response:
    svc = ReleaseSyncService(db)
    cos = CosStorage()

    asset = await svc.get_github_asset_info(version, platform, arch)
    filename = asset.get("original_name") if asset else None
    ftype = asset.get("file_type", "exe") if asset else "exe"
    if not filename:
        filename = f"Codex-Switch-{version}-{platform}-{arch}.{ftype}"

    ip = request.client.host if request.client else ""

    # 1. Local cache → nginx X-Accel-Redirect (reliable Content-Disposition)
    file_path = await svc.get_download_path(version, platform, arch)
    if file_path is not None:
        await svc.record_download(version, platform, arch, package_name="codex-switch", ip_hash=ip, delivery="local")
        return _send_file(file_path, filename)

    # 2. COS → fast download via Guangzhou CDN
    cos_key = f"codex-switch/{version}/{filename}"
    if cos.exists(cos_key):
        await svc.record_download(version, platform, arch, package_name="codex-switch", ip_hash=ip, delivery="cos")
        headers = {}
        if filename:
            headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"
        return RedirectResponse(url=cos.public_url(cos_key), status_code=302, headers=headers)

    # 3. Fetch from GitHub → cache locally
    if not asset:
        raise HTTPException(status_code=404, detail="No asset found for this platform")

    download_url = asset.get("download_url", "")
    if not download_url:
        raise HTTPException(status_code=404, detail="No download URL available")

    try:
        file_path = await svc.download_and_cache(download_url, version, platform, arch, ftype, original_name=filename)
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to download from GitHub")

    await svc.record_download(version, platform, arch, package_name="codex-switch", ip_hash=ip, delivery="github")
    return _send_file(file_path, filename)


def _send_file(full_path: str, filename: str | None = None) -> Response:
    """Serve cached files via nginx X-Accel-Redirect for zero-copy sendfile."""
    p = Path(full_path)
    # Path is like /app/data/codex-switch/1.4.0/win-x64.exe
    # Nginx /_cache/ aliases to /app/data/, so redirect = /_cache/codex-switch/...
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

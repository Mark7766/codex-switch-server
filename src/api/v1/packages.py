from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import _db_dep
from src.schemas.release import APIResponse, PackageInfo, PackageListData
from src.services.ai_working_ok_releases import AiWorkingOkReleaseService
from src.services.package_manager import PackageManager
from src.services.release_sync import ReleaseSyncService
from src.utils.cos_storage import CosStorage

router = APIRouter(prefix="/packages", tags=["packages"])


@router.get("", response_model=APIResponse[PackageListData])
async def list_packages() -> APIResponse[PackageListData]:
    mgr = PackageManager()
    raw = await mgr.list_packages()
    packages = [
        PackageInfo(
            name=p["name"],
            display_name=p["display_name"],
            description=p.get("description", ""),
            latest_version=p.get("latest_version", ""),
            platforms=p.get("platforms", []),
        )
        for p in raw
    ]
    return APIResponse(data=PackageListData(packages=packages))


# ── ai-working-ok release download ─────────────────────────────
# Registered BEFORE the parameterized route below to avoid path conflicts.


@router.get("/ai-working-ok/latest")
async def download_ai_working_ok_latest(request: Request, db: AsyncSession = _db_dep) -> Response:
    """Download the latest ai-working-ok release tarball."""
    svc = AiWorkingOkReleaseService()
    try:
        version = await svc.get_latest_version()
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to fetch latest version from GitHub")

    return await _serve_ai_working_ok(version, request, db)


@router.get("/ai-working-ok/releases/{version}")
async def download_ai_working_ok_version(
    version: str,
    request: Request,
    db: AsyncSession = _db_dep,
) -> Response:
    """Download a specific ai-working-ok release tarball by version (e.g. v1.0.0)."""
    return await _serve_ai_working_ok(version, request, db)


async def _serve_ai_working_ok(version: str, request: Request, db: AsyncSession) -> Response:
    """Shared helper: serve ai-working-ok tarball, cache-or-download from GitHub."""
    svc = AiWorkingOkReleaseService()

    # 1. Get file (local cache → GitHub download)
    try:
        file_path, filename = await svc.get_release(version)
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to download from GitHub")

    # 2. Record download
    ip = request.client.host if request.client else ""
    dl_svc = ReleaseSyncService(db)
    await dl_svc.record_download(
        version=version,
        platform="linux",  # ai-working-ok is a generic tarball
        arch="x64",
        package_name="ai-working-ok",
        ip_hash=ip,
        delivery="local",
    )

    # 3. Serve via nginx X-Accel-Redirect
    p = Path(file_path)
    parts = list(p.parts)
    try:
        idx = parts.index("data")
        cache_path = "/".join(parts[idx + 1 :])
    except ValueError:
        cache_path = f"packages/ai-working-ok/{p.name}"

    headers = {
        "X-Accel-Redirect": f"/_cache/{cache_path}",
        "Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}",
    }
    return Response(headers=headers)


@router.get("/{package_name}/{version}/{platform}-{arch}")
async def download_package(
    package_name: str,
    version: str,
    platform: str,
    arch: str,
    request: Request,
    db: AsyncSession = _db_dep,
) -> Response:
    mgr = PackageManager()
    file_path, original_filename = await mgr.get_download_path_with_name(package_name, platform, arch)
    if file_path is None:
        raise HTTPException(status_code=404, detail="Package not found")

    # Build deterministic COS key: packages/{name}/latest/{platform}-{arch}.{ext}
    plat_info = await mgr.get_package_info(package_name, platform, arch)
    file_type = plat_info.get("file_type", "bin") if plat_info else "bin"
    cos_key = f"packages/{package_name}/latest/{platform}-{arch}.{file_type}"

    ip = request.client.host if request.client else ""

    # 1. COS → fast download via Guangzhou CDN
    cos = CosStorage()
    if cos.exists(cos_key):
        dl_svc = ReleaseSyncService(db)
        await dl_svc.record_download(
            version="latest",
            platform=platform,
            arch=arch,
            package_name=package_name,
            ip_hash=ip,
            delivery="cos",
        )
        headers = {}
        if original_filename:
            headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(original_filename)}"
        return RedirectResponse(url=cos.public_url(cos_key), status_code=302, headers=headers)

    # 2. Fallback: nginx X-Accel-Redirect from local disk
    dl_svc = ReleaseSyncService(db)
    await dl_svc.record_download(
        version="latest",
        platform=platform,
        arch=arch,
        package_name=package_name,
        ip_hash=ip,
        delivery="local",
    )
    p = Path(file_path)
    parts = list(p.parts)
    try:
        idx = parts.index("data")
        cache_path = "/".join(parts[idx + 1 :])
    except ValueError:
        cache_path = f"packages/{p.parent.parent.name}/{p.parent.name}/{p.name}"

    headers = {"X-Accel-Redirect": f"/_cache/{cache_path}"}
    if original_filename:
        headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(original_filename)}"

    return Response(headers=headers)

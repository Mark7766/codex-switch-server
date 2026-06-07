from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import _db_dep
from src.schemas.release import APIResponse, PackageInfo, PackageListData
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

    # Record download for analytics
    dl_svc = ReleaseSyncService(db)
    await dl_svc.record_download(
        version="latest", platform=platform, arch=arch,
        package_name=package_name,
        ip_hash=request.client.host if request.client else "",
    )

    # Build deterministic COS key: packages/{name}/latest/{platform}-{arch}.{ext}
    plat_info = await mgr.get_package_info(package_name, platform, arch)
    file_type = plat_info.get("file_type", "bin") if plat_info else "bin"
    cos_key = f"packages/{package_name}/latest/{platform}-{arch}.{file_type}"

    # 1. COS → fast download via Guangzhou CDN
    cos = CosStorage()
    if cos.exists(cos_key):
        headers = {}
        if original_filename:
            headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(original_filename)}"
        return RedirectResponse(url=cos.public_url(cos_key), status_code=302, headers=headers)

    # 2. Fallback: nginx X-Accel-Redirect from local disk
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

from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from src.schemas.release import APIResponse, PackageInfo, PackageListData
from src.services.package_manager import PackageManager

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
) -> Response:
    mgr = PackageManager()
    file_path, filename = await mgr.get_download_path_with_name(package_name, platform, arch)
    if file_path is None:
        raise HTTPException(status_code=404, detail="Package not found")

    # nginx X-Accel-Redirect for zero-copy sendfile
    p = Path(file_path)
    parts = list(p.parts)
    try:
        idx = parts.index("data")
        cache_path = "/".join(parts[idx + 1:])
    except ValueError:
        cache_path = f"packages/{p.parent.parent.name}/{p.parent.name}/{p.name}"

    headers = {"X-Accel-Redirect": f"/_cache/{cache_path}"}
    if filename:
        headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"

    return Response(headers=headers)

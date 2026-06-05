from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

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
) -> StreamingResponse:
    mgr = PackageManager()
    file_path = await mgr.get_download_path(package_name, platform, arch)
    if file_path is None:
        raise HTTPException(status_code=404, detail="Package not found")

    def _iter():
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(_iter(), media_type="application/octet-stream")

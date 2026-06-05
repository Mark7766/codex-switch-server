from __future__ import annotations

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.schemas.release import APIResponse, PackageInfo, PackageListData
from src.utils.storage import LocalStorage

router = APIRouter(prefix="/packages", tags=["packages"])

PACKAGES: dict[str, PackageInfo] = {
    "claude-desktop": PackageInfo(
        name="claude-desktop",
        display_name="Claude Desktop",
        description="Anthropic 官方 Claude 桌面应用",
        latest_version="1.2.0",
    ),
    "codex-desktop": PackageInfo(
        name="codex-desktop",
        display_name="Codex Desktop",
        description="OpenAI 官方 Codex 桌面应用",
        latest_version="2.1.0",
    ),
    "nodejs": PackageInfo(
        name="nodejs",
        display_name="Node.js",
        description="JavaScript 运行时（Codex CLI 依赖）",
        latest_version="22.12.0",
    ),
    "git": PackageInfo(
        name="git",
        display_name="Git",
        description="版本控制工具（Claude Code CLI 依赖）",
        latest_version="2.47.0",
    ),
}


@router.get("", response_model=APIResponse[PackageListData])
async def list_packages() -> APIResponse[PackageListData]:
    return APIResponse(data=PackageListData(packages=list(PACKAGES.values())))


@router.get("/{package_name}/{version}/{platform}-{arch}")
async def download_package(package_name: str, version: str, platform: str, arch: str) -> StreamingResponse:
    storage = LocalStorage()
    key = f"packages/{package_name}/{version}/{platform}-{arch}"
    file_path = await storage.get_path(key)
    if file_path is None:
        raise HTTPException(status_code=404, detail="Package not found")

    def _iter():
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(_iter(), media_type="application/octet-stream")

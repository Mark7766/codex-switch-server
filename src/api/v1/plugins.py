from __future__ import annotations

from pathlib import Path
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import _db_dep
from src.services.release_sync import ReleaseSyncService
from src.utils.cos_storage import CosStorage
from src.utils.storage import LocalStorage

router = APIRouter(prefix="/plugins", tags=["plugins"])

_PACK_FILENAME = "codex-offline-pack.tar.gz"
_PACK_VERSION = "1.0.0"
_PACK_PLUGIN_COUNT = 173
_PACK_DESCRIPTION = "包含 Claude Code 集成、代码格式化、Git 辅助、中文优化等 173 个精选插件"


@router.get("/pack")
async def get_plugin_pack() -> dict:
    """Return plugin pack metadata for client display."""
    storage = LocalStorage()
    file_key = f"files/{_PACK_FILENAME}"
    path = await storage.get_path(file_key)
    size = path.stat().st_size if path else 37748736

    return {
        "code": 0,
        "data": {
            "version": _PACK_VERSION,
            "filename": _PACK_FILENAME,
            "size": size,
            "size_mb": round(size / 1048576),
            "plugin_count": _PACK_PLUGIN_COUNT,
            "description": _PACK_DESCRIPTION,
            "updated_at": "2026-06-14",
            "download_url": "/api/v1/plugins/pack/download",
        },
    }


@router.get("/pack/download")
async def download_plugin_pack(request: Request, db: AsyncSession = _db_dep) -> Response:
    """Download the offline plugin pack. COS Guangzhou 302, local nginx fallback."""
    cos = CosStorage()
    cos_key = f"files/{_PACK_FILENAME}"
    ip = request.client.host if request.client else ""
    dl_svc = ReleaseSyncService(db)

    # 1. COS → Guangzhou fast download (302 redirect)
    if cos.exists(cos_key):
        await dl_svc.record_download(
            version=_PACK_VERSION, platform="", arch="",
            package_name="codex-offline-pack", ip_hash=ip,
            source="plugin-install", delivery="cos",
        )
        headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(_PACK_FILENAME)}"}
        return RedirectResponse(url=cos.public_url(cos_key), status_code=302, headers=headers)

    # 2. Local cache → nginx sendfile
    storage = LocalStorage()
    file_key = f"files/{_PACK_FILENAME}"
    path = await storage.get_path(file_key)
    if path:
        await dl_svc.record_download(
            version=_PACK_VERSION, platform="", arch="",
            package_name="codex-offline-pack", ip_hash=ip,
            source="plugin-install", delivery="local",
        )
        return _send_file(str(path), _PACK_FILENAME)

    raise HTTPException(status_code=404, detail="Plugin pack not found")


def _send_file(full_path: str, filename: str | None = None) -> Response:
    """Serve cached files. Uses nginx X-Accel-Redirect in production, FileResponse locally."""
    p = Path(full_path)
    media_type = "application/gzip" if p.suffix == ".gz" else None

    return FileResponse(
        path=str(p),
        filename=filename or p.name,
        media_type=media_type,
    )

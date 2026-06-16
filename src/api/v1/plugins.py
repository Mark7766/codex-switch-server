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

_PACKS = {
    "codex": {
        "version": "1.0.0",
        "filename": "codex-offline-pack.tar.gz",
        "size": 37748736,
        "plugin_count": 173,
        "description": "包含 Claude Code 集成、代码格式化、Git 辅助、中文优化等 173 个精选插件",
        "updated_at": "2026-06-14",
        "package_name": "codex-offline-pack",
        "source": "plugin-install",
    },
    "claude": {
        "version": "1.0.0",
        "filename": "claude-offline-plugins.tar.gz",
        "size": 173015040,
        "plugin_count": 170,
        "description": "含 Superpowers 全系列 14 个 + 内置精品 6 个（精选 20），共 170+ 可选",
        "updated_at": "2026-06-15",
        "package_name": "claude-offline-plugins",
        "source": "plugin-install-claude",
    },
}


def _get_pack(type: str) -> dict:
    """Return pack metadata for the given type, defaulting to codex."""
    return _PACKS.get(type, _PACKS["codex"])


@router.get("/pack")
async def get_plugin_pack(type: str = "codex") -> dict:
    """Return plugin pack metadata for client display."""
    pack = _get_pack(type)
    storage = LocalStorage()
    file_key = f"files/{pack['filename']}"
    path = await storage.get_path(file_key)
    size = path.stat().st_size if path else pack["size"]

    return {
        "code": 0,
        "data": {
            "version": pack["version"],
            "filename": pack["filename"],
            "size": size,
            "size_mb": round(size / 1048576),
            "plugin_count": pack["plugin_count"],
            "description": pack["description"],
            "updated_at": pack["updated_at"],
            "download_url": f"/api/v1/plugins/pack/download?type={type}",
        },
    }


@router.get("/pack/download")
async def download_plugin_pack(request: Request, db: AsyncSession = _db_dep, type: str = "codex") -> Response:
    """Download the offline plugin pack. COS Guangzhou 302, local nginx fallback."""
    pack = _get_pack(type)
    filename = pack["filename"]
    cos = CosStorage()
    cos_key = f"files/{filename}"
    ip = request.client.host if request.client else ""
    dl_svc = ReleaseSyncService(db)

    # 1. COS → Guangzhou fast download (302 redirect)
    if cos.exists(cos_key):
        await dl_svc.record_download(
            version=pack["version"], platform="", arch="",
            package_name=pack["package_name"], ip_hash=ip,
            source=pack["source"], delivery="cos",
        )
        headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
        return RedirectResponse(url=cos.public_url(cos_key), status_code=302, headers=headers)

    # 2. Local cache → nginx sendfile
    storage = LocalStorage()
    file_key = f"files/{filename}"
    path = await storage.get_path(file_key)
    if path:
        await dl_svc.record_download(
            version=pack["version"], platform="", arch="",
            package_name=pack["package_name"], ip_hash=ip,
            source=pack["source"], delivery="local",
        )
        return _send_file(str(path), filename)

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

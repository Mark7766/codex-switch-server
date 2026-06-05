from __future__ import annotations

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


@router.get("/download/{version}/{platform}-{arch}")
async def download_release(
    version: str,
    platform: str,
    arch: str,
    request: Request,
    db: AsyncSession = _db_dep,
) -> StreamingResponse:
    svc = ReleaseSyncService(db)
    file_path = await svc.get_download_path(version, platform, arch)
    if file_path is None:
        raise HTTPException(status_code=404, detail="File not found")

    client_id = request.headers.get("X-Client-Id", "")
    ip_hash = request.client.host if request.client else ""
    await svc.record_download(version, platform, arch, client_id=client_id, ip_hash=ip_hash)

    def _iter():
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(_iter(), media_type="application/octet-stream")

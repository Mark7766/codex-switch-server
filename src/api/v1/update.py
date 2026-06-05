from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import _db_dep
from src.schemas.release import ReleaseRead, UpdateCheckRequest, UpdateCheckResponse
from src.services.release_sync import ReleaseSyncService

router = APIRouter(prefix="/update", tags=["update"])


@router.post("/check", response_model=UpdateCheckResponse)
async def check_update(body: UpdateCheckRequest, db: AsyncSession = _db_dep) -> UpdateCheckResponse:
    svc = ReleaseSyncService(db)
    return await svc.check_for_updates(body.current_version, body.platform, body.arch)


@router.get("/releases", response_model=list[ReleaseRead])
async def list_releases(db: AsyncSession = _db_dep) -> list[ReleaseRead]:
    svc = ReleaseSyncService(db)
    releases = await svc.get_releases(limit=20)
    return [ReleaseRead.model_validate(r) for r in releases]


@router.get("/download/{version}/{platform}-{arch}", response_model=None)
async def download_release(
    version: str,
    platform: str,
    arch: str,
    request: Request,
    db: AsyncSession = _db_dep,
) -> StreamingResponse | RedirectResponse:
    svc = ReleaseSyncService(db)

    # Try local cached file first
    file_path = await svc.get_download_path(version, platform, arch)
    if file_path is not None:
        await svc.record_download(version, platform, arch, ip_hash=request.client.host if request.client else "")
        return _stream_file(file_path)

    # Fallback: proxy from GitHub
    github_url = await svc.get_github_download_url(version, platform, arch)
    if github_url:
        await svc.record_download(version, platform, arch, ip_hash=request.client.host if request.client else "")
        return RedirectResponse(url=github_url, status_code=302)

    raise HTTPException(status_code=404, detail="File not found")


def _stream_file(file_path: str) -> StreamingResponse:
    def _iter():
        with open(file_path, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(_iter(), media_type="application/octet-stream")

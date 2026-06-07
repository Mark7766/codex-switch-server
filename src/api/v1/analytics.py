from __future__ import annotations

from fastapi import APIRouter, Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import _db_dep
from src.schemas.analytics import PageviewRequest
from src.services.analytics import AnalyticsService

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.post("/pageview")
async def record_pageview(body: PageviewRequest, request: Request, db: AsyncSession = _db_dep) -> dict:
    """Record a pageview or click event. Public endpoint, fire-and-forget."""
    ip = request.client.host if request.client else ""
    ua = request.headers.get("User-Agent", "")
    svc = AnalyticsService(db)
    await svc.record_page_event(body, ip=ip, ua=ua)
    return {"status": "ok"}

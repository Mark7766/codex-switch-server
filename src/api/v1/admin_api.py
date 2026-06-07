from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import _db_dep, verify_admin_token
from src.schemas.analytics import DownloadTrendsResponse, PageStatsResponse
from src.services.analytics import AnalyticsService

router = APIRouter(prefix="/admin/analytics", tags=["admin-analytics"], dependencies=[Depends(verify_admin_token)])


@router.get("/page-stats", response_model=PageStatsResponse)
async def page_stats(
    range_days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = _db_dep,
) -> PageStatsResponse:
    """Page view and click statistics with Chinese name mapping."""
    svc = AnalyticsService(db)
    return await svc.get_page_stats(range_days=range_days)


@router.get("/download-trends", response_model=DownloadTrendsResponse)
async def download_trends(
    range_days: int = Query(default=30, ge=1, le=365),
    db: AsyncSession = _db_dep,
) -> DownloadTrendsResponse:
    """Download trends with 8-package granularity breakdown."""
    svc = AnalyticsService(db)
    return await svc.get_download_trends(range_days=range_days)

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.download import DownloadRecord
from src.models.page_event import PageEvent
from src.schemas.analytics import (
    ClickItem,
    DailyAnalyticsTrend,
    DailyDownloadPoint,
    DownloadTrendsResponse,
    PackageDownloadItem,
    PageStatsResponse,
    PageViewItem,
    PageviewRequest,
    ProductDownloadItem,
    VersionDownloadItem,
    get_element_info,
    get_page_name,
    get_platform_name,
    get_product_name,
)

logger = logging.getLogger(__name__)


def _beijing_now() -> datetime:
    """Return current Beijing time (UTC+8) as naive datetime."""
    return (datetime.now(UTC) + timedelta(hours=8)).replace(tzinfo=None)


def _beijing_today_start() -> datetime:
    """Return Beijing midnight converted to UTC naive, for DB comparison.
    DB stores UTC, so Beijing 00:00 = UTC 16:00 previous day.
    """
    return _beijing_now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=8)


class AnalyticsService:
    """Portal page analytics + download trend aggregation."""

    def __init__(self, db: AsyncSession):
        self._db = db

    # ── Ingest ────────────────────────────────────────────

    async def record_page_event(self, event: PageviewRequest, ip: str = "", ua: str = "") -> None:
        """Record a pageview or click event. Fire-and-forget."""
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:64] if ip else ""
        ua_snippet = ua[:256] if ua else ""
        visitor_id = hashlib.sha256(f"{ip_hash}{ua_snippet}".encode()).hexdigest()[:16]
        record = PageEvent(
            event_type=event.event_type,
            page=event.page,
            element_id=event.element_id if event.element_id else None,
            ip_hash=ip_hash,
            user_agent=ua_snippet,
            visitor_id=visitor_id,
        )
        self._db.add(record)
        try:
            await self._db.commit()
        except Exception:
            logger.exception("Failed to record page event")
            await self._db.rollback()

    # ── Page stats ────────────────────────────────────────

    async def get_page_stats(self, range_days: int = 30) -> PageStatsResponse:
        cutoff = _beijing_now() - timedelta(days=range_days)

        # Page views
        pv_result = await self._db.execute(
            select(PageEvent.page, func.count())
            .where(PageEvent.event_type == "pageview", PageEvent.created_at >= cutoff)
            .group_by(PageEvent.page)
            .order_by(func.count().desc())
        )
        page_views = [
            PageViewItem(page=row[0], page_name=get_page_name(row[0]), count=row[1]) for row in pv_result.all()
        ]

        # Top clicks
        click_result = await self._db.execute(
            select(PageEvent.element_id, PageEvent.page, func.count())
            .where(PageEvent.event_type == "click", PageEvent.created_at >= cutoff, PageEvent.element_id.isnot(None))
            .group_by(PageEvent.element_id)
            .order_by(func.count().desc())
            .limit(20)
        )
        top_clicks = []
        for row in click_result.all():
            element_id = row[0]
            page = row[1]
            count = row[2]
            el_name, el_page = get_element_info(element_id)
            top_clicks.append(
                ClickItem(
                    element_id=element_id,
                    element_name=el_name,
                    page=page,
                    page_name=get_page_name(el_page),
                    count=count,
                )
            )

        # Daily trend — date labels use Beijing time, DB query uses UTC
        bj_today = _beijing_now().replace(hour=0, minute=0, second=0, microsecond=0)
        daily_trend = []
        for i in range(range_days - 1, -1, -1):
            day_start_bj = bj_today - timedelta(days=i)
            day_start_utc = day_start_bj - timedelta(hours=8)
            day_end_utc = day_start_utc + timedelta(days=1)

            pv_count = await self._db.scalar(
                select(func.count()).where(
                    PageEvent.event_type == "pageview",
                    PageEvent.created_at >= day_start_utc,
                    PageEvent.created_at < day_end_utc,
                )
            )
            click_count = await self._db.scalar(
                select(func.count()).where(
                    PageEvent.event_type == "click",
                    PageEvent.created_at >= day_start_utc,
                    PageEvent.created_at < day_end_utc,
                )
            )
            uv_count = await self._db.scalar(
                select(func.count(func.distinct(PageEvent.visitor_id))).where(
                    PageEvent.event_type == "pageview",
                    PageEvent.visitor_id != "",
                    PageEvent.created_at >= day_start_utc,
                    PageEvent.created_at < day_end_utc,
                )
            )
            daily_trend.append(
                DailyAnalyticsTrend(
                    date=day_start_bj.strftime("%Y-%m-%d"),
                    pageviews=pv_count or 0,
                    clicks=click_count or 0,
                    uv=uv_count or 0,
                )
            )

        return PageStatsResponse(page_views=page_views, top_clicks=top_clicks, daily_trend=daily_trend)

    # ── UV stats ──────────────────────────────────────────

    async def get_uv_stats(self) -> dict:
        """Return monthly UV, today UV, and PV/UV ratio."""
        today_start = _beijing_today_start()
        cutoff_30 = _beijing_now() - timedelta(days=30)

        month_uv = (
            await self._db.scalar(
                select(func.count(func.distinct(PageEvent.visitor_id))).where(
                    PageEvent.event_type == "pageview",
                    PageEvent.visitor_id != "",
                    PageEvent.created_at >= cutoff_30,
                )
            )
            or 0
        )

        today_uv = (
            await self._db.scalar(
                select(func.count(func.distinct(PageEvent.visitor_id))).where(
                    PageEvent.event_type == "pageview",
                    PageEvent.visitor_id != "",
                    PageEvent.created_at >= today_start,
                )
            )
            or 0
        )

        today_pv = (
            await self._db.scalar(
                select(func.count()).where(
                    PageEvent.event_type == "pageview",
                    PageEvent.created_at >= today_start,
                )
            )
            or 0
        )

        pv_uv_ratio = f"{today_pv / today_uv:.1f}" if today_uv > 0 else "—"

        return {
            "month_uv": month_uv,
            "today_uv": today_uv,
            "today_pv": today_pv,
            "pv_uv_ratio": pv_uv_ratio,
        }

    # ── Download trends ───────────────────────────────────

    async def get_download_trends(self, range_days: int = 30) -> DownloadTrendsResponse:
        cutoff = _beijing_now() - timedelta(days=range_days)

        # Total
        total = await self._db.scalar(select(func.count()).select_from(DownloadRecord)) or 0

        # Today
        today_start = _beijing_today_start()
        today = await self._db.scalar(select(func.count()).where(DownloadRecord.downloaded_at >= today_start)) or 0

        # By product (package_name) — coalesce NULL to 'codex-switch' for old records
        pkg_col = func.coalesce(DownloadRecord.package_name, "codex-switch")

        prod_result = await self._db.execute(
            select(
                pkg_col.label("product"),
                func.count(),
            )
            .where(DownloadRecord.downloaded_at >= cutoff)
            .group_by(pkg_col)
            .order_by(func.count().desc())
        )
        by_product = [
            ProductDownloadItem(
                package_name=row[0] or "unknown",
                product_name=get_product_name(row[0] or "unknown"),
                count=row[1],
            )
            for row in prod_result.all()
        ]

        # By package (product + platform + arch) — 8 download slots
        pkg_result = await self._db.execute(
            select(
                pkg_col.label("product"),
                DownloadRecord.platform,
                DownloadRecord.arch,
                func.count(),
            )
            .where(DownloadRecord.downloaded_at >= cutoff)
            .group_by(pkg_col, DownloadRecord.platform, DownloadRecord.arch)
            .order_by(func.count().desc())
        )
        by_package = [
            PackageDownloadItem(
                package_name=row[0] or "unknown",
                product_name=get_product_name(row[0] or "unknown"),
                platform=row[1] or "",
                arch=row[2] or "",
                platform_name=get_platform_name(row[1] or "", row[2] or ""),
                count=row[3],
            )
            for row in pkg_result.all()
        ]

        # Daily trend with breakdown — date labels use Beijing time
        bj_today = _beijing_now().replace(hour=0, minute=0, second=0, microsecond=0)
        daily = []
        for i in range(range_days - 1, -1, -1):
            day_start_bj = bj_today - timedelta(days=i)
            day_start_utc = day_start_bj - timedelta(hours=8)
            day_end_utc = day_start_utc + timedelta(days=1)

            day_total = (
                await self._db.scalar(
                    select(func.count()).where(
                        DownloadRecord.downloaded_at >= day_start_utc,
                        DownloadRecord.downloaded_at < day_end_utc,
                    )
                )
                or 0
            )

            day_rows = await self._db.execute(
                select(
                    pkg_col.label("product"),
                    DownloadRecord.platform,
                    DownloadRecord.arch,
                    func.count(),
                )
                .where(DownloadRecord.downloaded_at >= day_start_utc, DownloadRecord.downloaded_at < day_end_utc)
                .group_by(pkg_col, DownloadRecord.platform, DownloadRecord.arch)
            )
            breakdown = {}
            for row in day_rows.all():
                pkg = row[0] or "unknown"
                plat = row[1] or ""
                arch = row[2] or ""
                key = f"{pkg}-{plat}-{arch}"
                breakdown[key] = row[3]

            daily.append(
                DailyDownloadPoint(
                    date=day_start_bj.strftime("%Y-%m-%d"),
                    total=day_total,
                    breakdown=breakdown,
                )
            )

        # By version
        ver_result = await self._db.execute(
            select(DownloadRecord.release_id, func.count())
            .where(DownloadRecord.downloaded_at >= cutoff, DownloadRecord.release_id.isnot(None))
            .group_by(DownloadRecord.release_id)
            .order_by(func.count().desc())
        )
        # release_id stores version string in practice, adapt as needed
        by_version: list[VersionDownloadItem] = []
        for row in ver_result.all():
            if row[0]:
                by_version.append(VersionDownloadItem(version=str(row[0]), count=row[1]))

        # COS hit rate: downloads delivered via COS / total downloads (30-day window)
        cos_hits = (
            await self._db.scalar(
                select(func.count()).where(
                    DownloadRecord.downloaded_at >= cutoff,
                    DownloadRecord.delivery == "cos",
                )
            )
            or 0
        )
        total_window = await self._db.scalar(select(func.count()).where(DownloadRecord.downloaded_at >= cutoff)) or 1
        cos_rate = round(cos_hits / total_window, 2) if total_window > 0 else 0.0

        return DownloadTrendsResponse(
            total=total,
            today=today,
            daily=daily,
            by_product=by_product,
            by_package=by_package,
            by_version=by_version,
            cos_hit_rate=cos_rate,
        )

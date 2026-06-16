from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.telemetry import TelemetryEvent
from src.schemas.telemetry import (
    VALID_EVENT_TYPES,
    DailyTrend,
    EventTypeCount,
    IngestResult,
    OsItem,
    TelemetryPayload,
    TelemetryStats,
    VersionItem,
    VersionOsItem,
)
from src.services.release_sync import _parse_semver


def _beijing_now() -> datetime:
    """Return current Beijing time (UTC+8) as naive datetime."""
    return (datetime.now(UTC) + timedelta(hours=8)).replace(tzinfo=None)


def _beijing_today_start() -> datetime:
    """Return Beijing midnight converted to UTC naive, for DB comparison.
    DB stores UTC, so Beijing 00:00 = UTC 16:00 previous day.
    """
    return _beijing_now().replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(hours=8)


logger = logging.getLogger(__name__)

# Event types that need deduplication (same client_id+event_type+timestamp).
# High-frequency or one-shot events are excluded — dedup would be wasteful or incorrect.
_DEDUP_TYPES = frozenset({"app_start", "proxy_start", "proxy_error", "update_check"})


class TelemetryService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def ingest(
        self,
        payload: TelemetryPayload,
        max_per_client_per_minute: int = 60,
        ip_hash: str = "",
    ) -> IngestResult:
        accepted = 0
        rejected = 0

        for evt in payload.events:
            if evt.event_type not in VALID_EVENT_TYPES:
                rejected += 1
                continue

            # Skip events with zero count (client sent empty aggregation window)
            if evt.count <= 0:
                rejected += 1
                continue

            # Dedup: only for event types where duplicate submission is suspicious
            if evt.event_type in _DEDUP_TYPES:
                exists = await self._db.execute(
                    select(TelemetryEvent).where(
                        TelemetryEvent.client_id == payload.client_id,
                        TelemetryEvent.event_type == evt.event_type,
                        TelemetryEvent.timestamp == evt.timestamp,
                    )
                )
                if exists.scalar_one_or_none():
                    rejected += 1
                    continue

            cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(minutes=1)
            recent_count = await self._db.execute(
                select(func.count())
                .select_from(TelemetryEvent)
                .where(
                    TelemetryEvent.client_id == payload.client_id,
                    TelemetryEvent.created_at >= cutoff,
                )
            )
            if (recent_count.scalar() or 0) >= max_per_client_per_minute:
                rejected += 1
                continue

            # Merge aggregation fields into properties for storage
            props = dict(evt.properties)
            if evt.count > 1:
                props["count"] = evt.count
            if evt.period_start is not None:
                props["period_start"] = evt.period_start
            if evt.period_end is not None:
                props["period_end"] = evt.period_end
            if payload.install_source:
                props["install_source"] = payload.install_source

            record = TelemetryEvent(
                client_id=payload.client_id,
                event_type=evt.event_type,
                timestamp=evt.timestamp,
                properties=props,
                app_version=payload.app_version,
                platform=payload.platform,
                arch=payload.arch,
                os_version=payload.os_version,
                ip_hash=ip_hash,
            )
            self._db.add(record)
            accepted += 1

        await self._db.commit()
        logger.debug("Telemetry ingest: accepted=%d rejected=%d", accepted, rejected)
        return IngestResult(accepted=accepted, rejected=rejected)

    async def get_stats(self, range_days: int = 30) -> TelemetryStats:
        total = await self._db.scalar(select(func.count()).select_from(TelemetryEvent))
        total = total or 0

        today_start = _beijing_today_start()
        today = await self._db.scalar(
            select(func.count()).select_from(TelemetryEvent).where(TelemetryEvent.created_at >= today_start)
        )
        today = today or 0

        cutoff = _beijing_now() - timedelta(days=range_days)
        active = await self._db.scalar(
            select(func.count(func.distinct(TelemetryEvent.client_id))).where(
                TelemetryEvent.created_at >= cutoff, TelemetryEvent.client_id != ""
            )
        )
        active = active or 0

        type_counts_result = await self._db.execute(
            select(TelemetryEvent.event_type, func.count())
            .where(TelemetryEvent.created_at >= cutoff)
            .group_by(TelemetryEvent.event_type)
            .order_by(func.count().desc())
        )
        type_counts = [EventTypeCount(event_type=row[0], count=row[1]) for row in type_counts_result.all()]

        # Real model_call count: SUM properties->>'count' for today's events
        model_call_total = await self._db.scalar(
            select(func.sum(func.json_extract(TelemetryEvent.properties, "$.count"))).where(
                TelemetryEvent.event_type == "model_call",
                TelemetryEvent.created_at >= today_start,
            )
        )
        # Fallback: if no aggregated data, use COUNT(*)
        if not model_call_total:
            model_call_total = await self._db.scalar(
                select(func.count()).where(
                    TelemetryEvent.event_type == "model_call",
                    TelemetryEvent.created_at >= today_start,
                )
            )
        model_call_total = int(model_call_total or 0)

        trend_result = await self._db.execute(
            select(func.date(TelemetryEvent.created_at, "+8 hours"), func.count())
            .where(TelemetryEvent.created_at >= cutoff)
            .group_by(func.date(TelemetryEvent.created_at, "+8 hours"))
            .order_by(func.date(TelemetryEvent.created_at, "+8 hours"))
        )
        trend = [DailyTrend(date=str(row[0]), count=row[1]) for row in trend_result.all()]

        recent_result = await self._db.execute(
            select(TelemetryEvent).order_by(TelemetryEvent.created_at.desc()).limit(10)
        )
        recent = []
        for evt in recent_result.scalars().all():
            recent.append(
                {
                    "client_id": _mask_client_id(evt.client_id),
                    "event_type": evt.event_type,
                    "platform": evt.platform,
                    "app_version": evt.app_version,
                    "timestamp": str(evt.timestamp + timedelta(hours=8)),  # UTC → Beijing time
                }
            )

        # install success rate: app_start clients / download IPs (30-day window)
        from src.models.download import DownloadRecord

        app_start_clients = await self._db.scalar(
            select(func.count(func.distinct(TelemetryEvent.client_id))).where(
                TelemetryEvent.event_type == "app_start",
                TelemetryEvent.created_at >= cutoff,
                TelemetryEvent.client_id != "",
            )
        )
        download_ips = await self._db.scalar(
            select(func.count(func.distinct(DownloadRecord.ip_hash))).where(
                DownloadRecord.downloaded_at >= cutoff,
                DownloadRecord.ip_hash != "",
                DownloadRecord.package_name == "codex-switch",
            )
        )
        if download_ips and download_ips > 0:
            rate = round(app_start_clients / download_ips * 100)
            install_success_rate = f"{rate}%"
        else:
            install_success_rate = "—"

        # version insight: each client counted only under their LATEST version (30-day window)
        # Step 1: find each client's latest app_start
        latest_subq = (
            select(
                TelemetryEvent.client_id,
                func.max(TelemetryEvent.created_at).label("last_seen"),
            )
            .where(
                TelemetryEvent.event_type == "app_start",
                TelemetryEvent.created_at >= cutoff,
                TelemetryEvent.client_id != "",
                TelemetryEvent.app_version != "",
            )
            .group_by(TelemetryEvent.client_id)
        ).subquery()

        # Step 2: join back to get version+platform for the latest event
        version_result = await self._db.execute(
            select(
                TelemetryEvent.app_version,
                func.count().label("user_count"),
                func.max(TelemetryEvent.created_at).label("last_seen"),
            )
            .join(
                latest_subq,
                (TelemetryEvent.client_id == latest_subq.c.client_id)
                & (TelemetryEvent.created_at == latest_subq.c.last_seen),
            )
            .group_by(TelemetryEvent.app_version)
        )
        version_insight = sorted(
            (
                VersionItem(
                    version=row[0],
                    user_count=row[1],
                    event_count=row[1],
                    last_seen=str(row[2] + timedelta(hours=8)),
                )
                for row in version_result.all()
            ),
            key=lambda v: _parse_semver(v.version),
            reverse=True,
        )

        # latest version: check telemetry first, fall back to GitHub
        if version_insight:
            latest_version = version_insight[0].version
        else:
            from src.services.release_sync import _latest_cache

            latest_version = (_latest_cache or {}).get("version", "")

        # version coverage
        if version_insight and latest_version:
            latest_count = next((v.user_count for v in version_insight if v.version == latest_version), 0)
            total_users = sum(v.user_count for v in version_insight)
            coverage = round(latest_count / total_users * 100) if total_users > 0 else 0
            version_coverage = f"{coverage}%"
        else:
            version_coverage = "—"

        # OS insight: each client counted once (latest app_start only, same subquery)
        os_result = await self._db.execute(
            select(
                TelemetryEvent.platform,
                func.count().label("user_count"),
            )
            .join(
                latest_subq,
                (TelemetryEvent.client_id == latest_subq.c.client_id)
                & (TelemetryEvent.created_at == latest_subq.c.last_seen),
            )
            .where(TelemetryEvent.platform != "")
            .group_by(TelemetryEvent.platform)
        )
        platform_names = {"darwin": "Mac", "win32": "Windows"}
        os_rows = list(os_result.all())
        os_total_users = sum(row[1] for row in os_rows)
        os_insight = [
            OsItem(
                platform=row[0],
                platform_name=platform_names.get(row[0], row[0]),
                user_count=row[1],
                event_count=row[1],  # same as user_count after dedup
                percentage=f"{round(row[1] / os_total_users * 100)}%" if os_total_users > 0 else "0%",
            )
            for row in os_rows
        ]

        # Version × OS cross: each client counted once (latest app_start only)
        cross_result = await self._db.execute(
            select(
                TelemetryEvent.app_version,
                TelemetryEvent.platform,
                func.count().label("user_count"),
            )
            .join(
                latest_subq,
                (TelemetryEvent.client_id == latest_subq.c.client_id)
                & (TelemetryEvent.created_at == latest_subq.c.last_seen),
            )
            .where(
                TelemetryEvent.app_version != "",
                TelemetryEvent.platform != "",
            )
            .group_by(TelemetryEvent.app_version, TelemetryEvent.platform)
        )
        cross_map: dict[str, dict[str, int]] = {}
        for ver, plat, cnt in cross_result.all():
            cross_map.setdefault(ver, {})[plat] = cnt
        version_os_cross = sorted(
            (
                VersionOsItem(
                    version=ver,
                    mac_users=cross_map[ver].get("darwin", 0),
                    win_users=cross_map[ver].get("win32", 0),
                )
                for ver in cross_map
            ),
            key=lambda v: _parse_semver(v.version),
            reverse=True,
        )

        return TelemetryStats(
            total_events=total,
            today_events=today,
            active_users=active,
            model_call_total=model_call_total,
            install_success_rate=install_success_rate,
            latest_version=latest_version,
            version_coverage=version_coverage,
            version_insight=version_insight,
            os_insight=os_insight,
            version_os_cross=version_os_cross,
            event_type_counts=type_counts,
            daily_trend=trend,
            recent_events=recent,
        )


def _mask_client_id(client_id: str) -> str:
    if len(client_id) <= 6:
        return client_id + "***"
    return client_id[:6] + "***"

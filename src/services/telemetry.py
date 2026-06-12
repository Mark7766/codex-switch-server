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
    TelemetryPayload,
    TelemetryStats,
)

logger = logging.getLogger(__name__)

# Event types that need deduplication (same client_id+event_type+timestamp).
# High-frequency or one-shot events are excluded — dedup would be wasteful or incorrect.
_DEDUP_TYPES = frozenset({"app_start", "proxy_start", "proxy_error", "update_check"})


class TelemetryService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def ingest(self, payload: TelemetryPayload, max_per_client_per_minute: int = 60) -> IngestResult:
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

            record = TelemetryEvent(
                client_id=payload.client_id,
                event_type=evt.event_type,
                timestamp=evt.timestamp,
                properties=props,
                app_version=payload.app_version,
                platform=payload.platform,
                arch=payload.arch,
                os_version=payload.os_version,
            )
            self._db.add(record)
            accepted += 1

        await self._db.commit()
        logger.debug("Telemetry ingest: accepted=%d rejected=%d", accepted, rejected)
        return IngestResult(accepted=accepted, rejected=rejected)

    async def get_stats(self, range_days: int = 30) -> TelemetryStats:
        total = await self._db.scalar(select(func.count()).select_from(TelemetryEvent))
        total = total or 0

        today_start = datetime.now(UTC).replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
        today = await self._db.scalar(
            select(func.count()).select_from(TelemetryEvent).where(TelemetryEvent.created_at >= today_start)
        )
        today = today or 0

        cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=range_days)
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

        trend_result = await self._db.execute(
            select(func.date(TelemetryEvent.created_at), func.count())
            .where(TelemetryEvent.created_at >= cutoff)
            .group_by(func.date(TelemetryEvent.created_at))
            .order_by(func.date(TelemetryEvent.created_at))
        )
        trend = [DailyTrend(date=str(row[0]), count=row[1]) for row in trend_result.all()]

        recent_result = await self._db.execute(
            select(TelemetryEvent).order_by(TelemetryEvent.created_at.desc()).limit(20)
        )
        recent = []
        for evt in recent_result.scalars().all():
            recent.append(
                {
                    "client_id": _mask_client_id(evt.client_id),
                    "event_type": evt.event_type,
                    "platform": evt.platform,
                    "app_version": evt.app_version,
                    "timestamp": str(evt.timestamp),
                }
            )

        return TelemetryStats(
            total_events=total,
            today_events=today,
            active_users=active,
            event_type_counts=type_counts,
            daily_trend=trend,
            recent_events=recent,
        )


def _mask_client_id(client_id: str) -> str:
    if len(client_id) <= 6:
        return client_id + "***"
    return client_id[:6] + "***"

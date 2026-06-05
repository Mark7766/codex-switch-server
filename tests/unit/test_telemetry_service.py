from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.schemas.telemetry import TelemetryEventIn, TelemetryPayload
from src.services.telemetry import TelemetryService, _mask_client_id


def test_mask_client_id_short():
    assert _mask_client_id("abc") == "abc***"


def test_mask_client_id_long():
    assert _mask_client_id("abcdef123456") == "abcdef***"


@pytest.mark.asyncio
async def test_ingest_valid(db_session: AsyncSession):
    svc = TelemetryService(db_session)
    payload = TelemetryPayload(
        client_id="test1",
        app_version="1.4.0",
        platform="macos",
        events=[
            TelemetryEventIn(event_type="proxy_start", timestamp=datetime(2026, 6, 5, 10, 0, 0, tzinfo=UTC)),
            TelemetryEventIn(event_type="proxy_stop", timestamp=datetime(2026, 6, 5, 10, 1, 0, tzinfo=UTC)),
        ],
    )
    result = await svc.ingest(payload)
    assert result.accepted == 2
    assert result.rejected == 0


@pytest.mark.asyncio
async def test_ingest_invalid_type_rejected(db_session: AsyncSession):
    svc = TelemetryService(db_session)
    payload = TelemetryPayload(
        client_id="t1",
        events=[TelemetryEventIn(event_type="bad", timestamp=datetime(2026, 6, 5, 10, 0, 0, tzinfo=UTC))],
    )
    result = await svc.ingest(payload)
    assert result.accepted == 0
    assert result.rejected == 1


@pytest.mark.asyncio
async def test_ingest_dedup(db_session: AsyncSession):
    svc = TelemetryService(db_session)
    payload = TelemetryPayload(
        client_id="d1",
        events=[TelemetryEventIn(event_type="proxy_start", timestamp=datetime(2026, 6, 5, 10, 0, 0, tzinfo=UTC))],
    )
    r1 = await svc.ingest(payload)
    r2 = await svc.ingest(payload)
    assert r1.accepted == 1
    assert r2.rejected == 1


@pytest.mark.asyncio
async def test_get_stats_empty(db_session: AsyncSession):
    svc = TelemetryService(db_session)
    stats = await svc.get_stats()
    assert stats.total_events == 0
    assert stats.today_events == 0


@pytest.mark.asyncio
async def test_get_stats_with_data(db_session: AsyncSession):
    svc = TelemetryService(db_session)
    payload = TelemetryPayload(
        client_id="u1",
        events=[TelemetryEventIn(event_type="proxy_start", timestamp=datetime(2026, 6, 5, 10, 0, 0, tzinfo=UTC))],
    )
    await svc.ingest(payload)

    stats = await svc.get_stats(range_days=1)
    assert stats.total_events == 1
    assert stats.active_users == 1
    assert len(stats.event_type_counts) == 1
    assert stats.event_type_counts[0].event_type == "proxy_start"
    assert stats.event_type_counts[0].count == 1
    assert len(stats.recent_events) == 1
    assert stats.recent_events[0]["client_id"] == "u1***"

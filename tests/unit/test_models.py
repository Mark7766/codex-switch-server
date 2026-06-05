from __future__ import annotations

from datetime import UTC, date, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.release import Release


@pytest.mark.asyncio
async def test_release_creation(db_session: AsyncSession):
    release = Release(
        version="1.0.0",
        release_date=date(2026, 6, 5),
        release_notes="Initial release",
        is_critical=False,
        files=[{"platform": "macos", "arch": "arm64", "size": 100}],
    )
    db_session.add(release)
    await db_session.flush()

    assert release.id is not None
    assert release.version == "1.0.0"
    assert release.release_date == date(2026, 6, 5)
    assert release.is_critical is False
    assert len(release.files) == 1


@pytest.mark.asyncio
async def test_release_defaults(db_session: AsyncSession):
    release = Release(version="2.0.0", release_date=date(2026, 6, 5))
    db_session.add(release)
    await db_session.flush()

    assert release.release_notes == ""
    assert release.is_critical is False
    assert release.files == []
    assert isinstance(release.created_at, datetime)


@pytest.mark.asyncio
async def test_release_unique_version(db_session: AsyncSession):
    r1 = Release(version="1.0.0", release_date=date(2026, 6, 5))
    db_session.add(r1)
    await db_session.flush()

    r2 = Release(version="1.0.0", release_date=date(2026, 6, 5))
    db_session.add(r2)
    with pytest.raises(Exception):
        await db_session.flush()


@pytest.mark.asyncio
async def test_download_record_creation(db_session: AsyncSession):
    from src.models.download import DownloadRecord

    record = DownloadRecord(client_id="abc123", platform="macos", arch="arm64")
    db_session.add(record)
    await db_session.flush()

    assert record.id is not None
    assert record.client_id == "abc123"
    assert record.platform == "macos"
    assert record.arch == "arm64"
    assert record.package_name is None


@pytest.mark.asyncio
async def test_telemetry_event_creation(db_session: AsyncSession):
    from datetime import datetime

    from src.models.telemetry import TelemetryEvent

    event = TelemetryEvent(
        client_id="client1",
        event_type="proxy_start",
        timestamp=datetime(2026, 6, 5, 10, 0, 0, tzinfo=UTC),
        properties={"port": 11435},
        app_version="1.4.0",
        platform="macos",
        arch="arm64",
    )
    db_session.add(event)
    await db_session.flush()

    assert event.id is not None
    assert event.event_type == "proxy_start"
    assert event.properties == {"port": 11435}

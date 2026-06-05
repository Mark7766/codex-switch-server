from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.release import Release
from src.services.release_sync import ReleaseSyncService, _detect_platform, _parse_semver


def test_parse_semver():
    assert _parse_semver("1.2.3") == (1, 2, 3)
    assert _parse_semver("v2.0.0") == (2, 0, 0)
    assert _parse_semver("10.20.30") == (10, 20, 30)


def test_parse_semver_comparison():
    assert _parse_semver("1.4.0") > _parse_semver("1.3.0")
    assert _parse_semver("2.0.0") > _parse_semver("1.99.99")
    assert _parse_semver("1.0.0") == _parse_semver("1.0.0")


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("codex-switch-1.4.0-arm64.dmg", ("macos", "arm64", "dmg")),
        ("codex-switch-1.4.0-x64.dmg", ("macos", "x64", "dmg")),
        ("codex-switch-setup-1.4.0.exe", ("windows", "x64", "exe")),
        ("codex-switch-1.4.0-arm64.exe", ("windows", "arm64", "exe")),
        ("codex-switch-1.4.0.AppImage", ("linux", "x64", "appimage")),
        ("codex-switch-1.4.0-aarch64.AppImage", ("linux", "arm64", "appimage")),
    ],
)
def test_detect_platform(filename, expected):
    assert _detect_platform(filename) == expected


@pytest.mark.asyncio
async def test_check_update_with_release_present(db_session: AsyncSession):
    release = Release(
        version="2.0.0",
        release_date=date(2026, 6, 5),
        files=[{"platform": "macos", "arch": "arm64", "file_size": 100, "sha256": "abc", "path": ""}],
    )
    db_session.add(release)
    await db_session.flush()

    svc = ReleaseSyncService(db_session)
    result = await svc.check_for_updates("1.0.0", "macos", "arm64")
    assert result.has_update is True
    assert result.latest_version == "2.0.0"


@pytest.mark.asyncio
async def test_check_update_already_latest(db_session: AsyncSession):
    release = Release(version="1.0.0", release_date=date(2026, 6, 5))
    db_session.add(release)
    await db_session.flush()

    svc = ReleaseSyncService(db_session)
    result = await svc.check_for_updates("1.0.0", "macos", "arm64")
    assert result.has_update is False


@pytest.mark.asyncio
async def test_get_releases_paginated(db_session: AsyncSession):
    for i in range(5):
        db_session.add(Release(version=f"{i}.0.0", release_date=date(2026, 6, 1)))
    await db_session.flush()

    svc = ReleaseSyncService(db_session)
    releases = await svc.get_releases(limit=3)
    assert len(releases) == 3


@pytest.mark.asyncio
async def test_get_latest_release_empty(db_session: AsyncSession):
    svc = ReleaseSyncService(db_session)
    result = await svc.get_latest_release()
    assert result is None


def test_detect_platform_unknown():
    assert _detect_platform("README.md") == ("", "x64", "")


def test_semver_parse_invalid():
    with pytest.raises(ValueError):
        _parse_semver("not-a-version")


@pytest.mark.asyncio
async def test_record_download(db_session: AsyncSession):
    release = Release(version="1.0.0", release_date=date(2026, 6, 5))
    db_session.add(release)
    await db_session.flush()

    svc = ReleaseSyncService(db_session)
    await svc.record_download("1.0.0", "macos", "arm64", client_id="c1")

    stats = await svc.get_download_stats()
    assert stats.total_downloads == 1
    assert stats.active_users >= 0

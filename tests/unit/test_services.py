from __future__ import annotations

from datetime import date
from unittest.mock import AsyncMock, patch

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
        ("codex-switch-setup-1.4.0-win-x64.exe", ("windows", "x64", "exe")),
        ("codex-switch-1.4.0-arm64.exe", ("windows", "arm64", "exe")),
        ("codex-switch-1.4.0.AppImage", ("linux", "x64", "appimage")),
        ("codex-switch-1.4.0-aarch64.AppImage", ("linux", "arm64", "appimage")),
    ],
)
def test_detect_platform(filename, expected):
    assert _detect_platform(filename) == expected


def test_detect_platform_skips_blockmap_and_yml():
    assert _detect_platform("file.dmg.blockmap") == ("", "", "")
    assert _detect_platform("latest.yml") == ("", "", "")


def test_detect_platform_requires_arch_for_windows():
    # Windows exe without -x64 or -arm64 suffix is rejected
    assert _detect_platform("setup-1.0.0.exe") == ("", "", "")
    assert _detect_platform("Codex-Switch-Setup-1.4.0-win.exe") == ("", "", "")


def test_detect_platform_unknown():
    assert _detect_platform("README.md") == ("", "", "")


def test_semver_parse_invalid():
    with pytest.raises(ValueError):
        _parse_semver("not-a-version")


@pytest.mark.asyncio
async def test_check_update_no_releases_returns_no_update(db_session: AsyncSession):
    """When GitHub returns empty, has_update is False."""
    svc = ReleaseSyncService(db_session)
    with patch.object(svc, "get_latest_from_github", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"version": "", "files": []}
        result = await svc.check_for_updates("1.0.0", "macos", "arm64")
        assert result.has_update is False


@pytest.mark.asyncio
async def test_check_update_has_newer_version(db_session: AsyncSession):
    svc = ReleaseSyncService(db_session)
    with patch.object(svc, "get_latest_from_github", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {
            "version": "2.0.0",
            "release_date": "2026-06-05",
            "release_notes": "",
            "is_critical": False,
            "files": [{"platform": "macos", "arch": "arm64", "file_size": 100, "sha256": "", "download_url": ""}],
        }
        result = await svc.check_for_updates("1.0.0", "macos", "arm64")
        assert result.has_update is True
        assert result.latest_version == "2.0.0"


@pytest.mark.asyncio
async def test_check_update_already_latest(db_session: AsyncSession):
    svc = ReleaseSyncService(db_session)
    with patch.object(svc, "get_latest_from_github", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = {"version": "1.0.0", "files": []}
        result = await svc.check_for_updates("1.0.0", "macos", "arm64")
        assert result.has_update is False


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

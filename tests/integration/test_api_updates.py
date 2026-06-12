from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_latest_mac_yml_returns_yaml(client: AsyncClient, monkeypatch):
    """GET /api/v1/updates/latest-mac.yml returns yml content from GitHub."""
    fake_releases = [
        {
            "tag_name": "v1.5.0",
            "assets": [
                {"name": "latest-mac.yml", "browser_download_url": "https://example.com/latest-mac.yml"},
            ],
        }
    ]

    mock_http = AsyncMock()
    mock_http.get_json.return_value = fake_releases

    mock_client_ctx = AsyncMock()
    mock_resp = AsyncMock()
    mock_resp.text = "version: 1.5.0\nfiles:\n  - url: Codex-Switch-1.5.0-mac-arm64.zip\n"
    mock_resp.raise_for_status = AsyncMock()
    mock_client_ctx.get.return_value = mock_resp

    with patch("src.services.update_feed.HttpClient", return_value=mock_http):
        with patch("src.services.update_feed.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value = mock_client_ctx

            resp = await client.get("/api/v1/updates/latest-mac.yml")
            assert resp.status_code == 200
            assert "text/yaml" in resp.headers["content-type"]
            assert "version: 1.5.0" in resp.text


@pytest.mark.asyncio
async def test_latest_yml_returns_yaml(client: AsyncClient, monkeypatch):
    """GET /api/v1/updates/latest.yml returns yml content from GitHub."""
    fake_releases = [
        {
            "tag_name": "v1.5.0",
            "assets": [
                {"name": "latest.yml", "browser_download_url": "https://example.com/latest.yml"},
            ],
        }
    ]

    mock_http = AsyncMock()
    mock_http.get_json.return_value = fake_releases

    mock_client_ctx = AsyncMock()
    mock_resp = AsyncMock()
    mock_resp.text = "version: 1.5.0\nfiles:\n  - url: Codex-Switch-Setup-1.5.0-win-x64.exe\n"
    mock_resp.raise_for_status = AsyncMock()
    mock_client_ctx.get.return_value = mock_resp

    with patch("src.services.update_feed.HttpClient", return_value=mock_http):
        with patch("src.services.update_feed.httpx.AsyncClient") as mock_cls:
            mock_cls.return_value.__aenter__.return_value = mock_client_ctx

            resp = await client.get("/api/v1/updates/latest.yml")
            assert resp.status_code == 200
            assert "text/yaml" in resp.headers["content-type"]
            assert "version: 1.5.0" in resp.text


@pytest.mark.asyncio
async def test_download_updates_file_local_cache(client: AsyncClient, monkeypatch):
    """GET /api/v1/updates/{filename} returns X-Accel-Redirect for locally cached file."""
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_secret_id", "")
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_bucket", "")

    filename = "Codex-Switch-1.5.0-mac-arm64.zip"
    cache_dir = Path("data/codex-switch/1.5.0")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / filename
    cache_file.write_bytes(b"fake-zip-content-for-updates-test")

    try:
        resp = await client.get(f"/api/v1/updates/{filename}")
        assert resp.status_code == 200
        assert "x-accel-redirect" in resp.headers
        assert resp.headers["content-disposition"].startswith("attachment")
    finally:
        cache_file.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_download_updates_file_local_cache_win_setup(client: AsyncClient, monkeypatch):
    """GET /api/v1/updates/{filename} works for Windows Setup format."""
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_secret_id", "")
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_bucket", "")

    filename = "Codex-Switch-Setup-1.5.0-win-x64.exe"
    cache_dir = Path("data/codex-switch/1.5.0")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / filename
    cache_file.write_bytes(b"fake-exe-content")

    try:
        resp = await client.get(f"/api/v1/updates/{filename}")
        assert resp.status_code == 200
        assert "x-accel-redirect" in resp.headers
    finally:
        cache_file.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_download_updates_file_unsafe_filename_returns_404(client: AsyncClient):
    """Unsafe filenames (path traversal, strange chars) return 404."""
    unsafe_names = [
        "../latest-mac.yml",
        "Codex-Switch-1.5.0-mac-arm64.zip/../../../etc/passwd",
        "Codex-Switch-1.5.0-mac-arm64.zip; rm -rf /",
    ]
    for name in unsafe_names:
        resp = await client.get(f"/api/v1/updates/{name}")
        assert resp.status_code == 404, f"Expected 404 for filename: {name}"


@pytest.mark.asyncio
async def test_download_updates_file_invalid_format_returns_404(client: AsyncClient):
    """Filenames that don't match the expected pattern return 404."""
    resp = await client.get("/api/v1/updates/not-a-valid-release-file.exe")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_updates_file_nonexistent_returns_404(client: AsyncClient, monkeypatch):
    """Non-existent file returns 404 after exhausting all tiers."""
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_secret_id", "")
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_bucket", "")

    # Mock find_asset_by_filename to return None (file not on GitHub either)
    with patch.object(
        __import__("src.services.update_feed", fromlist=["UpdateFeedService"]).UpdateFeedService,
        "find_asset_by_filename",
        AsyncMock(return_value=None),
    ):
        resp = await client.get("/api/v1/updates/Codex-Switch-9.9.9-mac-arm64.zip")
        assert resp.status_code == 404


@pytest.mark.asyncio
async def test_download_updates_file_download_records_source(client: AsyncClient, db_session, monkeypatch):
    """Download via /updates/{filename} records download with source='electron-updater'."""
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_secret_id", "")
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_bucket", "")

    filename = "Codex-Switch-1.5.0-mac-arm64.zip"
    cache_dir = Path("data/codex-switch/1.5.0")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / filename
    cache_file.write_bytes(b"fake-content")

    try:
        resp = await client.get(f"/api/v1/updates/{filename}")
        assert resp.status_code == 200

        # Verify download record was created with source="electron-updater"
        from sqlalchemy import select

        from src.models.download import DownloadRecord

        result = await db_session.execute(select(DownloadRecord).where(DownloadRecord.source == "electron-updater"))
        records = result.scalars().all()
        assert len(records) >= 1
        assert records[0].source == "electron-updater"
        assert records[0].package_name == "codex-switch"
        assert records[0].platform == "macos"
        assert records[0].arch == "arm64"
    finally:
        cache_file.unlink(missing_ok=True)

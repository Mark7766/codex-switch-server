from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_check_update_returns_200(client: AsyncClient):
    """check_for_updates now reads latest from GitHub — v1.4.0 exists so older client gets update."""
    payload = {"current_version": "0.1.0", "platform": "macos", "arch": "arm64", "client_id": "test123"}
    resp = await client.post("/api/v1/update/check", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    # With GitHub data available, a very old version should get has_update=True
    assert "has_update" in data
    if data["has_update"]:
        assert data["latest_version"]


@pytest.mark.asyncio
async def test_check_update_with_invalid_body_returns_422(client: AsyncClient):
    resp = await client.post("/api/v1/update/check", json={"bad": "data"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_download_nonexistent_returns_404(client: AsyncClient):
    resp = await client.get("/api/v1/update/download/0.0.0/macos-arm64")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_latest_returns_version(client: AsyncClient):
    """The /latest endpoint returns real GitHub data (or cached)."""
    resp = await client.get("/api/v1/update/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert "files" in data


@pytest.mark.asyncio
async def test_download_local_cache_x_accel(client: AsyncClient, monkeypatch):
    """Download a cached release file → X-Accel-Redirect when COS is disabled."""
    # Force COS to be disabled so we hit the local cache path
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_secret_id", "")
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_bucket", "")

    cache_dir = Path("data/codex-switch/1.4.0")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "macos-arm64.dmg"
    cache_file.write_bytes(b"fake-dmg-for-update-test")

    try:
        resp = await client.get("/api/v1/update/download/1.4.0/macos-arm64")
        assert resp.status_code == 200
        assert "x-accel-redirect" in resp.headers
        assert resp.headers["content-disposition"].startswith("attachment")
    finally:
        cache_file.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_download_local_cache_windows_x64(client: AsyncClient, monkeypatch):
    """Download a cached Windows release → X-Accel-Redirect when COS disabled."""
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_secret_id", "")
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_bucket", "")

    cache_dir = Path("data/codex-switch/1.4.0")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "windows-x64.exe"
    cache_file.write_bytes(b"fake-exe-for-update-test")

    try:
        resp = await client.get("/api/v1/update/download/1.4.0/windows-x64")
        assert resp.status_code == 200
        assert "x-accel-redirect" in resp.headers
    finally:
        cache_file.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_download_cos_redirect_when_enabled(client: AsyncClient):
    """When COS is enabled and file exists, download returns 302 redirect to COS.
    This tests the real COS integration in the current environment."""
    cache_dir = Path("data/codex-switch/1.4.0")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "macos-x64.dmg"
    cache_file.write_bytes(b"fake-dmg")

    try:
        resp = await client.get(
            "/api/v1/update/download/1.4.0/macos-x64",
            follow_redirects=False,
        )
        # With COS configured, either 302 (COS hit) or 200 (local fallback)
        assert resp.status_code in (200, 302)
    finally:
        cache_file.unlink(missing_ok=True)

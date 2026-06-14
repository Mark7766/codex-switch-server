from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_plugin_pack_returns_metadata(client: AsyncClient):
    """GET /api/v1/plugins/pack returns pack info."""
    resp = await client.get("/api/v1/plugins/pack")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    pack = data["data"]
    assert pack["version"] == "1.0.0"
    assert pack["filename"] == "codex-offline-pack.tar.gz"
    assert pack["plugin_count"] == 173
    assert pack["size_mb"] == 36
    assert "download_url" in pack
    assert pack["download_url"] == "/api/v1/plugins/pack/download"


@pytest.mark.asyncio
async def test_get_plugin_pack_download_local_cache(client: AsyncClient, monkeypatch):
    """GET /api/v1/plugins/pack/download returns X-Accel-Redirect when file cached."""
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_secret_id", "")
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_bucket", "")

    from pathlib import Path

    cache_dir = Path("data/files")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "codex-offline-pack.tar.gz"
    cache_file.write_bytes(b"fake-plugin-pack")

    try:
        resp = await client.get("/api/v1/plugins/pack/download")
        assert resp.status_code == 200
        assert resp.headers["content-disposition"].startswith("attachment")
    finally:
        cache_file.unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_get_plugin_pack_download_not_found(client: AsyncClient, monkeypatch):
    """GET /api/v1/plugins/pack/download returns 404 when no file exists."""
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_secret_id", "")
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_bucket", "")

    # Ensure no cached file
    from pathlib import Path

    cache_file = Path("data/files/codex-offline-pack.tar.gz")
    if cache_file.exists():
        cache_file.unlink()

    resp = await client.get("/api/v1/plugins/pack/download")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_get_plugin_pack_download_records_tracking(client: AsyncClient, db_session, monkeypatch):
    """Download records download with package_name='codex-offline-pack'."""
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_secret_id", "")
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_bucket", "")

    from pathlib import Path

    from sqlalchemy import select

    from src.models.download import DownloadRecord

    cache_dir = Path("data/files")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_file = cache_dir / "codex-offline-pack.tar.gz"
    cache_file.write_bytes(b"fake-content")

    try:
        resp = await client.get("/api/v1/plugins/pack/download")
        assert resp.status_code == 200

        result = await db_session.execute(
            select(DownloadRecord).where(DownloadRecord.package_name == "codex-offline-pack")
        )
        records = result.scalars().all()
        assert len(records) >= 1
        assert records[0].package_name == "codex-offline-pack"
        assert records[0].source == "plugin-install"
    finally:
        cache_file.unlink(missing_ok=True)

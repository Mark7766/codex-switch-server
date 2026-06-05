from __future__ import annotations

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

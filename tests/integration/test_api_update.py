from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_check_update_no_releases_returns_no_update(client: AsyncClient):
    payload = {"current_version": "1.0.0", "platform": "macos", "arch": "arm64", "client_id": "test123"}
    resp = await client.post("/api/v1/update/check", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["has_update"] is False


@pytest.mark.asyncio
async def test_check_update_with_invalid_body_returns_422(client: AsyncClient):
    resp = await client.post("/api/v1/update/check", json={"bad": "data"})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_download_nonexistent_returns_404(client: AsyncClient):
    resp = await client.get("/api/v1/update/download/0.0.0/macos-arm64")
    assert resp.status_code == 404

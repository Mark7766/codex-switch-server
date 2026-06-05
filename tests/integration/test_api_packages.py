from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_packages_returns_200(client: AsyncClient):
    resp = await client.get("/api/v1/packages")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert len(data["data"]["packages"]) == 4


@pytest.mark.asyncio
async def test_list_packages_contains_expected_names(client: AsyncClient):
    resp = await client.get("/api/v1/packages")
    data = resp.json()
    names = [p["name"] for p in data["data"]["packages"]]
    assert "claude-desktop" in names
    assert "codex-desktop" in names
    assert "nodejs" in names
    assert "git" in names


@pytest.mark.asyncio
async def test_download_package_not_found_returns_404(client: AsyncClient):
    resp = await client.get("/api/v1/packages/unknown/1.0.0/macos-arm64")
    assert resp.status_code == 404

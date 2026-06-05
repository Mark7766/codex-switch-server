from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _login(client: AsyncClient) -> str:
    resp = await client.post("/admin/login", data={"token": "change-me"}, follow_redirects=False)
    return resp.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_packages_page_requires_auth(client: AsyncClient):
    resp = await client.get("/admin/packages")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_packages_page_with_auth(client: AsyncClient):
    cookie = await _login(client)
    resp = await client.get("/admin/packages", headers={"Cookie": cookie})
    assert resp.status_code == 200
    assert "安装包管理" in resp.text


@pytest.mark.asyncio
async def test_upload_without_auth_returns_401(client: AsyncClient):
    resp = await client.post("/admin/packages/upload")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_api_packages_returns_real_data(client: AsyncClient):
    resp = await client.get("/api/v1/packages")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "packages" in data["data"]

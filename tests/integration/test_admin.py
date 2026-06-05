from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_admin_login_page_returns_200(client: AsyncClient):
    resp = await client.get("/admin/login")
    assert resp.status_code == 200
    assert "管理员登录" in resp.text


@pytest.mark.asyncio
async def test_admin_dashboard_without_cookie_returns_401(client: AsyncClient):
    resp = await client.get("/admin")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_login_bad_token_returns_401(client: AsyncClient):
    resp = await client.post("/admin/login", data={"token": "wrong"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_admin_login_correct_token_redirects(client: AsyncClient):
    resp = await client.post("/admin/login", data={"token": "change-me"}, follow_redirects=False)
    assert resp.status_code == 302
    assert resp.headers["location"] == "/admin"


@pytest.mark.asyncio
async def test_admin_dashboard_with_valid_cookie(client: AsyncClient):
    login_resp = await client.post("/admin/login", data={"token": "change-me"}, follow_redirects=False)
    cookie = login_resp.headers.get("set-cookie", "")
    resp = await client.get("/admin", headers={"Cookie": cookie})
    assert resp.status_code == 200
    assert "运营后台" in resp.text


@pytest.mark.asyncio
async def test_admin_dashboard_contains_stats(client: AsyncClient):
    login_resp = await client.post("/admin/login", data={"token": "change-me"}, follow_redirects=False)
    cookie = login_resp.headers.get("set-cookie", "")
    resp = await client.get("/admin", headers={"Cookie": cookie})
    assert "总下载量" in resp.text
    assert "活跃用户" in resp.text

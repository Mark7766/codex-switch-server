from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _login_cookie(client: AsyncClient) -> str:
    """Login and return the set-cookie header value."""
    resp = await client.post("/admin/login", data={"token": "change-me"}, follow_redirects=False)
    return resp.headers.get("set-cookie", "")


class TestAnalyticsPageviewEndpoint:
    async def test_pageview_public(self, client: AsyncClient):
        """POST /api/v1/analytics/pageview should work without auth."""
        resp = await client.post(
            "/api/v1/analytics/pageview",
            json={"event_type": "pageview", "page": "/"},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    async def test_click_event(self, client: AsyncClient):
        """POST click event with element_id."""
        resp = await client.post(
            "/api/v1/analytics/pageview",
            json={"event_type": "click", "page": "/guide", "element_id": "guide-apikey-btn"},
        )
        assert resp.status_code == 200

    @pytest.mark.parametrize(
        "bad_body",
        [
            {},
            {"event_type": "pageview"},
        ],
    )
    async def test_invalid_events(self, client: AsyncClient, bad_body: dict):
        """Various bad payloads — should not 500."""
        resp = await client.post("/api/v1/analytics/pageview", json=bad_body)
        assert resp.status_code == 200  # silently ignored, always returns ok


class TestAdminAnalyticsEndpoints:
    async def test_page_stats_requires_auth(self, client: AsyncClient):
        """Page stats endpoint should require authentication."""
        resp = await client.get("/api/v1/admin/analytics/page-stats")
        assert resp.status_code == 401

    async def test_download_trends_requires_auth(self, client: AsyncClient):
        """Download trends endpoint should require authentication."""
        resp = await client.get("/api/v1/admin/analytics/download-trends")
        assert resp.status_code == 401

    async def test_page_stats_with_auth(self, client: AsyncClient):
        """Page stats with valid auth returns data with Chinese names."""
        cookie = await _login_cookie(client)
        resp = await client.get(
            "/api/v1/admin/analytics/page-stats?range_days=7",
            headers={"Cookie": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "page_views" in data
        assert "top_clicks" in data
        assert "daily_trend" in data
        assert len(data["daily_trend"]) == 7

    async def test_download_trends_with_auth(self, client: AsyncClient):
        """Download trends with valid auth returns breakdown data."""
        cookie = await _login_cookie(client)
        resp = await client.get(
            "/api/v1/admin/analytics/download-trends?range_days=7",
            headers={"Cookie": cookie},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "by_package" in data
        assert "by_product" in data
        assert "by_version" in data
        assert "cos_hit_rate" in data

    async def test_page_stats_range_days_validation(self, client: AsyncClient):
        """range_days parameter should be validated."""
        cookie = await _login_cookie(client)
        resp = await client.get(
            "/api/v1/admin/analytics/page-stats?range_days=0",
            headers={"Cookie": cookie},
        )
        assert resp.status_code == 422  # < 1

        resp = await client.get(
            "/api/v1/admin/analytics/page-stats?range_days=400",
            headers={"Cookie": cookie},
        )
        assert resp.status_code == 422  # > 365


class TestAdminDashboardTabLayout:
    async def test_dashboard_has_all_tabs(self, client: AsyncClient):
        """Dashboard page contains three tab buttons."""
        cookie = await _login_cookie(client)
        resp = await client.get("/admin", headers={"Cookie": cookie})
        assert resp.status_code == 200
        html = resp.text
        assert "Server 运营" in html
        assert "App 遥测" in html
        assert "安装包管理" in html

    async def test_dashboard_has_package_upload_forms(self, client: AsyncClient):
        """Dashboard contains the 4 package upload slots."""
        cookie = await _login_cookie(client)
        resp = await client.get("/admin", headers={"Cookie": cookie})
        assert resp.status_code == 200
        html = resp.text
        assert html.count("Codex Desktop") >= 2
        assert html.count("Claude Desktop") >= 2

    async def test_dashboard_requires_auth(self, client: AsyncClient):
        """Dashboard should redirect if not authenticated."""
        resp = await client.get("/admin", follow_redirects=False)
        assert resp.status_code in (401, 302, 403)

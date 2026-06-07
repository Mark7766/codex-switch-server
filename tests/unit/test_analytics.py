from __future__ import annotations

from sqlalchemy import func, select

from src.models.page_event import PageEvent
from src.schemas.analytics import (
    PageviewRequest,
    get_element_info,
    get_page_name,
    get_platform_name,
    get_product_name,
)
from src.services.analytics import AnalyticsService


class TestChineseMappings:
    """Verify all Chinese mapping functions return correct values."""

    def test_page_name_map_known(self):
        assert get_page_name("/") == "首页"
        assert get_page_name("/download") == "下载页"
        assert get_page_name("/guide") == "使用指南"

    def test_page_name_map_unknown(self):
        assert get_page_name("/unknown") == "/unknown"

    def test_element_info_known(self):
        name, page = get_element_info("hero-guide-cta")
        assert name == "Hero区-查看安装指南按钮"
        assert page == "首页"

    def test_element_info_click_with_page(self):
        name, page = get_element_info("nav-download")
        assert name == "导航栏-下载链接"
        assert page == "全局"

    def test_element_info_unknown(self):
        name, page = get_element_info("nonexistent-id")
        assert name == "nonexistent-id"
        assert page == "未知"

    def test_product_name_known(self):
        assert get_product_name("codex-switch") == "Codex Switch"
        assert get_product_name("codex-desktop") == "Codex Desktop"
        assert get_product_name("claude-desktop") == "Claude Desktop"

    def test_product_name_unknown(self):
        assert get_product_name("unknown-app") == "unknown-app"

    def test_platform_name_known(self):
        assert get_platform_name("macos", "arm64") == "macOS Apple Silicon"
        assert get_platform_name("macos", "x64") == "macOS Intel"
        assert get_platform_name("windows", "arm64") == "Windows ARM64"
        assert get_platform_name("windows", "x64") == "Windows x64"

    def test_platform_name_unknown(self):
        assert get_platform_name("linux", "x64") == "linux x64"

    def test_all_element_ids_have_mappings(self):
        """Smoke test: ensure no KeyError for all mapped keys."""
        from src.schemas.analytics import ELEMENT_NAME_MAP

        for element_id in ELEMENT_NAME_MAP:
            name, page = get_element_info(element_id)
            assert name != element_id  # should have a Chinese name
            assert page != ""


class TestPageviewRequest:
    def test_valid_pageview(self):
        req = PageviewRequest(event_type="pageview", page="/")
        assert req.event_type == "pageview"
        assert req.page == "/"
        assert req.element_id == ""

    def test_valid_click(self):
        req = PageviewRequest(event_type="click", page="/guide", element_id="guide-apikey-btn")
        assert req.event_type == "click"
        assert req.element_id == "guide-apikey-btn"


class TestPageEventModel:
    async def test_create_pageview(self, db_session):
        evt = PageEvent(event_type="pageview", page="/")
        db_session.add(evt)
        await db_session.commit()

        count = await db_session.scalar(select(func.count()).select_from(PageEvent))
        assert count == 1

    async def test_create_click(self, db_session):
        evt = PageEvent(event_type="click", page="/download", element_id="dl-btn-macos-arm64")
        db_session.add(evt)
        await db_session.commit()

        result = await db_session.execute(select(PageEvent).where(PageEvent.event_type == "click"))
        row = result.scalar_one()
        assert row.element_id == "dl-btn-macos-arm64"
        assert row.page == "/download"

    async def test_ip_hash_generation(self, db_session):
        evt = PageEvent(event_type="pageview", page="/")
        db_session.add(evt)
        await db_session.commit()
        assert evt.ip_hash == ""  # default empty when not set


class TestAnalyticsService:
    async def test_record_pageview(self, db_session):
        svc = AnalyticsService(db_session)
        req = PageviewRequest(event_type="pageview", page="/guide")
        await svc.record_page_event(req, ip="1.2.3.4", ua="TestAgent")

        count = await db_session.scalar(select(func.count()).select_from(PageEvent))
        assert count == 1

    async def test_record_click(self, db_session):
        svc = AnalyticsService(db_session)
        req = PageviewRequest(event_type="click", page="/", element_id="hero-guide-cta")
        await svc.record_page_event(req)

        result = await db_session.execute(select(PageEvent).where(PageEvent.event_type == "click"))
        evt = result.scalar_one()
        assert evt.element_id == "hero-guide-cta"

    async def test_get_page_stats_empty(self, db_session):
        svc = AnalyticsService(db_session)
        stats = await svc.get_page_stats(range_days=7)
        assert stats.page_views == []
        assert stats.top_clicks == []
        assert len(stats.daily_trend) == 7

    async def test_get_page_stats_with_data(self, db_session):
        svc = AnalyticsService(db_session)
        # Record some pageviews
        for _ in range(3):
            await svc.record_page_event(PageviewRequest(event_type="pageview", page="/"))
        for _ in range(2):
            await svc.record_page_event(PageviewRequest(event_type="pageview", page="/guide"))
        await svc.record_page_event(PageviewRequest(event_type="click", page="/", element_id="hero-guide-cta"))

        stats = await svc.get_page_stats(range_days=7)
        assert len(stats.page_views) == 2
        # / should be first (more visits)
        assert stats.page_views[0].page == "/"
        assert stats.page_views[0].page_name == "首页"
        assert stats.page_views[0].count == 3
        assert len(stats.top_clicks) == 1
        assert stats.top_clicks[0].element_name == "Hero区-查看安装指南按钮"

    async def test_get_download_trends_empty(self, db_session):
        svc = AnalyticsService(db_session)
        trends = await svc.get_download_trends(range_days=7)
        assert trends.total == 0
        assert trends.today == 0
        assert trends.by_package == []
        assert len(trends.daily) == 7

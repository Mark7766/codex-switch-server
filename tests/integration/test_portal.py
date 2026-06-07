from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_index_returns_200(client: AsyncClient):
    response = await client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_index_contains_hero_title(client: AsyncClient):
    response = await client.get("/")
    assert "让 AI 编程触手可及" in response.text


@pytest.mark.asyncio
async def test_index_contains_feature_cards(client: AsyncClient):
    response = await client.get("/")
    assert "一键接入" in response.text
    assert "多模型支持" in response.text
    assert "本地安全" in response.text


@pytest.mark.asyncio
async def test_index_contains_download_cta(client: AsyncClient):
    response = await client.get("/")
    assert "/download" in response.text


@pytest.mark.asyncio
async def test_download_returns_200(client: AsyncClient):
    response = await client.get("/download")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_download_contains_platform_segments(client: AsyncClient):
    response = await client.get("/download")
    assert "macOS" in response.text
    assert "Windows" in response.text
    assert "Linux" in response.text


@pytest.mark.asyncio
async def test_download_contains_version(client: AsyncClient):
    response = await client.get("/download")
    assert "加载中" in response.text or "v" in response.text


@pytest.mark.asyncio
async def test_download_contains_requirements(client: AsyncClient):
    response = await client.get("/download")
    assert "系统要求" in response.text


@pytest.mark.asyncio
async def test_guide_returns_200(client: AsyncClient):
    response = await client.get("/guide")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


@pytest.mark.asyncio
async def test_guide_contains_all_steps(client: AsyncClient):
    response = await client.get("/guide")
    assert "获取 DeepSeek API Key" in response.text
    assert "Codex Desktop" in response.text
    assert "Claude Desktop" in response.text
    assert "Codex CLI" in response.text
    assert "Claude Code CLI" in response.text
    assert "常见问题" in response.text
    assert "pickTool" in response.text
    assert "pickPlatform" in response.text
    assert "renderGuide" in response.text


@pytest.mark.asyncio
async def test_guide_contains_nav_links(client: AsyncClient):
    response = await client.get("/guide")
    assert "你要安装哪个工具" in response.text
    assert "screen-tool" in response.text
    assert "screen-platform" in response.text
    assert "screen-guide" in response.text


@pytest.mark.asyncio
async def test_template_inheritance_base_structure(client: AsyncClient):
    response = await client.get("/")
    assert "<!DOCTYPE html>" in response.text
    assert '<html lang="zh-CN"' in response.text
    assert '<nav class="nav"' in response.text
    assert '<footer class="footer"' in response.text


@pytest.mark.asyncio
async def test_all_pages_share_nav(client: AsyncClient):
    urls = ["/", "/download", "/guide"]
    for url in urls:
        response = await client.get(url)
        assert "Codex Switch" in response.text
        assert 'href="/download"' in response.text
        assert 'href="/guide"' in response.text


@pytest.mark.asyncio
async def test_nonexistent_page_returns_404(client: AsyncClient):
    response = await client.get("/nonexistent")
    assert response.status_code == 404

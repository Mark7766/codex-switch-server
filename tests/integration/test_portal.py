from __future__ import annotations

import pytest
from httpx import AsyncClient
from markupsafe import Markup

TOOL_DOC_URLS = ["/tools/codex-switch", "/tools/ai-coding-ok", "/tools/ai-working-ok"]

# 「本地代理」时代的字样：门户四页不得再出现（v3.0.0 对齐护栏，背景见项目记忆）
STALE_COPY_URLS = ["/", "/download", "/guide", "/tools/codex-switch"]
STALE_TOKENS = ["代理", "11435", "Agnes", "deepseek-chat", "deepseek-reasoner", "173", "Windows 11"]


@pytest.fixture(autouse=True)
def _stub_tool_changelog(monkeypatch):
    """Keep doc-page tests hermetic: stub the GitHub-backed changelog fetch."""

    async def _fake_get_changelog(self, tool):
        return [
            {
                "version": "2.1.0",
                "date": "2026-09-06",
                "html": Markup("<h3>重磅新增</h3><ul><li>Codex 可以看图</li></ul>"),
                "is_first": True,
            },
            {
                "version": "2.0.0",
                "date": "2026-08-19",
                "html": Markup("<h3>核心变更</h3><p>Codex 直连 DeepSeek。</p>"),
                "is_first": False,
            },
        ]

    monkeypatch.setattr("src.services.tool_changelog.ToolChangelogService.get_changelog", _fake_get_changelog)


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
    assert "Mac" in response.text
    assert "Windows" in response.text
    assert "dl-cards" in response.text  # new side-by-side card layout


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
async def test_index_no_ai_working_ok_direct_link(client: AsyncClient):
    response = await client.get("/")
    assert "AI Working OK" not in response.text


@pytest.mark.asyncio
async def test_tool_ai_coding_ok_returns_200(client: AsyncClient):
    response = await client.get("/tools/ai-coding-ok")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "快速开始" in response.text


@pytest.mark.asyncio
async def test_tool_ai_coding_ok_content(client: AsyncClient):
    response = await client.get("/tools/ai-coding-ok")
    assert "install.sh --claude-code" in response.text
    assert "scripts/verify.sh" in response.text
    assert 'id="sec-memory"' in response.text
    assert 'href="https://github.com/Mark7766/ai-coding-ok"' in response.text


@pytest.mark.asyncio
async def test_tool_ai_working_ok_returns_200(client: AsyncClient):
    response = await client.get("/tools/ai-working-ok")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "快速开始" in response.text


@pytest.mark.asyncio
async def test_tool_ai_working_ok_content(client: AsyncClient):
    response = await client.get("/tools/ai-working-ok")
    assert "安装 https://github.com/Mark7766/ai-working-ok/releases/latest" in response.text
    assert 'href="/api/v1/packages/ai-working-ok/latest"' in response.text
    assert 'id="sec-memory"' in response.text
    assert 'href="https://github.com/Mark7766/ai-working-ok"' in response.text


@pytest.mark.asyncio
async def test_tool_codex_switch_returns_200(client: AsyncClient):
    response = await client.get("/tools/codex-switch")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "快速开始" in response.text


@pytest.mark.asyncio
async def test_tool_codex_switch_content(client: AsyncClient):
    response = await client.get("/tools/codex-switch")
    assert "让 AI 编程触手可及" in response.text
    assert 'id="sec-key"' in response.text
    assert 'id="sec-memory"' not in response.text  # Codex Switch 无三层记忆章节
    assert 'href="/download"' in response.text
    assert 'href="/guide"' in response.text
    assert 'href="https://github.com/Mark7766/codex-switch"' in response.text


@pytest.mark.asyncio
async def test_tools_dropdown_links_in_shared_nav(client: AsyncClient):
    response = await client.get("/download")
    assert 'href="/tools/codex-switch"' in response.text
    assert 'href="/tools/ai-coding-ok"' in response.text
    assert 'href="/tools/ai-working-ok"' in response.text
    assert "nav-tools" in response.text


@pytest.mark.asyncio
async def test_old_tools_hub_removed(client: AsyncClient):
    response = await client.get("/tools")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_geo_artifacts_include_tool_docs(client: AsyncClient):
    sitemap = await client.get("/sitemap.xml")
    assert "/tools/ai-coding-ok" in sitemap.text
    assert "/tools/ai-working-ok" in sitemap.text
    assert "/tools/codex-switch" in sitemap.text
    llms = await client.get("/llms.txt")
    assert "/tools/ai-coding-ok" in llms.text
    assert "/tools/ai-working-ok" in llms.text
    assert "/tools/codex-switch" in llms.text
    robots = await client.get("/robots.txt")
    assert "Allow: /tools" in robots.text


@pytest.mark.asyncio
async def test_template_inheritance_base_structure(client: AsyncClient):
    response = await client.get("/")
    assert "<!DOCTYPE html>" in response.text
    assert '<html lang="zh-CN"' in response.text
    assert '<nav class="nav"' in response.text
    assert '<footer class="footer"' in response.text


@pytest.mark.asyncio
async def test_all_pages_share_nav(client: AsyncClient):
    urls = [
        "/",
        "/download",
        "/guide",
        "/support",
        "/tools/codex-switch",
        "/tools/ai-coding-ok",
        "/tools/ai-working-ok",
    ]
    for url in urls:
        response = await client.get(url)
        assert "Codex Switch" in response.text
        assert 'href="/download"' in response.text
        assert 'href="/guide"' in response.text
        assert 'href="/tools/codex-switch"' in response.text
        assert 'href="/tools/ai-coding-ok"' in response.text
        assert 'href="/tools/ai-working-ok"' in response.text


@pytest.mark.asyncio
async def test_nonexistent_page_returns_404(client: AsyncClient):
    response = await client.get("/nonexistent")
    assert response.status_code == 404


@pytest.mark.asyncio
@pytest.mark.parametrize("url", TOOL_DOC_URLS)
async def test_tool_doc_has_changelog_section(client: AsyncClient, url: str):
    response = await client.get(url)
    assert response.status_code == 200
    # 左侧目录 / 移动端 chips 锚点 + 正文 section
    assert 'href="#sec-changelog"' in response.text
    assert 'id="sec-changelog"' in response.text
    assert "更新日志" in response.text
    # 条目渲染：最新默认展开带「最新」，历史 <details> 折叠
    assert '<details class="changelog__entry"' in response.text
    assert "changelog__latest" in response.text
    assert "最新" in response.text
    assert "Codex 可以看图" in response.text  # 罐头最新条目正文
    assert "changelog__body" in response.text


@pytest.mark.asyncio
async def test_tool_doc_changelog_graceful_when_fetch_fails(client: AsyncClient, monkeypatch):
    """GitHub 不可达时文档页降级：仍 200 + 显示获取失败提示，而不是 500。"""

    async def _boom(self, tool):
        raise RuntimeError("github down")

    monkeypatch.setattr("src.services.tool_changelog.ToolChangelogService.get_changelog", _boom)
    response = await client.get("/tools/codex-switch")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "更新日志暂时无法获取" in response.text


# ═══════════════════════════════════════════════════════════════
# v3.0.0 对齐护栏（客户端已从「代理工具」转为「纯配置工具」）
# ═══════════════════════════════════════════════════════════════


@pytest.mark.asyncio
@pytest.mark.parametrize("url", STALE_COPY_URLS)
async def test_portal_page_has_no_stale_proxy_copy(client: AsyncClient, url: str):
    """门户四页不得再出现「本地代理」时代的字样（反向断言护栏）。"""
    response = await client.get(url)
    assert response.status_code == 200
    for token in STALE_TOKENS:
        assert token not in response.text, f"{url} 仍含过时字样：{token}"


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["/", "/download", "/tools/codex-switch"])
async def test_portal_page_mentions_current_suppliers(client: AsyncClient, url: str):
    """三家供应商（DeepSeek / 智谱 GLM / 自定义）都要能对上。"""
    response = await client.get(url)
    assert "DeepSeek" in response.text
    assert "智谱 GLM" in response.text
    assert "自定义" in response.text


@pytest.mark.asyncio
async def test_guide_points_at_current_client_ui(client: AsyncClient):
    """指南必须指向 v3.0.0 的真实界面（设置 / 保存并应用 / 工具接入状态）。"""
    response = await client.get("/guide")
    assert "保存并应用" in response.text
    assert "工具接入状态" in response.text
    assert "供应商设置" in response.text
    assert "CLI 管理" not in response.text


@pytest.mark.asyncio
async def test_guide_claude_core_version_consistent(client: AsyncClient):
    """Claude Desktop 虚拟机核心的版本号：目录路径与下载链接必须一致。"""
    response = await client.get("/guide")
    assert "/api/v1/files/2.1.138.zip" in response.text
    assert "2.1.142" not in response.text


@pytest.mark.asyncio
async def test_download_system_requirements_current(client: AsyncClient):
    response = await client.get("/download")
    assert "Windows 10" in response.text
    assert "macOS 11.0 及以上" in response.text
    assert "Apple 芯片 / Intel 芯片" in response.text


@pytest.mark.asyncio
async def test_support_page_returns_200(client: AsyncClient):
    response = await client.get("/support")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "技术支持" in response.text
    assert "github.com/Mark7766/codex-switch/issues" in response.text


@pytest.mark.asyncio
async def test_geo_artifacts_consistent(client: AsyncClient):
    """robots / sitemap / llms 三处页面清单必须一致，且不再声明不存在的 /faq。"""
    robots = await client.get("/robots.txt")
    assert "Allow: /support" in robots.text
    assert "/faq" not in robots.text

    sitemap = await client.get("/sitemap.xml")
    assert "/support" in sitemap.text

    llms = await client.get("/llms.txt")
    assert "/support" in llms.text


@pytest.mark.asyncio
async def test_llms_txt_reflects_current_product(client: AsyncClient):
    llms = await client.get("/llms.txt")
    for token in ["Agnes", "本地 HTTP 代理", "deepseek-chat", "deepseek-reasoner", "完成并启动代理"]:
        assert token not in llms.text, f"llms.txt 仍含过时内容：{token}"
    assert "智谱 GLM" in llms.text
    assert "deepseek-flash" in llms.text
    assert "保存并应用" in llms.text


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["/", "/download", "/guide", "/support"])
async def test_pages_have_canonical_and_current_og_domain(client: AsyncClient, url: str):
    response = await client.get(url)
    assert 'rel="canonical"' in response.text
    assert "codexswtich" not in response.text  # 旧域名（缺连字符）不得残留
    assert 'property="og:url" content="https://codex-switch.cloud"' in response.text


@pytest.mark.asyncio
async def test_no_baidu_verification_placeholder(client: AsyncClient):
    """百度站长验证码未配置时应整段省略，而不是留一个假占位符。"""
    response = await client.get("/")
    assert "codeva-xxxxxxxxxx" not in response.text


@pytest.mark.asyncio
async def test_footer_links_to_support(client: AsyncClient):
    response = await client.get("/")
    assert 'href="/support"' in response.text

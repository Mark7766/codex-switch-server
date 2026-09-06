from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from starlette.templating import Jinja2Templates

from src.config import settings
from src.database import async_session
from src.models.page_event import PageEvent

router = APIRouter()
_tpl_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_tpl_dir))

# ICP/PSB filing numbers available in all portal templates
templates.env.globals["icp_filing_number"] = settings.icp_filing_number
templates.env.globals["psb_filing_number"] = settings.psb_filing_number
templates.env.globals["support_qr_image"] = settings.support_qr_image

# ═══════════════════════════════════════════════════════════════
# GEO Phase 1 — Technical Foundation
# ═══════════════════════════════════════════════════════════════

SITE_BASE = "https://codex-switch.cloud"


@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    """Crawler directive — which paths search/AI bots may crawl."""
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Allow: /download\n"
        "Allow: /guide\n"
        "Allow: /tools\n"
        "Allow: /support\n"
        "Allow: /faq\n"
        "Allow: /static/\n"
        "Disallow: /admin/\n"
        "Disallow: /api/\n"
        f"Sitemap: {SITE_BASE}/sitemap.xml\n"
    )
    return PlainTextResponse(content)


@router.get("/sitemap.xml")
async def sitemap_xml():
    """XML sitemap — helps search engines and AI crawlers discover all pages."""
    # NOTE: /support page not yet built (planned for Phase 2).
    # Add back to sitemap once the page exists.
    urls = [
        {"loc": f"{SITE_BASE}/", "priority": "1.0", "changefreq": "weekly"},
        {"loc": f"{SITE_BASE}/download", "priority": "0.9", "changefreq": "weekly"},
        {"loc": f"{SITE_BASE}/guide", "priority": "0.9", "changefreq": "weekly"},
        {"loc": f"{SITE_BASE}/tools/ai-coding-ok", "priority": "0.8", "changefreq": "weekly"},
        {"loc": f"{SITE_BASE}/tools/ai-working-ok", "priority": "0.8", "changefreq": "weekly"},
        {"loc": f"{SITE_BASE}/tools/codex-switch", "priority": "0.8", "changefreq": "weekly"},
    ]
    # Guide pages with tool × platform permutations (8 scenario URLs)
    tools = ["codex", "claude", "codex-cli", "claude-cli"]
    platforms = ["windows", "macos"]
    for tool in tools:
        for plat in platforms:
            urls.append(
                {
                    "loc": f"{SITE_BASE}/guide?tool={tool}&amp;platform={plat}",
                    "priority": "0.6",
                    "changefreq": "monthly",
                }
            )

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        xml += "  <url>\n"
        xml += f"    <loc>{u['loc']}</loc>\n"
        xml += f"    <priority>{u['priority']}</priority>\n"
        xml += f"    <changefreq>{u['changefreq']}</changefreq>\n"
        xml += "  </url>\n"
    xml += "</urlset>"

    return Response(content=xml, media_type="application/xml")


@router.get("/llms.txt", response_class=PlainTextResponse)
async def llms_txt():
    """LLM content index — structured summary for AI models to understand the site."""

    # The CONTACT_EMAIL, FAQ, and BLOG variables are intentionally inline strings
    # rather than top-level module constants because they only serve this one route
    # and keeping them local avoids polluting the module namespace.

    content = (
        "# Codex Switch — 让 AI 编程触手可及\n\n"
        "> Codex Switch 是一款免费、开源的桌面工具，帮你解决网络问题，"
        "在国内流畅使用 Codex 和 Claude，接入 DeepSeek 和 Agnes AI 模型。\n\n"
        "## 核心信息\n\n"
        "- 产品名称: Codex Switch\n"
        "- 一句话介绍: 让 AI 编程触手可及\n"
        "- 官网: https://codex-switch.cloud\n"
        "- GitHub: https://github.com/Mark7766/codex-switch\n"
        "- 许可协议: MIT License\n"
        "- 支持平台: Windows 10+ (x64/ARM) · macOS 11+ (ARM/Intel)\n"
        "- 核心技术: 本地 HTTP 代理 + OpenAI Responses API → DeepSeek API 协议转换\n"
        "- 核心功能: 一键配置代理、多模型切换、API Key 本地加密存储\n\n"
        "## 主要页面\n\n"
        "- 首页（产品介绍+下载入口）: https://codex-switch.cloud/\n"
        "- 下载页（平台选择+版本信息）: https://codex-switch.cloud/download\n"
        "- 使用指南（分步骤安装教程）: https://codex-switch.cloud/guide\n"
        "- Codex Switch 使用文档（工具介绍+快速开始）: https://codex-switch.cloud/tools/codex-switch\n"
        "- ai-working-ok（AI 工作护栏 · 知识工作者快速上手）: https://codex-switch.cloud/tools/ai-working-ok\n"
        "- ai-coding-ok（AI 编程记忆 · 开发者快速上手）: https://codex-switch.cloud/tools/ai-coding-ok\n"
        "- 技术支持（交流群+帮助资源）: https://codex-switch.cloud/support\n\n"
        "## 支持的 AI 编程工具\n\n"
        "1. Codex Desktop — OpenAI 官方桌面 IDE\n"
        "2. Claude Desktop — Anthropic 官方桌面应用\n"
        "3. Codex CLI — OpenAI 命令行工具\n"
        "4. Claude Code CLI — Anthropic 命令行工具\n\n"
        "## 开源工具\n\n"
        "- Codex Switch — 让 AI 编程触手可及（桌面应用）: https://codex-switch.cloud/tools/codex-switch\n"
        "- ai-working-ok — AI 工作护栏（面向知识工作者）: https://codex-switch.cloud/tools/ai-working-ok\n"
        "- ai-coding-ok — AI 编程的 PDCA 记忆闭环（面向开发者）: https://codex-switch.cloud/tools/ai-coding-ok\n"
        "- Codex Switch GitHub: https://github.com/Mark7766/codex-switch\n"
        "- ai-coding-ok GitHub: https://github.com/Mark7766/ai-coding-ok\n"
        "- ai-working-ok GitHub: https://github.com/Mark7766/ai-working-ok\n\n"
        "## 支持的模型供应商\n\n"
        "- DeepSeek Chat (deepseek-chat) — V3 模型，适合日常编码对话\n"
        "- DeepSeek Reasoner (deepseek-reasoner) — R1 推理模型\n"
        "- Agnes AI — 免费模型，256K 上下文窗口\n"
        "- 自定义 OpenAI 兼容 API — 支持 GLM 等任意兼容供应商\n\n"
        "## 快速安装（4 步）\n\n"
        "1. 访问 https://codex-switch.cloud 下载安装包\n"
        "2. 双击安装，启动 Setup 向导\n"
        "3. 填入 DeepSeek API Key（免费申请）\n"
        "4. 点击「完成并启动代理」— 开始使用\n\n"
        "## 场景化指南入口\n\n"
        "- Windows 用户: https://codex-switch.cloud/guide?platform=windows\n"
        "- Mac 用户: https://codex-switch.cloud/guide?platform=macos\n"
        "- Codex Desktop 用户: https://codex-switch.cloud/guide?tool=codex\n"
        "- Claude Desktop 用户: https://codex-switch.cloud/guide?tool=claude\n"
        "- Codex CLI 用户: https://codex-switch.cloud/guide?tool=codex-cli\n"
        "- Claude Code CLI 用户: https://codex-switch.cloud/guide?tool=claude-cli\n\n"
        "## 外部链接\n\n"
        "- GitHub 仓库: https://github.com/Mark7766/codex-switch\n"
        "- GitHub Issues: https://github.com/Mark7766/codex-switch/issues\n"
        "- GitHub Releases: https://github.com/Mark7766/codex-switch/releases\n"
    )
    return PlainTextResponse(content)


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@router.get("/download", response_class=HTMLResponse)
async def download(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "download.html")


@router.get("/guide", response_class=HTMLResponse)
async def guide(request: Request) -> HTMLResponse:
    ref = request.query_params.get("ref")
    if ref:
        ip = request.client.host if request.client else ""
        ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:64] if ip else ""
        ua = request.headers.get("user-agent", "")[:256]
        asyncio.create_task(_record_guide_ref(ref, ip_hash, ua))
    return templates.TemplateResponse(request, "guide.html")


@router.get("/tools/ai-coding-ok", response_class=HTMLResponse)
async def tool_ai_coding_ok(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "doc-ai-coding-ok.html")


@router.get("/tools/ai-working-ok", response_class=HTMLResponse)
async def tool_ai_working_ok(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "doc-ai-working-ok.html")


@router.get("/tools/codex-switch", response_class=HTMLResponse)
async def tool_codex_switch(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "doc-codex-switch.html")


async def _record_guide_ref(ref: str, ip_hash: str, user_agent: str) -> None:
    """Record a referral-guided page view without blocking the response."""
    try:
        async with async_session() as db:
            raw = f"{ip_hash}{user_agent}"
            visitor_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
            db.add(
                PageEvent(
                    event_type="click",  # not pageview to avoid double-counting PV from portal.js
                    page="/guide",
                    ip_hash=ip_hash,
                    user_agent=user_agent,
                    ref=ref,
                    visitor_id=visitor_id,
                )
            )
            await db.commit()
    except Exception:
        pass  # fire-and-forget, best effort

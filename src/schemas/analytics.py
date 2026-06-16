from __future__ import annotations

from pydantic import BaseModel

# ── Request ────────────────────────────────────────────


class PageviewRequest(BaseModel):
    event_type: str  # 'pageview' | 'click'
    page: str  # '/' | '/download' | '/guide'
    element_id: str = ""  # only for click events


# ── Response: page stats ───────────────────────────────


class PageViewItem(BaseModel):
    page: str
    page_name: str
    count: int


class ClickItem(BaseModel):
    element_id: str
    element_name: str
    page: str
    page_name: str
    count: int


class DailyAnalyticsTrend(BaseModel):
    date: str
    pageviews: int = 0
    clicks: int = 0
    uv: int = 0


class PageStatsResponse(BaseModel):
    page_views: list[PageViewItem] = []
    top_clicks: list[ClickItem] = []
    daily_trend: list[DailyAnalyticsTrend] = []


# ── Response: download trends ──────────────────────────


class PackageDownloadItem(BaseModel):
    """One of the 8 download packages."""

    package_name: str  # 'codex-switch' | 'codex-desktop' | 'claude-desktop'
    product_name: str  # Chinese display name
    platform: str
    arch: str
    platform_name: str  # Chinese platform name
    count: int


class ProductDownloadItem(BaseModel):
    package_name: str
    product_name: str
    count: int


class DailyDownloadPoint(BaseModel):
    date: str
    total: int = 0
    breakdown: dict[str, int] = {}  # key: "{package_name}-{platform}-{arch}"


class VersionDownloadItem(BaseModel):
    version: str
    count: int


class DownloadTrendsResponse(BaseModel):
    total: int = 0
    today: int = 0
    daily: list[DailyDownloadPoint] = []
    by_product: list[ProductDownloadItem] = []
    by_package: list[PackageDownloadItem] = []
    by_version: list[VersionDownloadItem] = []
    cos_hit_rate: float = 0.0


# ── Chinese mapping tables (hard-coded, not in DB) ─────

PAGE_NAME_MAP: dict[str, str] = {
    "/": "首页",
    "/download": "下载页",
    "/guide": "使用指南",
}

ELEMENT_NAME_MAP: dict[str, tuple[str, str]] = {
    # element_id -> (中文名称, 所在页面)
    "hero-guide-cta": ("Hero区-查看安装指南按钮", "首页"),
    "hero-download-cta": ("Hero区-直接下载按钮", "首页"),
    "guide-entry-codex": ("安装指南入口-Codex Desktop卡片", "首页"),
    "guide-entry-claude": ("安装指南入口-Claude Desktop卡片", "首页"),
    "guide-entry-codex-cli": ("安装指南入口-Codex CLI卡片", "首页"),
    "guide-entry-claude-cli": ("安装指南入口-Claude Code CLI卡片", "首页"),
    "tool-card-codex-desktop": ("下载区-Codex Desktop下载按钮", "首页"),
    "tool-card-claude-desktop": ("下载区-Claude Desktop下载按钮", "首页"),
    "dl-tab-macos": ("下载页-macOS平台切换", "下载页"),
    "dl-tab-windows": ("下载页-Windows平台切换", "下载页"),
    "dl-tab-linux": ("下载页-Linux平台切换", "下载页"),
    "dl-btn-macos-arm64": ("下载页-macOS ARM64下载按钮", "下载页"),
    "dl-btn-macos-x64": ("下载页-macOS x64下载按钮", "下载页"),
    "dl-btn-windows-arm64": ("下载页-Windows ARM64下载按钮", "下载页"),
    "dl-btn-windows-x64": ("下载页-Windows x64下载按钮", "下载页"),
    "guide-choice-codex": ("指南-选择Codex工具卡片", "使用指南"),
    "guide-choice-claude": ("指南-选择Claude工具卡片", "使用指南"),
    "guide-choice-codex-cli": ("指南-选择Codex CLI工具卡片", "使用指南"),
    "guide-choice-claude-cli": ("指南-选择Claude Code CLI工具卡片", "使用指南"),
    "guide-platform-macos": ("指南-选择macOS平台按钮", "使用指南"),
    "guide-platform-windows": ("指南-选择Windows平台按钮", "使用指南"),
    "guide-dl-codex-switch": ("指南-下载Codex Switch按钮", "使用指南"),
    "guide-dl-codex-desktop": ("指南-下载Codex Desktop按钮", "使用指南"),
    "guide-dl-claude-desktop": ("指南-下载Claude Desktop按钮", "使用指南"),
    "guide-apikey-btn": ("指南-创建API Key按钮", "使用指南"),
    "nav-download": ("导航栏-下载链接", "全局"),
    "nav-guide": ("导航栏-指南链接", "全局"),
    "nav-github": ("导航栏-GitHub链接", "全局"),
    "footer-github": ("页脚-GitHub链接", "全局"),
}

PRODUCT_NAME_MAP: dict[str, str] = {
    "codex-switch": "Codex Switch",
    "codex-desktop": "Codex Desktop",
    "claude-desktop": "Claude Desktop",
}

PLATFORM_NAME_MAP: dict[str, str] = {
    "macos-arm64": "macOS Apple Silicon",
    "macos-x64": "macOS Intel",
    "windows-arm64": "Windows ARM64",
    "windows-x64": "Windows x64",
}


def get_page_name(page: str) -> str:
    return PAGE_NAME_MAP.get(page, page)


def get_element_info(element_id: str) -> tuple[str, str]:
    """Returns (element_name, page_name) or (element_id, '未知') if not found."""
    info = ELEMENT_NAME_MAP.get(element_id)
    if info:
        return info
    return (element_id, "未知")


def get_product_name(package_name: str) -> str:
    return PRODUCT_NAME_MAP.get(package_name, package_name)


def get_platform_name(platform: str, arch: str) -> str:
    key = f"{platform}-{arch}"
    return PLATFORM_NAME_MAP.get(key, f"{platform} {arch}")

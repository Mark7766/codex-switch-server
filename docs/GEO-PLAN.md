# GEO 改造方案 — codex-switch-server

> 让 codex-switch.cloud 被 DeepSeek、Kimi、豆包、通义千问、文心一言、元宝等国内 AI 聊天应用广泛收录和引用。
>
> **GEO** = Generative Engine Optimization（生成式引擎优化），面向 AI 时代的网站优化策略。
>
> ⚠️ **目标市场：中国大陆**。本方案所有策略和工具选择均基于国内用户和国内 AI 生态，不使用 Google/OpenAI 等境外服务。
>
> 版本: v1.1 | 最后更新: 2026-07-04 | 状态: 方案阶段（已针对国内市场 Review）

---

## 目录

1. [现状诊断](#1-现状诊断)
2. [第一阶段：技术地基（P0 · 1-2 天）](#2-第一阶段技术地基p0--1-2-天)
3. [第二阶段：内容改造（P1 · 1-2 周）](#3-第二阶段内容改造p1--1-2-周)
4. [第三阶段：权威建设（P2 · 长期持续）](#4-第三阶段权威建设p2--长期持续)
5. [第四阶段：监测与迭代（持续）](#5-第四阶段监测与迭代持续)
6. [附录：实施细节与验收标准](#6-附录实施细节与验收标准)

---

## 1. 现状诊断

### 1.1 当前状态

| 维度 | 状态 | 说明 |
|------|------|------|
| `robots.txt` | ❌ 缺失 | AI 爬虫没有明确的抓取指引 |
| `sitemap.xml` | ❌ 缺失 | 搜索引擎/AI 无法高效发现页面 |
| 结构化数据 (JSON-LD Schema) | ❌ 缺失 | 没有 SoftwareApp、FAQPage 等语义标记 |
| `llms.txt` | ❌ 缺失 | AI 大模型没有可直接读取的内容索引 |
| OG Meta 标签 | ✅ 已有基础 | `og:title/description/image/type/site_name/url` 6 个标签（TASK-040），微信分享卡片正常 |
| ICP 备案号 | ✅ 已备案 | 京ICP备2026035967号-1（TASK-078），国内 AI 更信任已备案网站 |
| 公安备案号 | ✅ 已悬挂 | （TASK-079） |
| meta keywords | ❌ 缺失 | 无 `keywords` meta 标签（百度仍会参考此标签） |
| 内容丰富度 | ⚠️ 一般 | 首页 + 下载页 + 指南页 + 支持页，缺少独立 FAQ/博客/案例页 |
| 百度收录 | ❌ 未提交 | 未在百度站长平台提交站点和 sitemap |
| 多平台分发 | ⚠️ 基础 | 仅 GitHub，缺少知乎/CSDN/掘金/微信公众号等中文社区 |
| 外链/交叉引用 | ⚠️ 基础 | GitHub ↔ 官网互相链接，缺少第三方信源引用 |

### 1.2 AI 为什么难收录 codex-switch.cloud？

```
用户问 AI：「国内怎么用 Codex/Claude？」
              │
              ▼
    AI 通过 RAG 搜索相关网页
              │
              ▼
    ┌─ 你的网站 codex-switch.cloud ─┐
    │                                │
    │  ❌ 没有 robots.txt            │ → AI 爬虫不确定能不能抓
    │  ❌ 没有 sitemap.xml           │ → AI 爬虫发现不了全部页面
    │  ❌ 没有 JSON-LD Schema        │ → AI 不知道这是软件产品
    │  ❌ 没有 llms.txt              │ → AI 不知道哪些内容最重要
    │  ❌ 没有独立 FAQ 页面           │ → AI 找不到可直接引用的问答
    │  ❌ 没有多平台信源交叉验证       │ → AI 觉得权威性不足
    │                                │
    └────────────────────────────────┘
              │
              ▼
    ❌ AI 不引用 codex-switch.cloud 的内容
    ❌ 用户得到的是 AI 训练数据中的片断信息（可能过时或不准确）
```

### 1.3 已有的 GEO 基础（优势）

| 优势 | GEO 价值 |
|------|---------|
| 产品解决真实痛点（国内流畅使用 AI 编程工具） | 高价值内容，国内 AI 偏好引用解决实际问题的中文网站 |
| 有详细的安装指南（分步骤 + 截图） | 教程类内容 AI 引用率最高 |
| 开源 MIT License + GitHub 仓库 | 权威性加分，AI 信任开源项目 |
| ICP 备案 + 公安备案双证齐全 | 国内 AI（Kimi/豆包/DeepSeek/文心一言）更信任已备案网站 |
| 广州服务器国内访问快 | AI 爬虫抓取速度快，体验好，爬取成功率更高 |
| 已有基础 OG 标签 | 微信分享卡片正常，朋友圈/群聊传播路径通 |
| 四款工具覆盖（Codex/Claude × Desktop/CLI） | 内容覆盖面广，命中更多长尾关键词 |
| 已有技术支持悬浮按钮 + 微信群二维码 | 用户信任度高，社区活跃信号 |

---

## 2. 第一阶段：技术地基（P0 · 1-2 天）

> 🎯 目标：让 AI 爬虫能发现、能抓取、能理解网站内容。
> 全部改动在 `src/portal/router.py` + `src/portal/templates/base.html` + `src/portal/templates/guide.html`，零新依赖。

### 2.1 创建 robots.txt

**文件**：`src/portal/router.py`（新增路由）

**为什么重要**：`robots.txt` 是爬虫访问网站时第一个请求的文件（`/robots.txt`）。没有它，AI 爬虫不确定哪些页面可以抓取，可能完全不抓。

**实施方案**：

```python
# 在 src/portal/router.py 中新增

from fastapi.responses import PlainTextResponse

@router.get("/robots.txt", response_class=PlainTextResponse)
async def robots_txt():
    """告知爬虫哪些路径可以抓取、哪些不可以。"""
    content = (
        "User-agent: *\n"
        "Allow: /\n"
        "Allow: /download\n"
        "Allow: /guide\n"
        "Allow: /support\n"
        "Allow: /static/\n"
        "Disallow: /admin/\n"
        "Disallow: /api/\n"
        f"Sitemap: https://codex-switch.cloud/sitemap.xml\n"
    )
    return PlainTextResponse(content)
```

**关键决策**：
- `Disallow: /admin/` — 后台不需要被索引
- `Disallow: /api/` — API 端点不需要被索引
- 引入 Sitemap 地址 — 告诉爬虫去哪找完整页面列表

### 2.2 创建 sitemap.xml

**文件**：`src/portal/router.py`（新增路由）

**为什么重要**：Sitemap 是网站的"地图"，列出所有需要被收录的页面 URL。搜索引擎和 AI 爬虫用它来发现新页面。

**实施方案**：

```python
from fastapi.responses import Response

@router.get("/sitemap.xml")
async def sitemap_xml():
    """生成站点地图 XML，帮助搜索引擎和 AI 爬虫发现所有页面。"""
    base = "https://codex-switch.cloud"

    # 核心页面
    urls = [
        {"loc": f"{base}/", "priority": "1.0", "changefreq": "weekly"},
        {"loc": f"{base}/download", "priority": "0.9", "changefreq": "weekly"},
        {"loc": f"{base}/guide", "priority": "0.9", "changefreq": "weekly"},
        {"loc": f"{base}/support", "priority": "0.7", "changefreq": "monthly"},
    ]

    # 指南页面的工具×平台组合 URL（这些是用户常搜索的具体场景）
    tools = ["codex", "claude", "codex-cli", "claude-cli"]
    platforms = ["windows", "macos"]
    for tool in tools:
        for plat in platforms:
            urls.append({
                "loc": f"{base}/guide?tool={tool}&platform={plat}",
                "priority": "0.6",
                "changefreq": "monthly",
            })

    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for u in urls:
        xml += f"  <url>\n"
        xml += f"    <loc>{u['loc']}</loc>\n"
        xml += f"    <priority>{u['priority']}</priority>\n"
        xml += f"    <changefreq>{u['changefreq']}</changefreq>\n"
        xml += f"  </url>\n"
    xml += "</urlset>"

    return Response(content=xml, media_type="application/xml")
```

**注意**：`guide?tool=xxx&platform=xxx` 参数化 URL 覆盖了用户最可能搜索的 8 个具体场景（如"macOS 安装 Codex CLI"），每个都是独立收录入口。

### 2.3 创建 llms.txt（GEO 核心文件）

**文件**：`src/portal/router.py`（新增路由）

**为什么重要**：`llms.txt` 是专门给 AI 大模型读取的内容索引文件（类似 `robots.txt` 但面向 LLM）。它帮 AI 快速了解网站的核心信息、关键页面和内容结构，避免 AI 需要爬取全站才能理解网站。这是当前 GEO 最佳实践中 ROI 最高的单项措施。

参考规范：https://llmstxt.org/

**实施方案**：

```python
@router.get("/llms.txt", response_class=PlainTextResponse)
async def llms_txt():
    """AI 大模型内容索引 — 帮助 LLM 快速理解网站核心信息和页面结构。"""
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
        "- 技术支持（交流群+帮助资源）: https://codex-switch.cloud/support\n\n"
        "## 支持的 AI 编程工具\n\n"
        "1. Codex Desktop — OpenAI 官方桌面 IDE\n"
        "2. Claude Desktop — Anthropic 官方桌面应用\n"
        "3. Codex CLI — OpenAI 命令行工具\n"
        "4. Claude Code CLI — Anthropic 命令行工具\n\n"
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
```

**设计要点**：
- 开头 3 行让 AI 立刻理解产品是什么
- "快速安装" 4 步让 AI 可以直接引用
- "场景化指南入口" 覆盖 6 种用户画像，提高 AI 匹配合适链接的概率
- 纯文本格式，零解析成本

### 2.4 添加 SoftwareApplication JSON-LD 结构化数据

**文件**：`src/portal/templates/base.html`（在 `<head>` 中新增）

**为什么重要**：JSON-LD Schema 是 Google、Bing 等搜索引擎和 AI 理解网页内容的标准格式。`SoftwareApplication` Schema 明确告诉 AI "这是一个软件产品"，包括它的名称、平台、价格、作者、许可协议等信息。

**实施方案**：在 `base.html` 的 `</head>` 前添加：

```html
<!-- Structured Data: SoftwareApplication -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "SoftwareApplication",
  "name": "Codex Switch",
  "applicationCategory": "DeveloperApplication",
  "operatingSystem": "Windows 10+, macOS 11+",
  "description": "Codex Switch 帮你解决网络问题，在国内流畅使用 Codex 和 Claude，接入 DeepSeek 和 Agnes AI——免费、快速、本地安全。",
  "url": "https://codex-switch.cloud",
  "sameAs": "https://github.com/Mark7766/codex-switch",
  "image": "https://codex-switch.cloud/static/images/logo.png",
  "offers": {
    "@type": "Offer",
    "price": "0",
    "priceCurrency": "CNY"
  },
  "author": {
    "@type": "Person",
    "name": "Mark7766",
    "url": "https://github.com/Mark7766"
  },
  "license": "https://opensource.org/licenses/MIT",
  "datePublished": "2025-01-01",
  "downloadUrl": "https://codex-switch.cloud/download"
}
</script>
```

**注意**：Jinja2 模板中 `{{` 和 `}}` 是模板变量语法，JSON-LD 中的 `{` `}` 不需要转义——只要不包含 `{{variable}}` 这样的模式即可。JSON-LD 内容放在 `<script type="application/ld+json">` 中是纯文本，不会与 Jinja2 冲突。

### 2.5 添加 FAQPage JSON-LD 结构化数据

**文件**：`src/portal/templates/guide.html`（在页面底部 `{% endblock %}` 之前新增）

**为什么重要**：`FAQPage` Schema 是 AI 引用率最高的结构化数据类型之一。当用户在 AI 中提问时，AI 优先从有 FAQPage 标记的页面提取答案。Google 也会在搜索结果中直接展示 FAQ 折叠面板（富文本搜索结果）。

**实施方案**：在 `guide.html` 中 FAQ 区块对应位置添加：

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [
    {
      "@type": "Question",
      "name": "Codex Switch 是什么？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "Codex Switch 是一款免费、开源的桌面工具，帮你解决网络问题，在国内流畅使用 Codex 和 Claude。它通过本地代理自动配置网络，无需手动设置任何参数，支持 DeepSeek 和 Agnes AI 模型。"
      }
    },
    {
      "@type": "Question",
      "name": "Codex Switch 支持哪些 AI 模型？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "支持 DeepSeek 全系列模型（deepseek-chat V3 模型和 deepseek-reasoner R1 推理模型）、Agnes AI（免费，256K 上下文窗口），以及任何 OpenAI 兼容的 API（如 GLM、自定义模型）。"
      }
    },
    {
      "@type": "Question",
      "name": "Codex Switch 安全吗？API Key 会泄露吗？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "完全本地安全。所有数据不出本机，API Key 存储在操作系统钥匙串（macOS Keychain / Windows Credential Manager）中，不落盘明文。代理仅监听 127.0.0.1（本机回环地址），外网无法访问。"
      }
    },
    {
      "@type": "Question",
      "name": "Codex Switch 免费吗？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "完全免费开源（MIT 许可）。Codex Switch 本身不收取任何费用。用户只需自行准备 DeepSeek API Key（注册即用，首次充值几块钱即可）或 Agnes AI Key。"
      }
    },
    {
      "@type": "Question",
      "name": "如何在国内使用 Codex 或 Claude？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "使用 Codex Switch 即可。步骤：1) 前往 codex-switch.cloud 下载安装包；2) 双击安装后启动 Setup 向导；3) 填入 DeepSeek API Key（在 platform.deepseek.com 申请）；4) 点击「完成并启动代理」。Codex/Claude 会自动通过本地代理解决网络问题。整个过程无需命令行操作。"
      }
    },
    {
      "@type": "Question",
      "name": "Codex Switch 支持哪些 AI 编程工具？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "支持四款 AI 编程工具：Codex Desktop（OpenAI 官方桌面 IDE）、Claude Desktop（Anthropic 官方桌面应用）、Codex CLI（OpenAI 命令行工具）、Claude Code CLI（Anthropic 命令行工具）。每款工具可以独立选择不同的 AI 模型供应商。"
      }
    },
    {
      "@type": "Question",
      "name": "Codex Switch 支持 Windows 和 Mac 吗？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "支持 Windows 10 及以上版本（x64 和 ARM 架构），以及 macOS 11 及以上版本（Apple Silicon 和 Intel 芯片）。"
      }
    },
    {
      "@type": "Question",
      "name": "DeepSeek API Key 怎么获取？",
      "acceptedAnswer": {
        "@type": "Answer",
        "text": "访问 platform.deepseek.com 注册账号，在 API Keys 页面创建 Key。注册后需要充值（几块钱即可），然后即可使用。将 Key 粘贴到 Codex Switch 的 Setup 向导中即可。"
      }
    }
  ]
}
</script>
```

**FAQ 问题选择策略**：
- 覆盖 5 类用户核心疑问：产品定义、模型支持、安全性、价格、安装方法
- 每个答案控制在 2-3 句话，让 AI 可以直接引用
- 使用具体数据（256K 上下文、127.0.0.1、MIT License）提升可信度

### 2.6 添加 Organization JSON-LD（网站身份声明）

**文件**：`src/portal/templates/base.html`（与 SoftwareApplication 并列）

```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Organization",
  "name": "Codex Switch",
  "url": "https://codex-switch.cloud",
  "logo": "https://codex-switch.cloud/static/images/logo.png",
  "sameAs": [
    "https://github.com/Mark7766/codex-switch"
  ],
  "description": "让 AI 编程触手可及 — 免费开源工具，帮助中国开发者在国内流畅使用 Codex 和 Claude。"
}
</script>
```

### 2.7 全站 meta 标签增强

**文件**：`src/portal/templates/base.html`

在现有 OG 标签基础上补充：

```html
<!-- 关键词（百度等搜索引擎仍会参考此标签） -->
<meta name="keywords" content="Codex Switch, Codex, Claude, DeepSeek, AI编程, AI编程工具, 国内使用Codex, 国内使用Claude, Codex代理, Codex国内, Claude国内, 免费开源, 代理工具, AI编程网络问题">

<!-- 百度站长平台验证（在百度站长平台添加站点后获取验证代码） -->
<!-- 两种方式二选一：①文件验证（在 router.py 中托管 HTML 文件）②meta 标签验证（在 head 中放百度给你的 content 值） -->
<meta name="baidu-site-verification" content="codeva-xxxxxxxxxx">

<!-- 应用名称（浏览器和操作系统识别） -->
<meta name="application-name" content="Codex Switch">

<!-- 主题色 -->
<meta name="theme-color" content="#f5f5f7">

<!-- 禁止百度自动转码（保持 Apple 设计风格不被破坏） -->
<meta http-equiv="Cache-Control" content="no-transform">
<meta http-equiv="Cache-Control" content="no-siteapp">
```

> ⚠️ **不推荐的 meta 标签**：
> - ~~`twitter:card`~~ — 国内用户不用 Twitter/X，加了也没意义
> - 不要在 meta 层面投入过多精力——国内 AI 更看重 Schema 结构化数据和正文字内容，不是 meta 标签

### 2.8 提交站点到百度站长平台（必须做）

**为什么这一步不能省**：百度是中国最大的搜索引擎，百度 AI（文心一言）的搜索索引也高度依赖百度站长平台的数据。不提交站点 = 百度和文心一言很难发现你的内容。

**操作步骤**（手动操作，非代码）：

1. 打开 [百度搜索资源平台](https://ziyuan.baidu.com/)（需百度账号）
2. 添加站点 `codex-switch.cloud`
3. 选择验证方式——推荐「文件验证」：百度提供 HTML 文件，在 `router.py` 中添加路由托管该文件：

```python
# src/portal/router.py
@router.get("/baidu_verify_codeva-xxxxxxxxxx.html", response_class=HTMLResponse)
async def baidu_verify():
    """百度站长平台站点验证文件"""
    return HTMLResponse("codeva-xxxxxxxxxx")  # 替换为百度提供的实际验证码
```

4. 验证通过后，在「数据引入 → 链接提交」中提交 sitemap 地址：`https://codex-switch.cloud/sitemap.xml`
5. 推荐使用「普通收录」→「手动提交」提交首页 URL

**注意**：
- 百度对已备案的 `.cloud` 域名的收录政策可能不同于 `.cn`，需要实际提交后观察
- 建议同时使用「API 推送」方式（在后续迭代中可考虑自动推送新页面）

### 2.9 不推荐的措施（针对国内市场）

以下措施虽然在国际 GEO 中常见，但对**仅面向国内用户**的本站不适用：

| 措施 | 不推荐的原因 |
|------|-------------|
| ~~`/.well-known/ai-plugin.json`~~ | ChatGPT Plugin 规范，国内用户无法使用 ChatGPT。DeepSeek/Kimi/豆包/通义千问均不支持此规范 |
| ~~Twitter Card (`twitter:card`)~~ | 国内无法访问 Twitter/X |
| ~~英文版页面 (`/en/`)~~ | 面向国内用户，中文内容是唯一需要的内容。国内 AI 语料以中文为主，不需要英文页面来「覆盖 GPT 训练数据」 |
| ~~Google Search Console 提交~~ | 国内被墙，且目标用户不用 Google 搜索。使用百度站长平台替代 |
| ~~Google Analytics~~ | 国内加载慢（或被墙），使用百度统计替代 |

> **核心原则**：每个措施都要问「这个对国内用户有帮助吗？」如果答案是「没有」或「微乎其微」，就不要做。在 GEO 上，精准比全面更重要。

### 第一阶段验收标准

- [ ] `GET /robots.txt` 返回 200，内容正确
- [ ] `GET /sitemap.xml` 返回 200，包含 4 核心页面 + 8 场景 URL
- [ ] `GET /llms.txt` 返回 200，内容覆盖核心信息+页面+工具+模型+安装步骤+外部链接
- [ ] 首页 HTML 源码中包含 `SoftwareApplication` 和 `Organization` JSON-LD（两个 `application/ld+json` 块）
- [ ] 指南页 HTML 源码中包含 `FAQPage` JSON-LD
- [ ] 首页 HTML 中包含 `keywords`、`baidu-site-verification`、`application-name` meta 标签
- [ ] 使用 [Schema.org Validator](https://validator.schema.org/) 验证全部 JSON-LD 无错误
- [ ] 在百度站长平台完成站点验证 + sitemap 提交
- [ ] （可选）使用 [百度结构化数据测试工具](https://ziyuan.baidu.com/) 验证 Schema 被百度正确识别

---

## 3. 第二阶段：内容改造（P1 · 1-2 周）

> 🎯 目标：生产 AI 偏好的高质量、高引用率内容。遵循 "AI 怎么问，我们就怎么答" 的原则。

### 3.1 创建独立 FAQ 页面

**新建文件**：
- `src/portal/templates/faq.html` — FAQ 页面模板
- `src/portal/router.py` — 新增 `GET /faq` 路由
- `src/static/css/apple.css` — 新增 FAQ 相关样式

**为什么重要**：FAQ 页面是 AI 引用率最高的内容类型。独立的 `/faq` URL 比散落在指南页中的 FAQ 区块更容易被 AI 发现和引用。

**内容策略**：按用户旅程组织问答

| 阶段 | 问题 |
|------|------|
| 了解产品 | Codex Switch 是什么？和直接用 Codex 有什么区别？免费吗？ |
| 开始使用 | 如何安装？DeepSeek API Key 怎么获取？需要什么系统？ |
| 日常使用 | 如何切换 V3 和 R1？响应速度怎么样？支持哪些 AI 工具？ |
| 遇到问题 | 代理启动失败怎么办？为什么连接不上？如何卸载？ |
| 安全隐私 | API Key 安全吗？数据经过第三方服务器吗？开源意味着什么？ |

**路由实现**：

```python
# src/portal/router.py
@router.get("/faq", response_class=HTMLResponse)
async def faq_page(request: Request):
    return templates.TemplateResponse(request, "faq.html")
```

**FAQ 页面设计**（遵循 Apple HIG）：
- 顶部 Hero：标题"常见问题" + 副标题
- 分类 Tab 或手风琴展开（`<details>/<summary>` 原生 HTML，零 JS 依赖）
- 每个答案独立成段，2-4 句，包含具体数据
- 每页底部 CTA："还没解决？扫码进技术支持群"

### 3.2 首页内容优化

**文件**：`src/portal/templates/index.html`

当前首页内容不错，但可增加 AI 友好的数据点：

**建议增加**：

1. **功能对比表格**（Hero 下方或功能卡片区域）：

```html
<section class="comparison">
  <h2>为什么选择 Codex Switch？</h2>
  <table class="comparison__table">
    <thead>
      <tr>
        <th>功能</th>
        <th>Codex Switch</th>
        <th>直接使用</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>国内网络</td>
        <td>✅ 自动配置代理，无需翻墙</td>
        <td>❌ 需要科学上网</td>
      </tr>
      <tr>
        <td>模型切换</td>
        <td>✅ 一键切换 DeepSeek/Agnes/自定义</td>
        <td>❌ 固定模型，无法切换</td>
      </tr>
      <tr>
        <td>安装配置</td>
        <td>✅ 零命令行，图形化 Setup 向导</td>
        <td>❌ 需手动配置环境变量和代理</td>
      </tr>
      <tr>
        <td>API Key 安全</td>
        <td>✅ 操作系统钥匙串加密存储</td>
        <td>⚠️ 明文配置文件，有泄露风险</td>
      </tr>
      <tr>
        <td>价格</td>
        <td>✅ 完全免费开源（MIT）</td>
        <td>❌ 需订阅（$10-200/月）</td>
      </tr>
      <tr>
        <td>多工具支持</td>
        <td>✅ Codex/Claude × Desktop/CLI 全覆盖</td>
        <td>⚠️ 仅单工具</td>
      </tr>
    </tbody>
  </table>
</section>
```

2. **数据背书**（在 Hero 或功能卡片下方）：

```html
<div class="stats-bar">
  <div class="stats-bar__item">
    <span class="stats-bar__number">4</span>
    <span class="stats-bar__label">款 AI 工具</span>
  </div>
  <div class="stats-bar__item">
    <span class="stats-bar__number">3+</span>
    <span class="stats-bar__label">种模型供应商</span>
  </div>
  <div class="stats-bar__item">
    <span class="stats-bar__number">2</span>
    <span class="stats-bar__label">个平台</span>
  </div>
  <div class="stats-bar__item">
    <span class="stats-bar__number">MIT</span>
    <span class="stats-bar__label">开源许可</span>
  </div>
</div>
```

3. **页面 description 优化**：确保 `<meta name="description">` 在 150 字以内，包含核心关键词（当前 base.html 可能已有，需检查）。

### 3.3 创建场景化 Landing Page 建议（未来）

以下页面可以在未来创建，每个页面精确命中一个用户搜索场景：

| 页面 URL | 目标搜索词 | 优先级 |
|----------|-----------|--------|
| `/guide/codex-windows` | "Windows 安装 Codex" | P2 |
| `/guide/claude-mac` | "Mac 安装 Claude" | P2 |
| `/guide/codex-deepseek` | "Codex 接入 DeepSeek" | P2 |
| `/blog/codex-switch-vs-direct` | "Codex Switch 和直接使用有什么区别" | P2 |

> ⚠️ 这些页面工作量较大，属于"锦上添花"。建议在完成第一阶段 + FAQ 页面 + 内容优化后，根据 AI 搜索数据决定优先做哪个。

### 3.4 创建技术博客栏目（P2，推荐做）

**新建目录与文件**：
- `src/portal/templates/blog/` — 博客模板目录
- `src/portal/templates/blog/index.html` — 博客首页
- `src/portal/router.py` — 新增 `/blog` 和 `/blog/{slug}` 路由

**为什么重要**：博客内容是 AI 引用的主要来源。每篇博客文章可以精确命中一个长尾搜索场景（"国内怎么用 Codex CLI"），而这恰恰是用户问 AI 的自然语言形式。

**建议发布的 5 篇核心文章**：

| 文章标题 | 目标关键词场景 | AI 引用场景 |
|----------|---------------|-------------|
| 《国内使用 Codex/Claude 完全指南（2026）》 | 国内使用 Codex, 国内使用 Claude | "国内怎么用 Codex" |
| 《DeepSeek V3 vs R1：Codex Switch 模型选择指南》 | DeepSeek V3 R1 区别 | "DeepSeek 选哪个模型" |
| 《Codex CLI 接入 DeepSeek 完整教程》 | Codex CLI DeepSeek | "Codex CLI 怎么配 DeepSeek" |
| 《AI 编程工具网络问题终极解决方案》 | AI 编程网络问题 | "Codex 连不上怎么办" |
| 《2026 年 AI 编程工具对比：Codex vs Claude vs Cursor》 | Codex Claude 对比 | "选哪个 AI 编程工具" |

**每篇文章的结构要求**（AI 友好格式）：
1. 开头 50 字直接给出核心答案（不要铺垫）
2. H2/H3 清晰分层，每个小节标题可以是一个问答
3. 步骤用编号列表，代码用代码块
4. 穿插数据（延迟、速度、大小等具体数字）
5. 文末 FAQ（3-5 条，呼应文章主题）

**博客技术实现**：
- 方案 A（极简，推荐）：Markdown 文件存储在 `data/blog/` 目录，FastAPI 读取并渲染为 HTML
- 方案 B（灵活）：Jinja2 模板直接写 HTML
- 本项目推荐方案 A：不引入数据库，Markdown 文件即内容，git 版本管理

### 3.5 微信公众号内容分发（推荐）

> ⚠️ 本节替代原方案的「英文版页面」——国内用户不需要英文版，需要的是微信公众号。

**为什么重要**：微信公众号文章可以被国内 AI（尤其是元宝/混元，因为它是腾讯的）直接索引和引用。同时公众号文章在微信搜索中有权重，用户通过微信搜一搜也能发现内容。

**建议发布**：
- 产品介绍文章（「Codex Switch：让 AI 编程触手可及」）
- 安装教程系列（Windows/Mac 分步骤图文教程）
- 模型选择指南（DeepSeek V3 vs R1，什么时候用哪个）
- 常见问题合集（FAQ 精简版，方便转发和收藏）

**和技术博客的不同**：公众号文章面向「非技术用户」——文字更通俗、截图更多、步骤更细。技术博客面向开发者，可以更深入。

### 第二阶段验收标准

- [ ] `GET /faq` 返回 200，包含 ≥15 条问答
- [ ] FAQ 页面使用 `<details>/<summary>` 手风琴（零 JS）
- [ ] FAQ 页面包含 FAQPage JSON-LD
- [ ] 首页包含对比表格和统计数据
- [ ] 全站 description meta 标签优化完成
- [ ] （如做博客）`GET /blog` 返回 200，≥3 篇文章
- [ ] （如做公众号）≥2 篇产品介绍/教程文章发布

---

## 4. 第三阶段：权威建设（P2 · 长期持续）

> 🎯 目标：让 AI 判定 codex-switch.cloud 为高可信信源。
> AI 判断信源权威性的核心逻辑：「多平台、多信源交叉验证」。

### 4.1 多平台分发矩阵

| 平台 | 发布内容 | 频率 | 优先级 | GEO 价值 |
|------|----------|------|--------|---------|
| **GitHub** | 代码 + README + Wiki + Releases | 随版本更新 | P0 | 开源背书，最高技术权威 |
| **知乎专栏** | 技术教程、使用指南、对比评测 | 每周 1 篇 | P0 | 国内 AI 首选中文信源，知乎内容被 DeepSeek/Kimi 高频引用 |
| **微信公众号** | 产品介绍、教程系列、FAQ 合集 | 每两周 1 篇 | P0 | 微信搜一搜权重高，元宝/混元可直接索引 |
| **CSDN** | 同步知乎内容（稍作调整） | 每周 1 篇 | P1 | 国内最大技术社区，百度搜索权重高 |
| **掘金** | AI 编程 / 工具链深度文章 | 每两周 1 篇 | P1 | 高质量开发者社区，内容被 AI 引用几率高 |
| **B站** | 安装教程视频、使用演示 | 每月 1 个 | P2 | 视频内容补充，年轻开发者聚集地 |
| **SegmentFault** | 技术问答 + 文章 | 随缘 | P2 | 技术 Q&A，QA 格式天然适合 AI 引用 |
| **V2EX** | 产品分享 + 讨论 | 每版本 1 帖 | P2 | 高质量技术讨论社区 |
| **小红书** | AI 工具推荐、效率提升分享 | 随缘 | P3 | 触达非传统开发者用户（产品经理、学生等） |

### 4.2 证据链建设

理想状态下，AI 爬虫会在多个独立平台发现相同的信息，从而提升信任度：

```
GitHub README ──→ 官网 codex-switch.cloud ←── 知乎专栏
       │                    │                      │
       └────────────────────┼──────────────────────┘
                            │
                    都是同一个产品的官方信源
                    信息一致 → 权威性 ↑
                            │
                      AI 爬虫判定：
                   「这是可信的一手信源」
```

**具体操作**：
1. GitHub README 中明确链接到官网（已有 ✅）
2. 官网页脚链接到 GitHub（已有的 Portal 页脚 ✅）
3. 知乎文章末尾链接到官网和 GitHub
4. 知乎个人简介标注"Codex Switch 作者"
5. 所有平台的描述文案保持一致（产品名、一句话介绍、核心功能）

### 4.3 GitHub 仓库 GEO 优化

| 项目 | 当前状态 | 优化建议 |
|------|---------|---------|
| README | 基础 | 增加使用案例（before/after）、Demo 视频、Star 数徽章 |
| Wiki | 未启用 | 创建安装指南 Wiki、FAQ Wiki |
| Discussions | 未启用 | 开启，作为社区交流入口 |
| Release Notes | 规范 ✅ | 保持当前质量 |
| Topics/标签 | 待检查 | 添加 `ai-coding` `deepseek` `codex` `claude` `proxy` `china` 等标签 |

### 第三阶段验收标准

- [ ] 知乎专栏 ≥5 篇文章发布
- [ ] CSDN 同步 ≥3 篇
- [ ] 微信公众号 ≥2 篇文章发布
- [ ] GitHub README 增加案例和数据
- [ ] GitHub 仓库 Topics 标签配置完成
- [ ] 所有平台的产品描述文案统一

---

## 5. 第四阶段：监测与迭代（持续）

> 🎯 目标：追踪 GEO 效果，数据驱动优化。所有工具均为国内可访问。

### 5.1 核心监测方法

| 监测项 | 方法 | 频率 |
|--------|------|------|
| AI 引用率 | 在 DeepSeek / Kimi / 豆包 / 通义千问 / 文心一言 / 元宝中搜索 5 个核心关键词 | 每两周 |
| 网站收录状态 | 百度站长平台 → 索引量 | 每月 |
| Sitemap 健康 | 百度站长平台 → 数据引入 → 链接提交 | 每月 |
| Schema 正确性 | [Schema.org Validator](https://validator.schema.org/) + 百度结构化数据测试工具 | 每次改版 |
| 自然搜索流量 | 百度统计 | 每周 |
| llms.txt 可访问性 | `curl -I https://codex-switch.cloud/llms.txt` | 每次部署 |
| 404/错误页面 | 百度站长平台 → 抓取诊断 | 每月 |
| 移动端适配 | 百度站长平台 → 移动适配 | 首次 + 按需 |

### 5.2 核心追踪关键词

| 关键词 | 目标 | 当前 AI 引用排名（基线） |
|--------|------|------------------------|
| "国内使用 Codex" | AI 回答前 3 条引用 | 待测量 |
| "国内使用 Claude" | AI 回答前 3 条引用 | 待测量 |
| "Codex Switch" | AI 回答中准确描述产品 | 待测量 |
| "Codex DeepSeek 配置" | AI 回答前 3 条引用 | 待测量 |
| "AI 编程工具国内网络问题" | AI 回答中提及 | 待测量 |
| "DeepSeek API Key 怎么用" | AI 回答中提及 Codex Switch | 待测量 |
| "Windows Mac 安装 Codex" | AI 回答中引用指南页 | 待测量 |

### 5.3 国内 AI 应用监测矩阵

> 每两周执行一轮，记录每个 AI 应用对核心关键词的引用情况。

| AI 应用 | 开发者 | 搜索方式 | 监测要点 |
|---------|--------|---------|---------|
| **DeepSeek** | 深度求索 | Web/App 对话中打开联网搜索 | 代码相关场景引用率最高，关注是否引用 GitHub + 官网 |
| **Kimi** | 月之暗面 | Web/App 对话 | 擅长长文总结，关注是否准确概述产品功能 |
| **豆包** | 字节跳动 | Web/App 对话 | 用户量大，关注是否在推荐产品时提及 Codex Switch |
| **通义千问** | 阿里巴巴 | Web/App 对话 | 阿里生态，技术问答能力强 |
| **文心一言** | 百度 | Web/App 对话 | 与百度搜索深度绑定，sitemap 提交后效果可能最先显现 |
| **元宝** | 腾讯 | 微信内/App | 与微信公众号内容深度绑定，发布公众号文章后重点监测 |

### 5.4 每两周检查清单

- [ ] 在 **DeepSeek** 中搜索「国内怎么用 Codex」，检查是否引用 codex-switch.cloud
- [ ] 在 **Kimi** 中搜索「Codex Switch 是什么」，检查回答准确性
- [ ] 在 **豆包** 中搜索「DeepSeek 配置 Codex」，检查引用
- [ ] 在 **通义千问** 中搜索「AI 编程工具国内网络」，检查是否提及
- [ ] 在 **文心一言** 中搜索「国内使用 Claude」，检查引用（百度生态，sitemap 提交后重点观察）
- [ ] 在 **元宝** 中搜索「Codex Switch」，检查引用（腾讯生态，公众号发布后重点观察）
- [ ] `curl -I https://codex-switch.cloud/robots.txt` → 200
- [ ] `curl -I https://codex-switch.cloud/sitemap.xml` → 200
- [ ] `curl -I https://codex-switch.cloud/llms.txt` → 200
- [ ] 百度站长平台检查索引量和抓取错误
- [ ] 发布至少 1 篇技术文章（知乎/CSDN/公众号/博客）
- [ ] 回复 GitHub Issues / Discussions
- [ ] 记录本轮监测结果到监测日志

### 5.5 监测日志模板

建议在 `docs/geo-monitoring-log.md` 中记录每轮监测结果：

```markdown
## 监测轮次 #1 — 2026-07-18

| 关键词 | DeepSeek | Kimi | 豆包 | 通义千问 | 文心一言 | 元宝 |
|--------|----------|------|------|---------|---------|------|
| "国内使用 Codex" | 第2条引用 ✅ | 未引用 ❌ | 未引用 ❌ | 未引用 ❌ | - | - |
| "Codex Switch" | 准确描述 ✅ | 未搜索到 ❌ | - | - | - | - |
| ... | | | | | | |

**本轮发现**：
- DeepSeek 已引用指南页，但 FAQ 页尚未出现

**下轮行动**：
- 重点在 Kimi 中优化——可能需要在知乎多发文章
```

### 5.6 效果预期（国内市场）

| 时间线 | 预期效果 |
|--------|---------|
| 第 1 周（第一阶段完成） | AI 爬虫开始抓取更多页面，`llms.txt` 帮助 AI 理解网站结构 |
| 第 2-4 周 | Schema 标记被收录，百度可能展示结构化搜索结果 |
| 第 1-3 个月 | 部分国内 AI 开始引用网站内容（DeepSeek/Kimi 可能最先见效） |
| 第 3-6 个月 | 多平台分发+证据链生效，国内 AI 引用率逐步提升 |
| 6 个月以上 | 形成「知乎专栏 + 公众号 + GitHub」三足鼎立的内容矩阵 |

---

## 6. 附录：实施细节与验收标准

### 6.1 文件变更清单

| 阶段 | 文件 | 操作 | 说明 |
|------|------|------|------|
| 1 | `src/portal/router.py` | 修改 | 新增 `/robots.txt` `/sitemap.xml` `/llms.txt` `/baidu_verify_*.html` 路由 |
| 1 | `src/portal/templates/base.html` | 修改 | 新增 SoftwareApplication + Organization JSON-LD，补充 keywords + baidu-site-verification + application-name meta，添加百度禁止转码标签 |
| 1 | `src/portal/templates/guide.html` | 修改 | 新增 FAQPage JSON-LD（FAQ 区块附近） |
| 1 | 百度站长平台 | 手动操作 | 添加站点 + 验证 + 提交 sitemap |
| 2 | `src/portal/templates/faq.html` | **新建** | 独立 FAQ 页面模板 |
| 2 | `src/portal/templates/index.html` | 修改 | 新增对比表格 + 统计数据条 |
| 2 | `src/static/css/apple.css` | 修改 | 新增 `.comparison` `.stats-bar` `.faq` 等 CSS |
| 2 | `src/portal/templates/blog/index.html` | **新建**（可选） | 博客首页模板 |
| 2 | `src/portal/templates/blog/post.html` | **新建**（可选） | 博客文章模板 |
| 2 | `data/blog/` | **新建**（可选） | Markdown 博客文章目录 |
| 3 | GitHub README | 修改 | 增加案例+数据+Topics 标签 |
| 3 | 知乎/CSDN/公众号/掘金 | 手动操作 | 多平台内容发布 |
| 5 | `docs/geo-monitoring-log.md` | **新建** | GEO 监测日志 |

### 6.2 技术约束与注意事项

- **零新依赖**：所有第一阶段改动只需 FastAPI 内置的 `PlainTextResponse` / `Response` / `JSONResponse`，不需要安装任何新包
- **不引入前端框架**：FAQ 页面使用原生 `<details>/<summary>` 实现折叠，CSS 动画使用 `@keyframes`，符合项目"前端极简"约束
- **SEO vs GEO**：本项目不需要刻意追求传统 SEO（关键词密度、外链），核心目标是让 AI 能准确理解并引用网站信息
- **路由注册**：新增路由在 `src/portal/router.py` 中以 `@router.get(...)` 添加，`router` 已在 `src/main.py` 中注册到 `/` 前缀
- **模板变量**：JSON-LD 中的 `{` `}` 不会与 Jinja2 的 `{{ }}` 冲突，只要 `{` 和 `}` 不直接跟在另一个 `{` 后面即可
- **测试**：门户路由测试在 `tests/integration/test_portal.py`，新增路由需补充 HTTP 200 检查

### 6.3 GEO vs SEO 核心区别（国内视角）

| 维度 | 传统 SEO（百度搜索） | GEO（国内 AI） |
|------|---------------------|----------------|
| 目标 | 百度搜索结果排名靠前 | DeepSeek/Kimi/豆包/通义千问/文心一言/元宝 回答中被引用 |
| 受众 | 人类用户 | AI 模型（RAG 检索增强生成） |
| 核心技术 | 百度收录 + 关键词 + 外链 | 结构化数据 + 语义清晰 + 权威信源 + 多平台交叉验证 |
| 内容偏好 | 长文、关键词密度 | FAQ、教程、对比表格、步骤列表 |
| 结构化数据 | 辅助排名 | **核心要求**——没有 Schema AI 就很难准确理解 |
| `llms.txt` | 无影响 | **核心文件**——AI 直接读取的内容索引 |
| 分发平台 | 百度系产品（百家号等） | 知乎 + CSDN + 公众号 + GitHub — 国内 AI 高频引用的信源 |
| 监测工具 | 百度站长平台 + 百度统计 | 手动在 6 个 AI 应用中搜索验证 |

### 6.4 为什么按这个顺序做

```
第一阶段（技术地基）─→ 第二阶段（内容改造）─→ 第三阶段（权威建设）
    ↓                        ↓                        ↓
 让 AI 能发现             让 AI 能引用            让 AI 信任
 （基础设施）              （内容质量）             （权威背书）
    ↓                        ↓                        ↓
 1-2 天                   1-2 周                   长期持续
 0 风险                    低风险                   高投入
 ROI 最高                  ROI 高                   ROI 中等
```

> 没有技术地基，AI 根本看不到你的内容。
> 没有好内容，AI 看到了也不知道怎么引用。
> 没有权威建设，AI 引用了但优先级低。

---

> **总结**：GEO 优化的本质是「用 AI 能理解的方式（结构化数据 + llms.txt + Schema）组织内容，用 AI 信任的方式（多平台交叉验证 + 开源背书 + ICP/公安双备案合规）建立权威」。
>
> **针对国内市场，核心记住三句话**：
> 1. **技术地基选对工具**：百度站长平台替代 Google Search Console，百度统计替代 Google Analytics，Schema.org 验证器（全球通用）替代 Google Rich Results Test
> 2. **内容分发选对平台**：知乎 + CSDN + 微信公众号 + GitHub 四件套打底，掘金/B站/V2EX 锦上添花，Hacker News/Twitter/Medium 不用碰
> 3. **监测选对 AI 应用**：DeepSeek + Kimi + 豆包 + 通义千问 + 文心一言 + 元宝 六家全测，不用测 ChatGPT
>
> 建议本周完成第一阶段（1-2 天），让国内 AI 开始能抓取和理解网站。效果通常在 1-3 个月后逐步显现。
>
> 本方案基于 codex-switch 项目的 GEO-PLAN.md 重构，针对 codex-switch-server 的技术栈和中国国内市场做了完整适配。

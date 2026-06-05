# codex-switch-server 系统设计方案

> **版本**：v1.3  
> **日期**：2026-06-05  
> **状态**：待 Review  
> **作者**：wangliang  
> **变更**：v1.3 — ollama 已从服务器卸载，更新资源规划（内存+700MB、磁盘+4GB）

---

## 目录

1. [项目概述与背景](#1-项目概述与背景)
2. [系统架构设计](#2-系统架构设计)
3. [门户与页面设计](#3-门户与页面设计)
4. [API 接口设计](#4-api-接口设计)
5. [数据库设计](#5-数据库设计)
6. [代码模块设计](#6-代码模块设计)
7. [安全设计](#7-安全设计)
8. [部署方案](#8-部署方案)
9. [开发计划](#9-开发计划)
10. [附录](#10-附录)

---

## 1. 项目概述与背景

### 1.1 项目定位

codex-switch-server 是 [codex-switch](https://github.com/Mark7766/codex-switch) 桌面应用的配套服务端系统，承担三个角色：

| 角色 | 面向用户 | 说明 |
|------|---------|------|
| **产品门户** | 所有用户（公开） | 展示 codex-switch 产品价值、引导下载、提供使用指南 |
| **下载镜像** | codex-switch 客户端用户 | 提供版本更新、桌面应用和 CLI 工具包的高速下载（解决国内用户访问 GitHub 困难） |
| **运营后台** | 管理员（仅 wangliang） | 查看下载数据、用户行为数据、产品运营指标 |

### 1.2 解决的问题

当前 codex-switch 用户面临的核心痛点：

| 痛点 | 现状 | 解决方案 |
|------|------|---------|
| **下载困难** | 用户从 GitHub Releases 下载 codex-switch 安装包经常超时/失败 | 服务端从 GitHub 同步安装包到国内服务器，用户从 codex-switch-server 高速下载 |
| **工具安装门槛高** | 很多用户不会安装 Claude Desktop、Codex Desktop、Node.js、Git | 服务端托管所有安装包，codex-switch 客户端提供一键安装 |
| **没有产品门户** | 用户只能通过 GitHub 页面了解产品，没有专业的产品展示 | 构建 Apple 极简风格门户，展示产品价值、提供下载和使用指南 |
| **不了解用户** | 不知道有多少用户、使用哪些功能、遇到什么问题 | 体验提升计划收集匿名使用数据，帮助产品改进 |

### 1.3 用户画像

| 角色 | 描述 | 核心诉求 |
|------|------|---------|
| **中国内地开发者** | 使用 Codex/Claude 进行 AI 编程，但受网络限制 | 快速下载、顺利安装、一键配置 |
| **非技术用户** | 想用 AI 编程工具但不会配置 | 傻瓜式安装、自动配置、有教程 |
| **管理员（wangliang）** | 维护 codex-switch 产品 | 看数据、控版本、低运维成本 |

### 1.4 设计原则

```
极简实用  >  功能丰富
维护简单  >  性能极致
够用就好  >  过度设计
```

**核心约束**：一个人维护，所有设计决策都围绕"一个人能轻松掌控"展开。

---

## 2. 系统架构设计

### 2.1 整体架构

```
用户浏览器                         codex-switch 客户端
(www.codexswtich.cloud)                 (macOS / Windows)
      │                                  │
      │  HTML / CSS / JS                │  JSON / binary
      ▼                                  ▼
┌───────────────────────────────────────────────────────┐
│                 codex-switch-server                   │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │              路由层（Thin Layer）                │  │
│  │                                                  │  │
│  │  portal/          api/v1/         admin/         │  │
│  │  ├── /            ├── /update     ├── /login     │  │
│  │  ├── /download    ├── /packages   └── /          │  │
│  │  └── /guide       └── /telemetry                │  │
│  └──────────────────────┬──────────────────────────┘  │
│                         │                              │
│  ┌──────────────────────▼──────────────────────────┐  │
│  │              服务层（Business Logic）            │  │
│  │                                                  │  │
│  │  ReleaseSync       Telemetry       PackageMgr    │  │
│  │  · 版本检测         · 事件验证      · 包索引      │  │
│  │  · 下载同步         · 去重聚合      · 代理缓存    │  │
│  │  · 缓存清理         · 统计分析      · 文件分发    │  │
│  └──────────────────────┬──────────────────────────┘  │
│                         │                              │
│  ┌──────────────────────▼──────────────────────────┐  │
│  │          数据层（Data Definition）                │  │
│  │                                                  │  │
│  │  models/                schemas/                 │  │
│  │  · Release              · ReleaseRead            │  │
│  │  · DownloadRecord       · TelemetryEvent         │  │
│  │  · TelemetryEvent       · DashboardStats         │  │
│  └──────────────────────┬──────────────────────────┘  │
│                         │                              │
│  ┌──────────────────────▼──────────────────────────┐  │
│  │          基础设施（Infrastructure）               │  │
│  │                                                  │  │
│  │  SQLite               data/ 目录                 │  │
│  │  (app.db)             (.dmg/.exe/.zip)           │  │
│  └─────────────────────────────────────────────────┘  │
│                                                       │
│  ┌─────────────────────────────────────────────────┐  │
│  │          工具层（Utilities）                      │  │
│  │  utils/http.py          utils/storage.py         │  │
│  │  · GitHub API 封装       · 本地/COS 存储抽象      │  │
│  │  · 重试 + 限速            · 文件校验              │  │
│  └─────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────┘
      │
      ▼
┌─────────────────┐     ┌──────────────────┐
│ GitHub Releases │     │ 腾讯云 COS        │
│ (上游数据源)     │     │ (生产环境存储)     │
└─────────────────┘     └──────────────────┘
```

### 2.2 技术栈

| 层面 | 选型 | 版本 | 选型理由 |
|------|------|------|---------|
| 语言 | Python | 3.12 | 部署简单、生态丰富、一人维护心智负担低 |
| Web 框架 | FastAPI | latest | 异步原生支持、自动 OpenAPI 文档、类型安全 |
| ASGI 服务器 | uvicorn | latest | 轻量、快速、支持热重载 |
| 数据库 | SQLite (aiosqlite) | — | 零配置、单文件、免维护、异步驱动 |
| ORM | SQLAlchemy | 2.0+ | 异步 session、成熟稳定、社区标准 |
| 数据校验 | Pydantic | v2 | 与 FastAPI 深度集成、类型安全 |
| 配置管理 | pydantic-settings | latest | 自动读取 .env、类型校验 |
| HTTP 客户端 | httpx | latest | 异步支持、用于访问 GitHub API |
| 模板引擎 | Jinja2 | — | FastAPI 内置、服务器渲染 |
| 测试 | pytest + pytest-asyncio | latest | 异步测试支持、fixture 丰富 |
| 格式化/Lint | ruff | latest | Rust 编写、极快、一个工具搞定 format+lint |
| 包管理 | uv | latest | 极快、统一 pip+venv |
| 管理端图表 | Chart.js | CDN | 仅 /admin 页面按需加载 |
| 前端框架 | **无** | — | 服务器渲染 + 手写 CSS + 极简 vanilla JS |

### 2.3 分层架构规则

```
┌──────────────────────────────────────────────────────────────┐
│ 路由层 (portal/ api/ admin/)                                  │
│   → 只做：参数校验 → 调用 service → 返回响应                   │
│   → 禁止：直接操作数据库、包含业务逻辑                          │
│   → 单文件 < 50 行                                            │
├──────────────────────────────────────────────────────────────┤
│ 服务层 (services/)                                            │
│   → 所有业务逻辑                                              │
│   → 接收参数和依赖（db session, http client），返回数据        │
│   → 禁止：操作 HTTP 请求/响应对象                              │
│   → 可单独测试（注入 mock 依赖）                                │
├──────────────────────────────────────────────────────────────┤
│ 数据层 (models/ + schemas/)                                   │
│   → ORM Model：纯字段定义 + 简单 property（贫血模型）          │
│   → Pydantic Schema：API 契约（Request / Response 分离）       │
│   → 禁止：包含业务方法                                        │
├──────────────────────────────────────────────────────────────┤
│ 工具层 (utils/)                                               │
│   → 无状态工具函数                                            │
│   → 外部服务访问封装（GitHub API、COS）                        │
│   → 禁止：导入 models 或 services                             │
└──────────────────────────────────────────────────────────────┘
```

### 2.4 目录结构

```
codex-switch-server/
├── src/
│   ├── main.py                    # create_app() 工厂函数 + lifespan
│   ├── config.py                  # pydantic-settings 配置
│   ├── database.py                # SQLAlchemy engine + async session
│   │
│   ├── models/                    # ORM 模型（贫血）
│   │   ├── __init__.py
│   │   ├── base.py                # DeclarativeBase
│   │   ├── release.py             # Release — 版本发布
│   │   ├── download.py            # DownloadRecord — 下载记录
│   │   └── telemetry.py           # TelemetryEvent — 遥测事件
│   │
│   ├── schemas/                   # Pydantic DTO
│   │   ├── __init__.py
│   │   ├── release.py             # ReleaseRead, ReleaseCheckResponse
│   │   ├── download.py            # PlatformDownload
│   │   └── telemetry.py           # TelemetryEventIn, TelemetryReport
│   │
│   ├── api/                       # API 路由（薄层）
│   │   ├── __init__.py
│   │   ├── deps.py                # get_db, verify_admin_token
│   │   ├── router.py              # 聚合所有 v1 路由
│   │   └── v1/
│   │       ├── __init__.py
│   │       ├── update.py          # 版本检查与下载
│   │       ├── packages.py        # 工具包下载
│   │       └── telemetry.py       # 遥测数据上报
│   │
│   ├── services/                  # 业务逻辑（核心）
│   │   ├── __init__.py
│   │   ├── release_sync.py        # GitHub 版本同步
│   │   └── telemetry.py           # 遥测事件处理
│   │
│   ├── portal/                    # 公开门户
│   │   ├── __init__.py
│   │   ├── router.py              # / /download /guide
│   │   └── templates/
│   │       ├── base.html          # 全局布局（导航+页脚）
│   │       ├── index.html         # 首页
│   │       ├── download.html      # 下载页
│   │       └── guide.html         # 使用指南
│   │
│   ├── admin/                     # 运营后台
│   │   ├── __init__.py
│   │   ├── router.py              # /admin /admin/login
│   │   └── templates/
│   │       ├── base.html          # 后台布局
│   │       ├── login.html         # 登录页
│   │       └── dashboard.html     # 数据面板
│   │
│   ├── static/                    # 静态资源
│   │   ├── css/
│   │   │   └── apple.css          # Apple 设计系统
│   │   ├── js/
│   │   │   └── portal.js          # 极简交互增强
│   │   └── images/
│   │       └── tool-icons/        # Codex/Claude/Node/Git 图标
│   │
│   └── utils/                     # 工具层
│       ├── __init__.py
│       ├── http.py                # httpx 封装
│       └── storage.py             # 存储抽象
│
├── tests/
│   ├── conftest.py                # fixtures: 内存 DB、测试客户端
│   ├── unit/                      # 单元测试（mock 外部依赖）
│   │   ├── test_release_sync.py
│   │   └── test_telemetry.py
│   ├── integration/               # 集成测试（真实 SQLite）
│   │   ├── test_update_api.py
│   │   ├── test_packages_api.py
│   │   ├── test_telemetry_api.py
│   │   └── test_portal.py
│   └── e2e/                       # 端到端（完整流程）
│       └── test_download_flow.py
│
├── data/                          # 安装包缓存目录（gitignore）
├── docs/
│   └── DESIGN.md                  # 本文件
├── pyproject.toml
├── .env.example
├── .gitignore
└── README.md
```

---

## 3. 门户与页面设计

### 3.1 设计哲学：Apple Human Interface Guidelines

```
Clarity（清晰）
  → 文字清晰可读，图标精确，功能一目了然
  → 实现：大标题 + 充足留白 + 单一视觉焦点 + 明确层级

Deference（遵从）
  → UI 退让，内容为王，去除无关界面元素
  → 实现：无边框卡片、微阴影、透明导航栏

Depth（深度）
  → 视觉分层，动效传递位置关系
  → 实现：毛玻璃导航、卡片悬浮抬升、平滑过渡
```

### 3.2 视觉系统（Design Tokens）

#### 颜色

```css
:root {
  /* 背景 */
  --color-bg-primary:    #f5f5f7;   /* 页面主背景（Apple 经典浅灰） */
  --color-bg-card:       #ffffff;   /* 卡片背景 */
  --color-bg-footer:     #fafafa;   /* 页脚背景 */
  --color-bg-nav-glass:  rgba(245,245,247,0.72); /* 毛玻璃导航 */

  /* 文字 */
  --color-text-primary:   #1d1d1f;  /* 主文字（Apple 黑） */
  --color-text-secondary: #86868b;  /* 辅助文字（Apple 灰） */
  --color-text-tertiary:  #6e6e73;  /* 弱文字 */
  --color-text-on-accent: #ffffff;  /* 强调色上的文字 */

  /* 强调色 */
  --color-accent:        #0071e3;   /* Apple 蓝 */
  --color-accent-hover:  #0077ed;   /* 悬浮蓝 */

  /* 语义色 */
  --color-success:       #34c759;   /* 成功 */
  --color-warning:       #ff9500;   /* 警告 */
  --color-error:         #ff3b30;   /* 错误 */

  /* 分割线 */
  --color-separator:     #d2d2d7;
}
```

#### 字体

```css
:root {
  --font-sans: -apple-system, BlinkMacSystemFont, "SF Pro Display",
               "SF Pro Text", "PingFang SC", "Hiragino Sans GB",
               "Microsoft YaHei", sans-serif;
  --font-mono: "SF Mono", Menlo, Consolas, "Courier New", monospace;
}
```

#### 字号层级

| Token | 值 | font-weight | letter-spacing | 场景 |
|-------|---|-------------|----------------|------|
| `--text-hero` | 56px | 600 | -0.015em | 首页 Hero 主标题 |
| `--text-page-title` | 40px | 600 | -0.01em | 页面大标题 |
| `--text-section-title` | 32px | 600 | 0 | 区块标题 |
| `--text-subsection` | 24px | 600 | 0 | 小节标题 |
| `--text-card-title` | 21px | 600 | 0 | 卡片标题 |
| `--text-body` | 17px | 400 | 0 | 正文（line-height: 1.5） |
| `--text-caption` | 14px | 400 | 0 | 辅助说明 |
| `--text-label` | 12px | 400 | 0 | 标签/小字 |

#### 间距（8px 网格系统）

| Token | 值 | 场景 |
|-------|---|------|
| `--space-0` | 4px | 图标与文字间距 |
| `--space-1` | 8px | 紧凑间距 |
| `--space-2` | 16px | 默认内边距 |
| `--space-3` | 24px | 段落间距 |
| `--space-4` | 32px | 模块间距 |
| `--space-5` | 48px | 区块间距 |
| `--space-6` | 64px | 大段间距 |
| `--space-7` | 80px | 页面级间距 |
| `--space-8` | 120px | Hero 上下间距 |

#### 圆角

| Token | 值 | 场景 |
|-------|---|------|
| `--radius-sm` | 8px | 按钮、输入框 |
| `--radius-md` | 12px | 小卡片 |
| `--radius-lg` | 18px | 标准卡片（Apple 标志性圆角） |
| `--radius-xl` | 20px | 大卡片、Modal |
| `--radius-full` | 44px | 全宽 CTA 胶囊按钮 |

#### 阴影

```css
/* 卡片阴影（自然光从上方） */
--shadow-card: 0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.06);
--shadow-card-hover: 0 4px 12px rgba(0,0,0,0.08), 0 2px 4px rgba(0,0,0,0.04);

/* 毛玻璃导航阴影 */
--shadow-nav: 0 0 0 1px rgba(0,0,0,0.04), 0 2px 8px rgba(0,0,0,0.04);
```

#### 过渡

```css
--transition-fast: 0.15s cubic-bezier(0.25, 0.1, 0.25, 1);
--transition-normal: 0.3s cubic-bezier(0.25, 0.1, 0.25, 1);
--transition-slow: 0.5s cubic-bezier(0.25, 0.1, 0.25, 1);
```

### 3.3 导航设计

#### 全局导航栏

```
┌──────────────────────────────────────────────────────────────┐
│  [Logo] Codex Switch       下载    指南    GitHub    ⭐      │
│  ─────────────────────────────────────────────────────────── │
│  毛玻璃背景 · backdrop-filter: saturate(180%) blur(20px)     │
│  页面顶部固定 · z-index: 100                                 │
│  滚动前：透明 · 滚动后：毛玻璃 + 阴影                         │
└──────────────────────────────────────────────────────────────┘
```

**行为**：
- 页面顶部 `position: fixed`
- 初始状态：背景透明，文字白色（仅首页 Hero 区域）
- 滚动超过 Hero：背景切换为毛玻璃（`rgba(245,245,247,0.72)` + `backdrop-filter`）
- Logo 和导航链接之间间距 32px
- 右侧 "GitHub" 链接带 GitHub 图标
- 移动端（< 768px）：导航链接折叠为汉堡菜单

#### 页脚

```
┌──────────────────────────────────────────────────────────────┐
│  ──────────────────────────────────────────────────────────  │
│                                                              │
│  Codex Switch                                                │
│  让 AI 编程触手可及                                          │
│                                                              │
│  产品             资源              联系                      │
│  下载             使用指南           GitHub                   │
│  更新日志         FAQ               反馈与建议                │
│                                                              │
│  ──────────────────────────────────────────────────────────  │
│  © 2026 Codex Switch · 开源软件 · MIT License                │
└──────────────────────────────────────────────────────────────┘
```

### 3.4 首页 `/` 详细设计

**页面目标**：用户 10 秒内理解产品价值，3 秒内找到下载入口。

#### 3.4.1 布局结构

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. Hero 区域（120px 上下间距，深色背景或渐变色）                   │
│    ┌─────────────────────────────────────────────────────────┐   │
│    │                                                         │   │
│    │    🖼️ 主视觉（应用截图或插画，居中）                      │   │
│    │                                                         │   │
│    │    让 AI 编程触手可及                                     │   │
│    │    ────────────────────────────────────                  │   │
│    │                                                         │   │
│    │    Codex Switch 帮你突破网络限制，                        │   │
│    │    在国内流畅使用 Codex 和 Claude，接入 DeepSeek，        │   │
│    │    免费、快速、本地安全。                                  │   │
│    │                                                         │   │
│    │    ┌──────────────────┐  ┌──────────────────┐           │   │
│    │    │  🍎 下载 macOS    │  │  🪟 下载 Windows  │           │   │
│    │    │     v1.4.0       │  │     v1.4.0       │           │   │
│    │    └──────────────────┘  └──────────────────┘           │   │
│    │                                                         │   │
│    │    支持 macOS 11+ · Windows 10+ · Linux                  │   │
│    │    完全免费 · 开源 · MIT License                         │   │
│    │                                                         │   │
│    └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│ 2. 价值主张区（64px 上下间距）                                    │
│    ┌─────────────────────────────────────────────────────────┐   │
│    │             为什么选择 Codex Switch？                    │   │
│    │                                                         │   │
│    │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │   │
│    │  │          │  │          │  │          │              │   │
│    │  │  🔌      │  │  🧠      │  │  🛡️      │              │   │
│    │  │ 一键接入  │  │ 多模型   │  │ 本地安全 │              │   │
│    │  │          │  │          │  │          │              │   │
│    │  │ 自动配置  │  │ DeepSeek │  │ 数据不出 │              │   │
│    │  │ 代理，    │  │ 全系列   │  │ 本机，   │              │   │
│    │  │ 无需手动  │  │ 模型     │  │ 本地代理 │              │   │
│    │  │ 设置任何  │  │ 随意切换 │  │ 转发请求 │              │   │
│    │  │ 网络参数  │  │          │  │          │              │   │
│    │  └──────────┘  └──────────┘  └──────────┘              │   │
│    └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│ 3. 支持工具展示区（64px 上下间距）                                │
│    ┌─────────────────────────────────────────────────────────┐   │
│    │           支持你熟悉的 AI 编程工具                        │   │
│    │                                                         │   │
│    │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐          │   │
│    │  │ 图标   │ │ 图标   │ │ 图标   │ │ 图标   │          │   │
│    │  │Codex   │ │Codex   │ │Claude  │ │Claude  │          │   │
│    │  │ CLI    │ │Desktop │ │CLI     │ │Desktop │          │   │
│    │  └────────┘ └────────┘ └────────┘ └────────┘          │   │
│    │                                                         │   │
│    │  + Node.js  ·  Git  ·  更多即将支持                      │   │
│    └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│ 4. 用户故事区（64px 上下间距）                                    │
│    ┌─────────────────────────────────────────────────────────┐   │
│    │                                                         │   │
│    │    "以前下载 Codex 要等半小时，太痛苦了。                  │   │
│    │     现在用 Codex Switch 几分钟就搞定。"                   │   │
│    │                       — 某后端开发工程师                  │   │
│    │                                                         │   │
│    │    "作为一个非技术背景的 PM，我居然也能自己                │   │
│    │     装好 AI 编程工具了，太神奇了。"                       │   │
│    │                       — 某产品经理                       │   │
│    │                                                         │   │
│    └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│ 5. 底部 CTA 区（80px 上下间距）                                   │
│    ┌─────────────────────────────────────────────────────────┐   │
│    │                                                         │   │
│    │        准备好开始了吗？                                   │   │
│    │                                                         │   │
│    │        ┌──────────────────────┐                          │   │
│    │        │     免费下载          │                          │   │
│    │        └──────────────────────┘                          │   │
│    │                                                         │   │
│    └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│ 6. 页脚                                                          │
└──────────────────────────────────────────────────────────────────┘
```

#### 3.4.2 交互细节

| 元素 | 行为 |
|------|------|
| 导航栏 | 初始透明，滚动过 Hero 后显示毛玻璃背景 |
| 下载按钮 | hover: `scale(1.02)` + `box-shadow` 加深；active: `scale(0.98)` |
| 功能卡片 | hover: `translateY(-4px)` + 阴影展开；transition: 0.3s |
| 工具图标卡片 | hover: 上浮 + 轻微放大；无点击跳转 |
| 用户故事 | 可选：自动轮播（5s），或静态排列（移动端） |
| CTA 按钮 | 点击滚动到下载区域或跳转下载页 |
| 全页 | 平滑滚动 `scroll-behavior: smooth` |

### 3.5 下载页 `/download` 详细设计

**页面目标**：用户快速找到对应平台的安装包，清楚了解版本信息和系统要求。

#### 3.5.1 布局结构

```
┌──────────────────────────────────────────────────────────────┐
│ 下载 Codex Switch                                            │
│ ─────────────────                                            │
│ 选择你的平台开始使用                                          │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │  平台分段控件 (Segmented Control)                         │ │
│ │  ┌─────────────┬──────────────┬──────────┐              │ │
│ │  │   🍎 macOS   │  🪟 Windows  │  🐧 Linux │              │ │
│ │  └─────────────┴──────────────┴──────────┘              │ │
│ │  （蓝色滑块指示器在选中平台下方滑动）                      │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │                    v1.4.0                                 │ │
│ │                                                          │ │
│ │  发布于 2026-06-05                                       │ │
│ │                                                          │ │
│ │  ┌────────────────────────────────────────────────────┐  │ │
│ │  │                ⬇️  下载 .dmg                        │  │ │
│ │  │                124 MB                              │  │ │
│ │  └────────────────────────────────────────────────────┘  │ │
│ │                                                          │ │
│ │  适用：Intel 芯片 · Apple Silicon（通用二进制）            │ │
│ │                                                          │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ 系统要求                                                     │
│ ─────────                                                    │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │  macOS 11.0 及以上                                        │ │
│ │  4 GB RAM 及以上                                          │ │
│ │  100 MB 可用磁盘空间                                       │ │
│ │  需要网络连接（用于代理 DeepSeek API）                      │ │
│ └──────────────────────────────────────────────────────────┘ │
│                                                              │
│ ──                                                           │
│ 历史版本 ▾                                                   │
│ ┌──────────────────────────────────────────────────────────┐ │
│ │  v1.3.0    2026-05-20    122 MB    下载                  │ │
│ │  v1.2.0    2026-05-10    118 MB    下载                  │ │
│ │  v1.1.0    2026-04-28    115 MB    下载                  │ │
│ └──────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

#### 3.5.2 分段控件设计

```
┌────────────────────────────────────────────────┐
│  ┌──────────┬──────────┬──────────┐            │
│  │   macOS  │ Windows  │  Linux   │            │
│  │ ──────── │          │          │            │
│  │  (蓝色)  │          │          │            │
│  └──────────┴──────────┴──────────┘            │
│                                                │
│  选中态：蓝色文字 + 底部蓝色指示条               │
│  未选中：灰色文字 + 无指示条                     │
│  切换动画：指示条滑动 transition 0.3s           │
│                                                │
│  背景：#e8e8ed（iOS 分段控件标准色）             │
│  圆角：8px                                     │
│  内边距：2px                                   │
└────────────────────────────────────────────────┘
```

#### 3.5.3 交互细节

| 元素 | 行为 |
|------|------|
| 平台切换 | 点击切换，自动更新下方版本信息、文件类型、系统要求 |
| 下载按钮 | 点击直接下载，按钮短暂变为"正在下载..." + spinner 动画 |
| 历史版本 | 使用 `<details>` / `<summary>` 折叠，无需 JS |
| 页面加载 | 默认选中用户当前 OS（通过 User-Agent 判断，或默认 macOS） |
| 下载计数 | 下载完成后异步 POST 记录（fire-and-forget） |

### 3.6 使用指南页 `/guide` 详细设计

**页面目标**：帮助用户从下载到成功使用完成全流程。

#### 3.6.1 布局结构

```
┌──────────────────────────────────────────────────────────────────┐
│  使用指南                                                        │
│                                                                  │
│  ┌─── 侧边栏（sticky）───┐ ┌─── 内容区 ───────────────────────┐  │
│  │                       │ │                                   │  │
│  │  ● 1. 下载安装        │ │  📥 第一步：下载安装               │  │
│  │  ○ 2. 获取 API Key   │ │                                   │  │
│  │  ○ 3. 启动代理        │ │  1. 前往下载页选择你的平台         │  │
│  │  ○ 4. 配置 Codex CLI │ │  2. 下载对应版本的安装包           │  │
│  │  ○ 5. 配置 Claude     │ │  3. macOS: 打开 .dmg，拖入应用文件夹│  │
│  │  ○ 6. 常见问题        │ │     Windows: 运行 .exe 安装向导    │  │
│  │                       │ │  4. 首次启动会弹出配置向导          │  │
│  │  当前高亮指示         │ │                                   │  │
│  │  平滑滚动跟踪         │ │  ┌─ 截图或动图 ─────────────────┐  │  │
│  │                       │ │  │ [安装过程截图]               │  │  │
│  │                       │ │  └─────────────────────────────┘  │  │
│  └───────────────────────┘ └───────────────────────────────────┘  │
│                                                                  │
│  （每个步骤章节 continue...）                                     │
│                                                                  │
│  ## 📥 第一步：下载安装                                           │
│  ## 🔑 第二步：获取 DeepSeek API Key                              │
│  ## 🚀 第三步：启动代理                                           │
│  ## 💻 第四步：配置 Codex CLI / Desktop                           │
│  ## 🧠 第五步：配置 Claude CLI / Desktop                          │
│  ## ❓ 第六步：常见问题 FAQ                                       │
└──────────────────────────────────────────────────────────────────┘
```

#### 3.6.2 侧边栏行为

```
侧边栏规范：
  position: sticky; top: 80px（导航栏高度 + 偏移）
  最大宽度：220px
  桌面端显示，移动端隐藏（内容区独立滚动）

步骤状态：
  ● 当前阅读中的步骤 — 蓝色文字 + 左侧蓝色指示条
  ○ 未阅读步骤 — 灰色文字
  ✓ 已完成步骤（可选） — 可选实现

实现方式：
  使用 Intersection Observer 监听内容区各 section
  滚动进入视口时更新侧边栏高亮
  降级：无 JS 时所有步骤直接可见，无高亮效果
```

#### 3.6.3 内容区设计

- 每步骤一个 `<section>` 带 id
- 图文混排：文字说明 + 屏幕截图/示意图
- 代码块：深色背景 + SF Mono 字体 + 右上角复制按钮
- 注意事项用蓝色左边框 blockquote 标注

```
┌────────────────────────────────────────────┐
│ ⚠️ 注意                                    │
│                                             │
│ 请确保 DeepSeek API Key 已正确填入，        │
│ 否则代理无法正常工作。                      │
└────────────────────────────────────────────┘
```

### 3.7 运营后台 `/admin` 详细设计

**页面目标**：管理员一眼看到核心运营指标，了解用户行为和产品使用情况。

#### 3.7.1 登录页

```
┌──────────────────────────────────────────┐
│                                          │
│          Codex Switch 运营后台            │
│                                          │
│  ┌────────────────────────────────────┐  │
│  │  管理员 Token                      │  │
│  │  ┌──────────────────────────────┐  │  │
│  │  │ 输入 Token ...               │  │  │
│  │  └──────────────────────────────┘  │  │
│  │                                    │  │
│  │  ┌──────────────────────────────┐  │  │
│  │  │          登  录               │  │  │
│  │  └──────────────────────────────┘  │  │
│  └────────────────────────────────────┘  │
│                                          │
│  （极简设计，仅 Token 输入，无用户名密码） │
└──────────────────────────────────────────┘
```

#### 3.7.2 仪表盘

```
┌──────────────────────────────────────────────────────────────┐
│  Codex Switch 运营后台                     [退出登录]          │
│ ──────────────────────────────────────────────────────────── │
│                                                              │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐         │
│  │   📥 总下载量  │ │  👤 活跃用户  │ │  📊 今日事件  │         │
│  │              │ │              │ │              │         │
│  │   12,345     │ │   3,892      │ │   1,203      │         │
│  │              │ │              │ │              │         │
│  │  较上月 +15% │ │  较上月 +8%  │ │  较昨日 +5%  │         │
│  └──────────────┘ └──────────────┘ └──────────────┘         │
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │  📈 下载趋势（7 天 / 30 天 / 90 天）                      ││
│  │                                                          ││
│  │  [Chart.js 折线图]                                        ││
│  │  X 轴：日期    Y 轴：下载次数                              ││
│  │  双线：codex-switch 下载 · 工具包下载                       ││
│  └──────────────────────────────────────────────────────────┘│
│                                                              │
│  ┌──────────────────────────┐ ┌─────────────────────────────┐│
│  │ 📊 平台分布（环形图）     │ │ 📊 功能使用 TOP5（柱状图）   ││
│  │                          │ │                             ││
│  │ macOS    65% ████████    │ │ 1. 启动代理    ████████████ ││
│  │ Windows  30% ████        │ │ 2. Codex CLI   ██████████   ││
│  │ Linux     5% █           │ │ 3. Claude CLI  ████████     ││
│  │                          │ │ 4. 模型切换    ██████       ││
│  │                          │ │ 5. 配置导出    ████         ││
│  └──────────────────────────┘ └─────────────────────────────┘│
│                                                              │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ 📋 最近事件                                               ││
│  │                                                          ││
│  │ 时间        客户端 ID       事件类型     平台    版本     ││
│  │ ─────────  ───────────────  ──────────  ──────  ──────   ││
│  │ 10:32:15   abc123def456     proxy_start  macOS   1.4.0   ││
│  │ 10:31:02   xyz789ghi012     model_call   Win     1.4.0   ││
│  │ ...                                                      ││
│  └──────────────────────────────────────────────────────────┘│
└──────────────────────────────────────────────────────────────┘
```

#### 3.7.3 数据刷新

- 页面加载时获取最新数据
- 手动刷新按钮（不自动轮询，保持简单）
- 时间范围切换按钮组：7 天 / 30 天 / 90 天

### 3.8 响应式策略

| 断点 | 宽度 | 布局变化 |
|------|------|---------|
| 桌面 | ≥ 980px | 标准布局，最大内容宽度 980px 居中，三列卡片 |
| 平板 | 768–979px | 两列卡片，Hero 字号缩至 40px，导航简化 |
| 手机 | < 768px | 单列堆叠，Hero 字号 32px，导航改汉堡菜单，侧边栏隐藏 |

### 3.9 浏览器支持

- macOS: Safari 16+, Chrome 120+, Firefox 120+
- Windows: Edge 120+, Chrome 120+
- 移动端: Safari iOS 16+, Chrome Android 120+

CSS 特性降级策略：
- `backdrop-filter`：不支持时回退为纯色半透明背景
- `scroll-behavior: smooth`：不支持时无平滑滚动（功能无损）
- Intersection Observer：不支持时侧边栏无高亮（内容仍完整可读）

---

## 4. API 接口设计

### 4.1 通用规范

```
Base URL: https://www.codexswtich.cloud/api/v1

请求头：
  Content-Type: application/json
  Accept: application/json
  User-Agent: CodexSwitch/<version> (<platform>)

响应格式：
  {
    "code": 0,        // 0=成功, 非0=错误
    "message": "ok",
    "data": { ... }
  }

错误响应：
  {
    "code": 40001,
    "message": "版本号格式不正确",
    "data": null
  }

HTTP 状态码：
  200  成功
  400  请求参数错误
  401  未认证
  404  资源不存在
  429  请求过于频繁
  500  服务器内部错误
```

### 4.2 版本更新 API

#### 4.2.1 检查更新

```
POST /api/v1/update/check

请求体：
  {
    "current_version": "1.3.0",   // 当前客户端版本号
    "platform": "macos",           // macos | windows | linux
    "arch": "arm64",               // x64 | arm64
    "client_id": "abc123def456"    // 客户端唯一标识（用于统计）
  }

成功响应（有新版本）：
  {
    "code": 0,
    "message": "ok",
    "data": {
      "has_update": true,
      "latest_version": "1.4.0",
      "release_date": "2026-06-05",
      "release_notes": "## v1.4.0\n\n- 新增 Claude Desktop 支持\n- 修复...",
      "download_url": "https://www.codexswtich.cloud/api/v1/update/download/1.4.0/macos-arm64",
      "file_size": 130023424,
      "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
      "is_critical": false
    }
  }

成功响应（已是最新）：
  {
    "code": 0,
    "message": "ok",
    "data": {
      "has_update": false,
      "latest_version": "1.3.0"
    }
  }
```

#### 4.2.2 下载安装包

```
GET /api/v1/update/download/{version}/{platform}-{arch}

路径参数：
  version: "1.4.0"
  platform: "macos" | "windows" | "linux"
  arch: "x64" | "arm64"

响应：
  Content-Type: application/octet-stream
  Content-Disposition: attachment; filename="codex-switch-1.4.0-arm64.dmg"
  Content-Length: 130023424
  X-Checksum-SHA256: e3b0c44298fc1c149afbf4c8996fb924...

  [二进制文件流]
```

### 4.3 工具包下载 API

#### 4.3.1 获取可用包列表

```
GET /api/v1/packages

响应：
  {
    "code": 0,
    "message": "ok",
    "data": {
      "packages": [
        {
          "name": "claude-desktop",
          "display_name": "Claude Desktop",
          "description": "Anthropic 官方 Claude 桌面应用",
          "latest_version": "1.2.0",
          "platforms": [
            {
              "platform": "macos",
              "arch": "arm64",
              "download_url": "https://www.codexswtich.cloud/api/v1/packages/claude-desktop/1.2.0/macos-arm64",
              "file_size": 245123456,
              "file_type": "dmg"
            }
          ]
        },
        {
          "name": "codex-desktop",
          "display_name": "Codex Desktop",
          "description": "OpenAI 官方 Codex 桌面应用",
          "latest_version": "2.1.0",
          "platforms": [...]
        },
        {
          "name": "nodejs",
          "display_name": "Node.js",
          "description": "JavaScript 运行时（Codex CLI 依赖）",
          "latest_version": "22.12.0",
          "platforms": [...]
        },
        {
          "name": "git",
          "display_name": "Git",
          "description": "版本控制工具（Claude Code CLI 依赖）",
          "latest_version": "2.47.0",
          "platforms": [...]
        }
      ]
    }
  }
```

#### 4.3.2 下载工具包

```
GET /api/v1/packages/{package_name}/{version}/{platform}-{arch}

路径参数：
  package_name: "claude-desktop" | "codex-desktop" | "nodejs" | "git"
  version: "1.2.0"
  platform: "macos" | "windows" | "linux"
  arch: "x64" | "arm64"

响应：
  Content-Type: application/octet-stream
  Content-Disposition: attachment; filename="claude-desktop-1.2.0-arm64.dmg"
  [二进制文件流]
```

### 4.4 遥测 API

#### 4.4.1 上报事件（批量）

```
POST /api/v1/telemetry/events

请求体：
  {
    "client_id": "abc123def456",
    "app_version": "1.4.0",
    "platform": "macos",
    "arch": "arm64",
    "os_version": "14.5",
    "events": [
      {
        "event_type": "proxy_start",       // 事件类型
        "timestamp": "2026-06-05T10:32:15Z",
        "properties": {                     // 事件属性（可扩展）
          "port": 11435,
          "model": "deepseek-v4-flash"
        }
      },
      {
        "event_type": "model_call",
        "timestamp": "2026-06-05T10:35:22Z",
        "properties": {
          "model": "deepseek-v4-flash",
          "streaming": true,
          "input_tokens": 1234,
          "output_tokens": 567
        }
      }
    ]
  }

响应：
  {
    "code": 0,
    "message": "ok",
    "data": {
      "accepted": 2,
      "rejected": 0
    }
  }

事件类型枚举：
  app_start         应用启动
  app_close         应用关闭
  proxy_start       代理启动
  proxy_stop        代理停止
  proxy_error       代理错误
  model_call        模型调用
  config_write      配置写入（Codex/Claude）
  tool_install      工具安装成功
  tool_install_fail 工具安装失败
  update_check      检查更新
  update_download   开始下载更新
  error             应用错误
```

#### 4.4.2 客户端去重

- 服务端按 `(client_id, event_type, timestamp)` 三元组去重
- 同一客户端同一事件类型同一秒内只记录一次
- 防止客户端重试导致重复计数

### 4.5 管理员 API（/admin 路由）

#### 4.5.1 登录

```
POST /admin/login

请求体：
  {
    "token": "admin-secret-token"
  }

成功：
  Set-Cookie: admin_session=<jwt>; HttpOnly; Secure; SameSite=Strict
  302 → /admin

失败：
  401 Unauthorized
```

#### 4.5.2 仪表盘数据

```
GET /admin/api/stats?range=7d

Query:
  range: "7d" | "30d" | "90d"

响应：
  {
    "total_downloads": 12345,
    "active_users": 3892,
    "today_events": 1203,
    "download_trend": [
      {"date": "2026-05-30", "app_downloads": 45, "package_downloads": 120},
      {"date": "2026-05-31", "app_downloads": 52, "package_downloads": 135},
      ...
    ],
    "platform_distribution": [
      {"platform": "macos", "count": 8025},
      {"platform": "windows", "count": 3703},
      {"platform": "linux", "count": 617}
    ],
    "top_events": [
      {"event_type": "proxy_start", "count": 12000},
      {"event_type": "model_call", "count": 95000},
      ...
    ],
    "recent_events": [
      {
        "timestamp": "2026-06-05T10:32:15Z",
        "client_id": "abc123***",    // 脱敏：只显示前 6 位
        "event_type": "proxy_start",
        "platform": "macos",
        "app_version": "1.4.0"
      },
      ...
    ]
  }
```

---

## 5. 数据库设计

### 5.1 ER 图

```
┌─────────────────────┐
│     releases         │
├─────────────────────┤
│ PK id: INTEGER       │
│    version: TEXT     │
│    release_date: DATE│
│    release_notes: TEXT│
│    is_critical: BOOL │
│    files: JSON       │  ← [{"platform":"macos","arch":"arm64","size":...,"sha256":"...","path":"..."}]
│    created_at: DATETIME│
└──────────┬──────────┘
           │
           │ 1:N
           ▼
┌─────────────────────┐
│   download_records   │
├─────────────────────┤
│ PK id: INTEGER       │
│ FK release_id: INT   │
│    client_id: TEXT   │
│    package_name: TEXT│  ← NULL 表示下载的是 codex-switch 本身
│    platform: TEXT    │
│    arch: TEXT        │
│    ip_hash: TEXT     │  ← IP 哈希（非原始 IP）
│    user_agent: TEXT  │
│    downloaded_at: DATETIME│
└─────────────────────┘

┌─────────────────────┐
│  telemetry_events    │
├─────────────────────┤
│ PK id: INTEGER       │
│    client_id: TEXT   │
│    event_type: TEXT  │
│    timestamp: DATETIME│
│    properties: JSON  │
│    app_version: TEXT │
│    platform: TEXT    │
│    arch: TEXT        │
│    os_version: TEXT  │
│    created_at: DATETIME│
│                      │
│ INDEX: (client_id, event_type, timestamp) ← 去重查询
│ INDEX: (event_type) ← 聚合统计
│ INDEX: (created_at) ← 时间范围查询
└─────────────────────┘
```

### 5.2 建表 SQL

```sql
-- 版本发布表
CREATE TABLE releases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version TEXT NOT NULL UNIQUE,
    release_date DATE NOT NULL,
    release_notes TEXT NOT NULL DEFAULT '',
    is_critical BOOLEAN NOT NULL DEFAULT FALSE,
    files JSON NOT NULL DEFAULT '[]',
    created_at DATETIME NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_releases_version ON releases(version);

-- 下载记录表
CREATE TABLE download_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    release_id INTEGER REFERENCES releases(id),
    client_id TEXT NOT NULL DEFAULT '',
    package_name TEXT,
    platform TEXT NOT NULL,
    arch TEXT NOT NULL,
    ip_hash TEXT NOT NULL DEFAULT '',
    user_agent TEXT NOT NULL DEFAULT '',
    downloaded_at DATETIME NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_downloads_date ON download_records(downloaded_at);
CREATE INDEX idx_downloads_package ON download_records(package_name);

-- 遥测事件表
CREATE TABLE telemetry_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp DATETIME NOT NULL,
    properties JSON NOT NULL DEFAULT '{}',
    app_version TEXT NOT NULL DEFAULT '',
    platform TEXT NOT NULL DEFAULT '',
    arch TEXT NOT NULL DEFAULT '',
    os_version TEXT NOT NULL DEFAULT '',
    created_at DATETIME NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_telemetry_client ON telemetry_events(client_id);
CREATE INDEX idx_telemetry_type ON telemetry_events(event_type);
CREATE INDEX idx_telemetry_created ON telemetry_events(created_at);
CREATE UNIQUE INDEX idx_telemetry_dedup
    ON telemetry_events(client_id, event_type, timestamp);
```

### 5.3 数据保留策略

| 数据表 | 保留期限 | 清理策略 |
|--------|---------|---------|
| releases | 永久 | 保留所有历史版本元数据 |
| download_records | 90 天 | 定时清理（lifespan 事件中检查） |
| telemetry_events | 90 天 | 定时清理，保留聚合数据 |

---

## 6. 代码模块设计

### 6.1 模块职责速查表

| 模块 | 职责 | 依赖 |
|------|------|------|
| `src/main.py` | `create_app()` 工厂，注册路由/中间件/lifespan | config, database, 各 router |
| `src/config.py` | 从 .env 读取所有配置，Pydantic 校验 | pydantic-settings |
| `src/database.py` | 创建 SQLAlchemy async engine + async session factory | config |
| `src/models/base.py` | `DeclarativeBase` 基类 | SQLAlchemy |
| `src/models/release.py` | `Release` ORM Model | base |
| `src/models/download.py` | `DownloadRecord` ORM Model | base |
| `src/models/telemetry.py` | `TelemetryEvent` ORM Model | base |
| `src/schemas/` | Pydantic Request/Response Schema | Pydantic |
| `src/api/deps.py` | `get_db()`, `verify_admin_token()` | database, config |
| `src/api/router.py` | 聚合所有子路由 | v1.update, v1.packages, v1.telemetry |
| `src/api/v1/update.py` | 版本检查、下载端点 | services.release_sync, schemas |
| `src/api/v1/packages.py` | 工具包列表、下载端点 | services.release_sync, schemas |
| `src/api/v1/telemetry.py` | 遥测上报端点 | services.telemetry, schemas |
| `src/services/release_sync.py` | 版本检测、同步、缓存、清理、查询 | models, utils.http, utils.storage |
| `src/services/telemetry.py` | 事件验证、去重、写入、聚合统计 | models |
| `src/portal/router.py` | / /download /guide 页面渲染 | services.release_sync |
| `src/admin/router.py` | /admin /admin/login 后台路由 | services.telemetry, config |
| `src/utils/http.py` | httpx 封装（重试、限速、超时） | httpx, config |
| `src/utils/storage.py` | 文件存储抽象（本地 + COS） | config |

### 6.2 Service 层详细设计

#### ReleaseSyncService

```python
# 伪代码接口

class ReleaseSyncService:
    """版本同步服务。"""

    def __init__(self, db: AsyncSession, http: HttpClient, storage: Storage):
        ...

    async def check_for_updates(self, current_version: str, platform: str, arch: str) -> UpdateCheckResult:
        """检查是否有新版本。对比请求版本与数据库最新版本。"""
        ...

    async def sync_from_github(self) -> SyncResult:
        """从 GitHub Releases API 检查新版本，下载文件到本地。返回同步结果（新增版本数）。"""
        ...

    async def get_latest_release(self) -> Release | None:
        """获取最新已缓存版本。"""
        ...

    async def get_releases(self, limit: int = 20) -> list[Release]:
        """获取最近版本列表。"""
        ...

    async def get_download_path(self, version: str, platform: str, arch: str) -> Path:
        """获取安装包文件路径。"""
        ...

    async def record_download(self, version: str, platform: str, arch: str, client_id: str, request) -> None:
        """记录下载事件。"""
        ...

    async def get_download_stats(self, range_days: int) -> DownloadStats:
        """获取下载统计数据。"""
        ...

    async def cleanup_old_files(self, keep_versions: int = 5) -> int:
        """清理旧版本文件，保留最近 N 个版本。返回清除的文件数。"""
        ...
```

#### TelemetryService

```python
# 伪代码接口

class TelemetryService:
    """遥测服务。"""

    def __init__(self, db: AsyncSession):
        ...

    async def ingest_events(self, payload: TelemetryPayload) -> IngestResult:
        """批量写入事件。自动去重：同一 (client_id, event_type, timestamp) 只写一次。"""
        ...

    async def get_event_counts(self, range_days: int) -> list[EventCount]:
        """按事件类型聚合计数。"""
        ...

    async def get_daily_trend(self, range_days: int) -> DailyTrend:
        """按天聚合的下载量和事件数趋势。"""
        ...

    async def get_platform_distribution(self) -> list[PlatformCount]:
        """各平台用户分布。"""
        ...

    async def get_recent_events(self, limit: int = 50) -> list[TelemetryEvent]:
        """最近事件列表（client_id 脱敏）。"""
        ...

    async def get_active_users(self, range_days: int) -> int:
        """活跃用户数（去重 client_id）。"""
        ...
```

### 6.3 Utils 层设计

#### HttpClient（`utils/http.py`）

```python
# 伪代码接口

class HttpClient:
    """HTTP 客户端封装。"""

    def __init__(self, base_url: str = "", timeout: int = 30, max_retries: int = 3):
        ...

    async def get(self, path: str, **kwargs) -> Response:
        """GET 请求，自动重试。"""
        ...

    async def download(self, url: str, dest: Path, progress_callback=None) -> Path:
        """流式下载大文件到指定路径，支持进度回调。"""
        ...

    async def get_json(self, path: str) -> dict:
        """GET + 解析 JSON。"""
        ...
```

#### Storage（`utils/storage.py`）

```python
# 伪代码接口

class Storage(ABC):
    """存储抽象基类。"""

    async def put(self, local_path: Path, remote_key: str) -> str:
        """上传文件，返回访问 URL 或本地路径。"""
        ...

    async def get(self, remote_key: str) -> Path | None:
        """获取文件本地路径。"""
        ...

    async def delete(self, remote_key: str) -> bool:
        """删除文件。"""
        ...

    async def exists(self, remote_key: str) -> bool:
        """检查文件是否存在。"""
        ...


class LocalStorage(Storage):
    """本地文件存储。数据存储在 data/ 目录。"""
    ...


class COSStorage(Storage):
    """腾讯云 COS 对象存储（生产环境）。"""
    ...
```

### 6.4 Lifespan 事件

```python
# src/main.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时
    init_db()                          # 创建表
    start_background_tasks()           # 启动定时任务（如有）

    yield

    # 关闭时
    await close_db()                   # 关闭数据库连接
```

### 6.5 后台任务

```python
# 轻量级：在 lifespan 中用 asyncio.create_task 启动
# 不引入 Celery / APScheduler，保持简单

async def periodic_sync():
    """定时检查 GitHub 新版本。"""
    while True:
        try:
            async with db_session() as db:
                service = ReleaseSyncService(db, http, storage)
                await service.sync_from_github()
        except Exception:
            logger.exception("Sync task failed")
        await asyncio.sleep(3600)  # 每小时检查一次

async def periodic_cleanup():
    """定时清理旧版本文件和过期数据。"""
    while True:
        try:
            async with db_session() as db:
                service = ReleaseSyncService(db, http, storage)
                await service.cleanup_old_files(keep_versions=5)
                await cleanup_old_records(db, days=90)
        except Exception:
            logger.exception("Cleanup task failed")
        await asyncio.sleep(86400)  # 每天清理一次
```

---

## 7. 安全设计

### 7.1 威胁模型与对策

| 威胁 | 风险等级 | 对策 |
|------|---------|------|
| 管理员后台被未授权访问 | 高 | Bearer Token 认证（.env 配置），HTTPS 传输，失败 5 次锁定 15 分钟 |
| 遥测 API 被滥用（伪造数据） | 中 | client_id 校验、事件类型白名单、请求频率限制（每客户端每分钟 60 条） |
| 安装包被篡改 | 高 | 下载时返回 SHA256，客户端校验；服务端同步时从 GitHub 校验 |
| SQL 注入 | 低 | SQLAlchemy ORM 参数化查询，无原始 SQL |
| 敏感信息泄露 | 中 | .env 不入 git，日志不记录 token/IP，admin 页面 client_id 脱敏 |
| DDoS / 资源耗尽 | 中 | Docker 容器内存限制 + 限速中间件（slowapi），大文件走 COS CDN |
| 路径遍历攻击 | 高 | 下载路径严格校验，`platform` 和 `arch` 必须是枚举值 |

### 7.2 管理员认证流程

```
1. 用户 POST /admin/login { "token": "xxx" }
2. 服务端对比 .env 中的 ADMIN_TOKEN
3. 匹配 → 签发 session cookie（itsdangerous 签名，24h 过期）
4. 不匹配 → 401，记录失败次数
5. 后续请求 → admin 路由依赖 verify_admin_token() 验证 cookie
```

### 7.3 数据脱敏规范

| 字段 | 脱敏方式 | 示例 |
|------|---------|------|
| client_id | 仅显示前 6 位 + `***` | `abc123***` |
| IP 地址 | SHA256 哈希后只存 hash | 不存原始 IP |
| API Key | 完全不记录 | — |
| Admin Token | 仅存于 .env，不出现于日志 | — |

---

## 8. 部署方案

### 8.1 生产服务器环境

> 已通过 SSH 实地确认，以下为真实服务器配置。

| 项目 | 配置 |
|------|------|
| 服务器 | 腾讯云轻量应用服务器 |
| 公网 IP | 43.134.110.192 |
| OS | Ubuntu 22.04 LTS (Jammy) |
| 内核 | 5.15.0-118-generic |
| CPU | 2 核 |
| 内存 | 1.9 GB（可用约 0.8 GB） |
| 磁盘 | 50 GB（已用 23 GB，可用 25 GB） |
| Docker | 27.1.2 |
| Docker Compose | v2.29.2 |
| 域名 | **www.codexswtich.cloud** |
| 部署路径 | `/home/lighthouse/codex-switch-server/` |
| 证书路径 | `/home/lighthouse/codex-switch-server/certs/` |
| 已占用端口 | 22 (SSH)、25 (SMTP)、8388 (ss-server) |
| 目标端口 | **80 (HTTP)、443 (HTTPS)** — 上线后停掉 ajepro 释放端口 |
| SSH 用户 | ubuntu（已在 docker 组，也可操作 lighthouse 目录） |

### 8.2 部署架构（Docker 单容器 + Nginx SSL）

> 参照已在服务器上稳定运行 2 个月的 ajepro (docker-compose) 配置模式：**Nginx + 应用共处同一容器，由 Supervisor 管理双进程**。
> 上线后，ajepro 容器停止，codex-switch-server 接管 80/443 端口。

```
互联网
  │
  │  HTTPS :443（SSL 终止于 Nginx）
  │  HTTP  :80（301 → HTTPS）
  ▼
┌──────────────────────────────────────────────────────┐
│  Docker Container: codex-switch-server               │
│                                                      │
│  Supervisor 管理双进程：                              │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  Nginx (:80, :443)                            │  │
│  │  · SSL 终止（证书挂载自宿主机 certs/ 目录）    │  │
│  │  · 静态文件直接 serve（/static/）              │  │
│  │  · 大文件下载（/api/v1/update/download/）     │  │
│  │  · 反向代理 API 请求 → uvicorn               │  │
│  │  · HTTP :80 → 301 HTTPS                       │  │
│  └────────────────────┬───────────────────────────┘  │
│                       │ proxy_pass                   │
│                       ▼ 127.0.0.1:8000               │
│  ┌────────────────────────────────────────────────┐  │
│  │  uvicorn (:8000, 仅 localhost)                 │  │
│  │  · workers: 1                                  │  │
│  │  · Jinja2 模板渲染                              │  │
│  │  · API 业务逻辑                                 │  │
│  │  · StreamingResponse 大文件流                   │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  ┌────────────────────────────────────────────────┐  │
│  │  /app/data/                                    │  │
│  │  ├── app.db         (SQLite, volume 持久化)     │  │
│  │  └── packages/      (安装包缓存, volume 持久化) │  │
│  └────────────────────────────────────────────────┘  │
│                                                      │
│  Volume mounts:                                      │
│    ./certs → /etc/nginx/ssl:ro  (SSL 证书，只读)     │
│    ./data  → /app/data          (数据库 + 安装包)    │
│                                                      │
│  Port mapping:                                       │
│    0.0.0.0:80  → 80   (Nginx HTTP → HTTPS 重定向)   │
│    0.0.0.0:443 → 443  (Nginx HTTPS 主服务)          │
│                                                      │
│  Restart: unless-stopped                             │
└──────────────────────────────────────────────────────┘
```

**设计要点**：
- **Nginx 负责**：SSL 终止、静态文件直送、大文件高效传输、HTTP→HTTPS 重定向、反向代理
- **uvicorn 负责**：业务逻辑、Jinja2 渲染、API 处理
- **Supervisor 负责**：管理 Nginx + uvicorn 双进程，进程崩溃自动重启
- **证书管理**：证书文件放在宿主机 `./certs/`，以只读方式挂载到容器，更新证书只需替换宿主机文件后重启容器
- **零外部依赖**：无需安装系统级 Nginx、无需 systemd 服务
- **与 ajepro 共存切换**：ajepro 停止 → codex-switch-server 启动，端口无缝接替

### 8.3 Dockerfile

```dockerfile
# Dockerfile — codex-switch-server
# 位于项目根目录
# 参照 ajepro 的 Nginx + Supervisor 多进程容器模式

FROM python:3.12-slim

# 安装 Nginx + Supervisor + 基础工具
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        nginx \
        supervisor \
        ca-certificates \
        curl && \
    rm -rf /var/lib/apt/lists/* && \
    rm -f /etc/nginx/sites-enabled/default

# 安装 uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# 先复制依赖文件，利用 Docker 缓存层
COPY pyproject.toml uv.lock* ./

# 安装 Python 依赖（生产模式，不含 dev）
RUN uv sync --frozen --no-dev

# 复制源代码
COPY src/ ./src/

# 复制 Docker 配置文件
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/supervisord.conf /etc/supervisor/conf.d/supervisord.conf
COPY docker/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# 创建数据目录和 SSL 目录
RUN mkdir -p /app/data /etc/nginx/ssl /var/log/supervisor

# 暴露端口
EXPOSE 80 443

# 健康检查（通过 Nginx HTTP 端口检查）
HEALTHCHECK --interval=30s --timeout=5s --retries=3 --start-period=10s \
    CMD curl -f http://localhost/ || exit 1

# Supervisor 启动（管理 Nginx + uvicorn）
ENTRYPOINT ["/app/entrypoint.sh"]
```

### 8.4 容器内配置文件

#### 8.4.1 Nginx 配置（`docker/nginx.conf`）

```nginx
# HTTP → HTTPS 301 重定向
server {
    listen 80;
    server_name www.codexswtich.cloud codexswtich.cloud;
    return 301 https://$host$request_uri;
}

# HTTPS 主服务
server {
    listen 443 ssl;
    server_name www.codexswtich.cloud codexswtich.cloud;
    charset utf-8;

    # SSL 证书（挂载自宿主机 certs/ 目录，只读）
    ssl_certificate     /etc/nginx/ssl/codexswtich.cloud_bundle.crt;
    ssl_certificate_key /etc/nginx/ssl/codexswtich.cloud.key;

    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;

    # Gzip 压缩
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml text/javascript image/svg+xml;
    gzip_min_length 1024;

    # 客户端最大上传大小
    client_max_body_size 16M;

    # ── 静态资源：Nginx 直接 serve ──
    location /static/ {
        alias /app/src/static/;
        expires 7d;
        add_header Cache-Control "public, immutable";
    }

    # ── 大文件下载：支持 Range 断点续传 ──
    location /api/v1/update/download/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_buffering off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
    }

    location /api/v1/packages/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_buffering off;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 600s;
    }

    # ── API 请求：反向代理到 uvicorn ──
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 10s;
        proxy_send_timeout 120s;
    }

    # ── 门户页面 + 管理后台：反向代理到 uvicorn ──
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 60s;
    }

    # 禁止访问隐藏文件
    location ~ /\. {
        deny all;
        access_log off;
        log_not_found off;
    }
}
```

#### 8.4.2 Supervisor 配置（`docker/supervisord.conf`）

```ini
[supervisord]
nodaemon=true
logfile=/var/log/supervisor/supervisord.log
pidfile=/var/run/supervisord.pid
user=root

[program:nginx]
command=/usr/sbin/nginx -g "daemon off;"
autostart=true
autorestart=true
startretries=3
redirect_stderr=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:uvicorn]
command=/usr/local/bin/uv run uvicorn src.main:app --host 127.0.0.1 --port 8000 --workers 1
directory=/app
autostart=true
autorestart=true
startretries=3
redirect_stderr=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
```

#### 8.4.3 入口脚本（`docker/entrypoint.sh`）

```bash
#!/bin/bash
set -e

echo "[entrypoint] Starting codex-switch-server..."

# 确保数据目录存在
mkdir -p /app/data/packages

# 检查 SSL 证书是否存在
if [ ! -f /etc/nginx/ssl/codexswtich.cloud_bundle.crt ]; then
    echo "[entrypoint] WARNING: SSL certificate not found at /etc/nginx/ssl/codexswtich.cloud_bundle.crt"
    echo "[entrypoint] HTTPS will not work. Mount certs directory to /etc/nginx/ssl:ro"
fi

# 检查环境变量
if [ -z "$ADMIN_TOKEN" ]; then
    echo "[entrypoint] WARNING: ADMIN_TOKEN is not set, admin panel will not be accessible"
fi

echo "[entrypoint] Starting supervisor (nginx + uvicorn)..."
exec /usr/bin/supervisord -c /etc/supervisor/supervisord.conf
```

### 8.5 docker-compose.yml

```yaml
# docker-compose.yml — codex-switch-server
# 位于项目根目录
# 部署路径：/home/lighthouse/codex-switch-server/

services:
  app:
    build: .
    container_name: codex-switch-server
    ports:
      - "80:80"
      - "443:443"
    volumes:
      # SSL 证书（宿主机 certs/ → 容器 /etc/nginx/ssl，只读）
      - ./certs:/etc/nginx/ssl:ro
      # 数据持久化（SQLite + 安装包缓存）
      - ./data:/app/data
    env_file:
      - .env
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### 8.6 certs/ 目录准备

证书文件来源于 `codexswtich.cloud_nginx.zip`，解压后结构：

```
certs/
├── codexswtich.cloud_bundle.crt   # 证书链（证书 + 中间证书）
├── codexswtich.cloud_bundle.pem   # PEM 格式（与 crt 相同）
├── codexswtich.cloud.key          # 私钥
└── codexswtich.cloud.csr          # 证书签名请求（部署不需要）
```

**服务器上准备步骤**：
```bash
# 在服务器上解压证书文件到 certs/ 目录
ssh ubuntu@43.134.110.192
cd /home/lighthouse/codex-switch-server
mkdir -p certs
# 将 codexswtich.cloud_nginx.zip 中的 crt 和 key 放到 certs/
# 确保 nginx.conf 引用的两个文件存在：
#   certs/codexswtich.cloud_bundle.crt
#   certs/codexswtich.cloud.key
```

### 8.7 .env（生产环境模板）

```bash
# 必填
DATABASE_URL=sqlite+aiosqlite:///app/data/app.db
ADMIN_TOKEN=<生成一个随机字符串>

# 可选 — 提高 GitHub API 速率限制（建议配置）
GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# 可选 — 未来使用腾讯云 COS 时配置
COS_SECRET_ID=
COS_SECRET_KEY=
COS_BUCKET=
COS_REGION=ap-guangzhou

# 遥测配置
TELEMETRY_MAX_EVENTS_PER_MINUTE=60
TELEMETRY_RETENTION_DAYS=90
```

### 8.8 .dockerignore

```dockerfile
# Python
__pycache__/
*.pyc
.venv/

# 本地数据（不打包进镜像，运行时通过 volume 挂载）
data/

# SSL 证书（不打包，运行时挂载）
certs/

# 测试与文档
tests/
docs/

# Docker 配置已通过 COPY 指令单独复制
# docker/ 目录中的文件在 Dockerfile 中显式 COPY

# Git
.git/
.gitignore

# 环境变量
.env
.env.local

# IDE
.vscode/
.idea/
.cursor/

# CI/CD
.github/

# 安装包缓存
*.zip
!codexswtich.cloud_nginx.zip
```

### 8.9 部署流程

#### 首次部署（上线时执行）

```bash
# === 服务器端操作 ===
ssh ubuntu@43.134.110.192

# 1. 停止旧服务 ajepro
cd /home/lighthouse/ajepro
sudo docker compose down

# 2. 确认 80/443 端口已释放
sudo ss -tlnp | grep -E ':80|:443'
# （应该无输出）

# 3. Clone 代码（或从本地 scp）
cd /home/lighthouse
git clone https://github.com/Mark7766/codex-switch-server.git
cd codex-switch-server

# 4. 准备 SSL 证书
mkdir -p certs
# 将 codexswtich.cloud_nginx.zip 上传到服务器并解压：
# unzip codexswtich.cloud_nginx.zip
# cp codexswtich.cloud_nginx/codexswtich.cloud_bundle.crt certs/
# cp codexswtich.cloud_nginx/codexswtich.cloud.key certs/

# 5. 创建 .env
cat > .env << 'EOF'
DATABASE_URL=sqlite+aiosqlite:///app/data/app.db
ADMIN_TOKEN=<your-random-token>
GITHUB_TOKEN=<your-github-token>
EOF

# 6. 构建并启动
sudo docker compose up -d --build

# 7. 验证
sudo docker compose logs -f --tail=50
# 确认看到 nginx 和 uvicorn 均已启动
curl -I https://www.codexswtich.cloud/
# 应返回 HTTP/2 200 或 301

# 8. （可选）首次版本同步
sudo docker compose exec app python -c "
import asyncio
from src.database import async_session
from src.services.release_sync import ReleaseSyncService
async def sync():
    async with async_session() as db:
        srv = ReleaseSyncService(db)
        result = await srv.sync_from_github()
        print(f'Synced {result.new_count} new releases')
asyncio.run(sync())
"
```

#### 日常更新

```bash
ssh ubuntu@43.134.110.192
cd /home/lighthouse/codex-switch-server
git pull
sudo docker compose up -d --build
sudo docker compose logs -f --tail=30
```

#### 常用运维命令

```bash
# 查看状态
sudo docker compose ps

# 查看日志
sudo docker compose logs -f --tail=100

# 重启
sudo docker compose restart

# 停止
sudo docker compose down

# 仅重启 Nginx（不重启整个容器）
sudo docker compose exec app supervisorctl restart nginx

# 仅重启 uvicorn
sudo docker compose exec app supervisorctl restart uvicorn

# 查看 supervisor 进程状态
sudo docker compose exec app supervisorctl status

# 更新 SSL 证书后重载 Nginx（无需重启容器）
# 1. 替换宿主机 certs/ 下的证书文件
# 2. sudo docker compose exec app nginx -s reload
# 3. 验证: curl -I https://www.codexswtich.cloud/

# 查看资源占用
sudo docker stats codex-switch-server

# 备份数据库
sudo cp data/app.db data/app.db.bak.$(date +%Y%m%d)
```

### 8.10 与 ajepro 的共存与切换

```
切换时间线：

  现在            上线当天          上线后
  ────────────  ─────────────────  ──────────────
  ajepro 运行    ajepro stop       codex-switch
  :80 :443      docker compose     独占 :80 :443
                down
                                  
                启动 codex-switch
                docker compose
                up -d --build

回滚方案（如果 codex-switch-server 出问题）：
  1. sudo docker compose down （停止 codex-switch-server）
  2. cd /home/lighthouse/ajepro && sudo docker compose up -d （恢复 ajepro）
  3. 80/443 端口回到 ajepro，服务不中断
```

### 8.11 服务器资源规划

```
总内存   1.9 GB
  ├── ss-server       ~50 MB   (已运行，代理)
  ├── 系统开销        ~300 MB  (内核、sshd、systemd…)
  ├── ajepro          ~500 MB  (上线前仍运行，上线后停服释放)
  ├── 预留缓冲        ~300 MB
  └── codex-switch    ~300 MB  (nginx ~20MB + uvicorn ~150MB + Python ~50MB)
      server          (ajepro 停止后实际可用 ~1.1GB)

总磁盘   50 GB
  ├── 系统 + 已有    19 GB
  └── codex-switch   ≤5 GB   (安装包缓存，保留 5 个版本)
      server data
```

**注意事项**：
- ollama 已卸载，释放 ~800MB 内存 + ~4GB 磁盘，服务器资源充足
- ajepro 停服后 codex-switch-server 独占 80/443，内存充裕
- uvicorn 单 worker（~150MB），资源宽裕后可增至 2 worker
- Nginx 作为反向代理比 uvicorn 直接 serve 更省内存（大文件零拷贝 sendfile）
- SQLite WAL 模式 + 单 worker 无并发问题
- 大文件下载走 Nginx `proxy_buffering off`，StreamingResponse 流式传输
- Docker 日志 10MB × 3 = 30MB 上限，防止磁盘写满
- SSL 证书到期前需手动更换（参考 ajepro.cn 证书约 3 个月有效期）

---

## 9. 开发计划

### 9.1 迭代策略

一人开发，采用**小步快跑**策略：
- 每个阶段产出可运行、可验证的最小版本
- 先配骨架（路由能通），再填血肉（业务逻辑），后打磨（UI 细节）
- 每完成一个阶段就部署验证，不留到最后集成

### 9.2 阶段划分

#### Phase 1：项目骨架（预计 1 天）

**目标**：项目能启动，数据库能连接，有个可访问的空白页面。

| # | 任务 | 产出 |
|---|------|------|
| 1.1 | 初始化项目结构：`pyproject.toml`、`.env.example`、`.gitignore` | 可 `uv sync && uv run uvicorn` 启动 |
| 1.2 | `src/config.py` — pydantic-settings 配置读取 | .env 中配置可读取 |
| 1.3 | `src/database.py` — SQLAlchemy async engine + session | 数据库连接正常 |
| 1.4 | `src/models/` — 4 个 ORM Model | 表创建成功 |
| 1.5 | `src/main.py` — `create_app()` 工厂 + lifespan（create_all） | 启动不报错 |
| 1.6 | `tests/conftest.py` — 测试 fixtures | `uv run pytest` 通过 |

**检查点**：`curl http://localhost:8000` 返回 404（说明服务已启动但无路由）。

#### Phase 2：公开门户（预计 2 天）

**目标**：3 个页面 HTML 可访问，Apple 风格 CSS 生效。

| # | 任务 | 产出 |
|---|------|------|
| 2.1 | `src/static/css/apple.css` — 完整 Design Token + 全局样式 | CSS 变量体系、字体、间距、颜色 |
| 2.2 | `src/portal/templates/base.html` — 页面壳（导航+页脚） | 公共布局 |
| 2.3 | `src/portal/templates/index.html` — 首页 | `/` 可访问，Hero + 卡片 + CTA |
| 2.4 | `src/portal/templates/download.html` — 下载页 | `/download` 可访问，分段控件 |
| 2.5 | `src/portal/templates/guide.html` — 使用指南 | `/guide` 可访问 |
| 2.6 | `src/portal/router.py` — 3 条路由 | 3 个页面均可通过浏览器访问 |
| 2.7 | 响应式验证 + 移动端适配 | 手机/平板/桌面均正常显示 |

**检查点**：浏览器访问首页，能看到完整的产品门户（数据硬编码占位）。

#### Phase 3：版本更新 API + 管理后台（预计 2 天）

**目标**：codex-switch 客户端能检测更新，管理员能查看数据。

| # | 任务 | 产出 |
|---|------|------|
| 3.1 | `src/utils/http.py` — HttpClient（httpx 封装） | 可请求 GitHub API |
| 3.2 | `src/utils/storage.py` — LocalStorage | 文件存入 data/ 目录 |
| 3.3 | `src/services/release_sync.py` — 版本同步服务 | 可从 GitHub 拉取版本信息 |
| 3.4 | `src/api/v1/update.py` — 检查更新 + 下载端点 | `POST /api/v1/update/check` + `GET .../download` |
| 3.5 | `src/api/v1/packages.py` — 工具包列表 + 下载 | 包管理 API |
| 3.6 | `src/admin/router.py` — 登录 + 仪表盘 | `/admin` 受保护访问 |
| 3.7 | `src/admin/templates/` — 仪表盘 HTML + Chart.js | 图表正常渲染 |
| 3.8 | `tests/` — 所有 API 的集成测试 | `uv run pytest` 全绿 |

**检查点**：用 Postman/curl 调用版本检查 API，返回正确 JSON。管理员登录后能看到数据面板。

#### Phase 4：遥测系统（预计 1 天）

**目标**：客户端能上报使用数据，管理员能在仪表盘看到聚合数据。

| # | 任务 | 产出 |
|---|------|------|
| 4.1 | `src/services/telemetry.py` — 遥测处理服务 | 事件验证、去重、写入、聚合 |
| 4.2 | `src/api/v1/telemetry.py` — 遥测上报端点 | `POST /api/v1/telemetry/events` 正常 |
| 4.3 | 管理后台接入遥测数据 | 仪表盘图表数据来自真实数据库 |
| 4.4 | 测试 | 遥测 API 集成测试 |

**检查点**：模拟 client 上报事件，在管理后台能看到数据变化。

#### Phase 5：部署上线（预计 1 天）

**目标**：Docker 部署到 43.134.110.192，HTTPS 可访问，ajepro 停服。

| # | 任务 | 产出 |
|---|------|------|
| 5.1 | 编写 docker/ 目录：nginx.conf + supervisord.conf + entrypoint.sh | Docker 配置三文件就绪 |
| 5.2 | 编写 Dockerfile + docker-compose.yml + .dockerignore | 容器编排文件就绪 |
| 5.3 | 本地构建验证：`docker compose up -d --build`，确认 nginx + uvicorn 均启动 | 本地 Docker 正常运行 |
| 5.4 | 服务器准备：创建 certs/、解压 SSL 证书、创建 .env | 生产配置就绪 |
| 5.5 | 停服 ajepro：`cd /home/lighthouse/ajepro && docker compose down` | 释放 80/443 端口 |
| 5.6 | 部署 codex-switch-server：`docker compose up -d --build` | 容器运行，HTTPS 可访问 |
| 5.7 | 验证：`curl -I https://www.codexswtich.cloud/`、API 检查、管理后台登录 | 全部正常 |
| 5.8 | 首次版本同步：手动触发 `sync_from_github()` 拉取 codex-switch 历史版本 | 安装包缓存就绪 |
| 5.9 | codex-switch 客户端 customMirrorUrl 指向 `https://www.codexswtich.cloud/api/v1` | 客户端更新检查可用 |

**检查点**：`https://www.codexswtich.cloud` 可访问，HTTPS 证书正确，API 返回正确数据。

### 9.3 总时间估算

| Phase | 耗时 | 里程碑 |
|-------|------|--------|
| Phase 1: 骨架 | 1 天 | 项目启动成功 |
| Phase 2: 门户 | 2 天 | 3 页面可浏览 |
| Phase 3: API + 后台 | 2 天 | API 可用 + 后台可看数据 |
| Phase 4: 遥测 | 1 天 | 遥测闭环 |
| Phase 5: 部署 | 1 天 | 生产上线 |
| **合计** | **7 天** | |

---

## 10. 附录

### 10.1 关键文件清单（实现时参考）

| 文件 | 行数估算 | 优先级 |
|------|---------|--------|
| `src/config.py` | ~30 | P0 |
| `src/database.py` | ~30 | P0 |
| `src/main.py` | ~50 | P0 |
| `src/models/base.py` | ~10 | P1 |
| `src/models/release.py` | ~25 | P1 |
| `src/models/download.py` | ~20 | P1 |
| `src/models/telemetry.py` | ~20 | P1 |
| `src/schemas/release.py` | ~40 | P1 |
| `src/schemas/download.py` | ~20 | P1 |
| `src/schemas/telemetry.py` | ~30 | P1 |
| `src/static/css/apple.css` | ~300 | P0（门户的基础） |
| `src/static/js/portal.js` | ~50 | P2 |
| `src/portal/templates/base.html` | ~80 | P0 |
| `src/portal/templates/index.html` | ~150 | P0 |
| `src/portal/templates/download.html` | ~120 | P1 |
| `src/portal/templates/guide.html` | ~200 | P2 |
| `src/portal/router.py` | ~40 | P1 |
| `src/admin/templates/base.html` | ~60 | P1 |
| `src/admin/templates/login.html` | ~40 | P1 |
| `src/admin/templates/dashboard.html` | ~150 | P1 |
| `src/admin/router.py` | ~80 | P1 |
| `src/api/deps.py` | ~30 | P1 |
| `src/api/router.py` | ~15 | P1 |
| `src/api/v1/update.py` | ~80 | P0 |
| `src/api/v1/packages.py` | ~60 | P1 |
| `src/api/v1/telemetry.py` | ~40 | P1 |
| `src/services/release_sync.py` | ~200 | P0 |
| `src/services/telemetry.py` | ~120 | P1 |
| `src/utils/http.py` | ~60 | P0 |
| `src/utils/storage.py` | ~80 | P1 |
| `tests/conftest.py` | ~50 | P0 |
| `tests/integration/*` | ~200 | P1 |
| `tests/unit/*` | ~150 | P1 |

### 10.2 依赖清单（pyproject.toml）

```toml
[project]
name = "codex-switch-server"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "sqlalchemy[asyncio]>=2.0",
    "aiosqlite>=0.20",
    "pydantic-settings>=2.7",
    "httpx>=0.28",
    "jinja2>=3.1",
    "itsdangerous>=2.2",     # session 签名
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3",
    "pytest-asyncio>=0.24",
    "pytest-cov>=6.0",
    "httpx>=0.28",           # TestClient 需要
    "ruff>=0.8",
]

[tool.ruff]
line-length = 120

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

### 10.3 环境变量模板（.env.example）

```bash
# 数据库
DATABASE_URL=sqlite+aiosqlite:///data/app.db

# 管理员
ADMIN_TOKEN=change-me-to-a-random-string

# GitHub（可选，提高 API 限速）
GITHUB_TOKEN=ghp_xxxxxxxxxxxx

# 腾讯云 COS（可选，生产环境使用）
COS_SECRET_ID=
COS_SECRET_KEY=
COS_BUCKET=codex-switch-1234567890
COS_REGION=ap-guangzhou

# 遥测
TELEMETRY_MAX_EVENTS_PER_MINUTE=60
TELEMETRY_RETENTION_DAYS=90
```

### 10.4 codex-switch 客户端兼容性

须在 codex-switch 客户端（`electron/updater/mirrors.ts`）中将 `customMirrorUrl` 默认值或推荐值指向本服务端：

```typescript
// 客户端修改点
const MIRROR_PRESETS = {
  auto: ...,
  github: ...,
  ghproxy: ...,
  custom: {
    prefix: "https://www.codexswtich.cloud/api/v1",
    label: "codex-switch 官方镜像",
  },
};
```
};
```

---

> **本文档版本**: v1.3  
> **下次 Review 时间**: 开发 Phase 1 前  
> **变更记录**: v1.0 初始版本 → v1.1 Docker 部署（实地勘测） → v1.2 Nginx+SSL 部署（参照 ajepro，域名 codexswtich.cloud） → v1.3 更新资源规划（ollama 已卸载）

# AGENTS.md — codex-switch-server

## ⚠️ AI Agent 必读规范（每次任务必须执行）

本项目使用 [ai-coding-ok](https://github.com/Mark7766/ai-coding-ok) 三层记忆系统。**在执行任何任务之前，必须完成以下步骤：**

### Plan 阶段（强制，任务开始前）
1. 读取 `AGENTS.md` — 本文件，架构速查
2. 读取 `.github/agent/system-prompt.md` — Agent 人格、角色切换、行为边界
3. 读取 `.github/agent/workflows.md` — 场景工作流（Feature/Bug/Refactor/部署）
4. 读取 `.github/agent/coding-standards.md` — 编码规范
5. 读取 `.github/agent/memory/project-memory.md` — 项目事实和架构约束
6. 读取 `.github/agent/memory/decisions-log.md` — 历史技术决策
7. 读取 `.github/agent/memory/task-history.md` — 近期任务上下文

### Act 阶段（强制，任务结束后）
1. 更新 `.github/agent/memory/task-history.md` — 记录本次任务摘要
2. 如有架构决策变化 → 更新 `.github/agent/memory/decisions-log.md`
3. 如有项目事实变化 → 更新 `.github/agent/memory/project-memory.md`
4. 如 AGENTS.md / system-prompt.md / workflows.md / coding-standards.md 有事实性过时内容 → 同步更新对应文件

> ⛔ 以上步骤不可跳过。若在使用 superpowers brainstorming / writing-plans，
> 在调用这些 skill **之前**先完成 Plan 阶段，**结束后**完成 Act 阶段。

---

## 项目概述

codex-switch-server 是一个 **Codex Switch 配套门户 + 服务端**。为 codex-switch 提供产品门户（展示、下载、指南）、版本更新镜像下载、桌面应用（Claude Desktop、Codex Desktop）及 CLI 依赖包（Node.js、Git）托管、运营后台和体验提升计划数据收集。目标用户是国内使用 codex-switch 的开发者——帮助他们发现产品、快速下载、顺利安装 AI 编程工具。

## 系统架构与数据流

```
用户浏览器 (codex-switch.cn)
      │
      ├── /               门户首页（展示产品、引导下载）
      ├── /download       下载页（平台选择、版本信息）
      ├── /guide          使用指南（安装教程、FAQ）
      │
      ▼
┌─────────────────────────────────────────┐
│         codex-switch-server             │
│                                         │
│  FastAPI (uvicorn)                      │
│  ├── portal/         门户路由（公开）    │
│  ├── api/v1/update   版本更新 API       │
│  ├── api/v1/packages  包下载 API        │
│  ├── api/v1/telemetry 遥测上报 API      │
│  └── admin/          运营后台（保护）    │
│                                         │
│  ┌────────────────────────────────┐     │
│  │  Services                      │     │
│  │  ├── ReleaseSync  版本同步     │     │
│  │  ├── Telemetry    遥测处理     │     │
│  │  └── PackageMgr   包管理       │     │
│  └────────────────────────────────┘     │
│              │                          │
│  ┌────────────────────────────────┐     │
│  │  SQLite (data/app.db)          │     │
│  └────────────────────────────────┘     │
└─────────────────────────────────────────┘
      │
      ▼
腾讯云 COS / 本地 data/ (安装包文件)
```

- **`src/main.py`** — FastAPI 应用工厂，注册路由、中间件、静态文件和 lifespan 事件
- **`src/portal/`** — 公开门户：首页、下载页、使用指南，Jinja2 服务器渲染
- **`src/admin/`** — 管理员后台：运营数据面板，Bearer Token 保护
- **`src/api/v1/`** — REST API：版本更新、包下载、遥测上报
- **`src/services/`** — 业务逻辑层：版本同步、遥测分析、包管理
- **`src/models/`** — SQLAlchemy ORM 模型（纯数据结构，无业务逻辑）
- **`src/schemas/`** — Pydantic 请求/响应模型（DTO 层）
- **`src/static/`** — 静态资源：Apple 风格 CSS、图标、极简 JS

---

## 常用命令

```bash
# 安装 & 运行
uv sync
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000

# 测试
uv run pytest
uv run pytest --cov=src --cov-report=term

# 代码检查 & 格式化
uv run ruff check .
uv run ruff format .

# 构建 / 部署
uv sync --frozen
```

---

## 代码结构设计

### 分层架构（Layered Architecture）

本项目采用 **轻薄路由层 + 独立服务层 + 数据访问层** 三层架构，遵循 FastAPI 社区最佳实践：

```
src/
├── main.py                    # 应用工厂 create_app() + lifespan
├── config.py                  # pydantic-settings（从 .env 读取）
├── database.py                # SQLAlchemy async engine + session factory
│
├── models/                    # 数据模型层（ORM，零业务逻辑）
│   ├── __init__.py
│   ├── base.py                # DeclarativeBase 基类
│   ├── release.py             # 版本发布记录
│   ├── download.py            # 下载记录
│   └── telemetry.py           # 遥测事件
│
├── schemas/                   # Pydantic DTO（API 契约）
│   ├── __init__.py
│   ├── release.py             # ReleaseRead, ReleaseCheckRequest
│   ├── download.py            # DownloadInfo
│   └── telemetry.py           # TelemetryEvent, TelemetryReport
│
├── api/                       # API 路由层（薄层，只做参数校验和调用 service）
│   ├── __init__.py
│   ├── deps.py                # 共享依赖：get_db, get_current_admin
│   ├── router.py              # 聚合所有子路由
│   └── v1/
│       ├── __init__.py
│       ├── update.py          # GET /api/v1/update/check, /download
│       ├── packages.py        # GET /api/v1/packages/{name}/{platform}
│       └── telemetry.py       # POST /api/v1/telemetry/events
│
├── services/                  # 业务逻辑层（可测试、可注入）
│   ├── __init__.py
│   ├── release_sync.py        # GitHub Release 检测、下载、缓存、清理
│   ├── telemetry.py           # 事件验证、去重、聚合、查询
│   └── package_manager.py     # 包文件索引、上传、代理缓存
│
├── portal/                    # 公开门户（面向用户）
│   ├── __init__.py
│   ├── router.py              # / /download /guide 路由
│   └── templates/
│       ├── base.html          # 全局布局 shell
│       ├── index.html         # 首页
│       ├── download.html      # 下载页
│       └── guide.html         # 使用指南
│
├── admin/                     # 运营后台（仅管理员）
│   ├── __init__.py
│   ├── router.py              # /admin /admin/login 路由
│   └── templates/
│       ├── base.html          # 后台布局 shell（不同于 portal）
│       ├── login.html         # 登录页
│       └── dashboard.html     # 运营数据面板
│
├── static/                    # 静态资源
│   ├── css/
│   │   └── apple.css          # Apple 设计系统 CSS
│   ├── js/
│   │   └── portal.js          # 极简交互（下载按钮、平滑滚动）
│   └── images/
│       ├── og-image.png       # Open Graph 社交分享图
│       └── tool-icons/        # Codex / Claude / Node.js / Git 图标
│
└── utils/                     # 工具层（跨模块复用）
    ├── __init__.py
    ├── http.py                # httpx 封装（GitHub API 访问、重试、限速）
    └── storage.py             # 文件存储抽象层（本地 / COS 统一接口）

tests/
├── conftest.py                # pytest fixtures：异步 DB、测试客户端
├── unit/                      # 单元测试（mock 外部依赖）
├── integration/               # 集成测试（真实 SQLite）
└── e2e/                       # 端到端测试（TestClient 模拟完整请求）
```

### 分层规则

```
┌──────────────────────────────────────────┐
│  portal / admin / api    (路由层)         │  ← 薄层：参数校验、依赖注入、调用 service
├──────────────────────────────────────────┤
│  services                (业务逻辑层)     │  ← 核心：所有业务规则在这里
├──────────────────────────────────────────┤
│  models / schemas        (数据层)         │  ← 纯数据结构 + 类型定义
├──────────────────────────────────────────┤
│  utils                   (工具层)         │  ← 无状态工具函数、外部访问封装
└──────────────────────────────────────────┘
```

**路由层不直接操作数据库**，必须通过 service。**Service 不操作 HTTP 请求/响应对象**，只接收参数返回数据。**Models 不含任何业务方法**（除简单的 property），保持贫血模型。

---

## 门户设计

### 设计哲学：Apple Design Principles

遵循 Apple Human Interface Guidelines 三大核心原则：

| 原则 | 说明 | 本项目的落地 |
|------|------|-------------|
| **Clarity（清晰）** | 文字清晰易读，图标精确醒目，功能明确 | 大标题 + 留白 + 清晰层级 + 单一视觉焦点 |
| **Deference（遵从）** | UI 退让于内容，减少无关界面元素 | 无边框卡片、微阴影、透明导航栏、内容驱动 |
| **Depth（深度）** | 视觉分层，动效传递位置关系 | 毛玻璃导航、卡片悬浮、平滑过渡、`backdrop-filter` |

### 视觉系统

```
颜色体系（Apple-style Color Palette）
┌─────────────────────────────────────────────┐
│ 背景                                          │
│   #f5f5f7  主背景（Apple 经典浅灰）            │
│   #ffffff  卡片背景                            │
│   #fafafa  次级背景 / 页脚                      │
│                                               │
│ 文字                                          │
│   #1d1d1f  主文字（Apple 黑）                  │
│   #86868b  次要文字（Apple 灰）                │
│   #6e6e73  更弱的辅助文字                       │
│                                               │
│ 强调                                          │
│   #0071e3  Apple 蓝（链接、按钮）              │
│   #0077ed  Hover 蓝                           │
│                                               │
│ 语义                                          │
│   #34c759  成功绿                              │
│   #ff9500  警告橙                              │
│   #ff3b30  错误红                              │
└─────────────────────────────────────────────┘

字体系统（System Font Stack）
  首选：-apple-system, BlinkMacSystemFont, "SF Pro Display",
        "SF Pro Text", "PingFang SC", "Hiragino Sans GB"
  等宽： "SF Mono", "Menlo", "Consolas", monospace

字号层级（8px 基线网格）
  Hero 标题    56px / font-weight: 600 / letter-spacing: -0.015em
  段标题       40px / font-weight: 600 / letter-spacing: -0.01em
  小节标题     28px / font-weight: 600
  卡片标题     21px / font-weight: 600
  正文         17px / font-weight: 400 / line-height: 1.5
  辅助文字     14px / font-weight: 400
  小字/标签    12px / font-weight: 400

间距系统（8pt Grid）
  4px   = 0.5x  细微间距
  8px   = 1x    紧凑间距
  16px  = 2x    默认内边距
  24px  = 3x    段落间距
  32px  = 4x    模块间距
  48px  = 6x    区块间距
  64px  = 8x    大段间距
  80px  = 10x   页面级间距
  120px = 15x   Hero 上下间距

圆角系统
  8px   按钮、输入框
  12px  小卡片
  18px  标准卡片（Apple 风格）
  20px  大卡片、Modal
  44px  全宽按钮（胶囊形）
```

---

### 页面设计

#### 页面路由表

| 路由 | 页面 | 访问权限 | 说明 |
|------|------|---------|------|
| `/` | 首页 | 公开 | 产品介绍 + 核心价值 + CTA |
| `/download` | 下载页 | 公开 | 平台选择 + 版本信息 + 系统要求 |
| `/guide` | 使用指南 | 公开 | 安装教程 + 配置说明 + FAQ |
| `/admin/login` | 管理员登录 | 公开 | Bearer Token 认证 |
| `/admin` | 运营仪表盘 | 管理员 | 下载量、用户数、遥测数据 |
| `/api/v1/*` | REST API | 公开 | 客户端调用，JSON 响应 |

---

#### 1. 首页 `/` — 产品门户

**设计目标**：让用户在 10 秒内理解 codex-switch 是什么，并产生下载冲动。

**页面布局（自上而下）**：

```
┌──────────────────────────────────────────────────────┐
│ 导航栏（毛玻璃透明底 + backdrop-filter）              │
│  [Codex Switch 图标+名称]    [下载] [指南] [GitHub]   │
├──────────────────────────────────────────────────────┤
│                                                      │
│  Hero 区域                                           │
│                                                      │
│  ┌────────────────────────────────────────────────┐   │
│  │                                                │   │
│  │  🖼️ 产品主视觉插画（应用窗口截图/抽象图）      │   │
│  │                                                │   │
│  │  让 AI 编程触手可及                             │   │
│  │  ─────────────────────────────────────          │   │
│  │                                                │   │
│  │  一行极简描述：Codex Switch 帮你突破网络限制，  │   │
│  │  在国内流畅使用 Codex 和 Claude，                │   │
│  │  接入 DeepSeek 模型，免费、快速、安全。          │   │
│  │                                                │   │
│  │  ┌──────────────────────┐  ┌──────────────┐    │   │
│  │  │  🍎 下载 macOS 版     │  │  🪟 Windows 版│   │   │
│  │  │      v1.4.0          │  │   v1.4.0     │    │   │
│  │  └──────────────────────┘  └──────────────┘    │   │
│  │                                                │   │
│  │  也支持 Linux · 免费开源                         │   │
│  │                                                │   │
│  └────────────────────────────────────────────────┘   │
│                                                      │
│  为什么选择 Codex Switch？（三列卡片）                 │
│                                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐  │
│  │  🔌           │ │  🧠           │ │  🛡️           │  │
│  │  一键接入      │ │  多模型支持    │ │  本地安全      │  │
│  │              │ │              │ │              │  │
│  │  自动配置代理  │ │  DeepSeek 全  │ │  数据不出本机  │  │
│  │  无需手动设置  │ │  系列可用     │ │  本地代理转发  │  │
│  └──────────────┘ └──────────────┘ └──────────────┘  │
│                                                      │
│  支持的 AI 工具（图标网格）                            │
│                                                      │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐               │
│  │      │ │      │ │      │ │      │               │
│  │Codex │ │Codex │ │Claude│ │Claude│               │
│  │ CLI  │ │Desk. │ │ CLI  │ │Desk. │               │
│  └──────┘ └──────┘ └──────┘ └──────┘               │
│                                                      │
│  用户故事（横向滚动卡片）                              │
│                                                      │
│  "以前下载 Codex 要等半小时，                          │
│   现在用 Codex Switch 秒装好。"                        │
│                        — 某后端开发工程师              │
│                                                      │
│  底部 CTA + 页脚                                      │
│                                                      │
├──────────────────────────────────────────────────────┤
│  Codex Switch  ·  开源免费  ·  GitHub  ·  反馈        │
└──────────────────────────────────────────────────────┘
```

**UI 交互细节**：
- 导航栏滚动后从透明变为毛玻璃背景（`backdrop-filter: saturate(180%) blur(20px)`）
- 下载按钮 hover 时微微放大（`scale: 1.02`）+ 阴影加深
- 功能卡片 hover 时上浮 4px + 阴影展开（`translateY(-4px)`）
- 平滑滚动锚点（`scroll-behavior: smooth`）
- Hero 区域微妙的视差效果（`translateY` 随滚动变化）

**响应式策略**：
- ≥ 980px：标准桌面布局，三列卡片
- 768px–979px：两列卡片，Hero 字号缩小
- < 768px：单列堆叠，导航改为汉堡菜单

---

#### 2. 下载页 `/download`

**设计目标**：用户能快速找到对应平台的下载，一眼看到版本号和更新日志。

```
┌──────────────────────────────────────────┐
│ 导航栏（同首页）                          │
├──────────────────────────────────────────┤
│                                          │
│  下载 Codex Switch                        │
│  ─────────────────────                   │
│  选择你的平台，开始使用                    │
│                                          │
│  ┌────────────────────┐                  │
│  │  平台切换 Tab       │                  │
│  │  [🍎 macOS] [🪟 Windows] [🐧 Linux]  │
│  ├────────────────────┤                  │
│  │                    │                  │
│  │  最新版本 v1.4.0    │                  │
│  │  发布于 2026-06-05  │                  │
│  │                    │                  │
│  │  ┌────────────────┐│                  │
│  │  │  ⬇️ 下载 .dmg    ││  ← 大 CTA 按钮  │
│  │  │  124 MB         ││                  │
│  │  └────────────────┘│                  │
│  │                    │                  │
│  │  Intel · Apple Silicon 通用           │
│  │                    │                  │
│  └────────────────────┘                  │
│                                          │
│  系统要求                                 │
│  ─────────                               │
│  macOS 11.0+  ·  4GB RAM  ·  100MB 磁盘  │
│                                          │
│  ──                                     │
│  全部版本（展开/收起）                    │
│  ├─ v1.3.0  2026-05-20                   │
│  ├─ v1.2.0  2026-05-10                   │
│  └─ ...                                  │
│                                          │
├──────────────────────────────────────────┤
│  页脚                                     │
└──────────────────────────────────────────┘
```

**交互细节**：
- 平台切换使用带滑块指示器的 Tab（Apple 风格分段控件）
- 点击非当前平台时自动切换到该平台的下载信息
- "全部版本" 使用 `<details>/<summary>` 优雅展开，无需 JS
- 下载按钮点击后有微反馈（短暂 spin + "正在下载..." 状态）

---

#### 3. 使用指南 `/guide`

**设计目标**：帮助用户完成从下载到成功使用的完整流程，降低支持成本。

```
┌──────────────────────────────────────────┐
│  使用指南                                 │
│                                          │
│  ┌─ 步骤导航（侧边栏） ─┐ ┌─ 内容区 ───┐  │
│  │                      │ │            │  │
│  │  1. 下载安装          │ │  📥 第一步  │  │
│  │  2. 获取 API Key     │ │            │  │
│  │  3. 启动代理          │ │  详细图文  │  │
│  │  4. 配置 Codex CLI   │ │  教程...   │  │
│  │  5. 配置 Claude      │ │            │  │
│  │  6. 常见问题          │ │            │  │
│  │                      │ │            │  │
│  └──────────────────────┘ └────────────┘  │
│                                          │
└──────────────────────────────────────────┘
```

**技术实现**：
- 单页面多锚点，侧边栏使用 `position: sticky` + 滚动高亮（Intersection Observer）
- 无 JS 降级：所有内容仍在同一页面可完整阅读
- 代码块使用深色主题（SF Mono），带复制按钮

---

#### 4. 运营后台 `/admin`

**设计目标**：管理员一眼看到核心运营指标，简单直观。

```
┌──────────────────────────────────────────┐
│  Codex Switch 运营后台                    │
│                                          │
│  ┌────────┐ ┌────────┐ ┌────────┐       │
│  │ 总下载量 │ │ 活跃用户 │ │ 今日事件 │      │
│  │ 12,345  │ │ 3,892   │ │ 1,203   │      │
│  └────────┘ └────────┘ └────────┘       │
│                                          │
│  ┌─ 下载趋势（7/30/90 天）─────────────┐  │
│  │  📈 简易折线图                        │  │
│  │  （Chart.js CDN + 服务器数据）        │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ┌─ 功能使用分布 ───────────────────────┐  │
│  │  📊 柱状图                            │  │
│  │  代理启动 · 模型调用 · CLI 配置 ...    │  │
│  └────────────────────────────────────┘  │
│                                          │
│  ┌─ 最近遥测事件表 ─────────────────────┐  │
│  │  时间 · 用户 · 事件 · 平台            │  │
│  └────────────────────────────────────┘  │
│                                          │
└──────────────────────────────────────────┘
```

---

## 约定与模式

- **所有 Python 文件** 开头必须有 `from __future__ import annotations`。
- **异步优先**：数据库操作使用 async session，API 使用 `async def`。
- **路由不操作 DB**：路由只做参数校验 → 调用 service → 返回响应。Service 负责所有业务逻辑。
- **贫血模型**：ORM Model 只有字段定义 + 简单 property。查询和写操作放在 service。
- **Pydantic 分两层**：`schemas/` 目录独立，Request Schema 和 Response Schema 分开定义。
- **测试数据库**：`conftest.py` 提供 `aiosqlite` 内存数据库 fixture 和 `httpx.AsyncClient` 测试客户端。
- **日志**：使用 `logging.getLogger(__name__)`，禁止 `print()`。
- **配置**：环境变量通过 `.env` 文件 + pydantic-settings 管理，禁止硬编码。
- **CSS 命名**：使用语义化类名（如 `.hero-title` `.feature-card`），不引入 CSS 框架。自定义属性（CSS Variables）管理颜色。
- **前端 JS**：尽量零 JS。必须用 JS 的场景（如下载交互、统计图表）使用原生 ES Module，不引入 React/Vue 等框架。Chart.js 从 CDN 按需加载（仅 admin 页面）。
- **文件存储**：安装包存储在本地 `data/` 目录，部署到腾讯云时使用 COS 对象存储。
- **管理员认证**：Bearer Token 认证，token 通过 `.env` 配置，够用就行。

## 测试模式

```python
# 测试数据初始化辅助函数
async def _seed_test_data(db: AsyncSession) -> list[Model]:
    items = [Model(name="test1"), Model(name="test2")]
    db.add_all(items)
    await db.flush()
    return items

# 时间敏感测试使用 freezegun
from freezegun import freeze_time

@freeze_time("2026-01-05 10:00:00")
async def test_something(db_session):
    ...

# Service 测试：注入 mock 的 HTTP client / storage
async def test_release_sync_pulls_new_version():
    mock_http = AsyncMock()
    mock_http.get.return_value = fake_github_response()
    service = ReleaseSyncService(http=mock_http, storage=InMemoryStorage())
    result = await service.check_and_sync()
    assert result.has_new is True
```

## 重要约束

- **禁止重量级依赖** — Redis、RabbitMQ、Celery 等重量级中间件一律不用。SQLite 单文件足够。
- **敏感数据** — `.env` 管理管理员密码和 GitHub Token，绝不硬编码。
- **数据库迁移** — 开发阶段直接修改 model 重建数据库；稳定后用 Alembic 迁移。
- **代码限制** — 行宽 120 字符，单函数不超过 50 行，单文件不超过 500 行。
- **前端极简** — 不引入任何前端框架（React/Vue/Angular 等）。服务器渲染 Jinja2 + 极简 vanilla JS。Chart.js 仅限 admin 页面，从 CDN 按需加载。
- **一个人维护** — 代码可读性 > 性能优化。三层以内的嵌套，拒绝回调地狱和过度抽象。

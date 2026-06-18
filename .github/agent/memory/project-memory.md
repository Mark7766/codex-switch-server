# 🧠 codex-switch-server — 项目长期记忆

> **用途**：存储项目的稳定事实、架构决策、关键约束和常见问题。
> AI Agent 在每次任务开始时应阅读此文件获取上下文。
> 当项目发生重大变化时，必须同步更新此文件。

---

## 📋 项目基本信息

| 属性 | 值 |
|------|---|
| 项目名称 | codex-switch-server |
| 项目类型 | 门户网站 + Web 服务 + 后台管理 |
| 业务场景 | 为 codex-switch 提供产品门户（展示/下载/指南），为客户端提供版本更新镜像、桌面应用/CLI 工具包下载，为管理员提供运营数据面板 |
| 用户规模 | 数百到数千（codex-switch 用户群体，面向中国内地开发者） |
| 当前阶段 | 0.1.0 / 已上线生产（https://www.codexswtich.cloud） |
| 设计原则 | 极简实用，维护优先 — 一个人维护，一切为了简单可靠 |
| UI/UX 哲学 | Apple Human Interface Guidelines — Clarity（清晰）、Deference（遵从）、Depth（深度） |
| 主语言 | Python 3.12 |
| 后端框架 | FastAPI |
| 数据库 | SQLite（aiosqlite 异步驱动） |
| 前端方案 | Jinja2 服务器渲染 + Apple 风格 CSS + 极简 vanilla JS |

---

## 🏗️ 架构概述

```
用户浏览器                    codex-switch 客户端
(codex-switch.cn)            (macOS / Windows)
      │                            │
      ▼                            ▼
┌──────────────────────────────────────────────────┐
│              codex-switch-server                 │
│                                                  │
│  FastAPI (uvicorn)                               │
│  ├── portal/        门户路由（Jinja2 渲染）        │
│  │   ├── /           首页                       │
│  │   ├── /download   下载页                     │
│  │   └── /guide      使用指南                   │
│  ├── api/v1/        客户端 API（JSON）            │
│  │   ├── /update     版本检查+下载              │
│  │   ├── /packages   工具包下载                  │
│  │   └── /telemetry  遥测上报                   │
│  └── admin/          运营后台（Bearer Token 保护）│
│      ├── /admin/login                           │
│      └── /admin       数据面板                   │
│                                                  │
│  ┌──────────────────────────────────────┐        │
│  │  Services（业务逻辑层）               │        │
│  │  ├── ReleaseSync  版本检测+同步+清理  │        │
│  │  ├── Telemetry    事件验证+去重+聚合  │        │
│  │  └── PackageMgr   包索引+缓存+分发    │        │
│  └──────────────────────────────────────┘        │
│              │                                   │
│  ┌──────────────────────────────────────┐        │
│  │  SQLite (data/app.db)                │        │
│  │  ├── releases      版本发布表         │        │
│  │  ├── downloads     下载记录表         │        │
│  │  ├── telemetry_events  遥测事件表    │        │
│  │  └── admin_tokens  管理员 Token 表   │        │
│  └──────────────────────────────────────┘        │
└──────────────────────────────────────────────────┘
      │
      ▼
腾讯云 COS 广州 codex-switch-1259344349 ← 主下载链路（302 跳转，2MB/s）
       ↑ 部署脚本 or admin 上传同步
本地 data/ 目录 ← 安装包文件缓存（COS 不可用时降级兜底）
       ↑ Docker volume: ./data → /app/data
```

### 生产环境

#### 广州（新主站，已备案）
| 项目 | 值 |
|------|---|
| 服务器 IP | 134.175.67.120 |
| 域名 | codex-switch.cloud |
| OS | Ubuntu 22.04 LTS |
| CPU/内存 | 2 核 / 2 GB |
| Docker | 27.1.2 + Compose v2.29.2 |
| Docker 镜像源 | 5 个国内镜像（DaoCloud / dockerhub.icu / 1ms.run / registry.cyou / 腾讯云） |
| 部署路径 | /home/lighthouse/codex-switch-server/ |
| 部署方式 | Docker 单容器（Nginx SSL + uvicorn，Supervisor 管理） |
| SSL 证书文件 | codex-switch.cloud_bundle.crt + codex-switch.cloud.key |

#### 新加坡（过渡期保留，4-6 个月后下线）
| 项目 | 值 |
|------|---|
| 服务器 IP | 43.134.110.192 |
| 域名 | www.codexswtich.cloud |
| OS | Ubuntu 22.04 LTS |
| CPU/内存 | 2 核 / 1.9 GB |
| Docker | 27.1.2 + Compose v2.29.2 |
| 部署路径 | /home/lighthouse/codex-switch-server/ |
| 部署方式 | Docker 单容器（Nginx SSL + uvicorn，Supervisor 管理） |
| SSL 证书文件 | codexswtich.cloud_bundle.crt + codexswtich.cloud.key |
| 当前角色 | 搬家页 + API 反代 → 广州 |
| Nginx 配置 | docker/nginx.conf volume mount 持久化，nginx-singapore.conf 为源文件 |
| SSL 证书文件 | codexswtich.cloud_bundle.crt + codexswtich.cloud.key |
| 当前角色 | 搬家页 + API 反代 → 广州 |

### 核心特征
- Docker 单容器部署：Nginx（SSL 终止）+ uvicorn（应用），Supervisor 管理双进程
- 门户和后台均为服务器渲染，无需前端构建工具链
- 安装包文件本地缓存 + 腾讯云 COS 广州对象存储（2MB/s 主链路，本地降级兜底）
- Apple 极简设计风格门户，强调内容、留白和清晰层级
- 分层架构：路由层 → 服务层 → 数据层，职责边界清晰

---

## 🔄 核心业务流程

```
版本同步（实时，无需手动触发）:
  /api/v1/update/latest → GitHub Releases API（5min 内存缓存）
  → 返回最新版本号、发布日期、各平台文件列表（标注是否已缓存）

用户下载 codex-switch:
  访问 /download → JS fetch /api/v1/update/latest → 显示最新版本
  → 点击下载 → 检查 COS codex-switch/{ver}/{filename} → 302 跳转广州（2MB/s）
  → COS 未命中 → 检查本地缓存 → nginx sendfile（降级）
  → 均未命中 → 服务端从 GitHub 下载 → 缓存本地（兜底）

客户端检查更新:
  codex-switch 启动 → POST /api/v1/update/check
  → 调用 get_latest_from_github() → 对比版本号 → 返回更新信息

用户下载 AI 工具安装包:
  访问首页 / → 首页"下载 AI 编程工具"区块
  → JS fetch /api/v1/packages → 为已上传的包生成下载按钮
  → 点击下载 → 检查 COS packages/{name}/latest/{platform}-{arch}.{ext} → 302 跳转广州（2MB/s）
  → COS 未命中 → 检查本地缓存 → nginx sendfile（降级）
  → COS 对象设置 ContentDisposition 元数据，保证浏览器下载文件名正确

遥测上报:
  codex-switch 定时 POST /api/v1/telemetry/events
  → 验证事件类型 → 按客户端 ID 去重 → 写入 SQLite

管理员查看数据:
  GET /admin → Bearer Token 验证 → 查询聚合统计
  → 渲染仪表盘（Chart.js 图表）
```

---

## 📦 核心模块

| 模块 | 说明 | 状态 |
|------|------|------|
| src/main.py | 应用工厂 create_app() + lifespan 生命周期 | ✅ Phase 1 |
| src/config.py | pydantic-settings 配置管理 | ✅ Phase 1 |
| src/database.py | SQLAlchemy async engine + session | ✅ Phase 1 |
| src/models/ | ORM 模型：release, download, telemetry | ✅ Phase 1 |
| src/schemas/ | Pydantic DTO：请求/响应模型 | ⬜ 待开发 |
| src/api/v1/update.py | 版本检查 + 客户端下载 API | ✅ Phase 3 |
| src/api/v1/updates.py | electron-updater generic provider 端点（latest-mac.yml / latest.yml / {filename}） | ✅ Phase 5 |
| src/api/v1/plugins.py | 离线插件包下载 API（pack 信息 + COS 302 下载） | ✅ Phase 6 |
| src/api/v1/client.py | 客户端身份信息 API（编号/早期成员/加入日期/邀请数） | ✅ Phase 7 |
| src/services/referral_matcher.py | 邀请归属匹配定时任务（IP+时间窗口） | ✅ Phase 7 |
| src/api/v1/packages.py | 工具包（Node.js/Git/Desktop）下载 API | ✅ Phase 3 |
| src/api/v1/telemetry.py | 遥测事件上报 API | ✅ Phase 4 |
| src/services/release_sync.py | 实时 GitHub 最新版查询 + 首次代理下载缓存 + 下载统计 | ✅ Phase 3（v2: 2026-06-06 重构为实时模式） |
| src/services/update_feed.py | electron-updater yml 缓存 + 文件查找 + 原始文件名缓存 | ✅ Phase 5 |
| src/services/telemetry.py | 事件验证、去重、聚合统计 | ✅ Phase 4 |
| src/services/package_manager.py | 包文件索引、上传、代理缓存 | 🚫 合并至 packages API |
| src/portal/ | 门户路由 + 首页/下载/指南模板 | ✅ Phase 2 |
| src/admin/ | 管理员路由 + 登录/仪表盘模板 | ✅ Phase 3 |
| src/static/ | Apple 风格 CSS + 图标 + 极简 JS | ✅ Phase 2 |
| src/utils/ | HTTP 客户端封装 + 存储抽象层 | ✅ Phase 3 |
| src/utils/ | HTTP 客户端封装 + 存储抽象层 | ⬜ 待开发 |

---

## 🎨 UI/UX 设计规范

### 设计系统（Apple Human Interface 风格）

**颜色**
| Token | 值 | 用途 |
|-------|---|------|
| --color-bg-primary | #f5f5f7 | 主背景 |
| --color-bg-card | #ffffff | 卡片背景 |
| --color-bg-footer | #fafafa | 页脚背景 |
| --color-text-primary | #1d1d1f | 主文字 |
| --color-text-secondary | #86868b | 辅助文字 |
| --color-accent | #0071e3 | 链接、按钮、强调 |
| --color-accent-hover | #0077ed | 按钮悬浮 |

**字体**
| Token | 值 |
|-------|---|
| --font-sans | -apple-system, BlinkMacSystemFont, "SF Pro Display", "PingFang SC", "Hiragino Sans GB", sans-serif |
| --font-mono | "SF Mono", Menlo, Consolas, monospace |

**字号**
| Token | 值 | 场景 |
|-------|---|------|
| --text-hero | 56px / 600 | Hero 主标题 |
| --text-section | 40px / 600 | 区块标题 |
| --text-subsection | 28px / 600 | 小节标题 |
| --text-card-title | 21px / 600 | 卡片标题 |
| --text-body | 17px / 400 / line-height 1.5 | 正文 |
| --text-caption | 14px / 400 | 辅助文字 |
| --text-label | 12px / 400 | 标签 |

**间距（8px 网格）**
| Token | 值 | 场景 |
|-------|---|------|
| --space-xs | 4px | 图标与文字间距 |
| --space-sm | 8px | 紧凑间距 |
| --space-md | 16px | 默认内边距 |
| --space-lg | 24px | 段落间距 |
| --space-xl | 32px | 模块间距 |
| --space-2xl | 48px | 区块间距 |
| --space-3xl | 64px | 大段间距 |
| --space-4xl | 80px | 页面级间距 |
| --space-hero | 120px | Hero 上下 |

**圆角**
| Token | 值 | 场景 |
|-------|---|------|
| --radius-sm | 8px | 按钮、输入框 |
| --radius-md | 12px | 小卡片 |
| --radius-lg | 18px | 标准卡片 |
| --radius-xl | 20px | 大卡片 |
| --radius-full | 44px | 全宽 CTA 按钮 |

### 页面设计要点

**首页**：Hero（双按钮：查看安装指南 / 直接下载）→ 安装指南快捷入口（4 卡片 → `/guide?tool=xxx`）→ 下载安装包（2 桌面版卡片）→ 价值主张（三列功能卡片）→ 用户故事 → 底部 CTA → 页脚。指南是用户最常用功能，Hero 直接引导。

**下载页**：平台切换（分段控件）→ 最新版本大卡片（版本号 + 日期 + 文件大小 + CTA 按钮）→ 系统要求 → 历史版本（details/summary 可折叠）。

**使用指南**：三步向导交互（4 工具卡片 2×2 网格 → 选平台 → 动态步骤）：支持 Codex Desktop / Claude Desktop（6 步）+ Codex CLI / Claude Code CLI（8 步，含 git/node/python 安装 + Git Bash 使用引导）。Codex Switch CLI 管理统一配置（设置 → CLI 管理 → 保存并应用）。URL 参数 `?tool=xxx` 可预选工具。`renderGuide()` 数组驱动动态渲染。16 张截图按场景加载。

**运营后台**：3 个指标卡片（总下载量/活跃用户/今日事件）→ 下载趋势折线图（Chart.js）→ 功能使用分布柱状图 → 最近事件表。仅管理员可访问。

### 响应式策略

| 断点 | 布局 |
|------|------|
| ≥ 980px | 标准桌面布局，最大内容宽度 980px 居中 |
| 768–979px | 两列卡片，Hero 字号缩小至 40px，导航简化 |
| < 768px | 单列堆叠，Hero 字号 32px，导航改汉堡菜单 |

---

## ⚠️ 关键约束

1. 一个人维护，拒绝复杂架构 — 单文件部署、SQLite 内嵌、无外部依赖服务
2. 禁止不必要的重量级依赖 — 不用 Redis、Celery、PostgreSQL
3. 管理员认证用简单 Bearer Token，不引入 OAuth/SSO
4. **时区规范**：数据库存储使用 UTC（naive datetime），所有业务逻辑（统计/查询/展示）统一使用北京时间（UTC+8）。`_beijing_now()` 辅助函数用于获取当前北京时间。
4. 前端零框架 — 不用 React/Vue/Angular。服务器渲染 + 极简 vanilla JS
5. Chart.js 仅限 admin 页面使用，从 CDN 按需加载，不计入前端构建
6. 门户设计严格遵循 Apple HIG：清晰、遵从、深度。每一个视觉元素都要有存在的理由

---

## 🐛 已知问题 & 常见坑

| 编号 | 问题描述 | 解决方案 | 日期 |
|------|---------|---------|------|
| 1 | `.env` 必须配置 `GITHUB_TOKEN`，否则 GitHub API 403 限速，下载页无法显示版本 | 创建 `.env`，填入 Fine-grained PAT，参考 `.env.example` | 2026-06-06 |
| 2 | 首次下载某个平台/架构组合需 1-2 分钟（从 GitHub 拉取并缓存），用户可能以为卡死 | 下载页 JS 显示"首次下载需从 GitHub 获取，请耐心等待"提示 | 2026-06-06 |
| 3 | `_detect_platform` 要求 Windows .exe 必须有显式 arch 后缀（-x64/-arm64），无后缀文件（如 `-win.exe`）会跳过 | Windows 发布时确保 asset 名称包含 `-x64` 或 `-arm64` | 2026-06-06 |

---

## 🔧 开发环境

### 启动方式
```bash
uv sync && uv run uvicorn src.main:app --reload
```

### 环境变量（.env）
```
DATABASE_URL=sqlite+aiosqlite:///data/app.db
ADMIN_TOKEN=your-secret-token-here
GITHUB_TOKEN=github_pat_xxx  # 必需！否则 GitHub API 403，下载页无版本数据
COS_BUCKET=  # 可选，部署到腾讯云时填写
```

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
│  │   ├── /guide      使用指南                   │
│  │   ├── /tools/codex-switch   工具文档（Codex Switch）│
│  │   ├── /tools/ai-working-ok  工具文档（AI 工作护栏）│
│  │   └── /tools/ai-coding-ok   工具文档（AI 编程记忆）│
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
| src/services/update_feed.py | electron-updater yml feed（COS 稳定 key 优先 + GitHub 兜底，ADR-017）+ 文件查找 + 原始文件名缓存 | ✅ Phase 5 |
| src/services/telemetry.py | 事件验证、去重、聚合统计 | ✅ Phase 4 |
| src/services/package_manager.py | 包文件索引、上传、代理缓存 | 🚫 合并至 packages API |
| src/services/ai_working_ok_releases.py | ai-working-ok 版本查询、本地缓存+GitHub 下载兜底 | ✅ 2026-07-26 |
| src/services/tool_changelog.py | 工具文档页「更新日志」：读各工具仓库 CHANGELOG.md → markdown 渲染 + 内存/磁盘 TTL 缓存 | ✅ 2026-09-07 |
| src/portal/ | 门户路由 + 首页/下载/指南/工具文档模板（下拉 codex-switch + ai-* 三页）+ **技术支持页 `/support`**（2026-10-07，复用 `.doc` 布局） | ✅ Phase 2（工具文档 2026-09-07；支持页 2026-10-07） |
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

**首页**：Hero（双按钮：Windows 安装指南 / Mac 安装指南）→ 安装指南快捷入口（4 卡片 → `/guide?tool=xxx`）→ 价值主张（三列功能卡片）→ 页脚。（2026-10-07 浏览器实测校正：线上**没有**「下载安装包 2 张桌面版卡片」与「用户故事」区块，此前本条记忆有漂移。）页脚「产品」列含 下载 / 使用指南 / ai-working-ok / ai-coding-ok，「资源」列含 GitHub / 反馈；右下角有全局「技术支持」悬浮按钮（微信二维码弹窗）。

**下载页**：平台切换（分段控件）→ 最新版本大卡片（版本号 + 日期 + 文件大小 + CTA 按钮）→ 系统要求 → 历史版本（details/summary 可折叠）。

**使用指南**：三步向导交互（4 工具卡片 2×2 网格 → 选平台 → 动态步骤）：支持 Codex Desktop / Claude Desktop（6 步）+ Codex CLI / Claude Code CLI（8 步，含 git/node/python 安装 + Git Bash 使用引导）。Codex Switch CLI 管理统一配置（设置 → CLI 管理 → 保存并应用）。URL 参数 `?tool=xxx` 可预选工具。`renderGuide()` 数组驱动动态渲染。16 张截图按场景加载。

**工具文档页（/tools/codex-switch、/tools/ai-coding-ok、/tools/ai-working-ok）**：导航「工具」为**下拉菜单**（顺序 **Codex Switch → ai-working-ok → ai-coding-ok**，无父级 URL），子项进入各自「左粘性目录 + 右正文」单页长文档（参考 codexguide.ai/start）；目录分组：开始/快速开始/理解/帮助，锚点 + 滚动高亮，移动端退化为顶部横向 chips。面向使用者中文写作、快速开始为重点。ai-working-ok 复用 `/api/v1/packages/ai-working-ok/latest` 国内镜像下载；ai-coding-ok 无下载（git 安装）；Codex Switch 的快速开始=精简 3 步，下载/图文深链站内 `/download` 与 `/guide`（安装细节单一来源）。**首页 hero 已移除 AI Working OK 直链**（入口收敛到下拉 + 页脚两条 ai 文档直链；Codex Switch 页脚入口即 下载/使用指南）。样式：apple.css `.nav__menu*`（下拉）与 `.doc*`（文档布局）。三个文档页正文末尾均含**「更新日志」区块**（`#sec-changelog`，左目录「帮助」组末 + 移动端 chips + 正文末尾；DeepSeek 式时间倒序，最新默认展开带「最新」徽标，历史 `<details>` 折叠）：这是文档页**唯一运行时拉取区块**——`ToolChangelogService` 读各工具仓库 CHANGELOG.md（api.github.com contents，python-markdown 渲染，内存+磁盘 TTL 300s，GitHub 不可达降级文案），发版只需在工具仓库更新 CHANGELOG.md 即自动跟上。其余内容为一次性改写（非运行时拉取 wiki），wiki 变更需手动同步。**排版与交互（ADR-021）**：桌面「工具」下拉**悬停即展开**（CSS `::after` 桥接按钮与面板 16px 间隙 + `@media (hover:hover)` 门控 + 箭头随开合旋转；触控/≤767 走点击/静态展开）。文档双栏字号采用 **`.doc` 组件级变量** `--doc-title(~34)/--doc-h2(28)/--doc-h3(20)/--doc-side-group(13)/--doc-side-item(15)/--doc-meta(13)/--doc-code(14)`——左栏升一档、右栏标题降一档、正文 17 与全局 token 不动；调整字号只改 `.doc` 里这组变量，其它页面用全局 `--text-*`。

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
7. **发布门禁（用户明确要求，2026-10-07）**：Agent **不得自行 `git push`、不得自行部署到服务器**。流程固定为「本地开发 → 本地**全量**验收测试（覆盖全部功能，不只改动点）→ 人工确认 → 才 `git push` → 再确认 → 才部署」。详见 `docs/assessment/2026-10-07-服务端升级评估报告.md` §8/§9。
8. **修改策略**：非必要不修改 —— 只改有证据的过时点，不做顺带重构/优化/依赖升级；下载更新链路、存储层、认证、Apple CSS 设计系统、数据库 schema 一律不动（见同报告 §6）。

---

## 🐛 已知问题 & 常见坑

| 编号 | 问题描述 | 解决方案 | 日期 |
|------|---------|---------|------|
| 1 | `.env` 必须配置 `GITHUB_TOKEN`，否则 GitHub API 403 限速，下载页无法显示版本 | 创建 `.env`，填入 Fine-grained PAT，参考 `.env.example` | 2026-06-06 |
| 2 | 首次下载某个平台/架构组合需 1-2 分钟（从 GitHub 拉取并缓存），用户可能以为卡死 | 下载页 JS 显示"首次下载需从 GitHub 获取，请耐心等待"提示 | 2026-06-06 |
| 3 | `_detect_platform` 要求 Windows .exe 必须有显式 arch 后缀（-x64/-arm64），无后缀文件（如 `-win.exe`）会跳过 | Windows 发布时确保 asset 名称包含 `-x64` 或 `-arm64` | 2026-06-06 |
| 4 | 本地缓存文件名从 `{platform}-{arch}.{ext}` 改为 GitHub 原始名（ADR-014）。`get_download_path()` 兼容新旧两种命名 | 旧缓存不需要手动迁移，兜底扫描会自动找到 | 2026-06-23 |
| 5 | 客户端自动更新（electron-updater）读的 `latest-mac.yml`/`latest.yml` feed 曾由 `UpdateFeedService` 实时从 GitHub asset 拉取；广州服务器连 github.com 下载会 30s 超时并回退内存陈旧缓存 → 新版本发布后客户端长期检测不到（2026-09-06 2.1.0 事件根因）。download/update/latest/check 走 api.github.com（可达）故显示正常，易误判 | ✅ 已修复（2026-09-06，ADR-017）：yml feed 以 COS 稳定 key `codex-switch/latest/*.yml` 为来源、GitHub 仅兜底；download/upload 脚本已同步 latest*.yml。⚠️ 尚未部署上线——需先跑脚本种 COS 稳定 key 再部署服务端代码 | 2026-09-06 |
| 6 | **门户内容整体停留在「本地代理时代」**，而客户端 v3.0.0（2026-09-10）已转型为「纯配置工具」。首页/下载页/指南/工具文档页仍在讲本地代理、端口 `11435`、Agnes、「启动代理」；「使用指南」共用的旧截图是 **v1.0.6 界面** | ✅ **已修复（2026-10-07，TASK-104）**：四页文案按 v3.0.0 重写，截图用真实客户端重截（**`step-config-switch-v3.png`** + 新增 `step-tools-status.png`），并加反向断言护栏（门户四页不得出现 代理/11435/Agnes/deepseek-chat/deepseek-reasoner/173/Windows 11） | 2026-10-07 修复 |
| 7 | `robots.txt`（`Allow: /support`、`/faq`）与 `llms.txt`（链接 `/support`）都指向技术支持页，但 `/support` 与 `/faq` 实测 **404**，且 `sitemap.xml` 未收录二者 → 三处口径不一致 | ✅ **已修复（2026-10-07，TASK-104）**：采用方案 A 落 `src/portal/templates/support.html` + `GET /support`；robots 去掉不存在的 `/faq`，sitemap 收录 `/support`；页脚新增「技术支持」链接 | 2026-10-07 修复 |
| 8 | `base.html` 的 `baidu-site-verification` 是占位符 `codeva-xxxxxxxxxx`；全站无 `rel=canonical`；`og:url`/`og:image` 指向旧域名 `www.codexswtich.cloud` | ✅ **已修复（2026-10-07，TASK-104）**：验证码改为 `BAIDU_SITE_VERIFICATION` 配置项（未配置不输出）；新增 canonical；og 统一 `codex-switch.cloud`。⚠️ 上线前需在 `.env` 填真实验证码，否则等于移除该标签 | 2026-10-07 修复 |
| 9 | 客户端 v3.0.0 起遥测上报体**不再含 `client_id`**，而 `src/schemas/telemetry.py` 仍将其设为**必填** → v3.0.0 全部 **422 被静默丢弃** | ✅ **已修复（2026-10-07，TASK-104）**：`client_id` 改可选，空值跳过 `ClientRegistry` 注册；实测无 id → 200、带 id → 200。**不要试图让客户端加回 `client_id`**（合规） | 2026-10-07 修复 |
| 10 | 未跟踪文件 `tests/integration/test_client_community.py` 存在 import 顺序告警，使 `uv run ruff check .` 非全绿 | 非本次引入；改动该文件前需确认归属，或直接 `uv run ruff check --fix` | 2026-10-07 记录 |
| 11 | `src/static/images/guide/step-dl-switch-windows.png` 文件不存在（指南「下载 Codex Switch」步骤引用它） | ✅ **已修复（2026-10-07，TASK-104）**：补上下载页 Windows 卡片截图（含修正后的系统要求），无需改代码、两处引用自动生效；指南 5 张图全部正常加载 | 2026-10-07 修复 |
| 12 | 移动端文档页 `.doc__chips` 与固定导航重叠（既有 `/tools/*` 三页 + 新 `/support` 同样表现） | 既有问题；修它需动 `apple.css`，按最小化修改纪律暂缓 | 2026-10-07 记录 |
| 13 | **`/static/` 的 `?v=` 缓存刷新在本站 CDN 上不生效**：腾讯云 CDN 对 `/static/` **忽略 query string**（实测 `apple.css` 带 `?v=1` / `?v=20260909` / `?v=zzz999` 与无参数返回**同一 ETag 与 Expires**）。nginx 对 `/static/` 设 `expires 7d` + `immutable`，CDN 侧 `max-age=86400` | 要真正刷新静态资源，**必须改文件名**（如 `xxx-v3.png`）或手动刷 CDN；改 `?v=` 无效。HTML 不受影响（`main.py` 的 `no_cache_html` 中间件给 `text/html` 加 `no-store`，线上实测 `GET /` 为 Cache Miss） | 2026-10-07 记录 |
| 14 | **Claude Desktop 安装步骤的 2 张插图缺失**：`step-install-claude-windows.png`、`step-install-claude-macos.png`（`guide.html` 的 `imgTag('step-install-' + selTool + '-' + selPlat + '.png')` 会请求它们） | 既有缺失（`onerror` 隐藏，不裂图，仅该步无插图）。补图需作者提供真实安装过程截图——**凭空造图会失真，故未补**。跑全「4 工具 × 2 平台」才发现的 | 2026-10-07 记录 |
| 15 | 移动端（≤400px）**所有门户页横向溢出 29px**（`scrollWidth 429` vs `innerWidth 400`），可轻微左右横滑 | 既有问题，**已用 `git stash` 基线对比确认非某次改动引入**（改动前四页同样是 429）。桌面/平板无溢出。根因在 `apple.css` 全局布局，修它需动设计系统，按最小化纪律暂缓 | 2026-10-07 记录 |
| 16 | **指南 9 张图片在生产返回 403**（`step-cli-*-win.png`、`step-install-codex-windows.png` 等），Windows CLI 流程一张图都不显示 | ✅ **已修复（2026-10-07，TASK-105）**：根因是文件以 git mode **100755** 提交、检出后为 **0700**，Docker 原样拷贝后 root 所有，nginx worker 降权读不到 → 403。已把 9 个文件改 0644（`100755→100644`），并在 Dockerfile 加 `chmod -R a+rX /app/src/static` 兜底。**教训：静态资源一律不要带可执行位** | 2026-10-07 修复 |
| 17 | **`/llms.txt` 经 CDN 仍是旧内容**（源站已正确）；同站的 robots/sitemap 却是新的 | ⚠️ 未处理：腾讯云 CDN 对该文件缓存了旧副本。处置：控制台 → CDN → 刷新预热 → URL 刷新填 `https://codex-switch.cloud/llms.txt`；或等 TTL 自然过期。**注意 CDN 忽略 query string，加 `?v=` 无效** | 2026-10-07 记录 |
| 18 | 静态资源带可执行位（`100755`）是**本项目的历史习惯**（多个 guide 图片都曾如此） | 预防：已由 Dockerfile 的 `chmod -R a+rX /app/src/static` 兜底；新增图片建议保持 0644 | 2026-10-07 记录 |

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
ICP_FILING_NUMBER=  # ICP 备案号，生产环境必填（如 京ICP备2026035967号-1）
BAIDU_SITE_VERIFICATION=  # 百度站长验证码；留空则 <head> 不输出 baidu-site-verification 标签
AI_WORKING_OK_CACHE_TTL=300  # ai-working-ok 版本查询 TTL
TOOL_CHANGELOG_CACHE_TTL=300  # 工具文档页 CHANGELOG.md 抓取缓存 TTL
```

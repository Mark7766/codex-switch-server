# Admin 运营后台优化方案 v2

> **状态**：待 Review  
> **日期**：2026-06-07  
> **设计者**：wangliang + Claude Code

---

## 1. 背景与目标

### 当前问题

| 问题 | 现状 |
|------|------|
| 门户无埋点 | 不知道 `/ /download /guide` 哪个页面访问多，用户点了什么按钮 |
| 下载统计粗 | 只有一个"总下载量"数字，不知道 8 个下载包各自被下载了多少次 |
| Admin 混杂 | Server 端指标（下载、包管理）和 App 端指标（遥测事件）混在一个面板 |

### 优化目标

1. **门户埋点** — 知道用户访问了哪些页面、点击了什么按钮，**中文展示**
2. **下载精细化** — 8 个下载包各自下载量、占比、趋势
3. **Admin 分家** — 两个独立 Tab：「Server 运营」和「App 遥测」

---

## 2. 方案设计

### 2.1 咱们的 8 个下载包

系统对外提供两类下载，共 8 个入口：

| 序号 | 类型 | 产品名 | 平台 | 架构 | 下载端点 | 文件扩展名 |
|------|------|--------|------|------|---------|-----------|
| 1 | Codex Switch | Codex Switch | macOS | ARM64 | `/api/v1/update/download/1.4.0/macos-arm64` | .dmg |
| 2 | Codex Switch | Codex Switch | macOS | x64 | `/api/v1/update/download/1.4.0/macos-x64` | .dmg |
| 3 | Codex Switch | Codex Switch | Windows | ARM64 | `/api/v1/update/download/1.4.0/windows-arm64` | .exe |
| 4 | Codex Switch | Codex Switch | Windows | x64 | `/api/v1/update/download/1.4.0/windows-x64` | .exe |
| 5 | 桌面应用 | Codex Desktop | macOS | ARM64 | `/api/v1/packages/codex-desktop/X/macos-arm64` | .dmg |
| 6 | 桌面应用 | Codex Desktop | Windows | x64 | `/api/v1/packages/codex-desktop/X/windows-x64` | .exe |
| 7 | 桌面应用 | Claude Desktop | macOS | ARM64 | `/api/v1/packages/claude-desktop/X/macos-arm64` | .dmg |
| 8 | 桌面应用 | Claude Desktop | Windows | x64 | `/api/v1/packages/claude-desktop/X/windows-x64` | .msix |

### 2.2 数据模型

#### 现有表：`download_records`

```
id, version, platform, arch, ip_hash, created_at
```

**问题**：当前 `download_records` 只区分 `platform` + `arch`（如 `macos` + `arm64`），无法区分是 Codex Switch 本体下载还是桌面应用下载（两者都可能是 `macos/arm64`）。

**方案**：给 `download_records` 加一个 `product` 字段区分来源。

```sql
-- 新增字段（SQLite ALTER TABLE ADD COLUMN 兼容）
ALTER TABLE download_records ADD COLUMN product TEXT NOT NULL DEFAULT 'codex-switch';
-- product 取值：'codex-switch' | 'codex-desktop' | 'claude-desktop'
```

> 历史数据 product 默认填 `codex-switch`（旧代码只记录 Codex Switch 下载），新代码写入时带上 product。

#### 新增表：`page_events`

```sql
CREATE TABLE page_events (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,        -- 'pageview' | 'click'
    page       TEXT NOT NULL,        -- '/' | '/download' | '/guide'
    element_id TEXT,                 -- 点击元素 ID（英文 key，展示时查映射表转中文）
    ip_hash    TEXT,                 -- SHA256(client_ip)
    user_agent TEXT,                 -- 浏览器 UA（截断到 256 字符）
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX idx_page_events_type ON page_events(event_type);
CREATE INDEX idx_page_events_page ON page_events(page);
CREATE INDEX idx_page_events_date ON page_events(created_at);
```

---

### 2.3 中文映射表

页面和元素 ID 用英文存储（编程友好），Admin 展示时通过映射表转为中文。

#### 页面 URL → 中文名称

| URL (存储值) | 中文名称 |
|-------------|---------|
| `/` | 首页 |
| `/download` | 下载页 |
| `/guide` | 使用指南 |

#### 元素 ID → 中文名称 + 所在页面

| element_id (存储值) | 中文名称 | 所在页面 |
|---------------------|---------|---------|
| `hero-guide-cta` | Hero区-查看安装指南按钮 | 首页 |
| `hero-download-cta` | Hero区-直接下载按钮 | 首页 |
| `guide-entry-codex` | 安装指南入口-Codex Desktop卡片 | 首页 |
| `guide-entry-claude` | 安装指南入口-Claude Desktop卡片 | 首页 |
| `guide-entry-codex-cli` | 安装指南入口-Codex CLI卡片 | 首页 |
| `guide-entry-claude-cli` | 安装指南入口-Claude Code CLI卡片 | 首页 |
| `tool-card-codex-desktop` | 下载区-Codex Desktop下载按钮 | 首页 |
| `tool-card-claude-desktop` | 下载区-Claude Desktop下载按钮 | 首页 |
| `dl-tab-macos` | 下载页-macOS平台切换 | 下载页 |
| `dl-tab-windows` | 下载页-Windows平台切换 | 下载页 |
| `dl-tab-linux` | 下载页-Linux平台切换 | 下载页 |
| `dl-btn-macos-arm64` | 下载页-macOS ARM64下载按钮 | 下载页 |
| `dl-btn-macos-x64` | 下载页-macOS x64下载按钮 | 下载页 |
| `dl-btn-windows-arm64` | 下载页-Windows ARM64下载按钮 | 下载页 |
| `dl-btn-windows-x64` | 下载页-Windows x64下载按钮 | 下载页 |
| `guide-choice-codex` | 指南-选择Codex工具卡片 | 使用指南 |
| `guide-choice-claude` | 指南-选择Claude工具卡片 | 使用指南 |
| `guide-choice-codex-cli` | 指南-选择Codex CLI工具卡片 | 使用指南 |
| `guide-choice-claude-cli` | 指南-选择Claude Code CLI工具卡片 | 使用指南 |
| `guide-platform-macos` | 指南-选择macOS平台按钮 | 使用指南 |
| `guide-platform-windows` | 指南-选择Windows平台按钮 | 使用指南 |
| `guide-dl-codex-switch` | 指南-下载Codex Switch按钮 | 使用指南 |
| `guide-dl-codex-desktop` | 指南-下载Codex Desktop按钮 | 使用指南 |
| `guide-dl-claude-desktop` | 指南-下载Claude Desktop按钮 | 使用指南 |
| `guide-apikey-btn` | 指南-创建API Key按钮 | 使用指南 |
| `nav-download` | 导航栏-下载链接 | 全局 |
| `nav-guide` | 导航栏-指南链接 | 全局 |
| `nav-github` | 导航栏-GitHub链接 | 全局 |
| `footer-github` | 页脚-GitHub链接 | 全局 |

> 映射表硬编码在 `src/services/analytics.py` 中，不在数据库。新增元素 ID 时同步更新映射表。

#### 下载产品 ID → 中文名称

| product (存储值) | 中文名称 |
|-----------------|---------|
| `codex-switch` | Codex Switch |
| `codex-desktop` | Codex Desktop |
| `claude-desktop` | Claude Desktop |

#### 平台 → 中文名称

| 存储值 | 中文名称 |
|--------|---------|
| `macos-arm64` | macOS Apple Silicon |
| `macos-x64` | macOS Intel |
| `windows-arm64` | Windows ARM64 |
| `windows-x64` | Windows x64 |

---

### 2.4 API 设计

#### 新增：`POST /api/v1/analytics/pageview`

```json
// Request
{
  "event_type": "pageview",        // 'pageview' | 'click'
  "page": "/guide",
  "element_id": "guide-choice-codex"   // 仅 click 事件
}

// Response
{
  "status": "ok"
}
```

- 无需认证（公开端点）
- 前端 `navigator.sendBeacon()` 异步发送

#### 新增：`GET /api/v1/admin/analytics/page-stats?range_days=30`

```json
{
  "page_views": [
    {"page": "/", "page_name": "首页", "count": 1234},
    {"page": "/guide", "page_name": "使用指南", "count": 890},
    {"page": "/download", "page_name": "下载页", "count": 456}
  ],
  "top_clicks": [
    {"element_id": "hero-guide-cta", "element_name": "Hero区-查看安装指南按钮", "page_name": "首页", "count": 320},
    {"element_id": "guide-dl-codex-switch", "element_name": "指南-下载Codex Switch按钮", "page_name": "使用指南", "count": 280}
  ],
  "daily_trend": [
    {"date": "2026-06-01", "pageviews": 120, "clicks": 45},
    {"date": "2026-06-02", "pageviews": 135, "clicks": 52}
  ]
}
```

> API 返回中同时包含英文 key 和中文名称，Admin 直接使用中文名称渲染。

#### 新增：`GET /api/v1/admin/analytics/download-trends?range_days=30`

```json
{
  "total": 12345,
  "daily": [
    {
      "date": "2026-06-01",
      "total": 145,
      "breakdown": {
        "codex-switch-macos-arm64": 28,
        "codex-switch-macos-x64": 12,
        "codex-switch-windows-arm64": 5,
        "codex-switch-windows-x64": 55,
        "codex-desktop-macos-arm64": 20,
        "codex-desktop-windows-x64": 15,
        "claude-desktop-macos-arm64": 8,
        "claude-desktop-windows-x64": 2
      }
    }
  ],
  "by_product": [
    {"product": "codex-switch", "product_name": "Codex Switch", "count": 8000},
    {"product": "codex-desktop", "product_name": "Codex Desktop", "count": 3000},
    {"product": "claude-desktop", "product_name": "Claude Desktop", "count": 1345}
  ],
  "by_package": [
    {"product": "codex-switch", "product_name": "Codex Switch", "platform": "windows-x64", "platform_name": "Windows x64", "count": 4200},
    {"product": "codex-switch", "product_name": "Codex Switch", "platform": "macos-arm64", "platform_name": "macOS Apple Silicon", "count": 2800}
  ],
  "by_version": [
    {"version": "1.4.0", "count": 8000},
    {"version": "1.3.0", "count": 3000}
  ],
  "cos_hit_rate": 0.85
}
```

> `by_package` 按 8 个下载包粒度拆分（product + platform + arch），按下载量降序排列。

---

### 2.5 前端埋点（portal JS）

```javascript
// 页面浏览 — 每个页面加载时自动上报
(function() {
  var data = {
    event_type: 'pageview',
    page: window.location.pathname
  };
  navigator.sendBeacon('/api/v1/analytics/pageview', JSON.stringify(data));
})();

// 按钮点击 — 给关键按钮加 data-track 属性
// HTML 示例:
//   <a href="/guide" data-track="hero-guide-cta" class="btn">查看安装指南</a>
//   <a href="/download" data-track="hero-download-cta" class="btn">直接下载</a>
document.addEventListener('click', function(e) {
  var el = e.target.closest('[data-track]');
  if (!el) return;
  var data = {
    event_type: 'click',
    page: window.location.pathname,
    element_id: el.getAttribute('data-track')
  };
  navigator.sendBeacon('/api/v1/analytics/pageview', JSON.stringify(data));
});
```

### 2.6 Admin 面板布局

```
┌──────────────────────────────────────────────────────────────────┐
│  Codex Switch 运营后台                                            │
│  [Server 运营]  [App 遥测]  [安装包管理]          [返回首页]      │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─ Server 运营 ─────────────────────────────────────────────┐   │
│  │                                                           │   │
│  │  指标卡片行                                                │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │   │
│  │  │ 总下载量  │ │ 今日下载  │ │ COS命中率 │ │ 今日访问  │     │   │
│  │  │  12,345  │ │    89    │ │   85%    │ │  1,203   │     │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘     │   │
│  │                                                           │   │
│  │  ┌─ 下载趋势 (7天/30天/90天 切换) ────────────────────┐   │   │
│  │  │  📈 折线图：每日总下载量，8 条线按产品+平台分层     │   │   │
│  │  │  （可选只显示 Top 5，其余归入"其他"）              │   │   │
│  │  └────────────────────────────────────────────────────┘   │   │
│  │                                                           │   │
│  │  ┌─ 各下载包明细（表格）────────────────────────────────┐   │   │
│  │  │  📋 8 行表格，按下载量降序                           │   │   │
│  │  │  排名 │ 产品名         │ 平台            │ 下载量 占比│   │   │
│  │  │   1  │ Codex Switch   │ Windows x64     │ 4,200  34% │   │   │
│  │  │   2  │ Codex Switch   │ macOS ARM64     │ 2,800  23% │   │   │
│  │  │   3  │ Codex Desktop  │ macOS ARM64     │ 2,100  17% │   │   │
│  │  │  ... │ ...            │ ...             │ ...    ... │   │   │
│  │  └────────────────────────────────────────────────────┘   │   │
│  │                                                           │   │
│  │  左右两列                                                  │   │
│  │  ┌─ 页面访问分布 ──────┐ ┌─ 热门点击 Top 10 ──────────┐  │   │
│  │  │  📊 横向柱状图       │ │  📋 表格                     │  │   │
│  │  │  首页      ████ 1234│ │  1. Hero区-查看安装指南 320 │  │   │
│  │  │  使用指南  ███  890 │ │  2. 指南-下载Codex Switch280│  │   │
│  │  │  下载页    ██   456 │ │  3. ...                     │  │   │
│  │  └────────────────────┘ └──────────────────────────────┘  │   │
│  │                                                           │   │
│  │  ┌─ 各产品下载占比 ────────────────────────────────────┐   │   │
│  │  │  🍩 环形图：Codex Switch / Codex Desktop / Claude   │   │   │
│  │  └────────────────────────────────────────────────────┘   │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─ App 遥测（切换到该 Tab 时显示）──────────────────────────┐   │
│  │                                                           │   │
│  │  指标卡片                                                  │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────────┐         │   │
│  │  │ 活跃用户 │ │ 今日事件 │ │ 事件总数 │ │ 新增用户(7天)│        │   │
│  │  │ 3,892  │ │ 1,203  │ │ 98,234 │ │   156      │         │   │
│  │  └────────┘ └────────┘ └────────┘ └────────────┘         │   │
│  │                                                           │   │
│  │  ┌─ 功能使用分布 ──┐ ┌─ 事件趋势 ────────────────────┐   │   │
│  │  │  📊 柱状图       │ │  📈 折线图 (30天)              │   │   │
│  │  └─────────────────┘ └────────────────────────────────┘   │   │
│  │                                                           │   │
│  │  ┌─ 最近遥测事件 ────────────────────────────────────┐   │   │
│  │  │  📋 表格                                           │   │   │
│  │  └───────────────────────────────────────────────────┘   │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─ 安装包管理（同现有，不变）───────────────────────────────┐   │
│  │  4 个固定卡片：Codex/Claude × macOS/Windows               │   │
│  └───────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

### 2.7 路由设计

| 路由 | 方法 | 说明 | 访问 |
|------|------|------|------|
| `/admin` | GET | 运营后台（三 Tab 导航），默认 Server 运营 | Token |
| `/admin?tab=server` | GET | Server 运营 Tab | Token |
| `/admin?tab=app` | GET | App 遥测 Tab | Token |
| `/admin/packages` | GET | 安装包管理页面 | Token |
| `/api/v1/analytics/pageview` | POST | 门户埋点上报 | 公开 |
| `/api/v1/admin/analytics/page-stats` | GET | 页面统计数据 API（含中文映射） | Token |
| `/api/v1/admin/analytics/download-trends` | GET | 下载趋势 + 各包明细 API（含中文映射） | Token |

### 2.8 CSS 设计

- 沿用 Apple 设计系统（`apple.css`）
- 新增 `.admin-tabs` 分段控件样式（跟下载页的 Apple 风格分段控件一致）
- Tab 切换纯 CSS + JS（三个面板同一个 HTML 文件，JS 控制 display）
- 图表容器响应式：≥980px 两列，<768px 单列
- 表格样式沿用现有 `.table-wrap` + `table` 样式

---

## 3. 实施计划

### 3.1 文件变更清单

| 文件 | 动作 | 说明 |
|------|------|------|
| `src/models/page_event.py` | **新建** | PageEvent ORM 模型（event_type, page, element_id, ip_hash, user_agent） |
| `src/schemas/analytics.py` | **新建** | PageviewRequest, PageStatsResponse, DownloadTrendsResponse DTO（含中文名） |
| `src/services/analytics.py` | **新建** | AnalyticsService：页面/点击统计 + 中文映射表 + 下载趋势查询 |
| `src/services/release_sync.py` | **修改** | `record_download()` 加 product 参数；新增 `get_download_trends()` 方法 |
| `src/api/v1/analytics.py` | **新建** | `POST /api/v1/analytics/pageview` |
| `src/api/v1/admin_api.py` | **新建** | `GET /admin/api/page-stats` + `GET /admin/api/download-trends` |
| `src/api/router.py` | **修改** | 注册 analytics router + admin api router |
| `src/api/v1/update.py` | **修改** | `record_download()` 调用传入 `product='codex-switch'` |
| `src/api/v1/packages.py` | **修改** | 包下载时调用 `record_download()` 传入 product |
| `src/admin/router.py` | **修改** | dashboard 改为三 Tab 布局，数据 API 驱动 |
| `src/admin/templates/dashboard.html` | **重写** | 三 Tab 布局 + 新图表（下载趋势、包明细表、页面分布、热门点击） |
| `src/admin/templates/packages.html` | 不变 | — |
| `src/static/js/portal.js` | **修改** | 新增 sendBeacon 埋点逻辑 |
| `src/portal/templates/index.html` | **修改** | 关键按钮加 `data-track` 属性 |
| `src/portal/templates/download.html` | **修改** | 关键按钮加 `data-track` 属性 |
| `src/portal/templates/guide.html` | **修改** | 关键按钮加 `data-track` 属性 |
| `src/static/css/apple.css` | **修改** | 新增 `.admin-tabs` 分段控件样式 |
| `src/database.py` | **修改** | 导入 PageEvent 模型；download_records 加 product 字段 |
| `src/main.py` | **修改** | 注册新路由 |
| `tests/` | **新建/修改** | page events 测试 + 下载趋势测试 + 中文映射测试 |

### 3.2 分阶段执行

| Phase | 内容 | 预估 |
|-------|------|------|
| **Phase A** | 数据层：PageEvent 模型 + download_records 加 product 字段 + AnalyticsService + 中文映射 | 35 min |
| **Phase B** | API 层：pageview 上报 + page-stats 查询（含中文）+ download-trends（8 包粒度） | 50 min |
| **Phase C** | 前端埋点：portal JS sendBeacon + 3 个模板加 data-track 属性 | 25 min |
| **Phase D** | Admin 重设计：三 Tab dashboard + Chart.js 新图表 + 包明细表格 | 60 min |
| **Phase E** | 测试（新增 ≥ 12 个测试）+ 部署 | 30 min |

---

## 4. 关键约束

1. **不引入任何新依赖** — 埋点用原生 `navigator.sendBeacon()`，不引入第三方统计
2. **不影响页面性能** — sendBeacon 异步、不阻塞渲染
3. **数据不出境** — 所有埋点数据存在自己的 SQLite，不经过外部服务
4. **保持 Apple 设计风格** — Tab 控件、卡片布局沿用现有 Design Token
5. **向后兼容** — 现有路由不变，`product` 字段有默认值 `'codex-switch'`
6. **隐私合规** — IP 只存 SHA256 哈希，不存原始 IP
7. **中文映射硬编码** — 映射表在 `analytics.py` 中，不存数据库，简单直接

---

## 5. 设计决策

### 为什么 product 字段加在 download_records 上而不是建新表？

download_records 数据量不大（数千条量级），加一个 TEXT 字段成本极低。SQLite 的 ALTER TABLE ADD COLUMN 原生支持，无需迁移工具。

### 为什么中文映射表硬编码？

30 个元素 ID 不到，放在代码里比放数据库更简单：改代码 = 改映射，不需要数据迁移。如果后续元素数量超过 50，可以考虑放 JSON 配置文件。

### 下载趋势图 8 条线会不会太乱？

默认只显示总量折线图。点击"按包拆分"复选框后才显示 8 条分层线。或者用堆叠面积图，按 product 聚合为 3 条主线（Codex Switch / Codex Desktop / Claude Desktop），hover 才显示平台明细。

---

## 6. 验证标准

- [ ] ruff check 零错误
- [ ] pytest 全部通过（新增 ≥ 12 个测试）
- [ ] 中文映射表覆盖所有 element_id 和 page URL
- [ ] 埋点：打开 / → admin 能看到"首页" pageview
- [ ] 埋点：点击下载按钮 → admin 能看到中文名称的 click
- [ ] 下载趋势：8 个包的下载量分别统计正确
- [ ] 下载明细表：8 行，中文名，按量降序
- [ ] Tab 切换：Server/App/Packages 三个 Tab 正常
- [ ] 移动端响应式：<768px 单列正常

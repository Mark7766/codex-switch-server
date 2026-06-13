# Spec: Client 运营 — Codex Switch 版本洞察

- **日期**：2026-06-14
- **状态**：方案设计，待 Review

---

## 1. 需求

在 Client 运营 Tab 增加"版本洞察"区块，回答两个核心运营问题：

1. **哪些版本在用？** — 版本分布全景
2. **有多少人在用最新版？** — 升级跟进率

---

## 2. 数据来源

`telemetry_events` 表已有 `app_version` 字段，每条 `app_start` 事件携带版本号。当前生产数据示例：

```
app_start 事件: 7 条
app_version: 1.6.0, 1.6.0, 1.8.0, 1.8.0, ...
```

统计口径：

| 指标 | 口径 | 说明 |
|------|------|------|
| 版本分布 | 30 天内 `app_start` 按 `app_version` 分组，COUNT 事件数 | 看哪些版本活跃 |
| 版本用户数 | 30 天内 `app_start` 按 `app_version` 分组，COUNT DISTINCT `client_id` | 去重用户数 |
| 最新版本覆盖率 | 最新版本用户数 / 总用户数 | 核心北极星指标 |
| 过时版本列表 | 非最新版本 + 最后活跃时间 | 是否需要强制升级提醒 |

---

## 3. 方案设计

### 3.1 布局

在 Client 运营 Tab，安装成功率卡片下方（或事件趋势上方），新增一个区块：

```
┌─ Codex Switch 版本洞察 ──────────────────────────────┐
│                                                      │
│  最新版本覆盖率                                       │
│  ┌──────────┐  ┌───────────────────────────────────┐  │
│  │   67%    │  │  ████████████████████████ v1.8.0  │  │
│  │ 使用最新  │  │  ██████ v1.6.0                   │  │
│  │          │  │  ██ v1.5.4                       │  │
│  └──────────┘  └───────────────────────────────────┘  │
│                                                      │
│  版本明细                                            │
│  ┌──────────┬──────────┬────────────┬──────────────┐ │
│  │ 版本     │ 用户数   │ 启动次数    │ 最后活跃     │ │
│  │ v1.8.0   │ 4        │ 24         │ 2026-06-14   │ │
│  │ v1.6.0   │ 2        │ 8          │ 2026-06-13   │ │
│  │ v1.5.4   │ 1        │ 3          │ 2026-06-12   │ │
│  └──────────┴──────────┴────────────┴──────────────┘ │
└──────────────────────────────────────────────────────┘
```

### 3.2 数据查询

```sql
-- 版本分布（30天）
SELECT app_version,
       COUNT(*) as event_count,
       COUNT(DISTINCT client_id) as user_count,
       MAX(created_at) as last_seen
FROM telemetry_events
WHERE event_type = 'app_start'
  AND created_at >= datetime('now', '-30 days')
  AND app_version != ''
GROUP BY app_version
ORDER BY app_version DESC
```

最新版本从 GitHub API 或 `/api/v1/update/latest` 获取（当前为 v1.6.0，但 GitHub 最新是 v1.8.1）。最新版本覆盖率 = 最新版本用户数 / 总用户数。

### 3.3 服务端改动

**TelemetryService.get_stats()** 新增 `version_insight` 字段：

```python
class VersionItem(BaseModel):
    version: str
    user_count: int
    event_count: int
    last_seen: str

class TelemetryStats(BaseModel):
    # ... existing fields ...
    latest_version: str = ""           # from GitHub, e.g. "1.8.0"
    version_coverage: str = "—"        # e.g. "67%"
    version_insight: list[VersionItem] = []
```

**Admin router** 将 `latest_version` 和 `version_insight` 传给模板。

### 3.4 模板改动

`dashboard.html` Client 运营 Tab 增加版本洞察区块（Jinja2 渲染表格 + 简易 CSS bar chart）。

### 3.5 最新版本号来源

两种方式：

| 方式 | 优点 | 缺点 |
|------|------|------|
| A. 复用 `ReleaseSyncService.get_latest_from_github()` 内存缓存 | 实时，零额外请求 | 依赖 GitHub API |
| B. 从 `telemetry_events` 取最大 `app_version` | 无外部依赖 | 如果有用户用旧版且没人用新版，就不知道最新版是什么 |

**选 A**。`get_latest_from_github()` 已有 5 分钟内存缓存，直接复用。

---

## 4. 运营价值

| 指标 | 价值 |
|------|------|
| **最新版本覆盖率** | 如果低于 80%，说明升级推送机制有问题（electron-updater 配置/用户跳过升级） |
| **版本分布** | 发现"钉子户版本"——如 v1.5.4 仍有用户，可能需要强制升级或安全提醒 |
| **最后活跃时间** | 区分"还在用的老版本"和"已弃用的老版本" |

---

## 5. 与现有 Client 运营 Tab 的关系

```
Client 运营 Tab 改后布局：
┌──────────────────────────────────────────────┐
│ 今日事件 │ 活跃用户 │ 模型调用 │ 安装成功率     │  ← 4 卡片
├──────────────────────────────────────────────┤
│ 模型调用活跃度 │ 功能使用(配置操作)             │  ← 2 图表
├──────────────────────────────────────────────┤
│ Codex Switch 版本洞察  ← 新增                  │
│ [覆盖率卡片] [版本柱状图] [版本明细表]          │
├──────────────────────────────────────────────┤
│ 事件趋势 (30天)                               │
├──────────────────────────────────────────────┤
│ 最近遥测事件                                  │
└──────────────────────────────────────────────┘
```

---

## 6. 实施

| 文件 | 改动 |
|------|------|
| `src/schemas/telemetry.py` | +`VersionItem`, +`latest_version`, +`version_coverage`, +`version_insight` |
| `src/services/telemetry.py` | `get_stats()` 加版本查询 + 覆盖率计算 |
| `src/admin/router.py` | 传 `latest_version` 给模板 |
| `src/admin/templates/dashboard.html` | +版本洞察区块 |

代码量估约 50 行。

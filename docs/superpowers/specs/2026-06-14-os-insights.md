# Spec: Client 运营 — 操作系统洞察

- **日期**：2026-06-14
- **状态**：方案设计，待 Review

---

## 1. 需求

在 Client 运营 Tab 增加"操作系统洞察"区块，回答：

1. **Codex Switch 跑在哪些 OS 上？** — 操作系统分布全景
2. **各 OS 有多少部署？** — 用户数/设备数
3. **哪个 OS 是主力？** — 指导开发和测试资源分配

## 2. 数据来源

`telemetry_events` 表的 `app_start` 事件已携带 `platform` 字段（`darwin`/`win32`）。已有数据：

```
app_start 事件携带:
  platform: "darwin"  → Mac
  platform: "win32"   → Windows
```

统计口径（30 天）：

| 指标 | 口径 |
|------|------|
| OS 分布 | `app_start` 按 `platform` 分组，COUNT DISTINCT `client_id` |
| 启动次数 | 同上，COUNT 事件数 |
| OS 占比 | 各 OS 用户数 / 总用户数 |

## 3. 方案设计

### 3.1 布局

放在版本洞察下方，与版本洞察共用同一设计语言（覆盖率卡片 + 明细表）：

```
┌─ 操作系统洞察 ──────────────────────────────────────┐
│                                                    │
│  ┌──────────┐  ┌──────────┐                          │
│  │ 🍎 Mac   │  │ 🪟 Win   │                          │
│  │   3      │  │   2      │                          │
│  │  60%     │  │  40%     │                          │
│  └──────────┘  └──────────┘                          │
│                                                    │
│  版本·OS 交叉明细                                   │
│  ┌──────────┬──────────┬──────────┬──────────────┐  │
│  │ 版本     │ Mac      │ Windows  │               │  │
│  │ v1.8.1   │ 1        │ —        │               │  │
│  │ v1.8.0   │ 2        │ —        │               │  │
│  │ v1.7.0   │ —        │ 1        │               │  │
│  └──────────┴──────────┴──────────┴───────────────┘  │
└────────────────────────────────────────────────────┘
```

### 3.2 三个卡片

每个 OS 一张小卡片，展示：
- 图标：Apple SVG / Microsoft 窗格 SVG（与首页 Hero 一致）
- 用户数
- 占比百分比

### 3.3 版本×OS 交叉表

结合已有的版本洞察数据，展示每个版本在各 OS 上的分布。一目了然看到"v1.8.1 主要在 Mac 上、v1.7.0 主要在 Windows 上"。

### 3.4 数据查询

```sql
-- OS 用户分布（30天）
SELECT platform,
       COUNT(DISTINCT client_id) as user_count,
       COUNT(*) as event_count
FROM telemetry_events
WHERE event_type = 'app_start'
  AND created_at >= datetime('now', '-30 days')
  AND platform != ''
GROUP BY platform

-- 版本×OS 交叉（30天）
SELECT app_version, platform,
       COUNT(DISTINCT client_id) as user_count
FROM telemetry_events
WHERE event_type = 'app_start'
  AND created_at >= datetime('now', '-30 days')
  AND app_version != '' AND platform != ''
GROUP BY app_version, platform
ORDER BY app_version DESC
```

## 4. 服务端改动

### Schema

```python
class OsItem(BaseModel):
    platform: str          # "darwin" / "win32"
    platform_name: str     # "Mac" / "Windows"
    user_count: int
    event_count: int

class VersionOsItem(BaseModel):
    version: str
    mac_users: int
    win_users: int

class TelemetryStats(BaseModel):
    # ... existing ...
    os_insight: list[OsItem] = []
    version_os_cross: list[VersionOsItem] = []
```

### Service

`get_stats()` 中加两个查询，约 20 行。

### Template

`dashboard.html` Client 运营 Tab 加 OS 洞察区块，约 30 行 HTML。

## 5. 涉及改动

| 文件 | 改动 |
|------|------|
| `src/schemas/telemetry.py` | +`OsItem`, +`VersionOsItem`, +2 字段 |
| `src/services/telemetry.py` | +2 查询 |
| `src/admin/templates/dashboard.html` | +OS 洞察区块 |

代码量估约 50 行。

## 6. 运营价值

| 指标 | 价值 |
|------|------|
| **OS 占比** | 指导测试资源——如果 Mac 占 90%，Windows 测试可以降优先级；反之亦然 |
| **版本×OS 交叉** | 发现"某个版本只在某个 OS 上有问题"——如 v1.7.0 在 Windows 上全部没升级 |

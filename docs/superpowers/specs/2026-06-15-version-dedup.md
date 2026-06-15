# Spec: 版本洞察去重 + 趋势图日期标签修复

- **日期**：2026-06-15
- **状态**：方案设计，待 Review
- **基于**：生产数据验证
- **包含**：Bug #1 版本去重 + Bug #2 趋势图日期显示

---

## 1. 问题

版本洞察和操作系统洞察中，同一个客户端在多个版本行被重复计数。

### 生产数据验证

```
旧方法（group by version, count distinct client_id）：
  1.10.0: 8
  1.9.1:  10
  1.7.0:  1
  1.8.0:  2
  1.8.1:  3
  1.9.0:  1
  合计:   25

新方法（每个 client 只计最新版本）：
  1.10.0: 8
  1.9.1:  7
  1.8.1:  2
  1.8.0:  1
  合计:   18 ← 等于总独立客户端数
```

### 根因

当前 SQL：`GROUP BY app_version, COUNT(DISTINCT client_id)` — 30 天内所有 `app_start` 事件都参与统计。如果客户端在窗口内从 v1.9.0 升级到 v1.9.1，它在两个版本中各被计数一次。**但对运营来说，这个客户应该只属于最新版本**——旧版本已经被它放弃了。

### 影响范围

| 区块 | 是否受影响 |
|------|----------|
| 版本洞察（版本分布） | ✅ 受影响：同一客户端出现在多个版本 |
| 操作系统洞察（OS 卡片） | 轻微：客户端通常不会换 OS |
| 版本×OS 交叉表 | ✅ 受影响：同版本问题 |

## 2. 方案

### 核心思路

**每个客户端只统计其最新版本**（30 天窗口内最后一条 `app_start` 的版本）。

### SQL 逻辑

```sql
-- Step 1: 找到每个 client 的最新 app_start
SELECT client_id, app_version, platform, MAX(created_at) as last_seen
FROM telemetry_events
WHERE event_type = 'app_start'
  AND created_at >= cutoff
  AND client_id != ''
  AND app_version != ''
GROUP BY client_id

-- Step 2: 在最新版本维度上聚合
-- 版本分布: GROUP BY app_version, COUNT(DISTINCT client_id)
-- OS 分布: GROUP BY platform, COUNT(DISTINCT client_id)
-- 版本×OS: GROUP BY app_version, platform, COUNT(DISTINCT client_id)
```

### Python 实现

```python
# Fetch each client's latest app_start in the window
subq = (
    select(
        TelemetryEvent.client_id,
        func.max(TelemetryEvent.created_at).label("last_seen"),
    )
    .where(
        TelemetryEvent.event_type == "app_start",
        TelemetryEvent.created_at >= cutoff,
        TelemetryEvent.client_id != "",
        TelemetryEvent.app_version != "",
    )
    .group_by(TelemetryEvent.client_id)
).subquery()

# Join back to get full row for the latest event
latest_rows = await self._db.execute(
    select(
        TelemetryEvent.app_version,
        TelemetryEvent.platform,
        func.count().label("user_count"),
        func.max(TelemetryEvent.created_at).label("last_seen"),
    )
    .join(subq, (TelemetryEvent.client_id == subq.c.client_id) & 
                 (TelemetryEvent.created_at == subq.c.last_seen))
    .group_by(TelemetryEvent.app_version)
    .order_by(...)
)
```

### 更简单的方式：两步 Python

```python
# 1. Get per-client latest app_start
rows = await db.execute(
    select(TelemetryEvent.client_id, TelemetryEvent.app_version, 
           TelemetryEvent.platform, func.max(TelemetryEvent.created_at))
    .where(event_type='app_start', created_at >= cutoff, ...)
    .group_by(TelemetryEvent.client_id)
).all()

# 2. Aggregate in Python
version_counts = Counter()
platform_counts = Counter()
cross_counts = Counter()
for cid, ver, plat, last in rows:
    version_counts[ver] += 1
    platform_counts[plat] += 1
    cross_counts[(ver, plat)] += 1
```

## 3. 效果

| 指标 | 改前 | 改后 |
|------|------|------|
| 版本分布合计 | 25（虚高） | 18（= 实际客户端数） |
| 最新版本覆盖率 | 40%（1.10.0:8 / 旧口径25） | 44%（1.10.0:8 / 18） |
| OS 分布合计 | 可能虚高 | 等于实际客户端数 |
| 版本×OS 交叉合计 | 可能虚高 | 等于实际客户端数 |

---

## Bug #2：趋势图日期标签是 UTC 而非北京时间

### 问题

Server 运营 Tab 的下载趋势和页面访问趋势折线图，横轴日期显示的是 **UTC 日期**，不是北京时间。

### 根因

`analytics.py` 中 `get_page_stats()` 和 `get_download_trends()` 的每日趋势循环：

```python
today = _beijing_today_start()  # 返回 UTC 16:00（北京 00:00 对应的 DB 时间戳）
for i in range(range_days - 1, -1, -1):
    day_start = today - timedelta(days=i)  # e.g., 2026-06-14 16:00:00
    ...
    DailyAnalyticsTrend(date=day_start.strftime("%Y-%m-%d"), ...)  # "2026-06-14"
```

`_beijing_today_start()` 返回的是 UTC `2026-06-14 16:00:00`——这个值用于 DB 查询是正确的（对齐 UTC 时间戳），但 `strftime("%Y-%m-%d")` 取出的是 **UTC 日期** `"2026-06-14"`，而非北京时间 `"2026-06-15"`。

### 验证

生产 API 返回的实际数据：
```json
{"date": "2026-06-14", "pageviews": 94, "clicks": 110}  // ← 这是最后一天，实际是6月15日数据
```

DB 查询确认 6 月 15 日北京时间有 204 次页面访问、151 次下载，API 也正确统计了这些数据——**只是日期标签错了**。

### 修复

趋势循环中的日期标签改用北京时间：

```python
# 改前
today = _beijing_today_start()
day_start = today - timedelta(days=i)
date_label = day_start.strftime("%Y-%m-%d")  # UTC 日期，错！

# 改后
today = _beijing_now().replace(hour=0, minute=0, second=0, microsecond=0)
day_start_bj = today - timedelta(days=i)  # 北京时间 00:00
day_start_utc = day_start_bj - timedelta(hours=8)  # DB 查询用 UTC
day_end_utc = day_start_utc + timedelta(days=1)
date_label = day_start_bj.strftime("%Y-%m-%d")  # 北京时间标签，对！
```

### 影响范围

| 函数 | 影响 |
|------|------|
| `get_page_stats()` | 页面访问趋势、点击趋势日期标签 |
| `get_download_trends()` | 下载趋势日期标签 |
| `get_stats()` 中的 `daily_trend` | 事件趋势日期标签（使用 `func.date()` SQL 函数，同样 UTC） |

---

## 5. 涉及改动

| Bug | 文件 | 改动 |
|-----|------|------|
| #1 版本去重 | `src/services/telemetry.py` | 版本洞察/OS洞察/版本×OS 改为先取每客户端最新版本再聚合 |
| #2 日期标签 | `src/services/analytics.py` | `get_page_stats()` + `get_download_trends()` 日期标签改用北京时间 |
| #2 日期标签 | `src/services/telemetry.py` | `get_stats()` 的 `daily_trend` 日期标签改用北京时间 |

总代码量约 50 行。

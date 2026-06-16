# Spec: UV 独立访客追踪 + PV/UV 趋势

- **日期**：2026-06-16
- **状态**：方案设计，待 Review
- **目标**：补齐 UV 统计能力，为接入广告联盟做准备；Server 运营 Tab 增加 PV/UV 趋势

---

## 1. 背景

### 1.1 为什么需要 UV

广告联盟的最低门槛是月 UV：

| 联盟 | 最低月 UV | 当前 |
|------|----------|------|
| Google AdSense | 无硬性门槛（内容审核） | ✅ 可申请 |
| 百度联盟 | 5,000 UV/月 | ❌ 无 UV 数据 |
| 腾讯优量汇 | 10,000 UV/月 | ❌ 同上 |

当前有 PV（page_events 的 pageview 计数），但没有 UV（去重访客数）。PV 重复计数同一用户多次访问，UV 按访客去重。广告联盟考核的是 UV，不是 PV。

### 1.2 当前 PV 数据（30 天）

| 页面 | PV | 说明 |
|------|-----|------|
| /guide | 757 | 指南页 |
| / | 628 | 首页 |
| /download | 309 | 下载页 |
| **合计** | **1,694** | |

按 PV/UV 比率 3:1 估算，月 UV 约 **560**。距百度联盟 5,000 还有 9 倍差距——但数据需要有，才能追踪增长。

---

## 2. 方案设计

### 2.1 UV 定义

**日 UV**：一天内访问网站的独立访客数。同一访客多次访问只计 1 次。

**访客标识**：`visitor_id = SHA256(IP + User-Agent)[:16]`。基于 IP+UA 哈希，不可逆，隐私友好。同一设备、同一网络环境的多次访问产生相同的 visitor_id。

> 局限性：同一家庭/公司 NAT 下的多台设备可能共享一个 IP，会被计为同一个 UV。但对于开发者工具类网站（用户多为个人开发者），这个误差在可接受范围内。

### 2.2 数据来源

已有 `page_events` 表，每行包含 `ip_hash`（SHA256[:64]）和 `user_agent`。不需要新建表。

**新增字段**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `visitor_id` | VARCHAR(16) | `SHA256(ip_hash + user_agent)[:16]`，跨页面去重标识 |

> `ip_hash` 是 IP 的 SHA256[:64]，再加 user_agent 哈希生成 visitor_id。双重不可逆——即使有人拿到 visitor_id，也无法还原 IP。

**历史数据回填**：上线时对已有 page_events 计算 `visitor_id = SHA256(ip_hash || user_agent)[:16]` 并回填。如果 `ip_hash` 或 `user_agent` 为空，用空字符串参与计算。

### 2.3 实时写入

portal.js 的 sendBeacon 埋点已上报 `page`、`event_type`。服务端 `analytics.py` 的 `record_page_event()` 在写入 `page_events` 时同步计算 `visitor_id`：

```python
raw = f"{ip_hash}{user_agent}"
visitor_id = hashlib.sha256(raw.encode()).hexdigest()[:16]
```

### 2.4 Admin 展示：Server 运营 Tab 新增 PV/UV 趋势

#### 卡片行增加 2 张卡片

现有 Server 运营卡片行（5 张）→ 改为 7 张（或替换 2 张低价值卡片）：

| 卡片 | 说明 | 数据来源 |
|------|------|---------|
| **月 UV** | 30 天去重访客数 | `COUNT(DISTINCT visitor_id)` 30 天 |
| **今日 UV** | 今日去重访客数 | 同上，今日 |
| **今日 PV** | 今日页面访问量（已有） | `COUNT(*)` 今日，已有 |
| **PV/UV 比** | 今日 PV / 今日 UV | 计算得出，衡量用户粘性 |
| 总下载量 | 已有，不变 |
| 今日下载 | 已有，不变 |
| COS 命中率 | 已有，不变 |

> 可在现有 5 卡基础上扩展，或将 COS 命中率替换为月 UV。

#### PV/UV 趋势图（新增）

在下载趋势折线图下方，新增一张折线图：

```
┌─ PV/UV 趋势 (30天) ──────────────────────────────┐
│  [折线图]                                          │
│  ── PV（页面访问量）                               │
│  ── UV（独立访客）                                 │
│                                                   │
│  双 Y 轴或同轴，直观展示 PV/UV 比值变化             │
└──────────────────────────────────────────────────┘
```

**数据接口**：扩展现有 `GET /api/v1/admin/analytics/page-stats` 的 `daily_trend`，每个日期增加 `uv` 字段：

```json
{
  "date": "2026-06-16",
  "pageviews": 158,
  "clicks": 152,
  "uv": 89
}
```

#### 各页面 UV 分布（可选）

在页面访问柱状图旁增加一行 UV 数据，或在同一个图表里切换 PV/UV：

| 页面 | PV | UV |
|------|-----|-----|
| /guide | 757 | ~250 |
| / | 628 | ~210 |
| /download | 309 | ~100 |

## 3. 涉及改动

| 文件 | 改动 | 说明 |
|------|------|------|
| `src/models/page_event.py` | +`visitor_id` 字段 | VARCHAR(16)，计算列 |
| `src/services/analytics.py` | `record_page_event()` 计算 visitor_id | +2 行 |
| `src/services/analytics.py` | `get_page_stats()` daily_trend +uv | +5 行 |
| `src/services/analytics.py` | 新增 `get_uv_stats()` 方法 | +15 行（月UV/今日UV/PVUV比） |
| `src/admin/templates/dashboard.html` | Server Tab 新增 PV/UV 卡片 + 趋势图 | +40 行 |
| `src/admin/router.py` | 传递 uv_stats 给模板 | +3 行 |
| DB migration | +visitor_id 列 + 历史回填 | |

代码量约 70 行。

---

## 4. 不做的

| 事项 | 原因 |
|------|------|
| Cookie-based visitor_id | 需要 cookie consent banner，增加复杂度 |
| IP 地理位置解析 | GeoLite2 免费，但隐私合规成本高，先不做 |
| 实时 UV 统计 | 只需日级别聚合，无需实时 |
| 独立 UV 表 | `page_events` 已有数据，增加字段即可，不新建表 |

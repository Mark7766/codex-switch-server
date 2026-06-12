# Spec: 遥测上报压力优化方案

- **日期**：2026-06-12
- **状态**：方案设计，待 Review
- **基于**：生产环境实测数据（2026-06-12）

---

## 1. 现状分析

### 1.1 生产数据（2026-06-12 06:53 ~ 08:10，约 77 分钟）

| 指标 | 值 |
|------|---|
| 总事件数 | 45 |
| 唯一客户端 | 1 |
| 数据库大小 | 0.7 MB |

### 1.2 事件分布

| 事件类型 | 数量 | 占比 | 频率（per user） |
|---------|------|------|---------------------|
| `model_call` | 34 | 75% | **~1 次/2 分钟** |
| `app_start` | 3 | 7% | 1-2 次/会话 |
| `proxy_start` | 3 | 7% | 1-2 次/会话 |
| `app_close` | 2 | 4% | 1 次/会话 |
| `proxy_stop` | 2 | 4% | 1 次/会话 |
| `update_check` | 1 | 2% | 1 次/会话 |

### 1.3 当前状态：无压力

当前 1 个用户，45 事件/77 分钟，SQLite 写入 < 1ms，DB 0.7MB。以下分析基于规模增长后的推断。

---

## 2. 压力推演

### 2.1 model_call 是唯一的高频来源

```
活跃用户行为：
  每小时约 20-30 次 AI 调用
  按 4 小时活跃/天 → 80-120 次 model_call/用户/天

100 用户规模：
  10,000 model_call/天 → 7/分钟

1000 用户规模：
  100,000 model_call/天 → 70/分钟 → 1.1/秒
```

### 2.2 三个维度的影响

| 维度 | 1000 用户/天 | 问题 |
|------|------------|------|
| **存储** | model_call 100K/天 × 200B = 20MB/天，**7.3GB/年** | SQLite 单文件膨胀 |
| **DB 写入** | 1.1 个 INSERT/秒 | SQLite 扛得住，但浪费在无价值数据上 |
| **去重查询** | 每个事件 SELECT 一次 | 83% 是为了 model_call——它本身不需要去重 |

### 2.3 model_call 的价值分析

```
问：model_call 事件告诉我们什么？
答：某用户在某秒调用了模型——除此之外没有其他信息（不含模型名、prompt 长度、响应时长）

问：这个信息对运营有什么用？
答：几乎没用。admin 面板不需要统计 model_call 总数，真正有用的是 DAU（app_start 去重）

问：那 model_call 完全没有价值吗？
答：有，但只需要"过去 N 分钟内调用了多少次"这个聚合信息就够了
```

---

## 3. 优化方案

**核心原则**：聚合责任在客户端，服务端保持无状态。

### 措施 ①：model_call 客户端定时批量上报（⭐ 核心方案）

**客户端改动**：

```
当前：
  每次 AI 调用 → 立即 POST /api/v1/telemetry/events {event_type: "model_call"}

改后：
  每次 AI 调用 → 内存计数器 model_call_count += 1
  每 5 分钟（或累积到 50 次）→ POST 一次汇总：
    {
      "events": [{
        "event_type": "model_call",
        "count": 47,                           // ← 新增字段
        "period_start": 1718163000,            // ← 本周期起始时间戳
        "period_end": 1718163300               // ← 本周期结束时间戳
      }]
    }
  然后重置计数器，开始下一轮
```

**服务端改动**：

```
当前：
  收到 model_call → validate → dedup query → INSERT 1 条

改后：
  收到 model_call（带 count） → validate → INSERT 1 条：
    event_type = "model_call"
    properties = {count: 47, period_start: ..., period_end: ...}
  去重：model_call 不在去重白名单中，跳过 dedup query
```

**新增字段**（向后兼容）：

| 字段 | 类型 | 说明 |
|------|------|------|
| `count` | int，可选，默认 1 | 本批次聚合的调用次数 |
| `period_start` | int，可选 | 聚合窗口起始 unix 时间戳 |
| `period_end` | int，可选 | 聚合窗口结束 unix 时间戳 |

老客户端不传这些字段 → `count` 默认 1 → 行为与现在完全一致。

**效果**：

| 指标 | 当前 | 改后 |
|------|------|------|
| model_call HTTP 请求 | 1 次/调用 | 1 次/5 分钟（减少 **99%+**） |
| model_call DB 写入 | 100K/天 | 288/天（减少 **99.7%**） |
| 存储增长 | 20MB/天 | 57KB/天 |
| 服务端内存 | 0 | 0（无状态） |
| 服务端重启安全性 | N/A | 数据在客户端，不丢 |

**客户端伪代码**：

```javascript
let modelCallCount = 0;
let periodStart = Date.now();
const FLUSH_INTERVAL = 5 * 60 * 1000;  // 5 分钟
const FLUSH_THRESHOLD = 50;            // 或累积 50 次

function onModelCall() {
  modelCallCount++;
  const elapsed = Date.now() - periodStart;
  if (elapsed >= FLUSH_INTERVAL || modelCallCount >= FLUSH_THRESHOLD) {
    sendTelemetry({
      event_type: "model_call",
      count: modelCallCount,
      period_start: Math.floor(periodStart / 1000),
      period_end: Math.floor(Date.now() / 1000),
    });
    modelCallCount = 0;
    periodStart = Date.now();
  }
}

// 进程退出前也 flush 一次
process.on('before-quit', () => {
  if (modelCallCount > 0) {
    sendTelemetry({ event_type: "model_call", count: modelCallCount, ... });
  }
});
```

**边界情况处理**：

| 场景 | 处理 |
|------|------|
| 客户端崩溃 | 本周期未上报的计数丢失（可接受，model_call 本身不是关键数据） |
| 客户端退出 | `before-quit` 钩子最后 flush 一次 |
| 客户端断网 | 同上，丢掉（不重试，避免堆积） |
| 服务端收到 count=0 | 忽略不写入 |

---

### 措施 ②：按事件类型拆分去重策略

**当前问题**：所有事件类型统一做去重（查询最近 1 分钟相同 client_id+event_type）。去重白名单：

| 事件类型 | 需要去重？ | 理由 |
|---------|----------|------|
| `app_start` | ✅ 是 | 短时间重复启动可能是 bug |
| `proxy_start` | ✅ 是 | 同上 |
| `update_check` | ✅ 是 | 短时间重复检查无意义 |
| `model_call` | ❌ 不需要 | 高频事件，聚合后已自带去重 |
| `app_close` | ❌ 不需要 | 正常退出 |
| `proxy_stop` | ❌ 不需要 | 正常退出 |

**服务端改动**：`telemetry.py` 的去重逻辑加一个 `DEDUP_TYPES` 集合，不在集合里的事件类型直接跳过去重查询。约 5 行代码。

---

### 措施 ③：DB 数据自动清理

```
telemetry_events:  保留 30 天 → 每小时清理一次过期数据
download_records:  保留 90 天
page_events:       保留 30 天
```

**实现**：lifespan background task，每小时 `DELETE WHERE created_at < datetime('now', '-30 days')`。约 15 行代码。

---

## 4. 方案总结

| # | 措施 | 改哪边 | 代码量 | 效果 |
|---|------|--------|--------|------|
| ① | model_call 客户端定时聚合上报 | 客户端 + 服务端 | 客户端~30行 + 服务端~15行 | **99%+ 减少请求和写入** |
| ② | 去重白名单 | 服务端 | ~5 行 | 消除 model_call 无效去重查询 |
| ③ | DB 自动清理 | 服务端 | ~15 行 | DB 不再无限增长 |

**三个措施独立实施，互不阻塞**：
- ② + ③ 可以立刻做（纯服务端，不需要客户端配合）
- ① 需要客户端配合，但向后兼容（老客户端不传 count 就走现有逻辑）

---

## 5. 不做的事项

| 事项 | 原因 |
|------|------|
| 服务端内存计数器 | 服务重启丢数据，客户端数量多时占内存 |
| 换 PostgreSQL/Redis | 违反轻量级约束 |
| 消息队列异步写入 | 增加依赖复杂度 |
| model_call 完全移除 | 聚合后数据仍有价值（活跃度趋势） |

---

## 6. 新增 API Schema（向后兼容）

```python
# schemas/telemetry.py — TelemetryEventIn 新增字段
class TelemetryEventIn(BaseModel):
    client_id: str
    event_type: str
    timestamp: int
    # ... 现有字段不变 ...
    
    # 新增（可选，向后兼容）
    count: int = 1              # model_call 聚合计数，默认 1
    period_start: int | None = None   # 聚合窗口起始 unix timestamp
    period_end: int | None = None     # 聚合窗口结束 unix timestamp
```

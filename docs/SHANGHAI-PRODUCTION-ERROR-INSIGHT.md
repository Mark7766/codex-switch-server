# 广州新生产环境 — 遥测错误洞察报告

> **数据来源**：广州生产服务器 `telemetry_events` 表（全量数据，截至 2026-07-01）
> **分析范围**：`error` / `tool_install_fail` / `proxy_error` 三类错误事件
> **分析日期**：2026-07-02

---

## 1. 总体概览

| 事件类型 | 全量总数 | 近 30 天占比 | 受影响用户数 | 严重程度 |
|----------|---------|-------------|-------------|---------|
| `error` | 133 | 1.22%（133/10,886） | 21 | ⚠️ 中等 |
| `tool_install_fail` | 49 | 0.45%（49/10,886） | 4 | 🔴 高 |
| `proxy_error` | 36 | 0.33%（36/10,886） | 6 | 🟡 低 |

> 近 30 天总事件量 10,886。三类错误合计占比约 2%，整体健康，但每个类型都有值得关注的结构性问题。

---

## 2. `error` — 通用错误（133 条）

### 2.1 核心发现：properties.message 100% 为空

**这是三类错误中最严重的数据质量问题。** 全部 133 条 `error` 事件的 `properties` 中 `message` 字段为空字符串，导致服务端完全无法判断错误根因。

```
error 事件典型记录：
  [2026-07-01 08:23:21] ver=1.16.0 plat=darwin arch=arm64 msg=""
  [2026-07-01 08:23:21] ver=1.16.0 plat=darwin arch=arm64 msg=""
  [2026-07-01 08:23:21] ver=1.16.0 plat=darwin arch=arm64 msg=""
  ... (12 条同一秒内)
```

**根因推断**：客户端 `error` 事件上报逻辑未将 Error 对象的 `message`/`stack` 写入 `properties`，导致服务端收到空壳事件。服务端能做的：验证 `event_type` 是否在白名单、去重检查 —— 当前都已做（`error` 不在去重白名单中，不会被丢弃），但入到 DB 的只有时间戳/平台/版本，没有诊断价值。

### 2.2 版本分布（近 30 天）

| 版本 | 次数 | 占比 |
|------|------|------|
| v1.14.1 | 41 | 30.8% |
| v1.13.0 | 30 | 22.6% |
| v1.16.0 | 27 | 20.3% |
| v1.9.1 | 13 | 9.8% |
| v1.10.0 | 10 | 7.5% |
| v1.14.0 | 6 | 4.5% |
| v1.12.1 | 4 | 3.0% |
| 其他 | 2 | 1.5% |

### 2.3 平台分布

| 平台 | 次数 |
|------|------|
| Windows (win32) | 72 |
| macOS (darwin) | 61 |

分布大致均衡，无平台倾向性。

### 2.4 时间趋势

- **6月20-22日**：峰值期，每天 22-25 条（v1.13.0/v1.14.1 集中上报）
- **6月23-30日**：静默期，几乎消失
- **7月1日**：突然回升至 27 条，其中 25 条来自**同一个用户**（v1.16.0, darwin arm64），该用户在 08:23:21 秒内连续上报 12 条 `error` 事件

### 2.5 影响评估

- 21 个用户受影响，但实际影响面可能更大（error 事件的 `message` 为空，没有人知道这些是什么错误）
- 这是 **客户端 bug**：上报 `error` 事件时未携带 `message`/`stack`
- **建议优先级**：先在客户端修复 error 事件的 properties 上报（写入 message + stack），等下一版有了有效数据后再回头分析根因

---

## 3. `tool_install_fail` — 工具安装失败（49 条）

### 3.1 核心发现：100% 是 claude-cli + Windows + setx 命令失败

这是三类错误中**最集中、最可定位**的问题。全部 49 条失败都是：

- **工具**：`claude-cli`（100%）
- **平台**：Windows / win32 / x64（100%）
- **根因**：`setx` 命令失败（100%）

### 3.2 两种失败模式

#### 模式 A：`spawn setx ENOENT`（44 条 / 89.8%）

```
props: {
  "tool": "claude-cli",
  "error_code": "spawn setx ENOENT",
  "platform": "win32",
  "app_version": "1.16.0"
}
```

- **含义**：Node.js `child_process.spawn('setx', ...)` 找不到 `setx.exe` 可执行文件
- **根因**：`setx.exe` 位于 `C:\Windows\System32\setx.exe`，在以下情况可能不在 PATH 中：
  - 从 32 位进程调用（会被 WOW64 重定向到 `SysWOW64`，其中没有 `setx.exe`）
  - 用户 PATH 环境变量被修改/损坏
  - 某些精简版 Windows 缺少该工具
- **影响版本**：v1.15.0 → v1.16.0（集中在最近两周）
- **受影响用户数**：约 2-3 个用户反复重试

#### 模式 B：`Command failed: setx ANTHROPIC_AUTH_TOKEN sk-***`（5 条 / 10.2%）

```
props: {
  "tool": "claude-cli",
  "error_code": "Command failed: setx ANTHROPIC_AUTH_TOKEN sk-***",
  "platform": "win32",
  "app_version": "1.16.0"
}
```

- **含义**：`setx` 命令找到了但执行失败
- **根因**：可能是权限不足（需要管理员权限写系统环境变量）、或 token 值中含特殊字符未正确转义
- **注意**：`sk-***` 说明客户端已在脱敏，但 error_code 仍泄露了 env var 名

### 3.3 时间趋势

- 近期持续发生（6月23日 → 6月29日 不断有上报）
- 每天 3-14 条，无消退迹象
- **仅 4 个用户**，高度集中——这些用户反复重试仍失败，说明客户端安装引导在 setx 失败后没有给用户替代方案

### 3.4 影响评估

- 4 个用户，但每个受影响的用户都无法完成 claude-cli 安装，**转化损失 100%**
- `setx` 用于设置 `ANTHROPIC_AUTH_TOKEN` 环境变量，这是 Claude CLI 的必需品——设置失败等于 claude-cli 不可用
- **建议**：
  1. **短期**：客户端兜底方案 —— `setx` 不可用时改用 `set` 命令（当前会话有效）或引导用户手动设置环境变量
  2. **中期**：客户端检查 `setx` 可用性，不可用时改用注册表写入（`reg add`）或 PowerShell `[Environment]::SetEnvironmentVariable()`
  3. **服务端可做**：在 guide 页面 FAQ 增加"claude-cli 安装后报 setx ENOENT 怎么办"条目

---

## 4. `proxy_error` — 代理错误（36 条）

### 4.1 核心发现：全部是端口冲突或运行时错误，集中在旧版本

### 4.2 两种错误类型

#### `runtime` 错误（23 条 / 63.9%）

```
props: {"error_kind": "runtime", "port": 11435}
```

- **含义**：代理进程在运行期间崩溃/异常退出
- **时间**：几乎全部在 2026-06-23 同一天（23 条），来自 2 个用户
- **版本**：v1.10.0、v1.15.0
- **判断**：可能是老版本的代理稳定性 bug，v1.15.0 之后已修复（v1.16.0 零报告）

#### `port-conflict` 错误（13 条 / 36.1%）

```
props: {"error_kind": "port-conflict", "port": 11435}    // 12 条
props: {"error_kind": "port-conflict", "port": 7890}     // 1 条
```

- **含义**：启动代理时端口已被占用
- **端口 11435**：codex-switch 代理的默认端口
- **端口 7890**：可能是用户自定义端口（1 例）
- **根因**：
  - 上一次代理进程未正常退出（crash 后端口没释放）
  - 用户手动启动了另一个 codex-switch 实例
  - TIME_WAIT 状态下的端口残留
- **版本**：v1.10.0 为主（66%），v1.13.0 次之

### 4.3 影响评估

- 6 个用户，其中 2 个用户贡献了 85% 的事件
- 新版（v1.16.0）**零 `proxy_error`** —— 说明代理稳定性在新版已改善
- **建议**：
  1. 确认 v1.16.0 的代理相关修复是否包含端口冲突检测 + 自动重试
  2. 如有 kill 旧进程 + 端口等待逻辑，说明修复生效，不需要额外动作
  3. `error_kind` 可以更细化（如 `port-conflict` → `port-conflict:previous-instance` / `port-conflict:other-process`），但优先级低

---

## 5. 跨类型洞察

### 5.1 `error` 事件质量 → 客户端修复优先级最高

`error` 是最通用的错误事件类型，理论上应覆盖所有未被其他特定类型捕获的错误。但 133 条全部空 message，**等于这 133 条数据完全浪费**。修复客户端上报逻辑后，error 事件的数据质量将指数级提升，可能揭示目前完全未知的 bug 类别。

### 5.2 `tool_install_fail` → 影响用户少但伤害大

4 个用户看起来不多，但这 4 个人反复重试安装 claude-cli 却一直失败。他们没有回退到手动方案，只能不断重试。**每个这样的用户都是流失风险。**

### 5.3 `proxy_error` → 旧版本问题，自愈趋势

新版本（v1.16.0）零 `proxy_error`，旧版本问题通过自然升级会消退。不需要紧急干预。

### 5.4 版本健康度一览

| 版本 | error | tool_install_fail | proxy_error | 总评 |
|------|-------|------------------|-------------|------|
| v1.16.0 | 27（burst） | 24（setx） | 0 | ⚠️ error burst 需关注 |
| v1.15.0 | 0 | 8 | 14 | 升级即可 |
| v1.14.1 | 41 | 1 | 0 | 升级即可 |
| v1.13.0 | 30 | 11 | 2 | 升级即可 |
| v1.10.0 | 10 | 3 | 20 | 🔴 建议强制升级 |

---

## 6. 行动建议（优先级排序）

### 🔴 P0 — 客户端：error 事件上报修复

- **问题**：`properties.message` 和 `properties.stack` 均为空
- **修复**：在客户端 `sendErrorEvent()` 中将 Error 对象的 `message` 和 `stack` 写入 properties
- **预期**：下一版 error 事件将变得可诊断，可能发现新的 bug 类别

### 🔴 P0 — 客户端：claude-cli setx 失败兜底

- **问题**：`spawn setx ENOENT` 占 tool_install_fail 的 90%
- **修复**：
  1. 检测 `setx` 是否存在（`where setx` / `which setx`）
  2. 不存在时 → 改用 PowerShell `[Environment]::SetEnvironmentVariable()`，或引导用户手动设置
  3. 执行失败时 → 给出明确的用户操作指南（而不是静默重试）

### 🟡 P1 — 服务端：admin 面板暴露 error/tool_install_fail/proxy_error 详情

- **当前**：admin App Tab 功能使用分布图表显示事件类型计数，但不区分成功/失败，也不展示 error 的 properties
- **建议**：新增"安装失败详情"区块，展示 tool_install_fail 的 tool/error_code 分布
- **数据源**：`json_extract(properties, '$.tool')`、`json_extract(properties, '$.error_code')`

### 🟢 P2 — 服务端：guide FAQ 新增 setx 问题条目

- 在 `/guide` 页面 FAQ 添加"安装 claude-cli 后提示 setx ENOENT 怎么办"
- 引导用户手动设置环境变量或使用 PowerShell 替代方案

### 🟢 P2 — 监控：设置 error 事件 message 为空的告警规则

- 如 `error` 事件 `properties.message` 持续为空，说明大量客户端仍在上报无效数据

---

## 7. 备注

- 数据来自广州生产 SQLite（134.175.67.120），与新加坡导入的历史数据合并后约 1 个月窗口
- `error` 事件去重：不在 `_DEDUP_TYPES` 白名单中，每个 `error` 事件都会被记录（不会因为相同 client_id+event_type+timestamp 被丢弃）
- `proxy_error` 在去重白名单中，同一秒内相同 client 的重复上报会被丢弃，所以实际代理错误频率可能略高于 DB 记录

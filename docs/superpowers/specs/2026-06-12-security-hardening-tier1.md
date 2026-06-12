# Spec: 服务端安全加固 Tier 1 — 零成本轻量防护

- **日期**：2026-06-12
- **状态**：方案设计，待 Review
- **前置**：electron-updater 支持已实现（TASK-050）
- **约束**：不引入任何新依赖（Redis/Celery/数据库新表），纯内存方案，代码量 < 100 行

---

## 1. 背景

codex-switch-server 目前对外暴露的下载端点全部无需认证：

```
GET /api/v1/update/download/{version}/{platform}-{arch}   # Codex Switch 下载
GET /api/v1/updates/{filename}                             # electron-updater 下载
GET /api/v1/packages/{name}/{version}/{platform}-{arch}    # 桌面应用安装包下载
GET /api/v1/files/{filename}                               # 静态文件下载
```

当前面临的 4 个风险：

1. **流量滥用**：任何人可无限次请求大文件（92MB+），消耗服务器带宽和 COS 出口流量
2. **磁盘耗尽**：触发 GitHub 兜底下载 → 每个新版本+平台+架构组合写入磁盘缓存，恶意请求可刷爆磁盘
3. **统计污染**：`record_download()` 无任何校验，admin 面板数据可被伪造请求污染
4. **完整性缺失**：客户端下载文件后无校验手段，完全信任传输链路

Tier 1 目标：**零成本、零新依赖、<100 行代码**，覆盖上述 4 个风险面。

---

## 2. 四项措施

### 措施 ①：下载端点 IP 速率限制

**目标**：防止单个 IP 刷流量和污染下载统计

**方案**：纯内存滑动窗口计数器

```
数据结构：
  {ip: [timestamp1, timestamp2, ...]}  ← 每个 IP 一个时间戳列表
  {global: [timestamp, ...]}            ← 全局计数器

清理策略：
  每次访问时自动清理过期记录（> 窗口时间的记录丢弃）

配置：
  PER_IP_LIMIT = 10       # 每个 IP 每分钟最多 N 次下载请求
  IP_WINDOW_SECONDS = 60  # 时间窗口
  GLOBAL_LIMIT = 200      # 全局每分钟最多 M 次（防止分布式 IP 攻击）
```

**实现要点**：

- 新建 `src/utils/rate_limiter.py`，约 40 行
- `RateLimiter` 类：`is_allowed(key: str) -> bool`，滑动窗口 + 自动清理
- 在下载端点中调用：提取 `request.client.host` → `rate_limiter.is_allowed(ip)` → 429 Too Many Requests
- 全局限制可选：防止攻击者切换 IP 绕过 per-IP 限制
- **不限制 yml 文件请求**（轻量文本，每次几 KB，客户端会频繁检查更新）
- **不限制门户页面访问**（HTML 渲染，本质是正常浏览）

**影响评估**：

| 项目 | 正常用户感知 | 攻击者感知 |
|------|------------|-----------|
| 每 IP 每分钟 10 次下载 | 无影响（普通用户不会连续下载 10 次） | 429 拒绝 |
| 全局每分钟 200 次 | 无影响（瞬时并发不足以达到） | 429 拒绝 |

**端点的特殊处理**：

| 端点 | 限制策略 |
|------|---------|
| `GET /api/v1/update/latest` | 不限（纯 JSON，无文件传输，正常门户频繁调用） |
| `GET /api/v1/update/check` (POST) | 不限（纯 JSON，客户端启动时检查更新） |
| `GET /api/v1/update/download/*` | 限速（大型二进制文件传输） |
| `GET /api/v1/updates/latest-mac.yml` | 不限（KB 级文本，electron-updater 频繁检查） |
| `GET /api/v1/updates/latest.yml` | 不限（同上） |
| `GET /api/v1/updates/{filename}` | 限速（electron-updater 二进制下载） |
| `GET /api/v1/packages/{name}/*/download` | 限速（桌面应用安装包，200MB+） |
| `GET /api/v1/files/{filename}` | 限速（静态文件 COS 302） |

**配置位置**：`.env` 中新增（非必需，默认值可工作）

```
RATE_LIMIT_PER_IP=10
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_GLOBAL=200
```

---

### 措施 ②：SHA256 校验和透传

**目标**：客户端下载文件后能校验完整性

**当前状态**：

`UpdateCheckResponse` schema 已有 `sha256` 字段：

```python
class UpdateCheckResponse(BaseModel):
    sha256: str = ""   # ← 已有字段，但始终为空字符串
```

GitHub Release API 不直接提供 SHA256（只提供 node_id 等），但有 `asset.url` 可获取更多信息。实际可行的方案：

**方案 A（推荐）**：服务端计算并缓存

```
首次下载/缓存文件时 → 计算 SHA256 → 存入内存缓存 + 数据库字段
后续请求 → 直接从缓存/DB 返回
```

**实现要点**：

- `download_and_cache()` / `download_asset_to_cache()` 下载完成后计算 SHA256
- 存储到 `DownloadRecord` 新字段 `file_sha256: str = ""`
- 在 `UpdateCheckResponse` 和 `/api/v1/update/latest` 中返回
- SHA256 计算用 Python 内置 `hashlib`，无新依赖
- 对已缓存的文件，初次部署后第一批下载会计算并持久化

**方案 B**：从 GitHub Release body 解析

有些项目在 release body 中写 SHA256。但格式不标准，不推荐作为唯一方案。

**影响评估**：

| 项目 | 变化 |
|------|------|
| 首次下载延迟 | +0.1-0.5s（92MB 文件 SHA256 计算） |
| 后续下载 | 无影响（缓存命中后 SHA256 已存储） |
| 用户体验 | 客户端可显式校验，安装失败时能区分"下载损坏"vs"安装问题" |

**涉及变更文件**：

- `src/services/release_sync.py` — `download_and_cache()` 加 SHA256 计算
- `src/services/update_feed.py` — `download_asset_to_cache()` 加 SHA256 计算
- `src/schemas/release.py` — `UpdateCheckResponse.sha256` 填充真实值
- `src/models/download.py` — `DownloadRecord` 加 `file_sha256` 字段
- `src/api/v1/update.py` — `check_for_updates()` 返回 sha256

---

### 措施 ③：GitHub 兜底下载文件大小限制

**目标**：防止恶意请求触发超大文件下载撑爆磁盘

**当前问题**：

```python
# release_sync.py / update_feed.py
await self._http.download(download_url, tmp_dest)  # ← 无大小限制
# 攻击者可以构造任意大小的文件下载请求
```

**方案**：在 `HttpClient.download()` 中加最大文件大小检查

```python
MAX_DOWNLOAD_SIZE = 200 * 1024 * 1024  # 200MB

# 在 stream 下载过程中累加已下载字节数
# 超过 MAX_DOWNLOAD_SIZE → 停止下载 → 删除临时文件 → 抛出异常
```

**配置**：`.env` 中可配置

```
MAX_DOWNLOAD_SIZE_MB=200
```

**影响**：

| 场景 | 行为 |
|------|------|
| 正常 Codex Switch 下载（<150MB） | 无影响 |
| 正常桌面应用下载（<300MB） | 需适当调高上限或按端点区分 |
| 恶意请求触发 GitHub 兜底 | 下载到 200MB 时中断，清理临时文件 |

**按端点区分上限**：

| 端点/场景 | 上限 | 理由 |
|----------|------|------|
| Codex Switch 下载 | 200MB | AppImage + 各平台文件 < 150MB |
| 桌面应用安装包 | 500MB | DMG/EXE 可能较大 |
| electron-updater 下载 | 200MB | 同 Codex Switch |

**实现位置**：`src/utils/http.py` 的 `HttpClient.download()` 方法

---

### 措施 ④：User-Agent 校验与标记

**目标**：区分真实客户端 vs 脚本/爬虫，但不拒绝服务

**策略**：**不拒绝、只标记**。可疑 UA 正常响应，但在日志和 DB 中标记，方便事后分析。

**规则**：

| UA 类型 | 判定 | source 字段 | 日志级别 |
|---------|------|------------|---------|
| 包含 `Electron/` | 真实 codex-switch 客户端 | 保持原值 | DEBUG |
| 包含 `python-requests` 或 `curl` | 脚本/工具 | 加 `-suspicious` 后缀 | WARNING |
| 其他/空 | 未知 | 加 `-unknown` 后缀 | INFO |

**实现要点**：

- 在 `record_download()` 中接收 `user_agent` 参数（已有），按规则判定
- 不阻塞请求，只标记
- 日志记录可疑来源，方便后续封禁

**涉及变更**：

- `src/services/release_sync.py` — `record_download()` 增加 UA 分类逻辑
- 各下载端点 — `record_download()` 调用时传入 UA（部分端点可能已传，需检查）

---

## 3. 实施计划

### 新增文件

| 文件 | 内容 | 行数（估） |
|------|------|----------|
| `src/utils/rate_limiter.py` | `RateLimiter` 类，滑动窗口 + 自动清理 | ~40 |

### 修改文件

| 文件 | 改动内容 | 行数（估） |
|------|---------|----------|
| `src/utils/http.py` | `download()` 加最大文件大小限制 | +8 |
| `src/services/release_sync.py` | `download_and_cache()` 加 SHA256 计算；`record_download()` 加 UA 分类 | +15 |
| `src/services/update_feed.py` | `download_asset_to_cache()` 加 SHA256 计算 | +8 |
| `src/schemas/release.py` | `UpdateCheckResponse` sha256 填充 | 0（已有字段） |
| `src/models/download.py` | `DownloadRecord` 加 `file_sha256` 字段 | +2 |
| `src/api/v1/update.py` | 下载端点加速率限制；check 端点返回 sha256 | +6 |
| `src/api/v1/updates.py` | 下载端点加速率限制 | +6 |
| `src/api/v1/packages.py` | 下载端点加速率限制 | +6 |
| `src/api/v1/files.py` | 下载端点加速率限制 | +4 |
| `src/config.py` | 新增 4 个配置项 | +4 |

### 配置新增（`.env`）

```
# 速率限制（可选，有默认值）
RATE_LIMIT_PER_IP=10
RATE_LIMIT_WINDOW_SECONDS=60
RATE_LIMIT_GLOBAL=200

# 下载文件大小上限（可选，有默认值）
MAX_DOWNLOAD_SIZE_MB=200
```

### 测试清单

| 层级 | 测试内容 |
|------|---------|
| 单元 | `RateLimiter.is_allowed()` 正常/超限/窗口滑动/自动清理 |
| 单元 | `HttpClient.download()` 文件大小超限中断 |
| 单元 | `record_download()` UA 分类逻辑 |
| 单元 | SHA256 计算正确性 |
| 集成 | 下载端点 429 限速返回 |
| 集成 | yml 端点不限速 |
| 集成 | 文件大小超限 413 返回 |
| 集成 | check 端点返回 sha256 |
| 集成 | UA 分类 source 字段正确标记 |

---

## 4. 不做的事项（明确排除）

| 事项 | 排除原因 |
|------|---------|
| Redis / 分布式限速 | 单服务器部署，内存限速足够 |
| 下载签名 URL | 需要 COS SDK 额外的预签名能力，留到 Tier 2 |
| 客户端密钥认证 | 需要客户端配合改动 + 密钥分发，留到 Tier 2 |
| 限速 IP 黑名单持久化 | 重启即释放，符合"轻量"原则 |
| 防 DDoS（全局限流 Nginx 层） | Nginx `limit_req_zone` 更合适，独立配置变更，不在此 spec 范围 |

---

## 5. 总体影响评估

| 维度 | 评估 |
|------|------|
| 代码量 | < 100 行增量（含注释） |
| 新依赖 | 0 |
| 性能影响 | 极低（内存字典查找 O(1)，SHA256 计算仅首次下载时触发） |
| 内存占用 | < 5MB（按 10000 个 IP × 10 条记录 × 8 字节时间戳） |
| 正常用户体验 | 无影响 |
| 防脚本/爬虫 | 单 IP 每分钟 10 次限制，需要 >200 个独立 IP 才能绕过全局限制 |
| 防统计污染 | UA 标记 + IP 限速，事后可清洗数据 |
| 防文件篡改 | SHA256 透传，客户端可校验（需客户端配合） |
| 防磁盘耗尽 | 文件大小限制，单次最大 200MB |

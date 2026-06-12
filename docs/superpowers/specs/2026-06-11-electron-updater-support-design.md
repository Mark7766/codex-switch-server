# Spec: codex-switch-server 适配 electron-updater generic provider

- **日期**：2026-06-11
- **状态**：设计完成，待用户 Review
- **关联文档**：`docs/SERVER-REQUIREMENTS-for-electron-updater.md`

---

## 1. 目标

让 codex-switch-server 提供与 electron-updater generic provider 兼容的更新检测和文件下载端点，使 codex-switch 客户端可通过服务器（而非直接 GitHub Releases）进行版本检查和增量更新。

## 2. 背景

codex-switch 客户端使用 `electron-updater` v6.8.3，provider 为 `generic`。当前客户端直接拉取 GitHub Releases 的 `latest-mac.yml` / `latest.yml`。接入 server 后，客户端将 feed URL 指向 server，server 提供与 GitHub Releases 相同格式的响应。

### 2.1 现有架构（相关部分）

```
src/api/v1/update.py          # 版本检查 + 下载（/api/v1/update/*）
src/api/v1/files.py           # 静态文件 COS 下载（/api/v1/files/{filename}）
src/services/release_sync.py  # GitHub Release 实时查询 + 缓存 + 下载
src/utils/cos_storage.py      # 腾讯云 COS SDK 封装
src/utils/storage.py          # 本地文件存储抽象
```

### 2.2 已知约束（来自 Review）

1. **文件名格式 mismatch**：本地缓存用 `{plat}-{arch}.{ext}`（如 `mac-arm64.dmg`），COS 和 GitHub 用原始 asset 名（如 `Codex-Switch-1.4.0-mac-arm64.dmg`）。electron-updater 请求原始 asset 名。
2. **扩展名缺失**：`get_download_path()` 只查 `dmg/exe/appimage`，不支持 `zip` 和 `blockmap`。
3. **过滤逻辑**：`_detect_platform()` 过滤了 `.blockmap` 和 `.yml`（这些恰是 electron-updater 必需的文件）。
4. **files 端点不可复用**：COS key 前缀不同（`files/` vs `codex-switch/{ver}/`）。
5. **ADR-013 引用不存在**：decisions-log.md 中无此 ADR。

## 3. 方案选择

**方案 A（选定）**：新建独立 `/api/v1/updates/` 路由组 + 独立 service

- 3 个端点：`latest-mac.yml`、`latest.yml`、`{filename}` 文件下载
- yml 从 GitHub Release 直接下载原文件并内存缓存（100% 准确）
- 文件下载：COS（原始 asset 名）→ 本地（解析映射）→ GitHub 兜底
- 与现有 `/api/v1/update/` 完全隔离，互不干扰

**方案 B（未选）**：扩展现有 `update.py`

- 改动文件少，但 URL 语义混乱，现有下载路径模式不兼容

## 4. 架构设计

### 4.1 数据流

```
客户端 (electron-updater)
    │
    │  GET /api/v1/updates/latest-mac.yml
    │ ──────────────────────────────────►
    │                                    │ ① 查内存缓存 (5min TTL)
    │                                    │ ② miss → GitHub API 下载最新 Release 的
    │                                    │    latest-mac.yml 资产原文
    │                                    │ ③ 缓存到内存 → 返回 text/yaml
    │  ←── yml 原文 (text/yaml; charset=utf-8)
    │
    │  解析 yml → version > current → 有新版本
    │
    │  GET /api/v1/updates/Codex-Switch-1.5.0-mac-arm64.zip
    │ ──────────────────────────────────►
    │                                    │ ① 从文件名提取 version
    │                                    │ ② COS: codex-switch/1.5.0/Codex-Switch-...zip
    │                                    │    ├─ 命中 → 302 广州 (2MB/s)
    │                                    │ ③ 本地: parse_filename() → 映射到
    │                                    │    data/codex-switch/1.5.0/mac-arm64.zip
    │                                    │    └─ 命中 → X-Accel-Redirect (sendfile)
    │  ←── 200 + Content-Disposition      │ ④ GitHub 兜底 → 缓存 → 返回
    │
    │  GET .../Codex-Switch-1.5.0-mac-arm64.zip.blockmap
    │ ──────────────────────────────────►  同上流程
    │  ←── 200 (支持 HTTP 206 Range)
```

### 4.2 模块设计

```
src/
├── api/v1/
│   ├── updates.py          ← 新增：3 个端点
│   └── router.py           ← 改：注册 updates_router
├── services/
│   ├── update_feed.py      ← 新增：yml 缓存 + 文件查找
│   └── release_sync.py     ← 改：扩展名列表加 zip/blockmap
└── models/
    └── download.py         ← 改：DownloadRecord 加 source 字段
```

### 4.3 端点详设

#### 4.3.1 `GET /api/v1/updates/latest-mac.yml`

- **响应**：`Content-Type: text/yaml; charset=utf-8`
- **逻辑**：
  1. 查内存缓存 `_mac_yml_cache`（TTL 5 分钟）
  2. 缓存 miss → 调 GitHub API 获取最新 Release，从 assets 列表找 `latest-mac.yml`
  3. 下载该 asset 的内容（纯文本 yml）
  4. 存入缓存，返回原文
- **错误处理**：GitHub API 不可用时，返回过期的缓存内容（如有）；无缓存则返回 502

#### 4.3.2 `GET /api/v1/updates/latest.yml`

- 同 4.3.1，但查找 `latest.yml` asset，使用独立的 `_win_yml_cache`

#### 4.3.3 `GET /api/v1/updates/{filename}`

- **路径参数**：`filename` — 原始 GitHub asset 名（如 `Codex-Switch-1.5.0-mac-arm64.zip`）
- **安全校验**：正则 `^[a-zA-Z0-9][a-zA-Z0-9._-]*$` + 拒绝 `..`
- **逻辑**（三级降级）：
  1. **从 filename 提取 version** → 正则 `Codex-Switch-(?:Setup-)?([0-9.]+)-` 
  2. **COS 检查**：`codex-switch/{version}/{filename}` → 命中则 302 广州
  3. **本地缓存**：`_parse_filename_to_cache_key(filename)` → 映射为 `{plat}-{arch}.{ext}` → 查 `data/codex-switch/{version}/` → 命中则 X-Accel-Redirect
  4. **GitHub 兜底**：调 `get_latest_from_github()` → 在 files 列表中按 `original_name` 匹配 → 下载并缓存
- **文件名解析函数** `_parse_filename_to_cache_key(filename) -> (version, platform, arch, file_type) | None`：
  ```
  Codex-Switch-1.5.0-mac-arm64.zip          → (1.5.0, macos, arm64, zip)
  Codex-Switch-1.5.0-mac-arm64.dmg          → (1.5.0, macos, arm64, dmg)
  Codex-Switch-1.5.0-mac-arm64.zip.blockmap → (1.5.0, macos, arm64, zip.blockmap)
  Codex-Switch-1.5.0-mac-x64.zip            → (1.5.0, macos, x64, zip)
  Codex-Switch-Setup-1.5.0-win-x64.exe      → (1.5.0, windows, x64, exe)
  Codex-Switch-Setup-1.5.0-win-arm64.exe    → (1.5.0, windows, arm64, exe)
  ```
- **记录下载**：`record_download(version, platform, arch, package_name="codex-switch", source="electron-updater")`

### 4.4 Service 设计

#### `UpdateFeedService` (`src/services/update_feed.py`)

```python
class UpdateFeedService:
    def __init__(self, http: HttpClient | None = None, storage: LocalStorage | None = None):
        ...
    
    async def get_latest_yml(self, platform: str) -> str | None:
        """获取 latest-mac.yml 或 latest.yml 原文，5 分钟内存缓存"""
        ...
    
    async def find_asset_by_filename(self, filename: str) -> dict | None:
        """在 GitHub 最新 Release 的 assets 中按 original_name 查找"""
        ...
    
    async def download_asset_to_cache(self, download_url: str, version: str, 
                                       filename: str) -> Path:
        """从 GitHub 下载文件并缓存到本地 data/codex-switch/{ver}/{filename}"""
        ...
```

### 4.5 现有代码修改

#### `release_sync.py` — `get_download_path()`

```python
# 改前：
for ext in ("dmg", "exe", "appimage"):
# 改后：
for ext in ("dmg", "exe", "appimage", "zip", "blockmap"):
```

或者更好的方式：接受 `original_name` 参数，直接按完整文件名查找。

#### `release_sync.py` — `download_and_cache()`

新增可选参数 `original_name: str | None = None`，当传入原始文件名时，使用原始文件名作为缓存 key（而非 `{plat}-{arch}.{ext}` 格式）。这样 electron-updater 下载的文件按原始文件名缓存，后续 COS 和本地查找都能精确匹配。

#### `models/download.py` — `DownloadRecord`

```python
source = Column(String(32), default="")  # '' = 门户下载, 'electron-updater' = 客户端自动更新
```

#### `api/router.py`

```python
from src.api.v1.updates import router as updates_router
v1_router.include_router(updates_router, prefix="/updates", tags=["updates"])
```

### 4.6 不修改的部分

- **`_detect_platform()` 的过滤逻辑保持不变**：该过滤服务于下载页展示，不影响 electron-updater 链路。yml 同步单独下载，blockmap 通过原始文件名直接处理。
- **`files.py` 不修改**：职责不同（静态文件 vs 版本发布文件），COS key 前缀不同。

## 5. 错误处理

| 场景 | HTTP 状态码 | 行为 |
|------|-----------|------|
| yml 文件 GitHub 获取失败 | 502 | 有旧缓存则返回旧缓存 |
| yml 文件在 Release 中不存在 | 404 | 首次发布可能没有 |
| 请求的文件名不安全（含 `..` 或非允许字符） | 404 | 静默拒绝 |
| 无法从文件名提取版本号 | 404 | 格式不匹配 |
| COS 不命中 → 本地不命中 → GitHub 也不命中 | 404 | 文件不存在 |
| GitHub 下载超时/失败 | 502 | 记录日志 |

## 6. 缓存策略

| 缓存对象 | 位置 | TTL | 说明 |
|---------|------|-----|------|
| latest-mac.yml 内容 | 进程内存 | 5 分钟 | 与现有 `_latest_cache` 保持一致 |
| latest.yml 内容 | 进程内存 | 5 分钟 | 同上 |
| 二进制文件 | COS + 本地 data/ | 永久 | 跟随现有缓存策略，由 `_purge_old_versions` 清理 |
| GitHub asset info | 进程内存 `_latest_cache` | 5 分钟 | 已有，复用 |

## 7. 测试策略

| 层级 | 测试内容 |
|------|---------|
| 单元 | `_parse_filename_to_cache_key()` 各种文件名格式 |
| 单元 | `UpdateFeedService.get_latest_yml()` mock GitHub API |
| 单元 | `UpdateFeedService.find_asset_by_filename()` |
| 集成 | `GET /api/v1/updates/latest-mac.yml` 返回 yml + 正确 Content-Type |
| 集成 | `GET /api/v1/updates/latest.yml` 同上 |
| 集成 | `GET /api/v1/updates/{filename}` COS 302 |
| 集成 | `GET /api/v1/updates/{filename}` 本地缓存 X-Accel-Redirect |
| 集成 | `GET /api/v1/updates/{filename}` GitHub 兜底下载 |
| 集成 | `GET /api/v1/updates/{filename}` 不安全文件名 → 404 |
| 集成 | download_records `source` 字段正确写入 |

## 8. 部署注意事项

- 首次部署后，`latest-mac.yml` / `latest.yml` 第一次请求会从 GitHub 下载（延迟 1-2 秒），后续请求走内存缓存（毫秒级）
- 需要在 COS 中已存在对应版本的 release 文件。如 COS 未上传，会自动降级到本地缓存或 GitHub 兜底
- `upload-codex-switch-to-cos.sh` 后续应加入 blockmap 文件的上传（非本次必需，可后续优化）

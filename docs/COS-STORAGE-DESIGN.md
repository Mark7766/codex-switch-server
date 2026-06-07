# COS 对象存储加速方案 — 完整设计

> **状态**：待 Review  
> **日期**：2026-06-07  
> **决策者**：wangliang  
> **关联**：ADR-005（下载流程重构）

---

## 1. 背景

### 1.1 当前问题

生产服务器位于腾讯云新加坡，国内用户下载速度仅 29KB/s。已验证腾讯云 COS 广州地域公网下载达 2MB/s（70 倍提速）。

### 1.2 测试数据

| 链路 | 速度 | 74MB 耗时 |
|------|------|----------|
| 新加坡直连 | 29 KB/s | ~43 分钟 |
| COS 广州公网 | 2,080 KB/s | ~36 秒 |

### 1.3 目标

- 用户下载走 COS 广州，速度提升 70 倍
- 上传机制自动同步 COS
- 新加坡本地缓存作为 COS 不可用时的降级
- 零用户感知迁移

---

## 2. 系统架构

### 2.1 当前架构

```
用户(国内) ────29KB/s────▶ 新加坡服务器
                            ├─ data/codex-switch/    (GitHub 下载缓存)
                            └─ data/packages/        (admin 上传安装包)
```

### 2.2 目标架构

```
                 ┌─ 检查 COS ──▶ 302 跳转 COS 广州直链（2MB/s）
用户(国内) ────▶ 新加坡 ─┤
                 └─ COS 不可用 ──▶ nginx sendfile 本地文件（降级，29KB/s）

上传链路:
admin 上传 ──▶ 新加坡磁盘（data/packages/）
              └─ 异步上传 COS ──▶ codex-switch-1259344349
                                  ├─ packages/{name}/{version}/{plat}-{arch}.{ext}
                                  └─ codex-switch/{version}/{filename}

GitHub 首次下载缓存:
用户请求下载 ──▶ 新加坡从 GitHub 拉取 ──▶ 缓存到本地磁盘
                                        └─ 上传到 COS
```

---

## 3. COS 配置信息

| 参数 | 值 |
|------|---|
| Bucket | `codex-switch-1259344349` |
| Region | `ap-guangzhou` |
| 公网域名 | `codex-switch-1259344349.cos.ap-guangzhou.myqcloud.com` |
| SecretId | `<YOUR_COS_SECRET_ID>` |
| SecretKey | `<YOUR_COS_SECRET_KEY>` |
| 访问权限 | 公有读私有写 |

## 4. COS 目录结构

```
codex-switch-1259344349/
├── codex-switch/
│   └── {version}/
│       ├── Codex-Switch-{version}-mac-arm64.dmg
│       ├── Codex-Switch-{version}-mac-x64.dmg
│       ├── Codex-Switch-Setup-{version}-win-arm64.exe
│       └── Codex-Switch-Setup-{version}-win-x64.exe
│
└── packages/
    ├── codex-desktop/
    │   └── latest/
    │       ├── Codex-Installer-3.exe        (admin 上传的原始文件名)
    │       └── Codex.dmg
    └── claude-desktop/
        └── latest/
            ├── Claude-5.dmg
            └── Claude.msix
```

**命名规则**：
- Codex Switch：保留 GitHub 原始文件名（如 `Codex-Switch-Setup-1.4.0-win-x64.exe`）
- Packages：保留 admin 上传的**原始文件名**（如 `Claude-5.dmg`），与 registry.json 中 `original_filename` 字段一致

---

## 5. 上传机制

### 5.1 上传触发时机

| 场景 | 触发 | 方式 |
|------|------|------|
| **admin 上传桌面应用安装包** | 上传完成即刻 | 同步上传 COS |
| **Codex Switch 安装包** | 每次部署时 | 运维手动执行脚本，从 GitHub Release 下载 → 上传 COS |

> Codex Switch 安装包不走"首次下载自动缓存"——部署时一次性上传，避免用户首次请求等 GitHub 下载 + COS 上传双重延迟。

### 5.2 admin 上传桌面应用流程

```
用户选文件 → POST /admin/packages/upload
  ├─ 1. 保存到 data/packages/{name}/latest/{original_filename}
  ├─ 2. 更新 registry.json
  └─ 3. 调用 cos_storage.put() → 上传到 COS packages/{name}/latest/{original_filename}
```

**COS 保留原始文件名**（如 `Claude-5.dmg`、`Codex-Installer-3.exe`），与 registry.json 中 `original_filename` 字段一致。

改动文件：`src/admin/router.py`（upload_package 函数末尾加 COS 上传）

### 5.3 Codex Switch 部署脚本

每次部署新版本时，运维手动执行：

```bash
# scripts/upload-codex-switch-to-cos.sh（新增脚本）
# 1. 从 GitHub Release 下载 4 个平台安装包
# 2. 上传到 COS codex-switch/{version}/
# 3. 脚本从 .env 读取 COS 密钥

./scripts/upload-codex-switch-to-cos.sh v1.4.0
```

**为什么不用后端自动上传**：
- Codex Switch 版本更新频率低（几周一次），部署时一次性搞定
- 避免用户首次下载时代理 GitHub → 新加坡 → COS 三层传输的延迟
- 部署时有明确的 4 个文件，不需要运行时动态判断

改动文件：`scripts/upload-codex-switch-to-cos.sh`（新增），不涉及 Python 代码

### 5.4 COS 上传伪代码

```python
# src/utils/cos_storage.py（新增文件）

class CosStorage:
    def __init__(self):
        self._client = CosS3Client(CosConfig(
            Region='ap-guangzhou',
            SecretId=settings.cos_secret_id,
            SecretKey=settings.cos_secret_key
        ))
        self._bucket = settings.cos_bucket

    async def put(self, local_path: Path, cos_key: str) -> str:
        """Upload file to COS, return public URL."""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: self._client.put_object_from_local_file(
                Bucket=self._bucket,
                LocalFilePath=str(local_path),
                Key=cos_key
            )
        )
        return f"https://{self._bucket}.cos.ap-guangzhou.myqcloud.com/{cos_key}"

    def exists(self, cos_key: str) -> bool:
        """Check if file exists on COS (for download routing)."""
        try:
            self._client.head_object(Bucket=self._bucket, Key=cos_key)
            return True
        except Exception:
            return False

    def public_url(self, cos_key: str) -> str:
        return f"https://{self._bucket}.cos.ap-guangzhou.myqcloud.com/{cos_key}"
```

---

## 6. 下载机制

### 6.1 两级下载路由

```
### Codex Switch 下载

```
GET /api/v1/update/download/{version}/{platform}-{arch}

1. 在 COS？
   cos_key = "codex-switch/{version}/{filename}"
   ├─ YES → 302 跳转 COS 公网 URL（快，2MB/s）
   └─ NO  →
       2. 本地缓存？
       ├─ YES → nginx X-Accel-Redirect 本地文件（降级，29KB/s）
       └─ NO  → 3. 从 GitHub 下载 → 缓存本地 → nginx 本地文件
```

> 不再在下载端点中上传 COS。COS 文件由部署脚本 `upload-codex-switch-to-cos.sh` 提前上传。

### 桌面应用安装包下载

```
GET /api/v1/packages/{name}/{version}/{platform}-{arch}

1. 在 COS？
   cos_key = "packages/{name}/latest/{original_filename}"
   ├─ YES → 302 跳转 COS 公网 URL
   └─ NO  → 2. 本地缓存 → nginx X-Accel-Redirect 本地文件（降级）

> 桌面应用安装包由 admin 上传时自动同步 COS，package 的 COS key 使用 registry.json 中的 original_filename。
```
```

### 6.2 下载端点伪代码

```python
# src/api/v1/update.py — download_release（Codex Switch 下载）

@router.get("/download/{version}/{platform}-{arch}")
async def download_release(...):
    svc = ReleaseSyncService(db)
    asset = await svc.get_github_asset_info(version, platform, arch)
    filename = asset["original_name"] if asset else f"Codex-Switch-{version}-{platform}-{arch}.{ftype}"

    # 1. COS 优先（部署脚本已提前上传）
    cos_key = f"codex-switch/{version}/{filename}"
    cos = CosStorage()
    if cos.exists(cos_key):
        await svc.record_download(...)
        return RedirectResponse(url=cos.public_url(cos_key), status_code=302)

    # 2. 本地缓存（降级）
    file_path = await svc.get_download_path(version, platform, arch)
    if file_path is not None:
        await svc.record_download(...)
        return _send_file(file_path, filename)

    # 3. 从 GitHub 下载 → 缓存本地（兜底，不再上传 COS）
    file_path = await svc.download_and_cache(...)
    await svc.record_download(...)
    return _send_file(file_path, filename)


# src/api/v1/packages.py — download_package（桌面应用下载）

@router.get("/{package_name}/{version}/{platform}-{arch}")
async def download_package(...):
    mgr = PackageManager()
    file_path, original_filename = await mgr.get_download_path_with_name(...)

    # 1. COS 优先（admin 上传时已同步）
    cos_key = f"packages/{package_name}/latest/{original_filename}"
    cos = CosStorage()
    if cos.exists(cos_key):
        return RedirectResponse(url=cos.public_url(cos_key), status_code=302)

    # 2. 本地缓存（降级）
    return _send_file(file_path, original_filename)
```

### 6.3 为什么 302 而不是代理

- COS 广州 2MB/s vs 新加坡 29KB/s，302 用户直连 COS 比服务端中转快 70 倍
- nginx X-Accel-Redirect 只在本地文件时有用（降级场景）
- COS 公网 URL 自带 CDN 级别可用性

---

## 7. 上传文件范围

### 7.1 Codex Switch 安装包（自动上传）

| 文件 | 来源 | COS Key |
|------|------|---------|
| macOS ARM64 .dmg | GitHub Release → 首次下载缓存 | `codex-switch/{ver}/Codex-Switch-{ver}-mac-arm64.dmg` |
| macOS x64 .dmg | 同上 | `codex-switch/{ver}/Codex-Switch-{ver}-mac-x64.dmg` |
| Windows ARM64 .exe | 同上 | `codex-switch/{ver}/Codex-Switch-Setup-{ver}-win-arm64.exe` |
| Windows x64 .exe | 同上 | `codex-switch/{ver}/Codex-Switch-Setup-{ver}-win-x64.exe` |

**触发**：用户首次下载时自动触发。不需要 admin 手动操作。

### 7.2 桌面应用安装包（admin 上传时同步）

| 文件 | 来源 | COS Key |
|------|------|---------|
| Codex Desktop macOS | admin 上传 | `packages/codex-desktop/latest/macos-arm64.dmg` |
| Codex Desktop Windows | admin 上传 | `packages/codex-desktop/latest/windows-x64.exe` |
| Claude Desktop macOS | admin 上传 | `packages/claude-desktop/latest/macos-arm64.dmg` |
| Claude Desktop Windows | admin 上传 | `packages/claude-desktop/latest/windows-x64.exe` |

**触发**：admin 上传安装包时同步上传。共 4 个固定槽位。

### 7.3 不上传 COS 的文件

| 文件 | 原因 |
|------|------|
| `registry.json` | 数据库级元数据，非下载文件 |
| `2.1.138.zip`（`src/static/files/`） | 小文件，新加坡直接服务即可 |
| 截图（`src/static/images/guide/`） | 静态资源，nginx 直接 serve，不需要 COS |

---

## 8. 需要改动的文件清单

| 文件 | 改动 | 说明 |
|------|------|------|
| `src/utils/cos_storage.py` | **新增** | COS 客户端封装（put / exists / public_url） |
| `src/config.py` | **修改** | 填入 COS 密钥等配置值 |
| `src/api/v1/update.py` | **修改** | `download_release` 加 COS 检查 → 302（仅检查，不上传） |
| `src/api/v1/packages.py` | **修改** | `download_package` 加 COS 检查 → 302 |
| `src/admin/router.py` | **修改** | `upload_package` 上传完成后同步上传 COS（用原始文件名） |
| `scripts/upload-codex-switch-to-cos.sh` | **新增** | 部署脚本：从 GitHub Release 下载 4 个文件 → 上传 COS |
| `.env.example` | **修改** | 新增 COS 配置示例 |
| `pyproject.toml` | **修改** | 新增依赖 `cos-python-sdk-v5` |

---

## 9. 配置变更

### 9.1 .env 新增字段

```bash
# Tencent Cloud COS
COS_SECRET_ID=<YOUR_COS_SECRET_ID>
COS_SECRET_KEY=<YOUR_COS_SECRET_KEY>
COS_BUCKET=codex-switch-1259344349
COS_REGION=ap-guangzhou
```

### 9.2 config.py 修改

```python
# 已有字段，只需确保 .env 正确加载
cos_secret_id: str = ""
cos_secret_key: str = ""
cos_bucket: str = ""
cos_region: str = "ap-guangzhou"
```

---

## 10. 风险与降级

| 风险 | 降级策略 |
|------|---------|
| COS 不可用 | `cos.exists()` 返回 False → 走本地文件 nginx sendfile |
| COS 上传失败 | 文件已在本地缓存，下次请求重试上传 |
| COS 密钥泄露 | 定期轮换 SecretKey，最小权限原则 |
| admin 上传大文件超时 | 改异步上传 COS，不影响 HTTP 响应 |

---

## 11. 验收标准

| 验收项 | 标准 |
|--------|------|
| COS 下载速度 | ≥ 1 MB/s（国内用户测） |
| 降级下载 | COS 不可用时仍可从新加坡下载 |
| admin 上传后下载 | 上传后立即从 COS 302 跳转 |
| Codex Switch 首次下载 | 首次从 GitHub 下载后自动缓存 + 上传 COS |
| 已有文件不丢失 | 存量本地文件仍可下载（降级） |
| 测试 | ruff + pytest 全部通过 |

---

## 12. 开发计划

| Phase | 内容 | 预估 |
|-------|------|------|
| 1 | 新增 `cos_storage.py` + `config.py` 配置 | 0.5h |
| 2 | 改 `update.py` / `packages.py` / `admin/router.py` | 0.5h |
| 3 | 新增 `scripts/upload-codex-switch-to-cos.sh` 部署脚本 | 0.5h |
| 4 | 测试 + 修复 | 0.5h |
| **合计** | | **2h** |

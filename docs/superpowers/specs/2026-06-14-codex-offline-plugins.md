# Spec: Codex Switch 离线插件安装 — 服务端 API 设计

- **日期**：2026-06-14
- **状态**：方案设计，待 Review
- **范围**：仅服务端接口设计，客户端 UI/UX 由 codex-switch 团队自行设计
- **离线包**：`codex-offline-pack.tar.gz`（36MB），包含 173 个 Codex 精选插件

---

## 1. 背景

Codex Desktop 用户在国内无法正常访问插件市场（依赖 GitHub/npm 等境外资源），插件安装是最大痛点。codex-switch-server 提供一个插件离线包的下载接口，codex-switch 客户端调用该接口完成下载，用户将离线包导入 Codex 即可完成插件安装。

**拉动增长策略**：插件下载接口仅在 Codex Switch 新版本中可用，作为升级激励。

## 2. 接口设计

### 2.1 获取插件包信息

```
GET /api/v1/plugins/pack

Response 200:
{
  "code": 0,
  "data": {
    "version": "1.0.0",
    "filename": "codex-offline-pack.tar.gz",
    "size": 37748736,
    "size_mb": 36,
    "plugin_count": 173,
    "description": "包含 Claude Code 集成、代码格式化、Git 辅助、中文优化等 173 个精选插件",
    "updated_at": "2026-06-14",
    "download_url": "/api/v1/plugins/pack/download"
  }
}
```

**字段说明**：

| 字段 | 说明 |
|------|------|
| `version` | 插件包版本号，客户端可比较本地缓存 |
| `filename` | 文件名，方便客户端保存时使用 |
| `size` / `size_mb` | 文件大小，客户端展示下载进度 |
| `plugin_count` | 包含的插件数量，用于营销展示 |
| `description` | 插件包内容描述 |
| `download_url` | 实际下载地址 |

### 2.2 下载插件包

```
GET /api/v1/plugins/pack/download

Response 302 → COS 广州（2MB/s，国内用户 15-20s 完成）
        或 200 + X-Accel-Redirect（nginx sendfile，降级）
```

**下载链路**（与现有文件下载一致）：

```
COS 广州 302 优先 → 本地缓存 nginx sendfile → GitHub（此包不在 GitHub，最后一级不可用）
```

**响应头**：
```
Content-Disposition: attachment; filename*=UTF-8''codex-offline-pack.tar.gz
Content-Length: 37748736
```

### 2.3 版本更新接口扩展（升级引导）

现有 `POST /api/v1/update/check` 返回新增 `update_highlights` 字段：

```diff
{
  "has_update": true,
  "latest_version": "1.9.1",
  "release_date": "2026-06-14",
  "download_url": "/api/v1/update/download/1.9.1/...",
+ "update_highlights": [
+   "一键安装 Codex 插件（173 个精选离线包）",
+   "COS 国内高速下载，15 秒完成"
+ ]
}
```

客户端收到 `update_highlights` 后可展示升级引导文案，推动用户下载新版本。

## 3. 数据存储

### 3.1 COS 上传

```bash
./scripts/upload-to-cos.sh --files
# 将 data/files/codex-offline-pack.tar.gz 上传到 COS
# COS Key: files/codex-offline-pack.tar.gz
```

### 3.2 本地缓存

插件包放在 `data/files/` 目录，作为 COS 不可用时的降级：

```
data/files/codex-offline-pack.tar.gz
```

## 4. 下载统计

下载插件包时记录到 `download_records`：

| 字段 | 值 |
|------|---|
| `package_name` | `codex-offline-pack` |
| `platform` | 从请求 UA 解析 |
| `source` | `plugin-install` |

Admin 运营后台 Server Tab 的下载趋势中自动出现 `codex-offline-pack` 分类。

## 5. 接口汇总

| 端点 | 方法 | 说明 | 状态 |
|------|------|------|------|
| `/api/v1/plugins/pack` | GET | 获取插件包信息（版本/大小/描述） | 🆕 新增 |
| `/api/v1/plugins/pack/download` | GET | 下载插件包（COS 302） | 🆕 新增 |
| `/api/v1/update/check` | POST | 扩展 `update_highlights` 字段 | 🔧 修改 |

## 6. 实施

| 文件 | 改动 | 说明 |
|------|------|------|
| `src/api/v1/plugins.py` | 新增 | 两个端点 |
| `src/api/router.py` | 修改 | 注册 plugins_router |
| `src/schemas/release.py` | 修改 | `UpdateCheckResponse` +`update_highlights` |
| `src/services/release_sync.py` | 修改 | `check_for_updates()` 返回 highlights |
| `data/files/codex-offline-pack.tar.gz` | 新增 | 本地降级副本 |
| COS `files/codex-offline-pack.tar.gz` | 上传 | 主下载链路 |

代码量估约 40 行（插件端点）+ 10 行（highlights 扩展）。

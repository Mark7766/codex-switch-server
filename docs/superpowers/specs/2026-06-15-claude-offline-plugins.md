# Spec: Claude Desktop 离线插件安装 — 服务端接口扩展

- **日期**：2026-06-15
- **状态**：方案设计，待 Review
- **范围**：仅服务端接口小幅扩展，复用现有 plugins API
- **关联**：`2026-06-14-codex-offline-plugins.md`（Codex 插件接口）

---

## 1. 背景

Codex Switch v1.10.0 已上线 Codex 离线插件安装。现在需要扩展同一个功能支持 Claude Desktop Cowork 扩展安装。

Claude Desktop 的扩展（skills）和 Codex 插件本质相同——都是纯文本文件（`SKILL.md` + `plugin.json`），零运行时依赖。Server 端只需增加第二个插件包（`claude-offline-plugins.tar.gz`，165MB），复用现有接口。

## 2. 接口变更

### 2.1 `GET /api/v1/plugins/pack` — 增加 type 参数

```
GET /api/v1/plugins/pack?type=codex   ← 默认，行为不变
GET /api/v1/plugins/pack?type=claude  ← 新增
```

**Response `?type=claude`**:

```json
{
  "code": 0,
  "data": {
    "type": "claude",
    "version": "1.0.0",
    "filename": "claude-offline-plugins.tar.gz",
    "size": 173015040,
    "size_mb": 165,
    "plugin_count": 170,
    "plugin_count": 170,
    "description": "含 Superpowers 全系列 14 个 + 内置精品 6 个（精选 20），共 170+ 可选",
    "updated_at": "2026-06-15",
    "download_url": "/api/v1/plugins/pack/download?type=claude"
  }
}
```

**新增字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | `"codex"` 或 `"claude"`，客户端据此切换 UI |

> 插件列表（精选 20 个 / 完整 170+ 个）由**客户端硬编码**，Server 不返回。Server 只负责包的元信息和下载链路。

**兼容性**：不带 `type` 参数时默认 `type=codex`，行为与 v1.10.0 完全一致。

### 2.2 `GET /api/v1/plugins/pack/download` — 同理

```
GET /api/v1/plugins/pack/download?type=claude
  → 302 → COS 广州 /files/claude-offline-plugins.tar.gz
  → COS 不可用 → 本地 FileResponse（X-Accel-Redirect）
```

下载记录 `source` 字段设为 `"plugin-install-claude"`，与 Codex 的 `"plugin-install"` 区分统计。

### 2.3 不需要变更的接口

| 端点 | 说明 |
|------|------|
| `POST /api/v1/update/check` | `update_highlights` 无需修改，已有插件引导文案 |

---

## 3. 文件

| 文件 | 路径 | 说明 |
|------|------|------|
| 插件包 | `data/files/claude-offline-plugins.tar.gz` | 165MB，本地降级副本 |
| COS | `files/claude-offline-plugins.tar.gz` | 广州节点，主下载链路 |

---

## 4. 实施

| 文件 | 改动 | 说明 |
|------|------|------|
| `src/api/v1/plugins.py` | +10 行 | `get_plugin_pack()` 接受 `type` 查询参数，返回不同包信息；`download_plugin_pack()` 同理 |
| `data/files/claude-offline-plugins.tar.gz` | 新增 | 165MB，本地降级副本 |

**代码量估约 10 行**（纯参数路由，无新逻辑）。

---

## 5. 两个包的对比

| | Codex pack | Claude pack |
|------|-----------|------------|
| 文件名 | `codex-offline-pack.tar.gz` | `claude-offline-plugins.tar.gz` |
| 大小 | 36 MB | 165 MB |
| 插件总数 | 173 | 170 |
| 推荐安装 | 173（全装） | 20（精选）/ 170+（可选，客户端内置列表） |
| 来源 | 1 个 marketplace | 130+ 个 GitHub 仓库聚合 |
| COS Key | `files/codex-offline-pack.tar.gz` | `files/claude-offline-plugins.tar.gz` |
| 下载记录 source | `plugin-install` | `plugin-install-claude` |

---

> 🤖 Generated with [Claude Code](https://claude.com/claude-code)

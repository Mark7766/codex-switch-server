# Codex Switch Server

[codex-switch](https://github.com/Mark7766/codex-switch) 配套门户 + 服务端。

**网站**: [https://www.codexswtich.cloud](https://www.codexswtich.cloud)

为 codex-switch 用户提供产品门户、版本更新镜像下载、AI 编程工具安装包（Claude Desktop / Codex Desktop）托管、运营后台和遥测数据收集。

## 架构

```
FastAPI (uvicorn)
├── portal/         门户路由（Jinja2 服务器渲染）
├── api/v1/update   版本更新 API（实时 GitHub + 本地缓存）
├── api/v1/packages  工具包下载 API
├── api/v1/telemetry  遥测上报 API
└── admin/          运营后台（Bearer Token 保护）
```

- **数据库**: SQLite（aiosqlite 异步驱动）
- **前端**: Jinja2 服务器渲染 + Apple 风格 CSS + 极简 vanilla JS
- **部署**: Docker 单容器（Nginx SSL + uvicorn，Supervisor 管理）

## 页面

| 路由 | 说明 |
|------|------|
| `/` | 首页 — 下载入口 + AI 工具安装包 |
| `/download` | 下载页 — 实时展示 GitHub 最新版 |
| `/guide` | 使用指南 |
| `/admin` | 运营后台（需登录） |

## 快速开始

```bash
# 安装依赖
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 GITHUB_TOKEN（必需）

# 启动
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000

# 测试
uv run pytest
uv run pytest --cov=src --cov-report=term
```

## 下载流程

1. 访问 `/download` → JS 调用 `/api/v1/update/latest` → 从 GitHub API 实时获取最新版本
2. 点击下载 → 检查 `data/codex-switch/` 本地缓存
3. 缓存命中 → 直接流式返回（秒下）
4. 缓存未命中 → 从 GitHub 下载 → 缓存 → 流式返回（首次较慢，后续秒下）

## AI 工具安装包

管理员通过 `/admin/packages` 上传 Codex Desktop / Claude Desktop 等安装包，用户从首页直接下载。

## COS 文件管理脚本

Codex Switch 安装包通过腾讯云 COS 广州分发（国内 2MB/s，比新加坡本地快 70 倍）。

### 一键脚本：`scripts/release-to-cos.sh`（推荐）

下载 GitHub Release → 上传 COS，一步完成：

```bash
# 指定版本
./scripts/release-to-cos.sh -v 1.8.0

# 自动检测最新版本
./scripts/release-to-cos.sh --latest

# 预览（不实际执行）
./scripts/release-to-cos.sh -v 1.8.0 --dry-run
```

### 下载脚本：`scripts/download-latest-release.sh`

从 GitHub Releases 下载最新（或指定版本）安装包到本地 `data/codex-switch/{version}/`。

```bash
# 自动检测最新版本并下载
./scripts/download-latest-release.sh

# 指定版本
./scripts/download-latest-release.sh -v 1.8.0

# 预览（不实际下载）
./scripts/download-latest-release.sh --dry-run

# 同时生成本地缓存用的简化名副本
./scripts/download-latest-release.sh --local-cache
```

### 上传脚本：`scripts/upload-to-cos.sh`

将本地文件上传到腾讯云 COS 广州，支持三类资源按需上传。

```bash
# 上传全部（Codex Switch + 桌面包 + 静态文件）
./scripts/upload-to-cos.sh --all

# 只上传 Codex Switch 指定版本
./scripts/upload-to-cos.sh --codex-switch 1.8.0

# 自动检测最新版本并上传
./scripts/upload-to-cos.sh --codex-switch latest

# 只上传桌面应用安装包（从 registry.json 读取）
./scripts/upload-to-cos.sh --packages

# 只上传静态文件（如 2.1.138.zip）
./scripts/upload-to-cos.sh --files

# 预览（不实际上传）
./scripts/upload-to-cos.sh --all --dry-run

# 强制覆盖已存在的 COS 对象
./scripts/upload-to-cos.sh --all --force
```

### 典型发布流程

```bash
# 一键完成：下载 + 上传 COS
./scripts/release-to-cos.sh -v 1.8.0
```

服务器上执行（SSH 进入后）：

```bash
cd /home/lighthouse/codex-switch-server
# 先预览
sudo docker exec codex-switch-server bash scripts/release-to-cos.sh -v 1.8.0 --dry-run
# 正式执行
sudo docker exec codex-switch-server bash scripts/release-to-cos.sh -v 1.8.0
```

> **注意**：需要配置 `.env` 中的 `COS_SECRET_ID`、`COS_SECRET_KEY`、`COS_BUCKET`、`COS_REGION`。

## 环境变量

| 变量 | 必需 | 说明 |
|------|------|------|
| `DATABASE_URL` | 否 | SQLite 路径，默认 `sqlite+aiosqlite:///data/app.db` |
| `ADMIN_TOKEN` | 是 | 管理后台登录 Token |
| `GITHUB_TOKEN` | 是 | GitHub Fine-grained PAT，用于 API 访问和下载 |

## License

MIT

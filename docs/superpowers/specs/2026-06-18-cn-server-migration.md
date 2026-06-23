# Spec: 服务器迁移方案 — 新加坡 → 广州（ICP 备案）

- **日期**：2026-06-18
- **状态**：方案设计，待 Review
- **原因**：广州服务器已通过 ICP 备案，可合法在境内提供服务

---

## 0. 代码一致性保障

### 核心原则：两服务器代码完全相同，仅 Nginx 配置不同

```
广州：代码 = 最新版         Nginx = 标准生产配置
新加坡：代码 = 最新版（不动） Nginx = 搬家页 + API 反代
```

**新加坡 Docker 容器不需要重新构建**——只需修改 Nginx 配置文件并 `nginx -s reload`。代码、数据库、Docker 镜像完全不动。

### 新加坡改动范围

| 组件 | 改动 | 风险 |
|------|------|------|
| Docker 容器（codex-switch-server） | **不动** | 无 |
| 数据库（data/app.db） | **不动** | 无 |
| 代码（src/） | **不动** | 无 |
| `.env` | **不动** | 无 |
| `docker/nginx.conf` | **改**：门户三页面 → 搬家页，/api/v1/* → proxy_pass 广州 | 低——改前备份原文件 |
| 静态文件 | **加**：一个 `moving.html` | 无 |

### 回滚保障

```
# 新加坡改动前备份
cp docker/nginx.conf docker/nginx.conf.bak

# 如果搬家有问题，一分钟回滚
cp docker/nginx.conf.bak docker/nginx.conf && nginx -s reload
```

### 为什么代码不需要动

新加坡的 Docker 容器继续运行现有镜像。Nginx 在容器内，配置文件通过 volume 挂载。改 Nginx 配置不触及代码、不重建镜像、不重启容器——只 `nginx -s reload`。

### 数据迁移安全保障

广州先升级并验证通过 → 新加坡再改 Nginx。如果广州有问题，新加坡不受影响（客户端还是走新加坡）。数据迁移在独立步骤中进行（新加坡 DB dump → 广州导入），原始数据不动。

---

## 1. 双服务器拓扑

```
                    codex-switch 客户端
                    ┌──────┴──────┐
                    │             │
              新版(v1.13+)    旧版(<v1.13)
                    │             │
                    ▼             ▼
        ┌─────────────────┐  ┌─────────────────┐
        │ 广州（新）        │  │ 新加坡（旧）      │
        │ 134.175.67.120   │  │ 43.134.110.192  │
        │ codex-switch.cloud│  │ codexswtich.cloud│
        │                  │  │                  │
        │ ✅ 主服务         │  │ ✅ 反代 → 广州    │
        │ ✅ Admin 后台     │  │ ✅ 搬家页(门户)   │
        │ ✅ 遥测接收       │  │ ✅ 下载302→广州   │
        └────────┬─────────┘  └────────┬─────────┘
                 │                     │
                 └──────────┬──────────┘
                            │
                    腾讯云 COS 广州
                codex-switch-1259344349
```

---

## 2. 服务器角色分配

### 2.1 广州服务器（新主站）

| 职责 | 说明 |
|------|------|
| 代码部署 | 和新加坡相同的 Docker 部署方式 |
| 域名 | `codex-switch.cloud`（新域名，已备案） |
| 门户首页 | 最新版本的门户页面 |
| 下载服务 | API + COS 302 |
| 遥测接收 | 新版客户端上报 |
| Admin 后台 | 唯一后台入口 |
| 插件 API | 173 Codex + 170 Claude |
| 邀请系统 | client_registry / referrals |

**部署方式**：和新加坡完全一致——git pull + docker compose up -d --build。`.env` 文件需要更新域名和 SSL 路径。

### 2.2 新加坡服务器（过渡期保留）

保留 4-6 个月，承担两个角色：

| 职责 | 说明 |
|------|------|
| **反向代理**：API 请求 | `proxy_pass` 到广州服务器，旧版客户端无感知切换 |
| **搬家页**：门户访问 | 首页/下载页/指南页显示搬家通知，引导用户去新站 |

**不保留的职责**：Admin 后台（迁移到广州）、遥测写入（迁移到广州）、新数据写入。

---

## 3. 分阶段实施

### 阶段 A：广州服务器升级到最新版（第一步）

广州服务器已有基础环境（SSL 证书、`.env` 域名配置均已就绪），只需升级代码和数据：

1. SSH 到广州服务器 → git pull → docker compose up -d --build
2. 验证门户 + API + 下载全部正常

**此阶段广州独立运行**，新加坡保持不变。

### 阶段 B：新加坡 Nginx 配置搬家页 + API 反代 + 流量监测

**搬家页**（Nginx 层）：

新加坡门户三页面（`/`、`/download`、`/guide`）全部返回同一个简洁搬家页：

```
┌────────────────────────────────────────────┐
│  Codex Switch 搬家啦！                      │
│                                            │
│  我们已经搬到了新家：                         │
│  https://codex-switch.cloud                 │
│                                            │
│  [🚀 前往新网站]                             │
└────────────────────────────────────────────┘
```

搬家页由一个 HTML 文件（`moving.html`）实现，放在 Nginx 静态目录。三页面路由都返回此文件。

**API 反代**（Nginx 层）：

```
# /api/v1/ 下的所有请求 → proxy_pass 到广州
location /api/v1/ {
    proxy_pass https://codex-switch.cloud;
    proxy_set_header Host codex-switch.cloud;
    proxy_set_header X-Forwarded-For $remote_addr;
}
```

这样旧版客户端的 API 调用（版本检查、下载、遥测、插件）全部透明转发到广州，**客户端零改动**。

**不反代的路径**：
- `/admin` — 新加坡 Admin 已废弃，直接返回 404 或重定向到广州

### 阶段 C：客户端切换到新域名

Codex Switch v1.13.0 起：
- `baseUrl` 从 `www.codexswtich.cloud` 改为 `codex-switch.cloud`
- 新安装用户直接连广州
- 旧版用户通过 electron-updater 升级到 v1.13.0 → 自动切到新域名

### 阶段 D：新加坡完全下线（4-6 个月后）

当不再有用户使用 < v1.13.0 版本时（版本洞察确认后）：
1. 停新加坡 Docker 容器
2. DNS CNAME `www.codexswtich.cloud` → `codex-switch.cloud`
3. 新加坡服务器释放

---

## 4. 数据迁移

### 4.1 不需要迁移的数据

| 数据 | 原因 |
|------|------|
| COS 安装包 | 广州、新加坡共用同一个 COS 存储桶，无需迁移 |
| GitHub Release 缓存 | 从 GitHub 重新拉取即可 |

### 4.2 需要迁移的数据

| 数据 | 迁移方式 | 优先级 |
|------|---------|--------|
| `telemetry_events` | SQLite dump → 广州导入 | P0 — 否则 Client 运营数据断层 |
| `download_records` | 同上 | P0 — 否则 Server 运营数据断层 |
| `page_events` | 同上 | P0 — 否则 UV/PV 数据断层 |
| `client_registry` | 同上 | P0 — 否则编号不连续 |
| `referrals` | 同上 | P0 — 否则邀请关系丢失 |
| 安装包本地缓存 | scp 或重新从 GitHub 下载 | P1 — 首次下载会慢但不影响功能 |

**迁移方式**：`sqlite3 data/app.db ".dump" > dump.sql` + scp + 广州 `sqlite3 data/app.db < dump.sql`。新加坡在迁移时间窗口内设为只读（Docker 容器仍运行但 Nginx 拒绝写请求的 API）。

### 4.3 数据合并策略

广州服务器上**已有老版本的数据库**（上次部署的旧版 codex-switch-server）。需要合并：

| 策略 | 说明 |
|------|------|
| 广州 DB 备份 | 先备份 `data/app.db.gz.backup` |
| 新加坡 DB 导入 | 直接覆盖广州 DB（新加坡数据量更大、更新） |

---

## 5. 域名与 SSL

| 服务器 | 域名 | SSL 证书 | 状态 |
|------|------|---------|------|
| 新加坡 | `www.codexswtich.cloud` | codexswtich.cloud 证书 | 保留 |
| 广州 | `codex-switch.cloud` | codex-switch.cloud 证书 | 新启用 |

过渡期后，`www.codexswtich.cloud` CNAME 指向 `codex-switch.cloud`（可选）。

---

## 6. 客户端接入策略

| 客户端版本 | API 指向 | 说明 |
|----------|---------|------|
| v1.13.0+ | `codex-switch.cloud` | 直接连广州 |
| v1.12.x 及以下 | `www.codexswtich.cloud` | → 新加坡反代 → 广州（无感知） |

**electron-updater 推送**：广州服务器上 `latest-mac.yml` / `latest.yml` 指向广州的下载地址。旧版本客户端从新加坡 API 反代拿到 yml 后，下载 URL 已经指向广州 COS——下载本身不受新加坡带宽影响。

---

## 7. 风险与回滚

| 风险 | 缓解 |
|------|------|
| 新加坡→广州反代延迟 | API 请求都是轻量 JSON（<1KB），增加 50-100ms 延迟，可接受 |
| 广州服务器性能不足 | 2 核 2GB 与新加坡同配置，已验证够用 |
| 数据迁移丢失 | 先备份广州 DB + 新加坡 DB，迁移后比对行数 |
| 客户端切换失败 | 新加坡反代保留 4-6 个月，保险期足够长 |
| SSL 证书过期 | 两个域名各自管理证书 |

**回滚**：如果广州出问题，客户端 codex-switch 紧急发 hotfix 把 baseUrl 切回新加坡。反向操作即可。

---

## 8. 检查清单

| # | 任务 |
|---|------|
| 1 | 广州服务器 git pull + docker compose up -d --build |
| 2 | 验证广州门户 + API + 下载 + Admin |
| 3 | 迁移新加坡 DB 到广州（dump + import + 验证行数） |
| 4 | 验证广州 Admin 数据完整 |
| 5 | 新加坡 Nginx 配置搬家页 |
| 6 | 新加坡 Nginx 配置 /api/v1/* 反代到广州 |
| 7 | 新加坡 Nginx 重载 |
| 8 | 验证搬家页能打开 |
| 9 | 验证旧版客户端 API 调用走反代正确 |
| 10 | codex-switch v1.13.0 配置 baseUrl 指向新域名 |
| 11 | 验证新版客户端连广州正常 | |

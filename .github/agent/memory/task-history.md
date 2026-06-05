# 📜 codex-switch-server — 任务历史

> **用途**：记录近期任务摘要，为 AI Agent 提供短期上下文记忆。
> 保留最近 30 条任务记录，超出后归档。

---

## 记录格式

```markdown
### [TASK-{编号}] {任务标题}
- **日期**：YYYY-MM-DD
- **类型**：feat / fix / refactor / docs / chore
- **摘要**：一句话说明做了什么
- **变更文件**：列出核心变更文件
- **关联 Issue**：#xxx（如有）
- **注意事项**：后续需要注意的事项（如有）
```

---

## 任务记录

### [TASK-001] 项目初始化
- **日期**：2026-06-05
- **类型**：chore
- **摘要**：通过 ai-coding-ok skill 安装三层记忆系统和编码规范；根据用户需求（为 codex-switch 构建配套服务端，提供版本更新镜像、桌面应用下载、CLI 工具包托管、运营后台和体验提升计划）自动推断并填充所有配置。
- **变更文件**：AGENTS.md, CLAUDE.md, .github/**/*
- **注意事项**：首次运行。项目从零开始，后续如架构调整请同步更新 project-memory.md 和 decisions-log.md。已选定 Python + FastAPI + SQLite 技术栈。

---

### [TASK-002] 门户 UI/UX 设计 + 代码结构设计
- **日期**：2026-06-05
- **类型**：design
- **摘要**：完成产品门户设计（Apple HIG 风格）、4 个页面布局设计（首页/下载/指南/后台）、视觉系统（颜色/字体/间距/圆角）、代码分层架构（路由→服务→数据），更新 AGENTS.md（新增门户设计/UI UX/代码结构章节）、project-memory.md（新增设计规范模块）、decisions-log.md（新增 ADR-002 门户设计决策、ADR-003 分层架构决策）
- **变更文件**：AGENTS.md, .github/agent/memory/project-memory.md, .github/agent/memory/decisions-log.md
- **关联 Issue**：无
- **注意事项**：设计阶段，尚未写代码。门户采用 Apple 极简风格 + 服务器渲染，前端零框架。代码结构采用 FastAPI 社区标准分层（路由→服务→数据）。下一步应进入 coding 实现阶段。

---

### [TASK-003] 编写完整系统设计方案文档
- **日期**：2026-06-05
- **类型**：docs
- **摘要**：编写 `docs/DESIGN.md` 完整系统设计方案，涵盖 10 个章节：项目概述、系统架构（含完整目录结构+分层规则）、门户 UI/UX 详细设计（4 个页面完整布局+Design Tokens）、API 接口设计（5 组 API 完整请求响应格式）、数据库设计（ER 图+DDL+索引）、代码模块设计（19 个模块职责+伪代码接口）、安全设计（威胁模型+脱敏规范）、部署方案（Nginx+systemd）、5 阶段 7 天开发计划、附录（依赖/环境变量/客户端兼容性）。总计约 800 行。
- **变更文件**：docs/DESIGN.md（新建）
- **关联 Issue**：无
- **注意事项**：此为完整设计方案，待用户 Review 后按 Phase 1→2→3→4→5 顺序进入开发。Review 通过后不可跳过实施方案中的任何 Phase。

---

### [TASK-004] 更新部署方案为 Docker + 实地服务器勘测
- **日期**：2026-06-05
- **类型**：design
- **摘要**：SSH 登录生产服务器 (43.134.110.192) 实地了解环境：Ubuntu 22.04、2 核 1.9GB、Docker 27.1.2 + Compose v2.29.2 已安装、ollama 占用约 800MB、端口 80/443 空闲。基于实地数据重构部署方案：废弃 Nginx+systemd，改为 Docker 单容器部署（Dockerfile + docker-compose.yml + .dockerignore），uvicorn 单 worker（内存限制 512MB），详细运维命令和 HTTPS 后续方案。
- **变更文件**：docs/DESIGN.md（§8 完全重写）、.github/agent/memory/project-memory.md（新增生产环境表）
- **注意事项**：服务器内存紧张（仅 800MB 可用），必须严格限制 uvicorn 为单 worker、容器内存上限 512MB。原始 Nginx/HTTPS/SSL 方案推迟至 Phase 5，先 HTTP :80 运行。

---

### [TASK-005] 更新部署方案：Nginx+SSL 单容器部署（参照 ajepro）
- **日期**：2026-06-05
- **类型**：design
- **摘要**：实地勘测 ajepro 生产环境（SSH + Docker inspect + 读取容器内 nginx.conf），学习其 Nginx+Supervisor 多进程容器模式。更新设计方案：新增 Nginx SSL 终止 + uvicorn + Supervisor 单容器架构，完整 nginx.conf 配置（SSL 配置/端口重定向/静态文件/API 代理/大文件下载），supervisord.conf 双进程管理，entrypoint.sh 启动脚本。域名更新为 www.codexswtich.cloud（SSL 证书 codexswtich.cloud_bundle.crt + .key）。部署路径 /home/lighthouse/codex-switch-server/。ajepro 停服切换流程和回滚方案。
- **变更文件**：docs/DESIGN.md（§8 完全重写为 Nginx+SSL+Supervisor 单容器）、.github/agent/memory/project-memory.md（更新部署方式、域名、证书信息）、.github/agent/memory/decisions-log.md（新增 ADR-004）
- **注意事项**：部署方案从"纯 uvicorn HTTP"改为"Nginx SSL + uvicorn"参照 ajepro 已验证模式。上线当天先停 ajepro 再启动 codex-switch-server 接管 80/443 端口。证书到期前需手动更换（参照 ajepro 约 3 个月换一次）。

---

### [TASK-006] 更新资源规划：服务器卸载 ollama
- **日期**：2026-06-05
- **类型**：design
- **摘要**：用户已在服务器上卸载 ollama，清理了所有相关文件。SSH 确认端口 11434 已释放、二进制和模型目录均已删除。更新设计方案资源规划：移除 ollama 行，内存可用从 ~800MB 升至 ~1.5GB，磁盘已用从 23GB 降至 19GB（释放 4GB）。更新 DESIGN.md §8.11、project-memory.md 生产环境表。
- **变更文件**：docs/DESIGN.md（§8.1 端口表、§8.11 资源规划图+注意事项）、.github/agent/memory/project-memory.md（已运行服务）
- **注意事项**：服务器资源充裕，uvicorn 可从单 worker 增至 2 worker 如果需要。ajepro 停服后 codex-switch-server 独占资源完全没有压力。

---

### [TASK-007] Phase 1：项目骨架开发
- **日期**：2026-06-05
- **类型**：feat
- **摘要**：完成 Phase 1 项目骨架。创建完整目录结构（src/models/schemas/api/services/portal/admin/utils + tests）、pyproject.toml（FastAPI + SQLAlchemy + aiosqlite + Jinja2 + httpx + pydantic-settings）、config.py（pydantic-settings）、database.py（async engine + session）、4 个 ORM 模型（Base/Release/DownloadRecord/TelemetryEvent）、main.py（create_app + lifespan 自动建表）、tests/conftest.py（内存数据库 + AsyncClient fixtures）、Docker 6 文件（Dockerfile/docker-compose.yml/.dockerignore + nginx.conf/supervisord.conf/entrypoint.sh）。
- **变更文件**：pyproject.toml, .env.example, .gitignore, .dockerignore, src/config.py, src/database.py, src/models/*.py, src/main.py, tests/conftest.py, tests/integration/test_app.py, Dockerfile, docker-compose.yml, docker/*, 30+ __init__.py
- **验证**：ruff check ✅, ruff format ✅, pytest 1 passed ✅, uvicorn 启动 → / 返回 404 ✅（符合检查点）
- **注意事项**：项目骨架就绪。数据库表在应用启动时自动创建。下一步 Phase 2 开发门户页面。

---

### [TASK-008] Phase 2：门户页面 + Apple 设计系统
- **日期**：2026-06-05
- **类型**：feat
- **摘要**：完成 Phase 2 门户开发。apple.css（300+ 行完整 Apple Design Token + 全局样式 + 导航/卡片/按钮/分段控件/指南布局 + 响应式 3 断点）、base.html（毛玻璃导航+页脚 Jinja2 模板继承壳）、index.html（Hero+三列价值卡片+工具图标网格+用户故事+CTA）、download.html（macOS/Windows/Linux 三段式下载页+系统要求+历史版本）、guide.html（sticky 侧边栏 6 步骤导航+内容区+代码块+note）、portal/router.py（3 条路由）、portal.js（导航毛玻璃效果）、main.py（注册 portal_router + StaticFiles）、测试 23 条（覆盖率 95%）
- **变更文件**：src/static/css/apple.css, src/static/js/portal.js, src/portal/templates/{base,index,download,guide}.html, src/portal/router.py, src/main.py, tests/{integration/test_portal,unit/test_config,unit/test_models,integration/test_app}.py, tests/conftest.py
- **验证**：ruff check ✅, ruff format ✅, pytest 23/23 ✅, coverage 95% ✅（目标 ≥80%）
- **注意事项**：门户页面数据目前硬编码（版本号 v1.4.0、下载链接 #），Phase 3 将接入真实数据。

---

### [TASK-009] Phase 3：版本更新 API + 管理后台 + 数据服务层
- **日期**：2026-06-05
- **类型**：feat
- **摘要**：完成 Phase 3 开发。utils/http.py（HttpClient httpx 封装/重试/流式下载）、utils/storage.py（LocalStorage 文件存取/列表/删除）、schemas/release.py（APIResponse 泛型包装 + 10 个 DTO）、services/release_sync.py（ReleaseSyncService/版本检查/语义版本比较/GitHub 同步/下载记录/统计/清理/平台检测）、api/v1/update.py（update/check + download 端点）、api/v1/packages.py（4 个工具包列表+下载）、api/deps.py（get_db + verify_admin_token itsdangerous cookie）、api/router.py（v1 聚合）、admin/router.py（登录/会话/仪表盘）、admin/templates（login + dashboard Chart.js）、main.py（集成所有路由）。测试 57 条、覆盖率 80%。
- **变更文件**：src/utils/{http,storage}.py, src/schemas/release.py, src/services/release_sync.py, src/api/{deps,router}.py, src/api/v1/{update,packages}.py, src/admin/{router,login,dashboard}.py, src/main.py, tests/{test_api_update,test_api_packages,test_admin,test_services,test_utils,test_deps}.py
- **验证**：ruff ✅, ruff format ✅, pytest 57/57 ✅, coverage 80% ✅
- **注意事项**：工具包下载和版本更新下载目前为占位。Phase 4 完成遥测闭环。

---

### [TASK-010] Phase 4：遥测系统
- **日期**：2026-06-05
- **类型**：feat
- **摘要**：完成 Phase 4 遥测系统。schemas/telemetry.py（TelemetryEventIn/Payload/IngestResult/TelemetryStats + 12 种事件类型白名单）、services/telemetry.py（TelemetryService：事件验证/三元组去重/每分钟限速/批量写入/聚合统计/趋势查询/client_id 脱敏）、api/v1/telemetry.py（POST /api/v1/telemetry/events）、admin dashboard 接入真实遥测数据（4 卡片+Chart.js 柱状图功能分布+折线图趋势+最近事件表）、commit 事务修复（解决集成测试跨 session 数据不可见问题）。测试 69 条/覆盖率 82%。
- **变更文件**：src/schemas/telemetry.py, src/services/telemetry.py, src/api/v1/telemetry.py, src/api/router.py, src/admin/router.py, src/admin/templates/dashboard.html, src/services/release_sync.py（flush→commit）, tests/{test_api_telemetry,test_telemetry_service}.py
- **验证**：ruff ✅, pytest 69/69 ✅, coverage 82% ✅
- **注意事项**：遥测端点为公开 API，依赖客户端正确上报。事件类型白名单 12 种，新增类型需同步更新 VALID_EVENT_TYPES。admin dashboard 的 Chart.js 从 CDN 加载（jsdelivr）。

---

### [TASK-011] Phase 5：生产环境部署
- **日期**：2026-06-05
- **类型**：deploy
- **摘要**：Docker 部署到 43.134.110.192。clone→certs→.env→停ajepro→build→start→修复DATABASE_URL→修复supervisord→验证。所有 7 端点 HTTPS 200。生产地址 https://www.codexswtich.cloud。
- **变更文件**：docker/supervisord.conf（uv run → .venv/bin/uvicorn）
- **部署信息**：IP 43.134.110.192, 域名 www.codexswtich.cloud, 路径 /home/lighthouse/codex-switch-server, ADMIN_TOKEN=627202abef4a70438c36c23cefc9e031
- **注意事项**：ajepro 已永久停服。证书到期手动换 certs/ 后 restart。更新流程：ssh → git pull → docker compose up -d --build

---

### [TASK-012] 后台上传安装包 + 门户真实下载
- **日期**：2026-06-05
- **类型**：feat
- **摘要**：实现安装包后台上传和门户下载功能。PackageManager（JSON registry + 文件系统存储，支持 add/list/delete/get_download_path）、admin router 新增 GET /admin/packages（管理页面）+ POST /admin/packages/upload（上传）+ POST /admin/packages/delete（删除）、packages API 改为读取真实 registry、admin 新增 packages.html 模板（上传表单+包列表表格）。部署到生产服务器验证通过。
- **变更文件**：src/services/package_manager.py, src/admin/router.py, src/admin/templates/packages.html, src/api/v1/packages.py, src/portal/templates/download.html, tests/unit/test_package_manager.py, tests/integration/test_admin_packages.py
- **验证**：ruff ✅, pytest 79/79 ✅, 容器内 API ✅, admin/packages 页面 ✅
- **注意事项**：安装包存储在 data/packages/ 目录，registry 为 JSON 文件。上传通过 admin/packages 页面操作，需先登录 admin。用户下载从 /api/v1/packages/{name}/{ver}/{plat}-{arch}。


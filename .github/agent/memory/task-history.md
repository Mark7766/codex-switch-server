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

---

### [TASK-013] 下载流程重构：实时 GitHub + 首次代理缓存 + 首页动态安装包下载
- **日期**：2026-06-06
- **类型**：refactor
- **摘要**：
  1. **Codex Switch 下载流程重构**：废弃 DB 存储 release + 手动同步模式。改为 `/api/v1/update/latest` 实时查 GitHub 最新版（5 分钟内存缓存），下载端点首次从 GitHub 代理拉取并缓存到 `data/codex-switch/{ver}/{plat}-{arch}.{ext}`，二次下载直接走本地缓存（92MB 从 98s 降至 0.78s）。
  2. **首页动态安装包下载**：tool-card 改为动态加载，JS fetch `/api/v1/packages`，为 Codex Desktop/Claude Desktop 自动生成下载按钮（显示平台+文件大小）。
  3. **首页布局调整**："下载 AI 编程工具"区块移到 Hero 下方最优先位置，features 区块下移。
  4. **Logo**：从 codex-switch 项目复制 icon.png 到 static/images/，nav 导航栏和 favicon 均显示。
  5. **Bug 修复**：admin 上传表单加 trim 防空格包名、`_detect_platform` 过滤 blockmap/yml/zip、Windows exe 无显式 arch 则拒绝、`get_github_asset_info` 版本不匹配时返回 None。
  6. **测试更新**：11 个旧测试适配新架构，81/81 passed，覆盖率 86%。
- **变更文件**：src/services/release_sync.py（重写）、src/api/v1/update.py（重写）、src/portal/templates/download.html、src/portal/templates/index.html、src/portal/templates/base.html、src/admin/router.py、src/admin/templates/dashboard.html、src/static/css/apple.css、tests/*.py（7 个文件）
- **验证**：ruff ✅, pytest 81/81 ✅, coverage 86% ✅, API /latest 返回 v1.4.0 ✅, 首次下载缓存 ✅, 二次下载秒下 ✅, 首页安装包下载 ✅
- **注意事项**：不再需要手动同步 release。admin dashboard 移除了同步按钮。`.env` 中 GITHUB_TOKEN 必须配置。首次下载每个平台/架构组合会慢（~1-2 分钟），之后走缓存。

---

### [TASK-014] 下载文件名修复 + 生产环境部署 + CI 修复
- **日期**：2026-06-06
- **类型**：fix
- **摘要**：
  1. **下载文件名修复**：Codex Switch 下载加 `Content-Disposition` 头，文件名取 GitHub 原始 asset 名（如 `Codex-Switch-1.4.0-mac-arm64.dmg`）；安装包下载文件名取上传时的 `original_filename`。
  2. **生产数据库修复**：`database.py` 显式导入所有模型，解决 `NoReferencedTableError`（`download_records.release_id` FK 找不到 `releases` 表）。
  3. **Nginx 配置修复**：`client_max_body_size` 从 16M 改到 512M（支持大安装包上传）；`location /api/v1/packages` 去尾部斜杠修复 301 重定向；移除废弃的 `/admin/sync-releases` location。
  4. **CI 修复**：`ruff format` 格式问题 + `test_settings_defaults` CI 环境变量覆盖问题。
  5. **部署信息存储**：`.deploy/production.md` 保存服务器 SSH 信息，`.gitignore` 添加 `.deploy/`。
- **变更文件**：src/api/v1/update.py, src/api/v1/packages.py, src/services/package_manager.py, src/services/release_sync.py, src/database.py, docker/nginx.conf, tests/unit/test_config.py, .gitignore
- **验证**：ruff ✅, pytest 81/81 ✅, 生产 200 ✅, download Content-Disposition ✅

---

### [TASK-015] 使用指南重写 + Windows 11 要求 + 图片占位
- **日期**：2026-06-06
- **类型**：feat
- **摘要**：
  1. **指南页完全重写**：5 步改为"获取 DeepSeek API Key → 安装 Codex 桌面版 → 安装 Claude 桌面版 → 安装 Codex Switch → 常见问题"。每步都包含动态下载按钮（JS 从 `/latest` 和 `/packages` API 拉取）。
  2. **Claude 桌面版安装指南**：详细 Windows 11 安装步骤，包括重命名为 `Claude.msix`、管理员 PowerShell 执行 `Add-AppxProvisionedPackage` 和 `dism` 命令、安装后打开 `Claude-3p\claude-code` 目录解压 `2.1.138.zip`。
  3. **Windows 系统要求**：下载页和指南页统一改为 Windows 11。
  4. **图片占位**：17 处 `guide__placeholder` 虚线框，标记 `[图：...]` 说明，方便后续填入截图。
  5. **CSS**：新增 `.guide__placeholder` 和 `.guide__download` 样式。
- **变更文件**：src/portal/templates/guide.html（重写）、src/portal/templates/download.html、src/static/css/apple.css、tests/integration/test_portal.py
- **验证**：ruff ✅, pytest 81/81 ✅, 指南页 5 步骤 ✅, 下载按钮 3 处 ✅, 图片占位 17 处 ✅

---

### [TASK-016] 使用指南改为二选一结构 + ai-coding-ok 触发修复
- **日期**：2026-06-06
- **类型**：refactor
- **摘要**：
  1. **指南二选一结构**：将"安装 Codex 桌面版"和"安装 Claude 桌面版"从顺序步骤改为同级的二选一选项。侧边栏加入二级子菜单（选项 A / 选项 B），内容区顶部加入两个选择卡片（`guide__choice-card`），视觉上明确用户只需选一个安装。
  2. **CLAUDE.md 强化**：改为极简 ALL-CAPS 直接指令，无法跳过。
  3. **sessionStart hook 修复**：settings.json 与 settings.local.json 冲突导致 hook 不生效，合并到 settings.local.json 并删除 settings.json。
  4. **CSS**：新增 `.guide__choice`、`.guide__choice-card`、`.guide__divider`、`.guide__subnav` 样式。
- **变更文件**：src/portal/templates/guide.html, src/static/css/apple.css, CLAUDE.md, .claude/settings.local.json, tests/integration/test_portal.py
- **验证**：ruff ✅, pytest 81/81 ✅, 二选一卡片 2 个 ✅, 侧边栏子菜单 ✅

---

### [TASK-017] 使用指南图片占位 → 具体命名 img 标签
- **日期**：2026-06-06
- **类型**：feat
- **摘要**：17 处 `guide__placeholder` 虚线框全部替换为具体命名的 `<img>` 标签（如 `step1-deepseek-home.png`）。新增 `guide__img` CSS 样式（`max-width:100%; border-radius; box-shadow`）。图片目录：`src/static/images/guide/`。
- **变更文件**：src/portal/templates/guide.html, src/static/css/apple.css
- **验证**：ruff ✅, pytest 81/81 ✅, 占位符 0 残留 ✅, img 标签 17 个 ✅

---

### [TASK-018] 使用指南 macOS/Windows 安装分区 + Claude 新增 macOS
- **日期**：2026-06-06
- **类型**：feat
- **摘要**：
  1. Codex 桌面版和 Claude 桌面版均分为 macOS 安装和 Windows 安装独立章节（`h4` + `guide__divider` 分隔）。
  2. Claude 桌面版新增 macOS 安装步骤（dmg → Applications），新增截图占位 `step2b-macos-install.png`。
  3. Claude 选择卡片描述从 "Windows 11" 改为 "macOS / Windows 11"。
- **变更文件**：src/portal/templates/guide.html
- **验证**：ruff ✅, pytest 81/81 ✅, macOS/Windows 标题各 2 个 ✅

---

### [TASK-019] 使用指南交互优化：渐进式选择（工具 → 平台 → 指南）
- **日期**：2026-06-06
- **类型**：feat
- **摘要**：第二步改为三步渐进式交互：
  1. 两个工具选择卡片（Codex / Claude），点击高亮选中
  2. 选择工具后出现 macOS / Windows 平台选择按钮
  3. 选择平台后显示对应安装指南面板（带淡入动画）
  支持随时切换。JS 函数 `selectTool()` / `selectPlatform()` 控制显示隐藏，4 个 `guide__step-content` 面板。
  新增 CSS：`.guide__choice-card--active`、`.guide__platform-picker`、`.guide__platform-btn`、`@keyframes guideFadeIn`。
- **变更文件**：src/portal/templates/guide.html, src/static/css/apple.css, tests/integration/test_portal.py
- **验证**：ruff ✅, pytest 81/81 ✅


---

### [TASK-020] admin/packages 极简化 + 指南下载动态匹配平台
- **日期**：2026-06-06
- **类型**：refactor
- **摘要**：
  1. **admin/packages 极简化**：移除复杂表单和表格，改为 4 张固定卡片（Codex/Claude × macOS/Windows），隐藏固定字段，只需选文件上传即可覆盖更新。修复 Jinja2 HTML 实体转义（`|safe`）。
  2. **指南下载匹配平台**：安装包下载从 `pkg.platforms[0]` 改为按 `selPlat` 精确匹配。
- **变更文件**：src/admin/templates/packages.html（重写）、src/portal/templates/guide.html
- **验证**：ruff ✅, pytest 81/81 ✅

---

### [TASK-021] xattr 文案修正 + 2.1.138.zip 下载 + 截图清单
- **日期**：2026-06-06
- **类型**：fix
- **摘要**：
  1. macOS 警告文案改为"安装后需要在终端执行以下命令，否则会报错"
  2. Claude Windows 安装步骤新增 `2.1.138.zip` 下载按钮（`/static/files/2.1.138.zip`）
  3. 整理 10 张截图清单，按场景分组（通用/Codex/Claude/macOS 错误）
- **变更文件**：src/portal/templates/guide.html, src/static/files/2.1.138.zip（新增）
- **验证**：本地渲染 ✅, zip 下载 200 ✅

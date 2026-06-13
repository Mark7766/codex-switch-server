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

---

### [TASK-022] Phase 1：门户首页调整
- **日期**：2026-06-07
- **类型**：feat
- **摘要**：
  1. **Hero 双按钮**："下载 macOS 版 / Windows 版" → "查看安装指南 → / 直接下载 →"，指南为主按钮
  2. **新增"安装指南"快捷入口**：4 张卡片（Codex Desktop / Claude Desktop / Codex CLI / Claude Code CLI），点击跳转 `/guide?tool=xxx` 预选工具
  3. **下载区精简**：从 4 张卡片（含 CLI 占位）缩减为 2 张（Codex Desktop / Claude Desktop），纯下载用途
  4. **CSS**：新增 `.guide-entry`、`.guide-entry__grid`、`.guide-entry__card` 样式，4 列桌面 / 2 列移动端
  5. **缓存版本**：CSS/JS URL 版本号更新为 `20260607`
- **变更文件**：src/portal/templates/index.html, src/static/css/apple.css, src/portal/templates/base.html
- **验证**：ruff ✅, pytest 81/81 ✅, 首页 200 ✅, 4 卡片链接正确 ✅

---

### [TASK-023] Phase 2：CLI 指南开发 + Stop hook asyncRewake 修复
- **日期**：2026-06-07
- **类型**：feat
- **摘要**：
  1. **guide.html 扩展 4 工具卡片**：2×2 网格（桌面应用 + 命令行工具），新增 Codex CLI 和 Claude Code CLI
  2. **CLI 安装指南**：8 步动态渲染（macOS 检查 git/python，Windows 安装 git/node/python，统一 Git Bash 执行，npm install CLI，Codex Switch CLI 管理配置）
  3. **URL 参数预选**：`?tool=codex-cli` 自动跳过工具选择步骤
  4. **步骤动态生成**：renderGuide() 完全重构为数组驱动，桌面版 6 步 / CLI 8 步
  5. **Stop hook 改为 asyncRewake**：退出码 2 强制唤醒，不更新记忆文件就无法结束回复
- **变更文件**：src/portal/templates/guide.html（重写 JS 渲染逻辑）、.claude/settings.local.json、tests/integration/test_portal.py
- **验证**：ruff ✅, pytest 81/81 ✅, 4 卡片 ✅, URL param ✅, CLI 8 步 ✅

---

### [TASK-024] ai-coding-ok 文档链路修复
- **日期**：2026-06-07
- **类型**：fix
- **摘要**：
  1. **定位根因**：AGENTS.md Plan 阶段只要求读 3 个记忆文件，从未要求读 system-prompt.md / workflows.md / coding-standards.md / copilot-instructions.md。导致这些文件内容过时无人发现。
  2. **修复 AGENTS.md**：Plan 阶段扩展为 7 个文件（新增 AGENTS.md / system-prompt.md / workflows.md / coding-standards），Act 阶段新增第 4 条"同步更新过时的 agent 文档"。
  3. **修复 system-prompt.md**：关键业务概念 3 条重复 copy-paste → 重写为 4 条独立概念；核心业务流程从旧同步架构更新为实时 GitHub 模式。
  4. **修复 copilot-instructions.md**："从 GitHub 同步" → "实时获取 GitHub 最新版本"。
- **变更文件**：AGENTS.md, .github/agent/system-prompt.md, .github/copilot-instructions.md
- **注意事项**：agent 文档（system-prompt/workflows/coding-standards）内容需持续维护，AGENTS.md 的 Plan 阶段清单已覆盖

---

### [TASK-025] Phase 3 + Phase 4：截图补充 + 联动调试 + 部署上线
- **日期**：2026-06-07
- **类型**：deploy
- **摘要**：
  1. **截图审计**：22 张截图全部就位（16 CLI + 6 通用/桌面），`onerror` 兜底缺失图片自动隐藏
  2. **端到端验证**：`?tool=xxx` 4 个 URL 参数全部正确传递，renderGuide 9 个关键函数正常
  3. **部署上线**：git push → docker compose up -d --build → 生产全端点 200
- **变更文件**：22 张截图（src/static/images/guide/）
- **验证**：ruff ✅, pytest 81/81 ✅, 生产 200 ✅

---

### [TASK-026] COS 对象存储集成开发
- **日期**：2026-06-07
- **类型**：feat
- **摘要**：
  1. **新增 `src/utils/cos_storage.py`**：COS 客户端封装（put/exists/public_url/delete），COS 未配自动降级
  2. **修改 `update.py`**：Codex Switch 下载 COS 优先 → 302 跳转广州；COS 不存在 → 本地缓存 → GitHub 下载兜底
  3. **修改 `packages.py`**：桌面应用下载 COS 优先（用 original_filename 作为 COS key）
  4. **修改 `admin/router.py`**：上传安装包时同步上传 COS（用原始文件名）
  5. **新增 `scripts/upload-codex-switch-to-cos.sh`**：部署时执行，从 GitHub Release 下载 4 平台文件并上传 COS
  6. **依赖**：`cos-python-sdk-v5` 加入 pyproject.toml
- **变更文件**：src/utils/cos_storage.py（新）、src/api/v1/update.py、src/api/v1/packages.py、src/admin/router.py、scripts/upload-codex-switch-to-cos.sh（新）、pyproject.toml、.env.example
- **验证**：ruff ✅, pytest 81/81 ✅, COS 302 ✅, 降级 nginx ✅

---

### [TASK-027] COS 集成 Act 阶段补漏
- **日期**：2026-06-07
- **类型**：fix
- **摘要**：TASK-026 只更新了 task-history，漏了 ADR 和 project-memory。补上 ADR-009（COS 广州架构决策）+ project-memory.md（下载流程、架构图更新）+ system-prompt.md（业务流更新）。
- **变更文件**：decisions-log.md（ADR-009）、project-memory.md、system-prompt.md
- **注意事项**：根因是 Act 阶段习惯只更新 task-history，不检查是否需要更新其他文件。需要在 Stop hook 的提醒中强化"检查是否架构变更/事实变更"

---

### [TASK-029] COS 下载链路修复：桌面包 COS miss + 文件名错误
- **日期**：2026-06-07
- **类型**：fix
- **摘要**：修复两个 COS 下载缺陷：①桌面应用安装包已上传 COS 但不走 COS（走本地降级），根因是 `packages.py` COS key 依赖 `original_filename` 字段（旧 registry 无此字段则跳过 COS）；②COS 下载文件名来自 URL 路径末段而非原始文件名，根因是 302 重定向的 Content-Disposition 不传递到 COS。
  - 修复 1：COS key 改为确定性格式 `packages/{name}/latest/{platform}-{arch}.{ext}`，不再依赖 `original_filename`
  - 修复 2：上传 COS 时设置 `ContentDisposition` 元数据（`cos_storage.py` put() 加 content_disposition 参数）
  - 修复 3：`exists()` 加 debug 日志，便于排查 COS miss
  - 修复 4：`upload-codex-switch-to-cos.sh` 同步加 Content-Disposition
- **变更文件**：src/utils/cos_storage.py, src/api/v1/packages.py, src/admin/router.py, src/api/v1/update.py, scripts/upload-codex-switch-to-cos.sh
- **验证**：ruff ✅, pytest 81/81 ✅
- **注意事项**：COS key 格式变更后，旧 COS 对象（`packages/{name}/latest/{原始文件名}`）变成孤儿。需在 admin/packages 页面重新上传一次桌面包即可。Codex Switch 的 COS key 不受影响。

---

### [TASK-030] COS 全量上传 + 8 端点链路验证
- **日期**：2026-06-07
- **类型**：ops
- **摘要**：
  1. 从 GitHub 下载 Codex Switch v1.4.0 缺失的 2 个平台文件（macos-x64, windows-arm64）并缓存本地
  2. 上传全部 4 个 Codex Switch 文件到 COS 广州（带 Content-Disposition 元数据）
  3. 上传 4 个桌面应用安装包到 COS（新建确定性 key 格式）
  4. 修复 GitHub push 被 secret scanning 拦截（`docs/COS-STORAGE-DESIGN.md` 泄露腾讯云 Secret ID/Key，改为占位符，force push 重写历史）
  5. 本地验证全部 8 个下载端点 → COS 302 ✅，文件名正确 ✅
  6. 更新 hooks：新增 git push / SSH 生产 / docker compose 三个 PreToolUse 阻断钩子
- **变更文件**：docs/COS-STORAGE-DESIGN.md, .claude/settings.local.json, data/codex-switch/1.4.0/*, COS 对象 8 个
- **验证**：8/8 COS 302 ✅, ruff ✅, pytest 81/81 ✅
- **注意事项**：生产环境尚未部署新代码（COS key 格式变更）。Codex Switch 的 COS key 不受影响。

---

### [TASK-031] 使用指南：DeepSeek API Key 文案修正
- **日期**：2026-06-07
- **类型**：fix
- **摘要**：将"获取 DeepSeek API Key"步骤的描述从"注册即送免费额度"改为"注册后需要充值几块钱才能使用 API"，反映 DeepSeek 实际付费政策。
- **变更文件**：src/portal/templates/guide.html
- **验证**：本地渲染 ✅

---

### [TASK-032] 生产部署：COS 修复 + DeepSeek 文案上线
- **日期**：2026-06-07
- **类型**：deploy
- **摘要**：SSH 部署到 43.134.110.192，commit range `74dae31`→`218fdc2`（17 files, +1350/-21）。部署内容：COS 下载链路修复（确定性 key + Content-Disposition）、新增 cos_storage.py/COS 设计文档/上传脚本、DeepSeek 文案修正。验证全部 6 个端点 200。生成部署记录 `.deploy/deployments.md`。
- **变更文件**：17 个（详见 .deploy/deployments.md）
- **验证**：全端点 200 ✅
- **注意事项**：COS 8 个对象已提前上传。回滚方案见 .deploy/deployments.md

---

### [TASK-033] Phase A：Admin 优化数据层开发
- **日期**：2026-06-07
- **类型**：feat
- **摘要**：按 ADMIN-REDESIGN-V2.md 执行 Phase A——数据层新增埋点表和下载趋势查询。新建 PageEvent ORM 模型（event_type/page/element_id/ip_hash/user_agent）、AnalyticsService（埋点写入/页面统计/下载趋势/下载包明细 8 粒度）、Pydantic DTOs + 中文映射表（3 页面 + 29 按钮 + 3 产品 + 4 平台）。download_records 已有 package_name 字段可直接区分类别，无需新增 product 字段。
- **变更文件**：src/models/page_event.py（新）、src/schemas/analytics.py（新）、src/services/analytics.py（新）、src/database.py（改）
- **验证**：ruff ✅, pytest 81/81 ✅
- **注意事项**：中文映射硬编码在 schemas/analytics.py 中。Phase B 将开发 API 层端点。

---

### [TASK-034] Phase B：API 层开发（埋点上报 + 统计查询端点）
- **日期**：2026-06-07
- **类型**：feat
- **摘要**：按 ADMIN-REDESIGN-V2.md 执行 Phase B——3 个 API 端点。`POST /api/v1/analytics/pageview` 公开埋点上报（fire-and-forget）、`GET /api/v1/admin/analytics/page-stats` 页面/点击统计（中文映射 + 趋势）、`GET /api/v1/admin/analytics/download-trends` 下载趋势（8 包粒度 + 产品/版本/平台拆分）。admin 端点 Bearer Token 保护。
- **变更文件**：src/api/v1/analytics.py（新）、src/api/v1/admin_api.py（新）、src/api/router.py（改）
- **验证**：ruff ✅, pytest 81/81 ✅, pageview 200 ✅, page-stats 200(中文) ✅, download-trends 200(49总) ✅
- **注意事项**：admin API 需要先 POST /admin/login 获取 cookie 后才能访问。

---

### [TASK-035] Phase C：前端埋点开发（portal JS + data-track）
- **日期**：2026-06-07
- **类型**：feat
- **摘要**：按 ADMIN-REDESIGN-V2.md 执行 Phase C——门户全站埋点。portal.js 新增 sendBeacon 页面浏览上报 + data-track 点击监听。3 个模板（index/download/guide）+ base.html 导航栏/页脚共埋 29 个点位。CSS/JS 版本号更新为 20260607b。
- **变更文件**：src/static/js/portal.js、src/portal/templates/base.html、index.html、download.html、guide.html
- **验证**：ruff ✅, pytest 81/81 ✅, pageview 上报 → admin 中文显示"使用指南" ✅
- **注意事项**：所有点位 ID 与 schemas/analytics.py 中文映射表对应，新增点位需同步更新映射表。

---

### [TASK-036] Phase D：Admin 面板三 Tab 重设计
- **日期**：2026-06-07
- **类型**：feat
- **摘要**：按 ADMIN-REDESIGN-V2.md 执行 Phase D——Admin dashboard 重写为三 Tab 布局（Server运营/App遥测/安装包管理）。Server Tab：4 指标卡片 + 下载趋势折线图（7/30/90天切换）+ 包明细表格 + 产品占比环形图 + 页面访问柱状图 + 热门点击 Top 10 表格；App Tab：保留原有遥测图表；Packages Tab：嵌入 4 固定卡位上传表单。数据由 JS fetch admin API 渲染，Chart.js 按 Tab 切换懒加载。
- **变更文件**：src/admin/templates/dashboard.html（重写）、src/admin/router.py（加 packages 数据）
- **验证**：ruff ✅, pytest 81/81 ✅, 24KB HTML/3 Tabs/4 packages ✅

---

### [TASK-037] Phase E：Admin 优化测试 + 完成全部 5 阶段
- **日期**：2026-06-07
- **类型**：test
- **摘要**：按 ADMIN-REDESIGN-V2.md 执行 Phase E——为 Phase A~D 全部新功能补充测试。单元测试：中文映射 10 个 + PageviewRequest 2 个 + PageEvent 模型 3 个 + AnalyticsService 5 个。集成测试：pageview 端点 3 个 + admin API 5 个 + dashboard Tab 布局 3 个。conftest.py 注册 PageEvent 模型。总计 113 tests（新增 32 个）。
- **变更文件**：tests/unit/test_analytics.py（新）、tests/integration/test_admin_api.py（新）、tests/conftest.py（改）
- **验证**：ruff ✅, pytest 113/113 ✅

---

### [TASK-038] 修复 admin 面板 "unknown" 显示 + 桌面应用下载记录
- **日期**：2026-06-07
- **类型**：fix
- **摘要**：Admin 面板下载统计显示 "unknown"——根因是旧 download_records 的 package_name 字段为 NULL。修复：① update.py 3 处 record_download 加 package_name="codex-switch" ② packages.py 新增 record_download 调用（桌面包下载之前未记录）③ database.py 启动时自动回填 NULL → 'codex-switch' ④ analytics.py 查询用 coalesce 兜底。
- **变更文件**：src/api/v1/update.py, src/api/v1/packages.py, src/database.py, src/main.py, src/services/analytics.py
- **验证**：ruff ✅, pytest 113/113 ✅, admin API 返回 Codex Switch 中文名 ✅

---

### [TASK-039] 生产部署：Admin v2 + 全站埋点上线
- **日期**：2026-06-07
- **类型**：deploy
- **摘要**：SSH 部署到 43.134.110.192，commit range `218fdc2`→`bacdebd`（22 files, +1682/-127）。部署内容：Admin 运营后台 v2（三 Tab + 埋点 + 下载精细化）、门户全站 29 点位埋点、桌面应用下载记录、NULL package_name 自动回填。生产验证 8/8 下载 COS 302 + 5/5 门户/API 200。
- **部署记录**：`.deploy/deployments.md` 部署 2026-06-07-002
- **验证**：8/8 COS 302 ✅, 5/5 门户/API 200 ✅

---

### [TASK-040] 修复微信分享卡片显示灰卡（缺少 OG 元标签）
- **日期**：2026-06-07
- **类型**：fix
- **摘要**：微信分享到朋友圈显示灰色空白卡片——根因是 base.html 完全缺少 Open Graph 元标签。新增 6 个 OG 标签（og:type/site_name/title/description/url/image + 尺寸），分享图使用 logo.png（1024×1024）。CSS 版本号更新为 20260607c。
- **变更文件**：src/portal/templates/base.html
- **验证**：ruff ✅, pytest 113/113 ✅, OG 标签渲染正确 ✅

---

### [TASK-041] 修复埋点数据为空——sendBeacon Content-Type 不兼容
- **日期**：2026-06-08
- **类型**：fix
- **摘要**：生产环境 admin 面板页面访问/点击数据始终为空。根因：portal.js 使用 navigator.sendBeacon() 发送 JSON 数据时，浏览器自动设置 Content-Type 为 text/plain，FastAPI 的 Pydantic 解析器要求 application/json，返回 422 静默失败（sendBeacon 无法读响应）。修复：analytics.py 端点改为手动 request.json() 解析 JSON，兼容任意 Content-Type。无效 payload 静默返回 200。
- **变更文件**：src/api/v1/analytics.py, tests/integration/test_admin_api.py
- **验证**：ruff ✅, pytest 113/113 ✅, text/plain 200 ✅, application/json 200 ✅

---

### [TASK-042] 生产部署：sendBeacon 埋点修复上线
- **日期**：2026-06-08
- **类型**：deploy
- **摘要**：SSH 部署到 43.134.110.192，commit `52e3540`→`6f906d2`（3 files）。sendBeacon Content-Type 修复上线——浏览器访问门户即自动上报埋点。部署记录：`.deploy/deployments.md` 部署 2026-06-08-003。
- **验证**：sendBeacon 模拟 200 ✅, 门户 200 ✅, OG 标签 ✅

---

### [TASK-043] 修复 3 个高优先级质量问题（质量报告 H1-H3）
- **日期**：2026-06-08
- **类型**：fix
- **摘要**：按 QUALITY-REPORT.md 修复 3 个高优问题。H1：download_records 加 `(downloaded_at, package_name)` 联合索引，加速 admin 下载趋势查询。H2：cos_storage.py 补充 14 个单元测试（禁用态 4 + 启用态 8 + Content-Disposition 1 + 异常 1），覆盖率 46%→100%。H3：http.py 补充 7 个单元测试（get_json 3 含重试 + download 4 含重试），覆盖率 49%→95%。
- **变更文件**：src/models/download.py（+索引）、tests/unit/test_cos_storage.py（新）、tests/unit/test_utils_http.py（新）
- **验证**：ruff ✅, pytest 133/133 ✅, cos_storage 100% ✅, http 95% ✅, 总覆盖率 83%→87%

---

### [TASK-044] 修复 M3：packages.py 和 update.py 覆盖率提升
- **日期**：2026-06-08
- **类型**：test
- **摘要**：按 QUALITY-REPORT.md M3 补充 packages.py 和 update.py 的测试覆盖。packages：新增 5 个集成测试（PackageManager add/list/delete/get_download_path/update roundtrip + HTTP 下载端点）。update：新增 3 个 HTTP 下载测试（macOS ARM 本地缓存 / Windows x64 本地缓存 / COS 302 路径），用 monkeypatch 模拟 COS 禁用覆盖降级路径。
- **变更文件**：tests/integration/test_api_packages.py, tests/integration/test_api_update.py
- **验证**：ruff ✅, pytest 141/141 ✅, packages 52%→57%, update 56%→75%, 总覆盖率 89%→90%

---

### [TASK-045] admin/router + packages COS 302 路径测试覆盖
- **日期**：2026-06-08
- **类型**：test
- **摘要**：补 admin/router 上传/删除测试（3 个）+ packages COS 302 mock 测试（1 个）。admin/router 覆盖率 64%→90%（+26pp）。packages COS 302 路径用 mock CosStorage 覆盖。总覆盖率 90%→92%，测试 141→145。
- **变更文件**：tests/integration/test_admin_packages.py, tests/integration/test_api_packages.py
- **验证**：ruff ✅, pytest 145/145 ✅, admin/router 90% ✅, 总覆盖率 92% ✅

---

### [TASK-046] 2.1.138.zip 改为 COS 优先下载
- **日期**：2026-06-08
- **类型**：feat
- **摘要**：Claude Desktop Windows 安装所需的 `2.1.138.zip` 原来直接走 `/static/files/` nginx 静态文件（新加坡服务器，国内 29KB/s），改为 COS 广州优先 302 跳转。新增 `/api/v1/files/{filename}` 端点（COS 命中→302 广州；COS 未命中→302 降级到 `/static/files/` nginx sendfile）。上传 COS key=`files/2.1.138.zip` 含 Content-Disposition 元数据。guide.html 下载链接更新。
- **变更文件**：src/api/v1/files.py（新）, src/api/router.py, src/portal/templates/guide.html
- **验证**：ruff ✅, pytest 145/145 ✅, COS 302 ✅, 不安全文件名 404 ✅, COS miss 降级 ✅

---

### [TASK-047] 生产部署：2.1.138.zip COS 优先下载 + Stop hook 修复
- **日期**：2026-06-08
- **类型**：deploy
- **摘要**：SSH 部署到 43.134.110.192，commit `24af2eb`→`e41b611`（4 files, +59/-1）。部署内容：①新增 `/api/v1/files/{filename}` COS 302 优先下载端点 ② guide.html zip 下载链接更新 ③ Stop hook `task-history.md` 已更新检查防死循环。验证全部 5 端点 200。
- **变更文件**：src/api/v1/files.py（新）, src/api/router.py, src/portal/templates/guide.html
- **验证**：files 302 COS → 200 ✅, 门户/指南/下载/版本API 200 ✅
- **部署记录**：`.deploy/deployments.md` 部署 2026-06-08-004

---

### [TASK-048] 生产部署：指南新增 Codex 中文 FAQ
- **日期**：2026-06-08
- **类型**：deploy
- **摘要**：SSH 部署到 43.134.110.192，commit `e41b611`→`40d7955`（2 files, +11）。指南页 FAQ 新增"Codex 说英文看不懂怎么办？"——教用户在项目根目录创建 AGENTS.md 让 Codex 默认用中文回复。
- **变更文件**：src/portal/templates/guide.html
- **验证**：生产 guide 页面 "Codex 说英文看不懂怎么办？" ✅
- **部署记录**：`.deploy/deployments.md` 部署 2026-06-08-005

---

### [TASK-049] COS 下载/上传脚本拆分
- **日期**：2026-06-11
- **类型**：feat
- **摘要**：将原来的 `upload-codex-switch-to-cos.sh`（下载+上传一体化）拆分为两个独立脚本：
  1. **`scripts/download-latest-release.sh`**：从 GitHub Releases 自动检测最新版本（或指定版本），下载全部 4 个平台文件（macOS ARM64/x64、Windows ARM64/x64），以原始 GitHub 文件名保存到 `data/codex-switch/{version}/`，并自动创建简化名称副本供本地服务缓存使用。支持 `--dry-run` 预览、`--local-cache` 显式创建简化名副本。
  2. **`scripts/upload-to-cos.sh`**：上传三类 COS 资源——①Codex Switch 发布文件（自动从 GitHub API 解析原始文件名→COS key `codex-switch/{ver}/{original_name}`）；②桌面应用安装包（从 `data/packages/registry.json` 读取，COS key 为确定性格式 `packages/{name}/latest/{plat}-{arch}.{ext}`）；③静态文件 `data/files/*`（如 `2.1.138.zip`，COS key=`files/{filename}`）。所有上传均设置 Content-Disposition 元数据，支持 `--dry-run`/`--force`/分类选择（`--codex-switch`/`--packages`/`--files`/`--all`），已存在的 COS 对象默认跳过。
  3. 旧 `scripts/upload-codex-switch-to-cos.sh` 保留向后兼容，顶部添加指向新脚本的迁移提示。
- **变更文件**：scripts/download-latest-release.sh（新）、scripts/upload-to-cos.sh（新）、scripts/upload-codex-switch-to-cos.sh（改）
- **验证**：bash syntax check ✅, download --dry-run 检测 v1.5.4 4 文件 ✅, upload --dry-run 全部 8 文件（4 Codex Switch + 4 桌面包）COS key 正确 ✅
- **注意事项**：下载脚本默认保存原始 GitHub 文件名，上传脚本通过 GitHub API 自动映射简化名→原始名。桌面包的 `original_filename` 来自 registry.json。静态文件目录 `data/files/` 需手动创建。

---

### [TASK-050] electron-updater generic provider 支持
- **日期**：2026-06-12
- **类型**：feat
- **摘要**：按设计规格 `docs/superpowers/specs/2026-06-11-electron-updater-support-design.md` 实现 codex-switch-server 对 electron-updater generic provider 的完整支持。新建独立 `/api/v1/updates/` 路由组（3 端点）+ UpdateFeedService，与现有 `/api/v1/update/` 完全隔离。
  1. **新建 `src/services/update_feed.py`**：`UpdateFeedService` 类 — `get_latest_yml()` 5 分钟内存缓存获取 latest-mac.yml/latest.yml 原文、`find_asset_by_filename()` 按原始 GitHub asset 名查找、`download_asset_to_cache()` 按原始文件名缓存、模块级 `_parse_filename_to_cache_key()` 解析 GitHub asset 名→(version, platform, arch, file_type)
  2. **新建 `src/api/v1/updates.py`**：3 个端点 — `GET /latest-mac.yml`（返回 text/yaml）、`GET /latest.yml`（同上）、`GET /{filename}`（三级降级：COS 302 → 本地 X-Accel-Redirect → GitHub 兜底下载，安全校验拒绝 `..` 和非允许字符）
  3. **修改 `src/models/download.py`**：`DownloadRecord` 新增 `source` 字段（String(32), default=""），区分门户下载 vs electron-updater 自动更新
  4. **修改 `src/services/release_sync.py`**：`get_download_path()` 扩展名列表加 zip/blockmap；`download_and_cache()` 新增 `original_name` 可选参数；`record_download()` 新增 `source` 参数
  5. **修改 `src/api/v1/router.py`**：注册 `updates_router`（prefix="/updates"）
  6. **测试**：37 个新测试（17 单元 + 10 文件名解析 + 10 集成），覆盖率全端点 + 文件名解析 + 缓存/错误/安全路径
- **变更文件**：src/services/update_feed.py（新）、src/api/v1/updates.py（新）、src/models/download.py（改）、src/services/release_sync.py（改）、src/api/v1/router.py（改）、tests/unit/test_update_feed.py（新）、tests/integration/test_api_updates.py（新）
- **验证**：ruff ✅, ruff format ✅, pytest 182/182 ✅（145 旧 + 37 新）
- **注意事项**：与现有 `/api/v1/update/` 完全隔离。首次部署后 yml 第一次请求需从 GitHub 下载（1-2s），后续 5 分钟内存缓存（毫秒级）。COS 需存在对应版本的 release 文件才能走快速链路。`_detect_platform()` 过滤逻辑保持不变（服务于下载页展示）。

---

### [TASK-051] Tier 1 安全加固方案设计
- **日期**：2026-06-12
- **类型**：design
- **摘要**：编写 `docs/superpowers/specs/2026-06-12-security-hardening-tier1.md` 安全加固方案。针对下载端点完全公开的风险面，设计 4 项零成本措施：①IP 速率限制（滑动窗口内存计数器，per-IP + 全局）②SHA256 校验和透传（服务端下载时计算+DB 存储+API 返回）③GitHub 兜底下载文件大小上限（防磁盘耗尽）④User-Agent 分类标记（区分真实客户端 vs 脚本，不拒绝只标记）。每项措施含实现要点、配置项、测试清单、影响评估。总代码量 <100 行，0 新依赖。
- **变更文件**：docs/superpowers/specs/2026-06-12-security-hardening-tier1.md（新）
- **验证**：方案 Review 中
- **注意事项**：明确排除 Redis/分布式限速、下载签名 URL、客户端密钥认证等重型方案。限速不应用于 yml 端点和门户页面访问。

---

### [TASK-052] 遥测优化：去重白名单 + 聚合计数 + 自动清理
- **日期**：2026-06-12
- **类型**：feat
- **摘要**：按 `docs/superpowers/specs/2026-06-12-telemetry-optimization.md` 实施服务端三项优化：
  1. **措施①（schema）**：`TelemetryEventIn` 新增 `count`/`period_start`/`period_end` 可选字段，向后兼容（默认 count=1）。count>1 时存入 properties，count=0 拒绝写入。
  2. **措施②（去重白名单）**：`_DEDUP_TYPES = {"app_start", "proxy_start", "proxy_error", "update_check"}`，model_call/app_close/proxy_stop 跳过 exact dedup 查询。
  3. **措施③（自动清理）**：lifespan 启动后台 asyncio task，每小时清理 telemetry_events/page_events 超 30 天、download_records 超 90 天的记录。
  4. **测试**：+8 测试（5 单元：model_call 去重跳过/count 存储/零计数值拒绝/默认值/无去重；3 集成：聚合计数 API/去重跳过 API/向后兼容 API），190 total passed。
  5. **部署**：生产冒烟全部通过（count 聚合 ✅、向后兼容 ✅、model_call 二次同事件均 accepted ✅）
- **变更文件**：src/schemas/telemetry.py（改）、src/services/telemetry.py（改）、src/main.py（改）、tests/unit/test_telemetry_service.py（改）、tests/integration/test_api_telemetry.py（改）、docs/superpowers/specs/2026-06-12-telemetry-optimization.md（新）
- **验证**：ruff ✅, ruff format ✅, pytest 190/190 ✅, 生产冒烟 4/4 ✅
- **注意事项**：客户端改造（措施① client-side aggregation）待客户端配合实施。当前服务端已支持 count 字段，老客户端不传 count 走原逻辑不受影响。

---

### [TASK-053] Admin App Tab 重构 — 模型调用独立展示 + 门户PV移回Server Tab
- **日期**：2026-06-13
- **类型**：feat
- **摘要**：按 `docs/superpowers/specs/2026-06-13-admin-app-tab-redesign.md` 重构运营后台 App 遥测 Tab：
  1. **门户 PV 移入 Server Tab**：将"累计页面访问"卡片从 App Tab 移到 Server Tab 第 5 卡片位，改名"门户 PV（累计）"，数据来源为 `page-stats?range_days=365` API。
  2. **功能使用分布拆分**：model_call 独立为"模型调用活跃度"柱状图（展示今日真实调用量 `SUM(count)`），配置操作独立为横向柱状图（排除 model_call，7 种事件类型）。
  3. **事件趋势加筛选**：全部 / 仅功能操作 / 仅模型调用 三个按钮切换。
  4. **新增 model_call_total**：`TelemetryStats` 新增字段，`get_stats()` 用 `SUM(json_extract(properties, '$.count'))` 计算今日真实调用量。
  5. **测试**：pytest 190/190 ✅，本地渲染验证全部卡片和图表正常。
- **变更文件**：src/schemas/telemetry.py（改）、src/services/telemetry.py（改）、src/admin/router.py（改）、src/admin/templates/dashboard.html（改）
- **验证**：ruff ✅, ruff format ✅, pytest 190/190 ✅, 本地渲染门户PV卡片 ✅/模型调用卡片 ✅/配置操作图表 ✅

---

### [TASK-054] 下载页重构：Linux 移除 + Windows/macOS 双卡并排
- **日期**：2026-06-13
- **类型**：feat
- **摘要**：按 `docs/superpowers/specs/2026-06-13-operations-optimization.md` 措施②重构下载页：
  1. **移除 Linux Tab**：30 天下载量为 0，API 保留但前端不展示
  2. **移除段控制器（Tab 切换）**：不再需要点击切换平台
  3. **双卡并排布局**：Windows 和 macOS 两个卡片左右并排显示，零交互直达下载
  4. **主架构按钮 + 次要链接**：每个卡片主按钮展示主力架构（Win x64 / Mac ARM64），次要架构用小字链接
  5. **动态版本信息**：JS fetch `/api/v1/update/latest` 自动填充版本号、文件大小、发布日期
- **变更文件**：src/portal/templates/download.html（重写）、src/static/css/apple.css（+双卡 CSS）、src/portal/templates/base.html（版本号）
- **验证**：ruff ✅, pytest 190/190 ✅, 本地渲染 dl-card 33 个 ✅, segment-control 0 ✅, Linux 0 ✅

---

### [TASK-055] Hero 双平台按钮 + 下载页品牌化 + install_source
- **日期**：2026-06-14
- **类型**：feat
- **摘要**：按 `docs/superpowers/specs/2026-06-13-operations-optimization.md` 执行三项运营优化：
  1. **措施① Hero 双平台按钮**：单 CTA→双按钮，主按钮"⊞ Windows 安装指南"（Microsoft 窗格 SVG, `/guide?platform=windows`），次按钮" macOS 安装指南"（Apple 咬苹果 SVG, `/guide?platform=macos`），次按钮小一号字体
  2. **措施⑤ install_source**：`TelemetryPayload` 新增字段，存入 properties 供后续安装成功率分析
- **变更文件**：src/portal/templates/index.html（改）、src/portal/templates/base.html（版本号）、src/schemas/telemetry.py（改）、src/services/telemetry.py（改）
- **验证**：ruff ✅, pytest 190/190 ✅, Hero 双按钮+SVG ✅, install_source accepted ✅

---

### [TASK-056] 品牌图标统一：emoji → Codex/Claude SVG logo
- **日期**：2026-06-14
- **类型**：design
- **摘要**：将首页安装指南入口、下载安装包、功能卡片（多模型支持）、指南选择卡片的 emoji 图标全部替换为品牌 SVG：
  - Codex（OpenAI）：六边形 SVG，色值 #10a37f
  - Claude（Anthropic）：圆形+弧线 SVG，色值 #D97757
  - 多模型支持 🧠 → Claude SVG
  - 共替换 10 处图标
- **变更文件**：src/portal/templates/index.html（改）、src/portal/templates/guide.html（改）、src/portal/templates/base.html（版本号）
- **验证**：ruff ✅, pytest 190/190 ✅

---

### [TASK-058] 操作系统洞察
- **日期**：2026-06-14
- **类型**：feat
- **摘要**：按 `docs/superpowers/specs/2026-06-14-os-insights.md` 实现操作系统洞察：
  1. **OS 分布卡片**：Mac / Windows 各一张统计卡片，Apple/Microsoft SVG 图标，显示用户数+占比
  2. **版本×OS 交叉表**：每个版本在 Mac/Windows 上的部署数
  3. 数据源：`app_start` 事件的 `platform` 字段（darwin/win32），30 天窗口
  4. 位置：Client 运营 Tab 版本洞察下方
- **变更文件**：src/schemas/telemetry.py（改）、src/services/telemetry.py（改）、src/admin/templates/dashboard.html（改）
- **验证**：ruff ✅, pytest 190/190 ✅

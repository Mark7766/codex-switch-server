# 📝 codex-switch-server — 技术决策日志 (ADR)

> **用途**：记录项目中的每个重要技术决策，使决策可追溯、可理解。
> 格式参考 [Architecture Decision Records](https://adr.github.io/)。

---

## ADR 模板

复制以下模板记录新决策：

```markdown
### ADR-{编号}: {标题}

- **日期**：YYYY-MM-DD
- **状态**：✅ 已采纳 / ❌ 已废弃 / 🔄 已替代
- **决策者**：{人员/Agent}

#### 背景
> 为什么需要做这个决策？遇到了什么问题？

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 方案 A | ... | ... |
| 方案 B | ... | ... |

#### 决策
> 选择了哪个方案？

#### 理由
> 为什么选这个方案？

#### 影响
> 这个决策会影响什么？
```

---

## 决策记录

### ADR-001: 选择 Python + FastAPI + SQLite 作为技术栈

- **日期**：2026-06-05
- **状态**：✅ 已采纳
- **决策者**：wangliang

#### 背景
> 需要为 codex-switch 构建配套服务端。核心需求：1) 提供版本更新下载镜像 2) 托管桌面应用和 CLI 工具安装包 3) 运营后台 4) 遥测数据收集。只有一个维护者，要求极简可维护。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| Node.js + Express | 与 codex-switch (TypeScript/Electron) 技术栈一致 | node_modules 臃肿，部署复杂度高，异步错误处理不如 Python 直观 |
| Python + FastAPI + SQLite | 单文件启动、零配置数据库、自动 API 文档、异步支持好 | 与客户端技术栈不一致（但无代码共享需求） |

#### 决策
> 选择 **Python + FastAPI + SQLite**。

#### 理由
> 1) 极简部署：单文件 uvicorn 启动，SQLite 零配置 2) FastAPI 自动生成 API 文档，开发效率高 3) 一个人维护 Python 后端比 Node.js 更省心智负担 4) 腾讯云轻量服务器原生支持 Python 部署

#### 影响
> 整个项目技术选型。后续所有开发都围绕 Python/FastAPI/SQLite 进行。

---

### ADR-002: 门户采用 Apple 设计哲学 + 服务器渲染

- **日期**：2026-06-05
- **状态**：✅ 已采纳
- **决策者**：wangliang

#### 背景
> codex-switch-server 需要一个面向用户的产品门户，用于展示产品、引导下载、提供使用指南。门户是用户对 codex-switch 的第一印象，设计质量直接影响用户信任度和下载转化率。目前仅一人维护，不能引入复杂的前端技术栈。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| React/Vue SPA + 组件库 | 组件丰富、交互灵活 | 构建工具链复杂、首屏慢、需要 SSR 额外配置、维护成本高 |
| 静态网站生成器（Hugo/Next.js） | SEO 友好、性能好 | 需要额外学习、部署流水线复杂、动态内容（版本号）需要构建时注入 |
| Jinja2 服务器渲染 + Apple 风格 CSS | 零构建工具、动态内容天然支持、部署即代码、一人可掌控全栈 | 交互不如 SPA 丰富（但门户场景不需要复杂交互） |

#### 决策
> 选择 **Jinja2 服务器渲染 + 纯手写 Apple 风格 CSS + 极简 vanilla JS**。

#### 理由
> 1) 门户的主要功能是展示 + 下载，不需要复杂的前端状态管理
> 2) 服务器渲染天然 SEO 友好、首屏快、对低端设备友好
> 3) 零前端构建工具链——写 HTML/CSS 直接刷新即可看到效果
> 4) Apple 设计风格的精髓恰恰是"少即是多"——简单页面反而最适合用简单的技术实现
> 5) 动态内容（最新版本号、下载次数）在服务器端直接渲染，无需额外 API 调用
> 6) 一个人可以掌控从前端到后端的全部代码

#### 影响
> - 前端不引入任何 npm 依赖或构建工具
> - CSS 使用自定义属性（CSS Variables）管理设计 Token
> - JS 仅用于少量增强交互（导航毛玻璃效果、下载反馈），优先使用 HTML 原生能力（details/summary、锚点）
> - Chart.js 从 CDN 加载，仅 admin 页面使用，不影响门户性能
> - 所有样式和交互逻辑在一人之力所能及的范围内

---

### ADR-003: 采用分层架构（路由 → 服务 → 数据）

- **日期**：2026-06-05
- **状态**：✅ 已采纳
- **决策者**：wangliang

#### 背景
> 项目需要清晰的代码组织方式，使得一个人维护时也能快速定位和修改代码。不做过度设计，但要避免路由函数里堆砌数据库操作——后续改逻辑时需要在大量路由代码里搜索。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 路由直写（FastAPI 直接在路由函数里操作 DB） | 代码量少、快速原型 | 路由和业务耦合，后续改逻辑要跨多个文件搜索；难以对业务逻辑单独测试 |
| 严格分层（路由 → 服务 → 数据） | 职责清晰、可单独测试业务逻辑、一人维护时修改定位快 | 多一层抽象，文件数量增加 |
| DDD（领域驱动设计） | 大型项目的最佳组织方式 | 抽象过重，不适合一人维护的中小型项目 |

#### 决策
> 选择 **三相分层：路由层 → 服务层 → 数据层（models/schemas）**。

#### 理由
> 1) 路由只做三件事：`解析参数 → 调用 service → 返回响应`，代码极其简洁
> 2) 所有业务规则集中在 service 层，修改一个功能只需要打开一个 service 文件
> 3) Service 可以被测试直接调用（注入 mock 的 db session 或 http client），不需要通过 HTTP
> 4) 贫血模型：ORM Model 只有字段定义，不含业务方法——避免"上帝对象"
> 5) 这个分层是 FastAPI 社区验证过的最佳实践，不是过度设计
> 6) 文件数量增加但每个文件职责单一，一人维护时反而更容易找代码

---

### ADR-004: Docker 单容器 + Nginx SSL 终止（参照 ajepro 模式）

- **日期**：2026-06-05
- **状态**：✅ 已采纳
- **决策者**：wangliang

#### 背景
> codex-switch-server 即将部署到已运行 ajepro 的生产服务器 (43.134.110.192)。已有 SSL 证书 `codexswtich.cloud_nginx.zip`（Nginx 格式），域名 `www.codexswtich.cloud`。服务器内存仅 1.9GB，已运行 ollama 和 ss-server。ajepro 使用 Nginx+Supervisor 容器模式已稳定运行 2 个月，被证明在低配服务器上可靠。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| uvicorn 直接 serve + Cloud CDN HTTPS | 最简单、无额外进程 | 无现成 SSL 证书方案，生产环境调试风险大 |
| Nginx + uvicorn 双容器 | 进程隔离好 | 两套容器配置、网络通信、资源占用多 |
| Nginx + uvicorn + Supervisor 单容器 | 与 ajepro 模式一致、已验证稳定、证书挂载简单 | 容器内双进程，需要 Supervisor 管理 |

#### 决策
> 选择 **Nginx + uvicorn + Supervisor 单容器**，完全参照 ajepro 已验证的部署模式。

#### 理由
> 1) ajepro 同一服务器上已用此模式稳定运行 2 个月，证明在 1.9GB 内存下可靠
> 2) SSL 证书已是 Nginx 格式（`_bundle.crt` + `.key`），nginx.conf 直接引用，零转换
> 3) Nginx 的 `sendfile` 零拷贝大文件传输比 uvicorn 直接 serve 更省内存
> 4) 证书更新只需替换宿主机 certs/ 文件 + `nginx -s reload`，无需重启容器
> 5) 单容器管理比双容器简单：`docker compose up/down/logs` 一条命令
> 6) ajepro 停服后，codex-switch-server 直接接管 80/443 端口，切换无缝

#### 影响
> - 需要编写 `docker/nginx.conf`、`docker/supervisord.conf`、`docker/entrypoint.sh`
> - 容器内运行 Nginx + uvicorn 两个进程，Supervisor 管理生命周期
> - certs/ 目录以只读方式挂载到容器 `/etc/nginx/ssl`
> - 部署路径 `/home/lighthouse/codex-switch-server/`，与 ajepro 同级

#### 影响
> - `src/api/` 目录下的代码不超过 50 行/文件，几乎全是路由注册 + 参数声明
> - `src/services/` 是代码量最大的目录，每个 service 文件对应一个业务领域
> - `src/models/` 和 `src/schemas/` 是纯数据定义，一眼看清数据结构
> - 测试分为三层：单元测试测 service（mock DB）、集成测试测路由（真实 SQLite）、E2E 测试测完整场景

---

### ADR-005: Codex Switch 下载改为实时 GitHub + 首次代理缓存

- **日期**：2026-06-06
- **状态**：✅ 已采纳
- **决策者**：wangliang + Claude

#### 背景
> 原有下载流程依赖管理员手动触发 GitHub Release 同步，将 release 元数据和文件缓存到 SQLite + 本地文件系统。流程存在以下问题：
> 1) 管理员忘记同步则用户看到过时版本或"加载中..."
> 2) 同步过程耗时（需下载 4 个平台的大文件），HTTP 请求易超时
> 3) release 表与 GitHub 实际状态可能不一致
> 4) DB 存储 release 元数据增加了不必要的持久化复杂性
>
> 用户明确要求："通过访问 GitHub 地址，把最新版本显示出来，下载时如果没有缓存就先去 GitHub 下载再传给用户"。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 保持原方案（DB + 手动同步） | 离线可用、下载即秒下 | 需手动触发、可能过时、同步超时风险、DB 元数据维护成本 |
| 实时 GitHub + 首次代理缓存 | 永远最新、零维护、首次下载后同样秒下 | 首次下载慢（需 GitHub 下载 + 本地缓存）、依赖 GitHub 可用性 |

#### 决策
> 选择 **实时 GitHub + 首次代理缓存**。

#### 理由
> 1) 版本信息 5 分钟内存缓存，页面加载不每次打 GitHub API
> 2) 用户首次下载时服务端从 GitHub 拉取并缓存，后续下载秒下（实测 92MB 从 98s → 0.78s）
> 3) 不需要手动同步，零运维成本
> 4) 释放 SQLite releases 表的维护负担（仅保留 download_records 统计用）
> 5) 使用 GitHub Fine-grained Personal Access Token 突破 API 限速

#### 影响
> - `ReleaseSyncService` 完全重写：移除 DB 依赖的 `sync_from_github`/`_purge_all_releases`/`get_releases`，新增 `get_latest_from_github`（内存缓存）/`download_and_cache`/`get_github_asset_info`
> - `/api/v1/update/latest` 新端点替代 `/api/v1/update/releases`
> - 下载端点改为 cache-or-proxy 模式：检查本地缓存 → 从 GitHub 下载并缓存 → 流式返回
> - 管理后台移除"同步 Release"按钮，改为提示"版本信息实时取自 GitHub"
> - `_detect_platform` 加强过滤：拒绝 blockmap/yml/zip、Windows exe 必须显式标注架构后缀

---

### ADR-006: 使用指南改为三步向导交互

- **日期**：2026-06-06
- **状态**：✅ 已采纳
- **决策者**：wangliang

#### 背景
> 使用指南经历了三次迭代：侧边栏+长内容 → 渐进式选择面板 → 最终的三步向导。用户反馈"设计的太差了"，要求从用户角度出发：一次只做一件事，选完工具和平台后展示对应安装步骤。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 侧边栏+全内容 | 所有信息一页可见 | 信息过载，用户不知从何开始 |
| 渐进式面板（选工具→选平台→显示） | 分流明确 | 仍需滚动大量内容 |
| 三步向导（选工具→选平台→6步线性指南） | 一次一个决策，Apple 风格，零学习成本 | JS 依赖，无 JS 降级不可用 |

#### 决策
> 选择 **三步向导交互**，纯前端 JS 控制显示/隐藏，无页面跳转。

#### 理由
> 1) 用户明确要求"先选工具、再选平台、然后看指南"，符合 Apple HIG 的渐进式披露
> 2) 6 步安装指南覆盖完整流程：API Key → 下载工具 → 安装工具 → 下载 Codex Switch → 配置 → 验证
> 3) 支持返回重新选择，灵活切换
> 4) 截图按场景动态加载，不存在的图片自动隐藏，不破坏布局

#### 影响
> - `guide.html` 完全重写为纯 JS 驱动，不再依赖侧边栏和锚点
> - 截图按场景分 10 张（通用 3 + Codex 3 + Claude 3 + macOS 错误 1）

---

### ADR-007: 安装包管理固化为 4 个固定槽位

- **日期**：2026-06-06
- **状态**：✅ 已采纳
- **决策者**：wangliang

#### 背景
> 原 admin/packages 页面使用自由表单（name/version/platform/arch 自由填写）和通用表格。用户反馈"设计太乱"，要求简化为 4 个固定位置：Codex/Claude × macOS/Windows。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 自由表单+表格 | 灵活，支持任意包 | 复杂，易出错（空格、版本号混乱） |
| 4 个固定卡片 | 极简，name/platform/arch 隐藏固定，只需选文件 | 不支持扩展新包类型 |

#### 决策
> 选择 **4 个固定卡片**，每个卡片包含固定隐藏字段（name/display_name/platform/arch/version），用户只需选择文件上传。重复上传自动覆盖。

#### 理由
> 1) 业务场景固定：只需要 Codex Desktop 和 Claude Desktop 各两个平台版本
> 2) 消除用户输入错误（之前在 name 中不小心输入空格导致 404）
> 3) 隐藏字段让上传操作极简：选文件 → 点上传
> 4) 版本号固定为 "latest"，减少概念负担

#### 影响
> - `admin/templates/packages.html` 重写为 2×2 卡片布局
> - 首页和指南下载按钮按 `selPlat` 动态匹配对应平台的包

---

### ADR-008: Stop hook 使用 asyncRewake 强制 PDCA Act 阶段执行

- **日期**：2026-06-07
- **状态**：✅ 已采纳
- **决策者**：wangliang + Claude

#### 背景
> ai-coding-ok 的 Act 阶段（更新 task-history / decisions-log / project-memory）频繁被遗漏。尽管配置了 SessionStart、UserPromptSubmit、PreToolUse、Stop 四层 hook，均为 `echo` 文本提醒，无强制力。AI Agent 在完成任务后直接报告结果，忽略了记忆文件更新。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 继续依赖文本提醒 | 简单 | 已被证明无效 |
| PreToolUse 阻断所有 Edit/Write | 强制 Plan | 过于激进，每次编辑都打断 |
| Stop hook 使用 asyncRewake + exit 2 | 只在回复结束时阻断，精确有力 | 每次回复都触发，略微增加延迟 |

#### 决策
> **Stop hook 使用 `asyncRewake: true` + `exit 2`**。每次 Agent 准备结束回复时，hook 强制唤醒并打印 PDCA ACT CHECK 提醒。Agent 必须确认记忆文件已更新才能最终结束。

#### 理由
> 1) `asyncRewake` 是 Claude Code hooks 框架中唯一能强制阻断 Agent 回复流程的机制
> 2) Stop 事件恰好在回复结束前触发，不影响正常编码流程
> 3) exit code 2 触发"blocking error"语义，hook 输出作为 system-reminder 注入上下文

#### 影响
> - `.claude/settings.local.json` Stop hook 配置修改
> - 每次回复结束前都会强制检查记忆更新状态

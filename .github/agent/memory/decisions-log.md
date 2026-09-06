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

---

### ADR-009: 使用腾讯云 COS 广州地域加速国内下载

- **日期**：2026-06-07
- **状态**：✅ 已采纳
- **决策者**：wangliang

#### 背景
> 生产服务器位于腾讯云新加坡，国内用户下载速度仅 29KB/s（74MB 需 43 分钟）。经实测，腾讯云 COS 广州地域公网下载达 2MB/s（70 倍提速）。需要在不影响新加坡服务器正常功能的前提下，将下载流量分流到 COS。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 腾讯云 CDN | 自动就近加速 | 需要备案域名，当前域名未备案 |
| 腾讯云 COS 广州 | 2MB/s，无需备案，`cos-python-sdk-v5` SDK 简单 | 文件需手动/自动上传 |
| GitHub Fastly CDN 302 | 免费，零配置 | 国内 GitHub 访问不稳定 |
| ghproxy 代理 | 免费 | 服务器在法国，同样慢 |

#### 决策
> 选择 **COS 广州 + 新加坡本地双链路降级**。COS 存储桶 `codex-switch-1259344349`（ap-guangzhou，公有读私有写）。

#### 理由
> 1) COS 广州国内下载 2MB/s（实测），无需备案
> 2) 两级下载路由：COS 302 优先 → 本地 nginx sendfile 降级 → GitHub 兜底
> 3) Codex Switch 安装包由部署脚本 `upload-codex-switch-to-cos.sh` 每次发布时一次性上传
> 4) 桌面应用安装包在 admin 上传时同步上传 COS（保留原始文件名）
> 5) COS 不可用时自动降级到新加坡本地文件，不影响服务可用性
> 6) 成本极低：存储 0.118 元/GB/月 + 下载流量 0.5 元/GB

#### 影响
> - 新增 `src/utils/cos_storage.py`（COS 客户端封装，未配自动降级）
> - `update.py` / `packages.py` 下载端点加 COS 检查 → 302 跳转
> - `admin/router.py` 上传端点加 COS 同步上传
> - `scripts/upload-codex-switch-to-cos.sh` 部署脚本
> - `.env` 新增 `COS_SECRET_ID/COS_SECRET_KEY/COS_BUCKET/COS_REGION`

---

### ADR-010: COS 包下载 key 采用确定性格式

- **日期**：2026-06-07
- **状态**：✅ 已采纳
- **决策者**：wangliang

#### 背景
> 桌面应用安装包的 COS key 原格式为 `packages/{name}/latest/{original_filename}`，依赖 registry 中的 `original_filename` 字段。旧 registry 条目无此字段会导致 COS 整段跳过（走本地降级）。同时 302 重定向的 `Content-Disposition` 无法传递到 COS 实际下载，文件名来自 URL 路径。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 保持 original_filename 作为 key | COS URL 自带友好文件名 | 依赖 registry 字段；旧条目无此字段则 COS 失效 |
| 确定性格式 `{name}/latest/{platform}-{arch}.{ext}` | 不依赖 registry 字段；上传和下载 key 天然一致 | COS URL 文件名不友好（如 `macos-arm64.dmg`） |
| 确定性格式 + COS Content-Disposition 元数据 | key 确定；文件名通过 COS 对象元数据保留友好名 | 上传时需额外设置元数据 |

#### 决策
> 选择 **确定性格式 + COS Content-Disposition 元数据**。COS key = `packages/{name}/latest/{platform}-{arch}.{ext}`，上传时设置 `ContentDisposition` 为原始文件名。

#### 理由
> 1) COS key 完全由程序可控的字段构成，不再依赖 registry 中可能缺失的 `original_filename`
> 2) `file_type`（扩展名）在 registry 中总是存在，保证 key 始终可构造
> 3) 友好文件名通过 COS 对象元数据 `ContentDisposition` 保留，浏览器下载时仍显示正确文件名
> 4) Codex Switch 的 COS key（`codex-switch/{ver}/{filename}`）不受影响——其文件名来自 GitHub asset，总是存在

#### 影响
> - `cos_storage.py`: `put()` 加 `content_disposition` 参数
> - `packages.py`: COS key 格式变更，移除 `original_filename` 门控
> - `admin/router.py`: COS 上传 key 与下载对齐
> - `upload-codex-switch-to-cos.sh`: 同步加 Content-Disposition
> - 旧 COS 对象（`packages/{name}/latest/{原始文件名}`）变成孤儿，需重新上传

---

### ADR-011: electron-updater 支持采用独立路由组 + 独立 service

- **日期**：2026-06-12
- **状态**：✅ 已采纳
- **决策者**：wangliang

#### 背景
> codex-switch 客户端使用 `electron-updater` v6.8.3 generic provider 进行自动更新。当前客户端直接拉取 GitHub Releases，需要改为通过 server 代理，以利用 COS 广州加速和本地缓存。electron-updater 要求的 URL 格式（`latest-mac.yml`、`latest.yml`、`{原始 asset 名}`）与现有 `/api/v1/update/` 路径模式（`{plat}-{arch}.{ext}` 简化名）不兼容。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 扩展现有 `update.py` | 改动文件少 | URL 语义混乱，路径模式不兼容，需大量条件分支，测试复杂度高 |
| 新建独立 `/api/v1/updates/` + 独立 service | 完全隔离，互不干扰，各自独立演进 | 新增文件，少量代码重复（`_send_file`、`record_download`） |

#### 决策
> 选择 **新建独立路由组 + 独立 service**。

#### 理由
> 1) electron-updater 的 URL 语义与现有 API 完全不同（yml 原文 vs JSON、原始文件名 vs 简化名）
> 2) 独立路由组 URL 清晰：`/api/v1/updates/latest-mac.yml`、`/api/v1/updates/{filename}`
> 3) 独立 service 可单独测试、单独缓存，不影响现有 ReleaseSyncService
> 4) 下载链路复用 COS 广州 + 本地缓存 + GitHub 兜底三级降级，与现有 update.py 保持一致
> 5) `DownloadRecord.source` 字段区分来源（'' = 门户, 'electron-updater' = 自动更新），不破坏现有统计

#### 影响
> - 新增 `src/services/update_feed.py`（UpdateFeedService + `_parse_filename_to_cache_key()`）
> - 新增 `src/api/v1/updates.py`（3 端点）
> - `src/models/download.py` 新增 `source` 列
> - `src/services/release_sync.py` 扩展：`get_download_path()` 加 zip/blockmap、`download_and_cache()` 加 `original_name` 参数、`record_download()` 加 `source` 参数
> - `_detect_platform()` 过滤逻辑保持不变（服务于下载页展示，不影响 electron-updater 链路）

---

### ADR-012: 数据库存 UTC，业务层统一用北京时间

- **日期**：2026-06-14
- **状态**：✅ 已采纳
- **决策者**：wangliang

#### 背景
> 运营后台的"今日"统计一直使用 UTC 0 点作为日期分界，导致北京时间凌晨 0-8 点的数据被归入前一天。用户看到"今日事件 0"直到早上 8 点才更新，体验很差。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| DB 存北京时间 | 查询简单，直接比较 | 跨时区扩展困难；Python SQLite 的 aware datetime 处理复杂 |
| DB 存 UTC，查询层转换 | 标准做法，DB 保持时区无关 | 每处查询都要转换 |
| DB 存 UTC naive，业务层用北京时间 helper | 简单统一，一处定义到处使用 | 非标准做法，需要 discipline |

#### 决策
> **DB 存储使用 UTC naive datetime，所有业务统计/查询/展示统一使用北京时间（UTC+8）**。

#### 理由
> 1) SQLite 对 aware datetime 支持有限，naive datetime 是现有约定
> 2) 用户全部在中国，没有多时区需求，北京时间是唯一需要的时区
> 3) `_beijing_now()` helper 统一所有服务的时间获取，一处修改全局生效
> 4) 展示层（timedelta +8h）与统计层（_beijing_now）一致，不矛盾

#### 影响
> - `src/services/telemetry.py`、`src/services/analytics.py`、`src/services/release_sync.py` 均使用 `_beijing_now()`
> - 新增功能时必须遵循此规范，不允许直接使用 `datetime.now()`
> - 入库时间（`created_at`）仍为 UTC naive datetime，不改变存储格式

---

### ADR-013: 离线插件包通过 COS 分发，复用现有 files 下载链路

- **日期**：2026-06-15
- **状态**：✅ 已采纳
- **决策者**：wangliang

#### 背景
> Codex Desktop 用户急需安装插件，但插件市场依赖境外资源，国内无法访问。提供一个 173 个插件的离线包（36MB tar.gz），通过 codex-switch-server 分发给 codex-switch 客户端，用户导入 Codex 完成安装。需要设计服务端 API。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 新增独立下载端点 `/api/v1/plugins/pack/download` | 语义清晰，可独立扩展 | 与 files 下载逻辑重复 |
| 复用 `/api/v1/files/codex-offline-pack.tar.gz` | 零代码 | 缺少元数据（版本/大小/插件数），客户端需要额外查询 |
| 元数据端点 + COS 302 下载（选定方案） | 元数据独立更新，下载复用 COS 链路 | 多一个端点 |

#### 决策
> `GET /api/v1/plugins/pack` 提供元数据（版本号/大小/插件数/描述），`GET /api/v1/plugins/pack/download` COS 302 下载，与现有 files/updates 下载链路一致。

#### 理由
> 1) 插件包版本独立于 codex-switch 版本，需要独立的元数据端点告知客户端版本
> 2) 下载链路复用已验证的 COS 广州 → nginx sendfile 三级降级
> 3) `update_highlights` 字段推动用户升级到支持插件功能的新版本

#### 影响
> - 新增 `src/api/v1/plugins.py`（2 端点）
> - `UpdateCheckResponse` 扩展 `update_highlights`
> - 离线包上传 COS `files/codex-offline-pack.tar.gz`，本地 `data/files/` 降级

---

### ADR-014: 本地缓存统一使用 GitHub 原始文件名

- **日期**：2026-06-23
- **状态**：✅ 已采纳
- **决策者**：wangliang + Claude

#### 背景
> `74dae31` 将 `StreamingResponse` 替换为 `X-Accel-Redirect`（nginx sendfile）后，下载文件名从正确的 GitHub 原始名（如 `Codex-Switch-Setup-1.15.0-win-x64.exe`）变为短缩写格式（`windows-x64.exe`）。根因有二：①`download_and_cache()` 未被传入 `original_name`，文件缓存为 `{platform}-{arch}.{ext}` 缩写格式；②`get_download_path()` 只搜索缩写格式。COS 层使用 `original_name` 做 key，与本地缓存命名不一致。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 改 `_send_file` 设 Content-Disposition | 改动最小 | 治标不治本，X-Accel-Redirect 后 Content-Disposition 不一定可靠 |
| 统一使用原始文件名 | 本地/COS 命名一致，Content-Disposition + 磁盘文件名 双重保险 | 需改 3 处代码，旧缩名缓存需兼容 |
| 回退到 StreamingResponse | 恢复旧行为 | 下载速度从 nginx sendfile 48MB/s 掉回 Python chunk 45KB/s |

#### 决策
> **统一使用 GitHub 原始 asset 文件名作为本地缓存 key**。

#### 理由
> 1) COS 已经用原始文件名，本地对齐可消除不一致
> 2) 即使 X-Accel-Redirect 丢失 Content-Disposition，磁盘上的文件名就是正确的
> 3) `get_download_path()` 增加目录扫描兜底，兼容旧缩名缓存文件
> 4) `get_latest_from_github()` 同时检查两种命名规范的 cached 状态，保证"已缓存"标记准确

#### 影响
> - `src/api/v1/update.py:74`: `download_and_cache` 传入 `original_name=filename`
> - `src/services/release_sync.py:get_download_path()`: 短格式查找后增加目录扫描
> - `src/services/release_sync.py:get_latest_from_github()`: cache key 改用 `original_name`，双向检查 cached
> - 旧缩名缓存（`data/codex-switch/{ver}/{plat}-{arch}.{ext}`）仍可被兜底扫描找到，无需手动迁移

---

### ADR-015: 网站技术支持采用"悬浮按钮 + 专用页面"双入口体系

- **日期**：2026-07-04
- **状态**：🔄 提案中（待 Review）
- **决策者**：wangliang + Claude

#### 背景
> codex-switch 客户端内置了微信交流群功能（`QaGroupModal.tsx`），但网站缺少对应的技术支持入口。用户在使用中遇到困难时没有渠道求助，需要为网站建立完整的技术支持体系。业内常规做法包括：纯页面入口、纯悬浮按钮、悬浮按钮+页面双入口。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 纯 `/support` 页面 + 导航/页脚链接 | 干净，零打扰 | 用户需要手动导航，即时求助场景不够便捷 |
| 仅悬浮按钮 + Modal | 即时可达，操作步骤最少 | 无 SEO 价值，无法被分享，功能扩展受限 |
| 悬浮按钮 + 专用页面双入口（选定方案） | 即时求助 + 信息汇总 + SEO 友好 + 4 条路径覆盖不同用户行为 | 新增文件稍多（1 页面 + 6 文件变更） |

#### 决策
> 选择 **"悬浮按钮 + 专用页面"双入口体系**。4 条用户路径：悬浮按钮 → Modal（即时扫码）、导航栏/页脚 → `/support` 页面（帮助资源汇总）、指南页底部 CTA（教程后自然引导）、直接访问 `/support`（搜索引擎/分享）。

#### 理由
> 1) 悬浮按钮捕获"即时求助"场景——遇到问题 → 点按钮 → 扫码进群，零跳转
> 2) 专用页面作为帮助信息汇总，可被搜索引擎索引、可被社交媒体分享
> 3) 导航栏和页脚提供发现入口，覆盖浏览探索型用户
> 4) 指南页底部 CTA 在教程完成后自然引导，覆盖"跟着教程走但遇到困难"的用户
> 5) Modal 在 `base.html` 全局注入，一次编写处处生效
> 6) 全部零外部依赖，纯 HTML+CSS+vanilla JS，符合项目前端极简约束
> 7) 二维码路径通过 `config.py` → `.env` → Jinja2 模板变量三级注入，与 ICP 备案号模式一致
> 8) 设计完全遵循 Apple HIG（毛玻璃按钮、18px 圆角卡片、微动画、内容驱动）

#### 影响
> - 新增 `src/portal/templates/support.html` 支持页面
> - 新增 `src/static/images/wechat-qr.png` 二维码图片（需管理员提供）
> - 修改 `base.html`：导航+页脚+悬浮按钮+Modal HTML
> - 修改 `guide.html`：底部 CTA 区块
> - 修改 `portal/router.py`：新增 `/support` 路由 + `support_qr_image` 全局变量注入
> - 修改 `config.py`：新增 `support_qr_image` 配置字段
> - 修改 `apple.css` / `portal.js`：新增样式和交互逻辑
> - 修改 `schemas/analytics.py`：新增 13 个埋点中文映射
> - 纯前端变更，对后端 API 和数据库零影响

---

### ADR-016: ai-working-ok 下载服务 — 本地缓存 + GitHub 兜底

- **日期**：2026-07-26
- **状态**：✅ 已采纳
- **决策者**：wangliang + Claude

#### 背景
> 用户新做了一个工程 ai-working-ok（https://github.com/Mark7766/ai-working-ok），需要在 codex-switch-server 网站上提供一个下载地址，始终可以下载到最新版本，同时也可以指定版本。服务器上如果没有缓存，就从 GitHub 下载后缓存，之后再从本地缓存下载。不使用 COS。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 静态文件直链 | 零代码 | 不能自动更新，每次 release 要手动上传 |
| 302 重定向到 GitHub | 零存储 | 国内访问不稳定，用户体验差 |
| 本地缓存 + GitHub 兜底（选定方案） | 首次后秒下，自动跟随最新版，无 COS 依赖 | 首次下载慢（需从 GitHub 拉取），需要 GitHub token |

#### 决策
> 选择 **本地缓存 + GitHub 兜底**。新增 `AiWorkingOkReleaseService` 统一管理：latest 版本有双层 TTL（内存 + 磁盘 releases.json），版本文件优先本地缓存，未命中则从 GitHub 下载并缓存。

#### 理由
> 1) 不需 COS — 需求明确不要 COS，本地文件系统够用
> 2) latest 端点有 TTL（默认 5 分钟，可配），避免每次请求打 GitHub API（有 rate limit）
> 3) 复用现有的 HttpClient（重试/限速）+ LocalStorage（文件存取）工具层
> 4) 路由复用 `/api/v1/packages/` 前缀，与现有包下载体系一致，无需新建路由组
> 5) 文件下载走 X-Accel-Redirect（nginx sendfile），与现有下载链路一致
> 6) 首页只需一个链接，零 UI 改动

#### 影响
> - 新增 `src/services/ai_working_ok_releases.py` 服务
> - `src/api/v1/packages.py` 新增 2 个路由（注册在参数化路由之前避免冲突）
> - `src/config.py` 新增 `AI_WORKING_OK_CACHE_TTL` 配置项
> - 缓存目录 `data/packages/ai-working-ok/`，含 `releases.json` 元数据文件
> - 首页 Hero 区域底部增加链接，改动一行 HTML
> - 不使用 COS、不需要数据库迁移

---

### ADR-017: electron-updater yml feed 改以 COS 为来源，GitHub 仅兜底

- **日期**：2026-09-06
- **状态**：✅ 已采纳
- **决策者**：wangliang + Claude

#### 背景
> 客户端（electron-updater，`updateMirror=server`）靠服务端 `/api/v1/updates/latest-mac.yml|latest.yml` 的 `version` 判断升级。原实现 `UpdateFeedService.get_latest_yml()` 每次 TTL 过期都实时从 GitHub release asset 下载 yml 字节；广州服务器连 github.com 下载域名不稳定（30s httpx 超时），失败时**静默回退进程内陈旧缓存**。v2.1.0 发布落在 GitHub 不通的窗口，缓存停在 v2.0.0，2.0.0 客户端长期检测不到 2.1.0；而 `/update/latest`、`/update/check`、下载页走 api.github.com（REST，广州可达）正常，形成"页面 2.1.0、客户端 2.0.0"的割裂。此前版本未暴露是因为每个版本有数周窗口、总有一次服务器能连上 GitHub 把缓存刷到新版；失败又静默无告警。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 保持 GitHub 实时拉取 + 失败回退内存缓存（原状） | 零改动 | 检测依赖广州能连 github.com；失败静默陈旧，无法保证发版即检测 |
| 服务端最小自愈（成功落盘 + 启动重试） | 改动小 | 仍依赖 GitHub 偶发可达；不是 100% 解耦 |
| **yml feed 以 COS 稳定 key 为来源（选定）** | 与安装包一样全走 COS，检测彻底脱离 GitHub 可达性 | 需改服务端 + 2 个发布脚本，发布流程要多一步种 yml |

#### 决策
> 客户端 yml feed（latest.yml / latest-mac.yml）**以 COS 稳定 key `codex-switch/latest/{yml}` 为来源**，GitHub release asset 仅作兜底。发布脚本把 yml 从 GitHub 下载到本地 `data/codex-switch/{ver}/` 并上传 COS（版本化 key + 稳定 key 每次 force 覆盖）。

#### 理由
> 1) COS（腾讯云广州）对国内服务器始终可达，yml 读取不再受 github.com 抖动影响
> 2) 稳定 key 每次发版覆盖，服务端无需知道"当前最新是哪个版本目录"，直接读稳定 key
> 3) 与既有"安装包走 COS"的心智模型一致，符合用户认知
> 4) COS 禁用/缺失时退回原 GitHub 逻辑，对本地开发/无 COS 环境零行为变化
> 5) electron-updater 用**配置的 feed URL** 解析 yml 内相对文件名去下载，与服务端从哪读到 yml 文本无关，下载链路（`/api/v1/updates/{filename}` → COS 302）不变

#### 影响
> - `src/utils/cos_storage.py` 新增 `get_bytes()`（读对象内容）
> - `src/services/update_feed.py` `get_latest_yml()` 取数顺序：COS 稳定 key → GitHub 兜底 → 陈旧缓存；构造可选注入 `cos`
> - `src/api/v1/updates.py` 两个 yml 端点 `UpdateFeedService(cos=CosStorage())`
> - `scripts/download-latest-release.sh` 额外下载 latest*.yml；`scripts/upload-to-cos.sh` 上传版本化 + 稳定 key（force 覆盖）
> - 上线顺序：先跑 download + upload 种 COS，再部署服务端代码
> - 已知独立隐患（未修）：GitHub v2.1.0 的 latest-mac.yml 仅含 x64 条目（mac arm64 走客户端自定义 DMG 下载不受影响）；Windows latest.yml 顶层 path 指向无架构 win.exe（electron-updater 按架构选 files[]，历史正常）

---

### ADR-018: 门户「工具」顶级菜单 → 下拉 + 两工具文档页（左目录 + 右正文）；移除首页 AI Working OK 直链

- **日期**：2026-09-07（2026-09-06 初版「/tools 单页两区块」经用户预览后重构替代）
- **状态**：✅ 已采纳
- **决策者**：wangliang + Claude

#### 背景
> 网站需给作者另两个开源 AI 护栏工具（ai-coding-ok 面向开发者、ai-working-ok 面向知识工作者）加导航入口。目标用户是国内 AI 工具使用者，github.com 不稳定，需使用者视角中文介绍、重点快速开始。两工程 GitHub 上已写好 wiki，要求最小改动复用。初版做「导航平铺 工具 → /tools 单页两区块」，用户预览后要求更像文档站：**工具下要有下拉可选两款工具，进入后左目录右正文**（参考 codexguide.ai/start），并移除首页 hero 的 AI Working OK 直链。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 仅链接 GitHub Wiki / 单页两区块概览（初版） | 改动小 | 单页信息密度弱、非文档站体验；github.com 国内不稳 |
| **下拉 + 每工具「单页长文档 + 左粘性目录」（选定）** | 使用者导向、快速开始突出、结构像文档站；正文站内即达，GitHub/Wiki 做外链补充 | 两个长模板 + 下拉/目录 CSS/JS，内容与样式工作量中等；wiki 变更需人工同步（一次性改写，非运行时拉取） |
| 多子页镜像 wiki 每章 | 每页短、最贴近 codexguide | 路由/模板/测试成倍增加，内容需大幅扩写，维护成本高 |

#### 决策
> 顶级导航「工具」= **下拉菜单**（子项 ai-working-ok、ai-coding-ok，顺序即此），纯下拉、无父级落地页。子项进入各自**单页长文档**：`/tools/ai-working-ok`、`/tools/ai-coding-ok`，文档页 = 移动端顶部横向 chips + 桌面左侧粘性分组目录（开始/快速开始/理解/帮助，锚点 + 滚动高亮）+ 右侧白卡正文（这是什么/适合谁/解决什么问题/快速开始…+ FAQ + GitHub·Wiki 外链）。**删除初版 /tools 单页概览**与首页 hero「🧩 AI Working OK 工具集」链接（入口收敛到下拉 + 页脚两条直链）。ai-working-ok 复用 `/api/v1/packages/ai-working-ok/latest` 国内镜像下载；ai-coding-ok 无下载（git 安装）。纯前端 Jinja2，零后端/DB/依赖。

#### 理由
> 1) 使用者视角中文正文站内即达，不依赖 github.com 2) 下拉是文档站常见导航；左目录右正文对"介绍+快速开始+概念+FAQ"阅读体验最优 3) 两工具本质是"装进 AI 的脚手架"，快速开始=安装指令+一句对话，单页锚点文档内容量适中、最贴现有 README/wiki 素材 4) 复用既有 token/btn/portal.js 基建，改动收敛 portal 层，未提交历史即重构（初版无提交，干净替换）5) 埋点/SEO 对齐既有体系。

#### 影响
> - 新增 `doc-ai-coding-ok.html`、`doc-ai-working-ok.html`（左目录+右正文）；`apple.css` 新增 `.nav__menu*` 下拉与 `.doc*` 文档样式（复用 :root token，≤979/≤767 响应式）；`portal.js` 加下拉开关 + TOC 滚动高亮；`base.html` 导航 li 改 button+menu、页脚两条直链、CSS/JS 版本 `20260907`。
> - 删除初版 `tools.html`、`GET /tools` 路由、`.tools-*` 样式、旧 /tools 埋点/测试；首页 hero 移除 AI Working OK 链接。
> - `router.py` 两个 doc 路由 + robots/sitemap(2 条)/llms.txt 指向 doc URL；`schemas/analytics.py` 页面/元素映射改两 doc 页；`test_portal.py` 重构（两 doc 200/内容/下拉/404/首页无直链/GEO）。
> - 下拉入口无父级 URL；页脚直链两个文档页。移动端汉堡菜单内下拉静态展开（无 hover）。
> - 内容一次性改写，后续两工具 wiki/命令变更需人工同步本站文案（已记 task-history 注意事项）。

---

### ADR-019: 「工具」下拉收录 Codex Switch（置顶）+ 文档页快速开始采用"站内单源"策略

- **日期**：2026-09-07
- **状态**：✅ 已采纳
- **决策者**：wangliang + Claude

#### 背景
> 上一迭代把「工具」做成了下拉 + 文档站形态，收录 ai-working-ok / ai-coding-ok 两个 AI 护栏工具。用户要求把作者的主产品 **Codex Switch** 也收进「工具」下拉（它同样有 wiki），风格与其他工具一致。Codex Switch 本身是本站主产品，站内已有较深的 下载页(/download) 与 使用指南(/guide)，需要避免文档页与其重复维护。

#### 方案对比

| 方案 | 优点 | 缺点 |
|------|------|------|
| 不在文档站收录 Codex Switch（保持现有下拉两项） | 零改动 | 不满足"作者工具集中展示"，入口不统一 |
| 文档页内完整复制 Codex Switch 安装图文 | 自给自足 | 与站内 /download、/guide 内容重复，需双份维护、易失同步 |
| **下拉收录 + 文档页"精简快速开始 + 深链站内下载/指南"（选定）** | 工具集完整展示；安装细节单一来源（/download、/guide）；快速开始在文档站仍可独立看懂 | 多一页内容；下载/指南若大改需留意文档页里的简述与深链文案 |

#### 决策
> 「工具」下拉改为 **Codex Switch（置顶，主产品）→ ai-working-ok → ai-coding-ok**。新增 `/tools/codex-switch` 文档页（左目录 + 右正文，样式复用 `.doc*`），内容改写自 codex-switch 仓库 README/CHANGELOG/`docs/help/faq.json`/onboarding + GitHub wiki；其「快速开始」= 精简 3 步自包含（下载安装→填 API Key→启动连接 + 验证），下载/图文深链 `href=/download` 与 `href=/guide`。页脚不重复加 Codex Switch 文档链接（其站内入口即 下载/使用指南）。纯前端，零后端/DB/依赖。

#### 理由
> 1) 「工具」成为作者三个开源项目的统一入口（桌面应用 + 两个 AI 护栏），使用户探索路径一致 2) 安装细节单一来源在 /download、/guide，文档页不做双份维护 3) 复用既有 `.doc*`/下拉/埋点/测试基建，本轮零 CSS/JS 改动 4) 措辞沿用站点既有「帮你解决网络问题 / 本地安全 / 数据不出本机」语气，避免照搬内部合规文案风险。

#### 影响
> - 新增 `doc-codex-switch.html` + `GET /tools/codex-switch`；`base.html` 下拉加 Codex Switch 置顶；sitemap/llms.txt 收录；`schemas/analytics.py` 补页与点位；`test_portal.py` +2。
> - 下拉顺序确定为 Codex Switch 置顶；ai-working-ok/ai-coding-ok 页面与顺序不变。
> - 文档一次性与 wiki/README 内容同步；后续 Codex Switch wiki 变更需人工同步本站。

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

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

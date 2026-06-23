# ICP 备案号悬挂设计方案

> **版本**：v1.0
> **日期**：2026-06-23
> **状态**：待 Review
> **作者**：wangliang
> **参考**：[腾讯云备案文档](https://cloud.tencent.com/document/product/243)、[工信部备案管理系统](http://beian.miit.gov.cn)

---

## 目录

1. [法规依据与核心要求](#1-法规依据与核心要求)
2. [现状分析](#2-现状分析)
3. [悬挂方案设计](#3-悬挂方案设计)
4. [配置管理](#4-配置管理)
5. [实现要点](#5-实现要点)
6. [测试验证清单](#6-测试验证清单)
7. [运维注意事项](#7-运维注意事项)

---

## 1. 法规依据与核心要求

### 1.1 法律依据

根据中华人民共和国《互联网信息服务管理办法》（国务院令第292号）及工业和信息化部（MIIT）相关规定：

> 所有在中国大陆境内提供非经营性互联网信息服务的网站，必须完成 ICP 备案，并将备案号醒目地展示在网站首页底部（即"悬挂备案号"）。

### 1.2 悬挂规范（腾讯云指引）

| 维度 | 要求 |
|------|------|
| **悬挂位置** | 网站所有页面的底部（`<footer>` 区域），版权信息附近等固定公共区域 |
| **展示格式** | 完整、准确地展示备案号，如 `粤ICP备12345678号-1` |
| **可点击** | 备案号必须是超链接，点击后跳转至工信部备案管理系统 `http://beian.miit.gov.cn` |
| **展示样式** | 颜色、样式需与网站整体设计协调，但必须清晰可辨、易于发现 |
| **覆盖范围** | 所有页面，不仅仅是首页 |

### 1.3 违规后果

- 通信管理局定期核查，未悬挂或链接失效 → 责令整改
- 严重者可能影响备案状态（备案号被注销）

---

## 2. 现状分析

### 2.1 当前站点结构

本项目有 **两类页面体系**，它们的 footer 实现方式不同：

| 页面体系 | 路由 | 模板方式 | Footer 现状 |
|----------|------|---------|------------|
| **门户页面** | `/` `/download` `/guide` | 共享 `portal/templates/base.html` | ✅ 有统一 footer（`footer__bottom` div） |
| **管理后台** | `/admin` `/admin/login` `/admin/packages` | 各自独立 HTML 文件 | ❌ dashboard.html 无 footer；login.html 无 footer；packages.html 无 footer |

### 2.2 门户 footer 现状（base.html L40-L67）

```html
<footer class="footer">
  <div class="footer__inner">
    <!-- logo + 链接列表 -->
  </div>
  <div class="footer__bottom content-width">
    <span>&copy; 2026 Codex Switch</span>
    <span>开源软件 · MIT License</span>
  </div>
</footer>
```

`footer__bottom` 是悬挂备案号的最自然位置——紧邻版权信息、所有页面共享。

### 2.3 管理后台现状

- `login.html`：极简登录页，无 footer
- `dashboard.html`：有 `admin-header` 但无 footer
- `packages.html`：无 footer

管理后台虽然不面向公众，但只要是本站域名下可访问的页面，都需要悬挂备案号（法规要求"所有页面"）。

### 2.4 当前无 ICP 相关基础设施

- `.env` 中无备案号配置
- `config.py` 中无相关设置项
- 模板中无备案号占位符
- 前端 CSS 无备案号链接样式

---

## 3. 悬挂方案设计

### 3.1 总体策略

```
┌─────────────────────────────────────────────────────┐
│                    配置层                            │
│  .env → config.py → app.state / template context    │
│  ICP_FILING_NUMBER=粤ICP备12345678号-1               │
└──────────────────────┬──────────────────────────────┘
                       │
       ┌───────────────┼───────────────┐
       ▼                               ▼
┌──────────────┐              ┌──────────────────┐
│  门户页面     │              │  管理后台         │
│  base.html   │              │  各独立 HTML      │
│  (模板变量)   │              │  (模板变量)       │
└──────────────┘              └──────────────────┘
```

### 3.2 门户页面方案（base.html）

在现有 `footer__bottom` div 中，新增备案号 `<span>`：

```
┌──────────────────────────────────────────────────────┐
│  footer__bottom                                      │
│                                                      │
│  © 2026 Codex Switch    开源软件 · MIT License       │
│  粤ICP备12345678号-1    ← 新增（可点击，跳转工信部）  │
│                                                      │
└──────────────────────────────────────────────────────┘
```

**展示规则**：
- ICP 备案号独立成行（或与现有信息同行），与 copyright 保持相同的视觉层级
- 链接使用与 footer 次要文字一致的灰色（`#86868b`），hover 时变为 Apple 蓝（`#0071e3`）
- 下划线默认隐藏，hover 时出现（与 footer 其他链接风格统一）
- 字号与版权信息保持一致：14px / `--text-caption`

**HTML 结构（概念）**：
```
<div class="footer__bottom">
  <span>&copy; 2026 Codex Switch</span>
  <span>开源软件 · MIT License</span>
  <span>
    <a href="http://beian.miit.gov.cn"
       target="_blank"
       rel="noopener"
       class="footer__icp">
      {{ icp_filing_number }}
    </a>
  </span>
</div>
```

### 3.3 管理后台方案

管理后台三个页面各自独立，建议采用 **最小化统一** 方式：

**方案 A（推荐）：提取后台公共 footer 片段**

- 创建 `admin/templates/_footer.html` 公共片段
- 在 dashboard.html、login.html、packages.html 中 `{% include '_footer.html' %}`
- 优点：单一维护点，修改一处全部生效
- 工作量：3 个文件各加 1 行 `{% include %}`

**方案 B：直接在三个页面各自写入**

- 在每个页面底部硬编码备案号
- 优点：无需新建文件
- 缺点：三个副本，后续修改容易遗漏

**推荐方案 A**，理由：后台页面虽然现在只有 3 个，但未来可能增加，公共 footer 片段是合理的抽象。

**后台 footer 样式**：
```
┌──────────────────────────────────────────────────────┐
│                                                      │
│        粤ICP备12345678号-1                            │
│                                                      │
└──────────────────────────────────────────────────────┘
```

- 居中显示，与后台整体简洁风格一致
- 字号、颜色与前台保持一致
- 不显示 copyright（后台不面向公众，只保留法规要求的备案号）

### 3.4 CSS 样式设计

新增 `.footer__icp` 链接样式类，遵循 Apple 设计系统：

```css
.footer__icp {
  color: var(--color-text-secondary);   /* #86868b */
  text-decoration: none;
  font-size: var(--text-caption);       /* 14px */
  transition: color 0.2s;
}

.footer__icp:hover {
  color: var(--color-accent);           /* #0071e3 */
  text-decoration: underline;
}
```

设计考量：
- 默认低调（灰色），符合 "deference（遵从）" 原则 — footer 信息让步于内容
- hover 时变蓝 + 下划线，满足 "clarity（清晰）" — 明确表示这是一个可点击的链接
- 与 footer 现有链接风格（`.footer__col a`）保持一致

---

## 4. 配置管理

### 4.1 配置层级

```
.env                    →  ICP_FILING_NUMBER=粤ICP备12345678号-1
src/config.py           →  Settings 类新增 icp_filing_number: str 字段
src/main.py             →  create_app() 中将备案号注入 Jinja2 全局上下文
所有模板                 →  {{ icp_filing_number }} 模板变量可用
```

### 4.2 config.py 新增字段

```python
# src/config.py — Settings 类
class Settings(BaseSettings):
    # ... 现有字段 ...

    # ICP 备案
    icp_filing_number: str = ""
    """ICP 备案号，如 粤ICP备12345678号-1。
    为空字符串时不在页面上显示备案号（用于本地开发环境）。"""
```

**关键设计决策**：`icp_filing_number` 为空时不显示

这样做的理由：
- 本地开发环境（`localhost`）不需要显示备案号
- 生产环境 `.env` 配置后自动显示
- 避免硬编码，部署灵活

### 4.3 Jinja2 全局上下文注入

```python
# src/main.py — create_app()
app.jinja_env.globals["icp_filing_number"] = settings.icp_filing_number
```

### 4.4 生产环境 .env 示例

```bash
# .env（生产环境）
ICP_FILING_NUMBER=粤ICP备12345678号-1
```

---

## 5. 实现要点

### 5.1 涉及文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/config.py` | 修改 | Settings 类新增 `icp_filing_number` 字段 |
| `src/main.py` | 修改 | 注册 Jinja2 全局变量 |
| `src/portal/templates/base.html` | 修改 | `footer__bottom` 中新增备案号 |
| `src/static/css/apple.css` | 修改 | 新增 `.footer__icp` 样式 |
| `src/admin/templates/_footer.html` | **新建** | 后台公共 footer 片段 |
| `src/admin/templates/dashboard.html` | 修改 | 底部 `{% include '_footer.html' %}` |
| `src/admin/templates/login.html` | 修改 | 底部 `{% include '_footer.html' %}` |
| `src/admin/templates/packages.html` | 修改 | 底部 `{% include '_footer.html' %}` |
| `.env` | 修改 | 生产环境添加 `ICP_FILING_NUMBER` |

### 5.2 代码修改量估算

| 类别 | 量级 |
|------|------|
| Python 代码 | ~5 行（config.py 1 行 + main.py 3 行） |
| HTML 模板 | ~15 行（base.html 3 行 + _footer.html 6 行 + 3 个 include 各 1 行） |
| CSS | ~12 行 |
| 总计 | ~32 行业务代码 |

### 5.3 不做什么

- ❌ 不修改 Jinja2 模板引擎配置（Jinja2 默认已对表达式输出做 HTML 转义，直接输出 ICP 号是安全的）
- ❌ 不在 portal JS 中操作备案号 DOM（纯 SSR，无 JS 依赖）
- ❌ 不为后台页面创建 base.html（过度设计，3 个页面用 include 即可）
- ❌ 不引入数据库存储备案号（备案号是部署级配置，属于 .env 范畴）

---

## 6. 测试验证清单

### 6.1 功能验证

- [ ] 本地开发环境（`ICP_FILING_NUMBER=""`）：备案号不显示
- [ ] 本地模拟生产（`ICP_FILING_NUMBER=粤ICP备12345678号-1`）：备案号显示且可点击
- [ ] 点击备案号链接：在新标签页中打开 `http://beian.miit.gov.cn`
- [ ] 链接 `rel="noopener"` 属性存在（安全最佳实践）

### 6.2 覆盖范围验证

访问以下所有页面，确认底部均有备案号：

| 页面 | 路由 | 验证项 |
|------|------|--------|
| 首页 | `/` | footer 中有备案号 |
| 下载页 | `/download` | footer 中有备案号 |
| 使用指南 | `/guide` | footer 中有备案号 |
| 管理后台首页 | `/admin` | 底部有备案号 |
| 管理员登录 | `/admin/login` | 底部有备案号 |
| 包管理 | `/admin/packages` | 底部有备案号 |

### 6.3 样式验证

- [ ] 备案号颜色与其他 footer 次要文字一致（灰色）
- [ ] hover 时变为蓝色 + 下划线
- [ ] 在不同屏幕宽度下（320px–1440px）布局正常
- [ ] 深色模式下可读（如果项目未来支持深色模式，当前暂不需要）

### 6.4 回归验证

- [ ] 现有测试全部通过（`uv run pytest`）
- [ ] `ruff check .` 无新增警告

---

## 7. 运维注意事项

### 7.1 备案号变更流程

当 ICP 备案号发生变化时（如新增备案主体、变更接入商），只需：

1. 修改生产环境 `.env` 中的 `ICP_FILING_NUMBER`
2. 重启 uvicorn 进程

无需修改代码、无需重新构建。

### 7.2 链接可用性监控

工信部备案系统域名 `beian.miit.gov.cn` 存在变更历史，建议：

- 每季度手动验证一次链接可正常跳转
- 关注腾讯云备案公告，及时更新跳转地址

### 7.3 合规提醒

- 备案号必须与工信部颁发的完全一致（包括大小写、空格、符号）
- 如果网站有多个域名，每个域名都需要单独备案
- 网站改版后，备案号悬挂位置可能变动，需要重新验证

---

## 附录 A：参考链接

- [工信部备案管理系统](http://beian.miit.gov.cn)
- [腾讯云 ICP 备案文档](https://cloud.tencent.com/document/product/243)
- [《互联网信息服务管理办法》（国务院令第292号）](http://www.gov.cn/gongbao/content/2000/content_60540.htm)

## 附录 B：现有设计文档索引

- [系统设计方案](../DESIGN.md)
- [运营后台 V2 重设计](ADMIN-REDESIGN-V2.md)
- [COS 存储方案](COS-STORAGE-DESIGN.md)
- [CLI 安装指南设计](CLI-INSTALL-GUIDE-DESIGN.md)

# 网站技术支持体系设计方案

> **状态**：待 Review  
> **日期**：2026-07-04  
> **设计者**：wangliang + Claude  
> **关联**：客户端交流群功能（`QaGroupModal.tsx`）

---

## 1. 背景与目标

### 1.1 背景

codex-switch 客户端内置了"交流群"功能（`QaGroupModal.tsx`）——扫码添加作者微信，拉用户进微信群，用于反馈问题、获取使用技巧。但网站（codex-switch-server 门户）缺少对应的技术支持入口，使用中遇到困难的用户没有渠道求助。

### 1.2 目标

在网站上建立完整的技术支持体系，让用户能：
1. 扫码加入微信交流群，获取实时帮助
2. 找到 GitHub Issues 提交 Bug 或功能请求
3. 快速跳转到已有的 FAQ 和使用指南
4. 从多个触点发现支持入口，降低求助门槛

### 1.3 设计原则

- **符合 Apple HIG**：入口低调不打扰，弹窗简洁干净，内容驱动
- **零外部依赖**：纯 HTML+CSS+vanilla JS，不引入第三方客服 SaaS
- **一次配置，全局生效**：二维码图片路径通过模板变量注入，修改一处即可
- **与客户端体验一致**：交流群文案和视觉与客户端 `QaGroupModal` 保持统一

---

## 2. 用户触点矩阵

```
用户获取帮助的 4 条路径，覆盖不同行为模式：

路径 1：悬浮按钮（所有门户页面右下角）
  "遇到问题了 → 找悬浮按钮 → 扫码进群"
  适合：即时求助型用户

路径 2：导航栏 / 页脚链接（所有页面）
  "浏览网站 → 看到'支持'链接 → 进入支持页"
  适合：浏览探索型用户

路径 3：使用指南页底部（/guide）
  "跟着教程走完 → 还有问题 → 底部 CTA → 进群"
  适合：按步骤操作但遇到困难的用户

路径 4：直接访问 /support
  "从搜索引擎/社交媒体/别人分享 → 直接进支持页"
  适合：已知目标用户
```

### 2.1 路由变更

| 路由 | 页面 | 访问权限 | 变更类型 |
|------|------|---------|---------|
| `/support` | 技术支持中心 | 公开 | **新增** |

### 2.2 现有页面变更

| 页面 | 变更内容 |
|------|---------|
| `base.html` | 导航栏新增「支持」链接；页脚"反馈"→"技术支持"并链接到 `/support`；全局注入悬浮按钮 HTML + Modal |
| `guide.html` | 内容末尾新增「还有问题？」CTA 区块 |
| `apple.css` | 新增悬浮按钮、Modal、支持页、CTA 区块样式 |
| `portal.js` | 新增悬浮按钮和 Modal 的交互逻辑（打开/关闭/点击外部关闭/ESC 关闭） |
| `portal/router.py` | 新增 `GET /support` 路由 |

---

## 3. 组件详细设计

### 3.1 悬浮支持按钮（Floating Support Button）

**位置**：所有门户页面右下角，固定定位，距底部 24px，距右侧 24px  
**视觉**：Apple 风格圆形按钮，白色背景 + 微阴影 + 毛玻璃效果

```
┌────────────────────────────────────────────────┐
│                                                │
│                                        页面内容  │
│                                                │
│                                                │
│                                         ┌────┐ │
│                                         │ 💬 │ │
│                                         └────┘ │
│                                    24px ─┘      │
│                                       ↑         │
│                                    距底 24px    │
└────────────────────────────────────────────────┘
```

**设计规格**：

| 属性 | 值 |
|------|---|
| 尺寸 | 56×56px 圆形 |
| 背景 | `rgba(255,255,255,0.85)` + `backdrop-filter: saturate(180%) blur(20px)` |
| 阴影 | `0 2px 12px rgba(0,0,0,0.08)`，hover 时加深至 `0 4px 20px rgba(0,0,0,0.15)` |
| 图标 | 聊天气泡 SVG（24×24px，`#0071e3`） |
| 文字 | 无文字，纯图标按钮（移动端可选添加"帮助"文字标签） |
| 位置 | `position: fixed; bottom: 24px; right: 24px; z-index: 50` |
| 动画 | 初始加载后 3s 微呼吸一次（`scale: 1→1.05→1`），提示用户注意 |
| Hover | `scale: 1.05` + 阴影加深，过渡 0.2s ease |
| 响应式 | <768px 时缩小为 48×48px，距底 16px，距右 16px |

**HTML 结构**（伪代码）：

```html
<button id="supportFloat" class="support-float" aria-label="获取帮助"
        data-track="support-float">
  <!-- 聊天气泡 SVG inline -->
</button>
```

---

### 3.2 支持 Modal（Support Modal）

**触发**：点击悬浮按钮  
**布局**：居中弹窗，半透明黑色遮罩，白色卡片内容区

```
┌──────────────────────────────────────────┐
│ 半透明黑色遮罩 (rgba(0,0,0,0.4))         │
│                                          │
│     ┌────────────────────────┐           │
│     │  ✕  加入交流群          │  ← header │
│     │────────────────────────│           │
│     │                        │           │
│     │  ┌──────────────────┐  │           │
│     │  │                  │  │           │
│     │  │   微信二维码图片   │  │           │
│     │  │   240×240 px     │  │           │
│     │  │                  │  │           │
│     │  └──────────────────┘  │           │
│     │                        │           │
│     │  扫码添加作者微信       │           │
│     │  拉你进技术支持群           │           │
│     │  反馈问题·获取技巧      │           │
│     │                        │           │
│     │  ── 其他渠道 ──        │           │
│     │                        │           │
│     │  🐛 GitHub Issues  →   │           │
│     │  📖 使用指南      →    │           │
│     │  📮 邮件反馈      →    │           │
│     │                        │           │
│     └────────────────────────┘           │
│                                          │
└──────────────────────────────────────────┘
```

**设计规格**：

| 属性 | 值 |
|------|---|
| 遮罩背景 | `rgba(0,0,0,0.4)`，带 `backdrop-filter: blur(4px)` |
| 卡片宽度 | `max-width: 420px`，水平居中，`margin: 0 16px` |
| 卡片背景 | `#ffffff` |
| 卡片圆角 | `18px`（标准卡片） |
| Header | 标题"加入交流群" 17px/600，右侧 ✕ 关闭按钮 |
| 二维码尺寸 | 240×240px，白色背景，8px 内边距，8px 圆角，居中 |
| 二维码文案 | 14px `#86868b`，居中，"扫码添加作者微信，拉你进交流群" |
| 分隔线 | `1px solid #e5e5e7`，上下 16px 间距 |
| 快捷链接 | 每行一个，左侧 emoji 图标 + 文字，右侧 → 箭头，hover 背景变 `#f5f5f7` |
| 关闭方式 | ✕ 按钮 / 点击遮罩 / ESC 键 |
| 动画 | 遮罩 `opacity 0.2s ease`；卡片 `opacity + scale(0.95→1)` 0.25s ease |

**二维码配置**：

二维码图片路径通过 Jinja2 模板变量 `{{ support_qr_image }}` 传入，默认值 `/static/images/wechat-qr.png`。在生产环境 `.env` 中可配置：

```
SUPPORT_QR_IMAGE=/static/images/wechat-qr.png
```

配置项加在 `src/config.py`：

```python
support_qr_image: str = "/static/images/wechat-qr.png"
```

`portal/router.py` 注入到模板上下文。

**快捷链接项**：

| 图标 | 文字 | 链接 | 说明 |
|------|------|------|------|
| 🐛 | 提交 Issue | `https://github.com/Mark7766/codex-switch/issues` | GitHub Issues，target=_blank |
| 📖 | 使用指南 | `/guide` | 站内链接 |
| 📮 | 邮件反馈 | `mailto:mark.coder@outlook.com` | （待确认具体邮箱） |

---

### 3.3 技术支持页面 `/support`

**设计布局**：单栏，`max-width: 980px` 居中，自上而下分 4 个区块

```
┌──────────────────────────────────────────────────┐
│ 导航栏（同首页）                                   │
├──────────────────────────────────────────────────┤
│                                                  │
│           获取帮助                                  │
│     ───────────────────                           │
│     遇到问题了？选择适合你的方式                     │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │             加入交流群（主卡片）              │  │
│  │                                            │  │
│  │  ┌──────────┐   扫码添加作者微信             │  │
│  │  │          │   拉你进技术支持群                 │  │
│  │  │ 二维码    │                              │  │
│  │  │          │   群内可以：                   │  │
│  │  │          │   · 反馈使用中遇到的问题        │  │
│  │  └──────────┘   · 获取最新使用技巧           │  │
│  │                 · 参与产品功能讨论            │  │
│  │                 · 了解版本更新动态            │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
│  ┌─────────────────┐  ┌──────────────────────┐  │
│  │  📖 使用指南     │  │  🐛 提交 Issue        │  │
│  │                 │  │                      │  │
│  │  安装教程       │  │  在 GitHub 提交      │  │
│  │  FAQ 常见问题   │  │  Bug 报告或功能请求   │  │
│  │  配置说明       │  │                      │  │
│  │                 │  │  → GitHub Issues     │  │
│  │  → 查看指南     │  │                      │  │
│  └─────────────────┘  └──────────────────────┘  │
│                                                  │
│  ┌────────────────────────────────────────────┐  │
│  │  常见问题（FAQ 摘要）                        │  │
│  │                                            │  │
│  │  Q: Codex 说英文看不懂怎么办？              │  │
│  │  A: 在项目根目录创建 AGENTS.md...           │  │
│  │                                            │  │
│  │  Q: DeepSeek API Key 在哪获取？             │  │
│  │  A: 访问 platform.deepseek.com...          │  │
│  │                                            │  │
│  │  → 查看全部 FAQ                             │  │
│  └────────────────────────────────────────────┘  │
│                                                  │
├──────────────────────────────────────────────────┤
│  页脚                                             │
└──────────────────────────────────────────────────┘
```

**各区块设计规格**：

#### 3.3.1 Hero 区

| 属性 | 值 |
|------|---|
| 标题 | "获取帮助"，40px/600，`#1d1d1f` |
| 副标题 | "遇到问题了？选择适合你的方式"，17px，`#86868b` |
| 间距 | 标题距顶 80px，标题与副标题间距 8px，区块下方 48px |

#### 3.3.2 交流群主卡片

| 属性 | 值 |
|------|---|
| 布局 | 水平：左侧二维码 200×200px + 右侧文字说明 |
| 背景 | `#ffffff`，圆角 18px，微阴影 |
| 内边距 | 32px |
| 二维码 | 200×200px，8px 白边，8px 圆角 |
| 标题 | "加入交流群"，21px/600 |
| 说明文字 | 14px `#86868b`，列出群内价值（反馈问题/获取技巧/参与讨论/版本动态） |
| 响应式 | <768px 时改为垂直布局，二维码居中在上、文字在下 |

#### 3.3.3 双卡片行

两个并排卡片，与首页"功能卡片"风格一致：

| 属性 | 值 |
|------|---|
| 布局 | 2 列网格，间距 24px |
| 卡片 | 背景 `#ffffff`，圆角 18px，内边距 24px，hover 上浮 4px |
| 图标 | emoji（📖/🐛） 28px |
| 标题 | 21px/600 `#1d1d1f` |
| 描述 | 14px `#86868b` |
| CTA | 文字链接，Apple 蓝 `#0071e3`，hover 下划线 |
| 响应式 | <768px 时单列堆叠 |

#### 3.3.4 FAQ 摘要区

| 属性 | 值 |
|------|---|
| 标题 | "常见问题"，28px/600 |
| 内容 | 从 guide.html 的 FAQ 中提取 3-4 个最高频问题，Q&A 格式 |
| 底部链接 | "→ 查看全部 FAQ"，链接到 `/guide#faq` |
| 样式 | Q 加粗 17px，A 14px `#86868b`，每项间距 16px |

---

### 3.4 使用指南页底部 CTA

在 `guide.html` 内容最末尾（所有步骤面板之后），增加：

```
┌────────────────────────────────────────────┐
│                                            │
│              还有问题？                      │
│                                            │
│     🎯 扫码加入交流群，作者在线解答           │
│                                            │
│     ┌──────────────────────┐               │
│     │  [交流群二维码小图]    │               │
│     │   120×120 px         │               │
│     └──────────────────────┘               │
│                                            │
│     或者 → 提交 GitHub Issue                │
│                                            │
└────────────────────────────────────────────┘
```

**设计规格**：

| 属性 | 值 |
|------|---|
| 区块 | 淡灰背景 `#fafafa`，居中，上下 48px 间距 |
| 标题 | "还有问题？"，28px/600 |
| 副标题 | "扫码加入交流群，作者在线解答"，17px，`#86868b` |
| 二维码 | 120×120px，居中 |
| 备选链接 | "或者 → 提交 GitHub Issue"，14px，Apple 蓝链接 |
| 响应式 | 宽度自适应，最大 420px 居中 |

---

### 3.5 导航栏和页脚变更

**导航栏**（`base.html`）：

```html
<!-- 在"指南"和"GitHub"之间新增 -->
<li><a href="/support" class="nav__link" data-track="nav-support">支持</a></li>
```

导航链接顺序变为：`[下载] [指南] [支持] [GitHub]`

**页脚**（`base.html`）：

"资源"列下将现有"反馈"链接改为"技术支持"，链接到 `/support`：

```html
<li><a href="/support">技术支持</a></li>
```

---

## 4. 二维码图片管理

### 4.1 存放位置

二维码图片存放在 `src/static/images/wechat-qr.png`，与现有的 `logo.png`、`og-image.png` 同级。

### 4.2 配置方式

遵循项目现有模式（如 ICP 备案号的配置方式），通过 `config.py` → `.env` → 模板注入三级传递：

```python
# src/config.py 新增字段
class Settings(BaseSettings):
    ...
    support_qr_image: str = "/static/images/wechat-qr.png"
```

```python
# src/portal/router.py 注入模板上下文
@app.get("/support")
async def support(request: Request):
    return templates.TemplateResponse("support.html", {
        "request": request,
        "support_qr_image": settings.support_qr_image,
    })
```

悬浮按钮和 Modal 需要在 `base.html` 中获取二维码路径。由于 `base.html` 是所有页面的布局壳，二维码路径作为 Jinja2 全局变量注入（与 `icp_filing_number` 一致的方式）：

```python
# portal/router.py — 在每个请求中注入
templates.env.globals["support_qr_image"] = settings.support_qr_image
```

### 4.3 降级策略

如果二维码图片不存在（路径错误或文件缺失），Modal 和页面中显示占位虚线框 + 文字"二维码图片未配置"，不破坏页面布局。实现方式：

```html
<img src="{{ support_qr_image }}" alt="微信交流群二维码"
     onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
<div class="support__qr-placeholder" style="display:none">
  二维码图片未配置
</div>
```

---

## 5. 交互设计

### 5.1 Modal 打开/关闭

| 触发 | 行为 |
|------|------|
| 点击悬浮按钮 | Modal 显示（`opacity 0→1`，卡片 `scale 0.95→1`） |
| 点击 Modal ✕ 按钮 | Modal 关闭 |
| 点击 Modal 外部遮罩 | Modal 关闭 |
| 按下 ESC 键 | Modal 关闭 |
| Modal 打开时 | `document.body` 添加 `overflow: hidden` 禁止背景滚动 |

### 5.2 悬浮按钮动画

| 时机 | 动画 |
|------|------|
| 页面加载后 3s | 按钮呼吸一次：`scale(1) → scale(1.05) → scale(1)`，持续 1s，`ease-in-out` |
| Hover | `scale(1.05)` + 阴影 `0 4px 20px rgba(0,0,0,0.15)`，过渡 0.2s ease |
| Modal 打开时 | 按钮隐藏（`opacity: 0`） |
| Modal 关闭后 | 按钮重新显示（`opacity: 1`），但不重复呼吸动画 |

### 5.3 键盘无障碍

- 悬浮按钮可 Tab 聚焦，Enter/Space 打开 Modal
- Modal 打开后焦点自动移到 Modal 容器
- Modal 内 Tab 循环锁定（焦点在 Modal 内循环）
- ESC 关闭 Modal，焦点回到悬浮按钮

### 5.4 JS 实现要点（伪代码）

```javascript
// portal.js 新增部分
(function() {
  const floatBtn = document.getElementById('supportFloat');
  const modal = document.getElementById('supportModal');
  const overlay = modal.querySelector('.support-modal__overlay');
  const closeBtn = modal.querySelector('.support-modal__close');

  function openModal() {
    modal.classList.add('is-open');
    document.body.style.overflow = 'hidden';
    floatBtn.style.opacity = '0';
    modal.querySelector('.support-modal__card').focus();
  }

  function closeModal() {
    modal.classList.remove('is-open');
    document.body.style.overflow = '';
    floatBtn.style.opacity = '1';
    floatBtn.focus();
  }

  floatBtn.addEventListener('click', openModal);
  closeBtn.addEventListener('click', closeModal);
  overlay.addEventListener('click', closeModal);
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape' && modal.classList.contains('is-open')) {
      closeModal();
    }
  });

  // 呼吸动画：页面加载 3s 后触发
  setTimeout(function() {
    floatBtn.classList.add('support-float--breathe');
  }, 3000);
})();
```

---

## 6. CSS 设计（Apple 设计系统 Token）

### 6.1 悬浮按钮 `.support-float`

```css
.support-float {
  position: fixed;
  bottom: 24px;
  right: 24px;
  z-index: 50;
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: saturate(180%) blur(20px);
  -webkit-backdrop-filter: saturate(180%) blur(20px);
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.support-float:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
}

.support-float--breathe {
  animation: supportBreathe 1s ease-in-out;
}

@keyframes supportBreathe {
  0%   { transform: scale(1); }
  50%  { transform: scale(1.05); }
  100% { transform: scale(1); }
}

/* 移动端 */
@media (max-width: 768px) {
  .support-float {
    width: 48px;
    height: 48px;
    bottom: 16px;
    right: 16px;
  }
}
```

### 6.2 Modal `.support-modal`

```css
.support-modal {
  display: none;
  position: fixed;
  inset: 0;
  z-index: 100;
}

.support-modal.is-open {
  display: block;
}

.support-modal__overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  animation: modalFadeIn 0.2s ease;
}

.support-modal__card {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: #ffffff;
  border-radius: 18px;
  width: calc(100% - 32px);
  max-width: 420px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.16);
  animation: modalScaleIn 0.25s ease;
}

.support-modal__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 0;
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
}

.support-modal__close {
  background: none;
  border: none;
  font-size: 20px;
  color: #86868b;
  cursor: pointer;
  padding: 4px;
  border-radius: 50%;
  transition: color 0.15s ease;
}

.support-modal__close:hover {
  color: #1d1d1f;
}

.support-modal__body {
  padding: 20px 24px 24px;
  text-align: center;
}

.support-modal__qr {
  width: 240px;
  height: 240px;
  background: #ffffff;
  border-radius: 8px;
  padding: 8px;
  margin: 0 auto 12px;
}

.support-modal__qr-text {
  font-size: 14px;
  color: #86868b;
  margin-bottom: 16px;
}

.support-modal__divider {
  border: none;
  border-top: 1px solid #e5e5e7;
  margin: 16px 0;
  position: relative;
}

.support-modal__divider::after {
  content: '其他渠道';
  position: absolute;
  top: -10px;
  left: 50%;
  transform: translateX(-50%);
  background: #ffffff;
  padding: 0 12px;
  font-size: 12px;
  color: #86868b;
}

.support-modal__link {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border-radius: 8px;
  text-decoration: none;
  color: #1d1d1f;
  font-size: 15px;
  transition: background 0.15s ease;
}

.support-modal__link:hover {
  background: #f5f5f7;
}

.support-modal__link-icon {
  margin-right: 10px;
}

@keyframes modalFadeIn {
  from { opacity: 0; }
  to   { opacity: 1; }
}

@keyframes modalScaleIn {
  from { opacity: 0; transform: translate(-50%, -50%) scale(0.95); }
  to   { opacity: 1; transform: translate(-50%, -50%) scale(1); }
}
```

### 6.3 支持页样式（`.support-page`）

复用现有设计 Token，遵循 Apple 风格：

| 元素 | 样式 |
|------|------|
| `.support-hero` | text-align: center; padding: 80px 0 48px |
| `.support-hero__title` | 40px/600, `#1d1d1f` |
| `.support-hero__sub` | 17px, `#86868b`, margin-top: 8px |
| `.support-primary-card` | max-width: 780px 居中, 白色, 圆角 18px, display:flex, gap:32px, padding:32px |
| `.support-primary-card__qr` | 200×200px, flex-shrink: 0 |
| `.support-primary-card__text` | flex:1, 21px/600 标题 + 14px `#86868b` 列表 |
| `.support-links` | 2 列 grid, gap:24px, 与首页 features 卡片风格一致 |
| `.support-faq` | 标题 28px/600, Q&A 列表, 与 guide FAQ 风格一致 |
| `.support-bottom-cta` | 淡灰背景 `#fafafa`, 居中, 48px 上下间距 |

### 6.4 指南页底部 CTA（`.guide__support-cta`）

```css
.guide__support-cta {
  text-align: center;
  padding: 48px 16px;
  margin-top: 48px;
  background: #fafafa;
  border-radius: 18px;
}

.guide__support-cta__title {
  font-size: 28px;
  font-weight: 600;
  color: #1d1d1f;
  margin-bottom: 8px;
}

.guide__support-cta__sub {
  font-size: 17px;
  color: #86868b;
  margin-bottom: 20px;
}

.guide__support-cta__qr {
  width: 120px;
  height: 120px;
  border-radius: 8px;
  margin-bottom: 16px;
}

.guide__support-cta__alt {
  font-size: 14px;
  color: #86868b;
}
```

---

## 7. 埋点设计

新增以下埋点点位，与现有 `data-track` 体系衔接：

| 点位 ID | 位置 | 事件类型 |
|---------|------|---------|
| `support-float` | 悬浮按钮点击 | click |
| `support-modal-open` | Modal 打开（任一方式） | click |
| `support-modal-close` | Modal 关闭（任一方式） | click |
| `support-modal-qr` | Modal 内二维码点击（放大查看） | click |
| `support-modal-issue` | Modal 内 GitHub Issues 链接点击 | click |
| `support-modal-guide` | Modal 内使用指南链接点击 | click |
| `support-modal-email` | Modal 内邮件链接点击 | click |
| `nav-support` | 导航栏"支持"链接点击 | click |
| `footer-support` | 页脚"技术支持"链接点击 | click |
| `support-page-view` | `/support` 页面浏览 | pageview |
| `support-page-issue` | 支持页 GitHub Issues 卡片点击 | click |
| `support-page-guide` | 支持页使用指南卡片点击 | click |
| `guide-support-cta` | 指南页底部 CTA 点击 | click |

共 13 个新埋点点位。在 `src/schemas/analytics.py` 的中文映射表中新增对应条目。

---

## 8. 需要变更的文件清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `src/portal/templates/support.html` | **新建** | 技术支持页面模板 |
| `src/portal/templates/base.html` | 修改 | 导航栏+"支持"链接；页脚"反馈"→"技术支持"；全局悬浮按钮+Modal HTML |
| `src/portal/templates/guide.html` | 修改 | 内容末尾新增"还有问题？"CTA 区块 |
| `src/portal/router.py` | 修改 | 新增 `GET /support` 路由；注入 `support_qr_image` 全局变量 |
| `src/static/css/apple.css` | 修改 | 新增悬浮按钮/Modal/支持页/CTA 全部样式 |
| `src/static/js/portal.js` | 修改 | 新增悬浮按钮+Modal 交互逻辑（打开/关闭/ESC/呼吸动画） |
| `src/static/images/wechat-qr.png` | **新建** | 微信交流群二维码图片（需提供） |
| `src/config.py` | 修改 | 新增 `support_qr_image` 配置字段 |
| `src/schemas/analytics.py` | 修改 | 新增 13 个埋点中文映射 |
| `tests/integration/test_portal.py` | 修改 | 新增 `/support` 页面测试 |
| `.env.example` | 修改 | 新增 `SUPPORT_QR_IMAGE` 环境变量说明 |

---

## 9. 实施步骤

### Phase 1：资源准备（管理员）
1. 提供微信交流群二维码图片 → 保存为 `src/static/images/wechat-qr.png`
2. 确认反馈邮箱地址

### Phase 2：后端变更
1. `config.py` — 新增 `support_qr_image` 字段
2. `portal/router.py` — 新增 `/support` 路由 + 模板全局变量注入
3. `schemas/analytics.py` — 新增埋点映射

### Phase 3：前端变更
1. `support.html` — 新建支持页面模板
2. `base.html` — 导航+页脚+悬浮按钮+Modal
3. `guide.html` — 底部 CTA 区块
4. `apple.css` — 全部新增样式
5. `portal.js` — Modal 交互逻辑

### Phase 4：测试
1. `test_portal.py` — 新增 `/support` 页面 200 测试
2. 本地启动 → 验证 4 条支持路径全部畅通
3. `ruff check` + `ruff format` + `pytest` 全绿

### Phase 5：部署
1. `git push` → 广州服务器 `docker compose up -d --build`
2. 验证生产环境全端点

---

## 10. 设计决策

### ADR-提案：技术支持体系采用"悬浮按钮 + 专用页面"双入口

- **背景**：网站在客户端交流群功能之外，需要为网站用户提供技术支持入口。业内常规做法包括：纯页面入口、纯悬浮按钮、悬浮按钮+页面双入口。
- **方案**：选择双入口——悬浮按钮提供即时扫码进群能力（零跳转），专用 `/support` 页面汇集全部帮助资源（也利于 SEO 和社交分享）。
- **理由**：
  1. 悬浮按钮捕获"即时求助"场景，减少用户操作步骤
  2. 专用页面作为帮助信息汇总，可被搜索引擎索引、可被社交媒体分享
  3. 导航栏和页脚提供第三、第四入口，覆盖不同用户行为模式
  4. Modal 在 `base.html` 中全局注入，一次编写处处生效
  5. 全部零外部依赖，纯 HTML+CSS+vanilla JS，符合项目约束
- **影响**：新增 1 个页面、1 个路由、约 6 个文件变更。代码量小，对现有功能无影响。

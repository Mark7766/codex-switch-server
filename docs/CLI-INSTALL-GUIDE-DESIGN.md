# Codex CLI / Claude Code CLI 安装指南设计方案

> **状态**：修改中，待 Review  
> **日期**：2026-06-07  
> **决策者**：wangliang  
> **关联**：ADR-006（指南三步向导架构）

---

## 1. 背景与目标

### 1.1 现状

使用指南当前支持 2 个工具（Codex Desktop / Claude Desktop），4 个场景（macOS / Windows × 2）。

### 1.2 目标

新增 **Codex CLI** 和 **Claude Code CLI** 两个命令行工具的安装指南。

| 工具 | macOS | Windows |
|------|-------|---------|
| Codex Desktop | 已有 | 已有 |
| Claude Desktop | 已有 | 已有 |
| **Codex CLI** | **新增** | **新增** |
| **Claude Code CLI** | **新增** | **新增** |

### 1.3 核心变化

**以前的流程**：安装 CLI 工具 → 手动配置环境变量 / settings.json → 接入 DeepSeek

**现在的流程**：安装 CLI 工具 → **Codex Switch 一键配置** → 接入 DeepSeek

> Codex Switch 已经内置了 Codex CLI 和 Claude Code CLI 的配置管理功能，用户不需要手动编辑任何配置文件，不需要在终端设置环境变量。一切通过 Codex Switch 图形界面完成。

---

## 2. 交互设计

### 2.1 第一步：选择工具（扩展为 4 个卡片）

```
你要安装哪个工具？

┌────────────┐ ┌────────────┐
│  Codex     │ │  Claude    │
│  Desktop   │ │  Desktop   │
│  桌面应用   │ │  桌面应用   │
└────────────┘ └────────────┘

┌────────────┐ ┌────────────┐
│  Codex     │ │  Claude    │
│  CLI       │ │  Code CLI  │
│  命令行工具 │ │  命令行工具  │
└────────────┘ └────────────┘
```

- 2×2 网格，第一行桌面应用、第二行命令行工具
- CLI 卡片用终端风格图标区分
- 每个卡片下方标注"桌面应用"或"命令行工具"

### 2.2 第二步：选择平台（不变）

### 2.3 第三步：安装指南

CLI 工具的安装指南结构与桌面版相同（6 步线性流程），但步骤内容针对 CLI 定制。

**关键设计决策**：Codex CLI 和 Claude Code CLI 的安装**前 3 步骤完全相同**（都是安装 git → node → python），只有第 4 步安装具体 CLI 工具不同，第 5-6 步由 Codex Switch 统一完成。

---

## 3. CLI 安装前提条件（共通步骤）

Codex CLI 和 Claude Code CLI 在 Windows 上都需要三个基础环境：**git**、**Node.js**、**Python**。

macOS 用户通常已预装 git 和 Python，只需安装 Node.js。

---

## 4. Codex CLI 安装步骤

### 4.1 Codex CLI — macOS

| 步骤 | 标题 | 内容 | 截图 |
|------|------|------|------|
| ① | 获取 DeepSeek API Key |  访问 platform.deepseek.com → 创建 Key → 复制 `sk-xxx` | `step-apikey.png` |
| ② | 检查 / 安装 git | 打开**终端**，执行 `git --version`。<br>如果显示版本号 → 已安装，跳过此步。<br>如果提示 "command not found" → 终端执行 `xcode-select --install` 安装 Command Line Tools（含 git）。 | `step-cli-git-check-mac.png` |
| ③ | 检查 / 安装 Python | 终端执行 `python3 --version`。<br>如果显示版本号 → 已安装，跳过此步。<br>如果提示 "command not found" → 访问 https://pythonlang.cn/downloads/ 下载 macOS 版安装。 | `step-cli-python-check-mac.png` |
| ④ | 安装 Node.js | 访问 https://nodejs.org/zh-cn/download 下载 macOS 安装包（LTS 版本）。<br>打开 `.pkg` 文件，一直点"继续/下一步"即可。 | `step-cli-node-mac.png` |
| ⑤ | 验证环境 | 终端执行以下三条命令，确认均显示版本号：<br>`git --version`<br>`python3 --version`<br>`node --version` | `step-cli-verify-mac.png` |
| ⑥ | 安装 Codex CLI | 在终端执行：<br>`npm install -g @openai/codex`<br>等待安装完成。 | `step-cli-codex-install-mac.png` |
| ⑦ | 下载并配置 Codex Switch |  下载 Codex Switch macOS 版 → 安装 → 填入 API Key → 点击"启动代理"。| `step-config-switch.png` |
| ⑧ | 验证 | 终端执行 `codex`，确认能正常对话。<br>如报错检查 Codex Switch 代理是否运行中。 | `step-cli-codex-verify.png` |

### 4.2 Codex CLI — Windows

| 步骤 | 标题 | 内容 | 截图 |
|------|------|------|------|
| ① | 获取 DeepSeek API Key |  同上 | `step-apikey.png` |
| ② | 安装 git | 访问 https://git-scm.com/install/windows → 下载 Windows 版本。<br>安装时**一直点 "Next / 下一步"**，不需要调整任何配置。<br>安装完成后，在开始菜单搜索 **"Git Bash"**，打开它。 | `step-cli-git-install.png` |
| ③ | 安装 Node.js | 访问 https://nodejs.org/zh-cn/download → 下载 Windows 安装包（LTS 版本）。<br>安装时**一直点 "Next / 下一步"**，不需要调整任何配置。 | `step-cli-node-install.png` |
| ④ | 安装 Python | 访问 https://pythonlang.cn/downloads/ → 下载 Windows 安装包。<br>安装时**勾选 "Add Python to PATH"**（重要！），其余一直点 Next。 | `step-cli-python-install.png` |
| ⑤ | 验证环境 + 找到 Git Bash | 打开 **Git Bash**（开始菜单搜索 "Git Bash"）：<br>执行 `node --version`<br>执行 `git --version`<br>执行 `python --version`<br>均显示版本号即为成功。<br><br>**怎么找到 Git Bash？**<br>方法 1：开始菜单搜索 "Git Bash"，点击打开<br>方法 2：在任意文件夹空白处右键 → "Git Bash Here"<br>方法 3：C:\Program Files\Git\git-bash.exe | `step-cli-verify-win.png` |
| ⑥ | 安装 Codex CLI | 在 **Git Bash** 中执行：<br>`npm install -g @openai/codex`<br>等待安装完成。 | `step-cli-codex-install-win.png` |
| ⑦ | 下载并配置 Codex Switch |  下载 Codex Switch Windows 版 → 安装 → 填入 API Key → 点击"启动代理"。| `step-config-switch.png` |
| ⑧ | 验证 | 在 Git Bash 中执行 `codex`，确认能正常对话。 | `step-cli-codex-verify.png` |

---

## 5. Claude Code CLI 安装步骤

### 5.1 Claude Code CLI — macOS

| 步骤 | 标题 | 内容 | 截图 |
|------|------|------|------|
| ① | 获取 DeepSeek API Key |  同上 | `step-apikey.png` |
| ② | 检查 / 安装 git | 打开**终端**，执行 `git --version`。<br>如果显示版本号 → 已安装，跳过此步。<br>如果提示 "command not found" → 终端执行 `xcode-select --install` 安装 Command Line Tools（含 git）。 | `step-cli-git-check-mac.png` |
| ③ | 检查 / 安装 Python | 终端执行 `python3 --version`。<br>如果显示版本号 → 已安装，跳过此步。<br>如果提示 "command not found" → 访问 https://pythonlang.cn/downloads/ 下载 macOS 版安装。 | `step-cli-python-check-mac.png` |
| ④ | 安装 Node.js | 访问 https://nodejs.org/zh-cn/download 下载 macOS 安装包（LTS 版本）。<br>打开 `.pkg` 文件，一直点"继续/下一步"即可。 | `step-cli-node-mac.png` |
| ⑤ | 验证环境 | 终端执行以下三条命令，确认均显示版本号：<br>`git --version`<br>`python3 --version`<br>`node --version` | `step-cli-verify-mac.png` |
| ⑥ | 安装 Claude Code CLI | 在终端执行：<br>`npm install -g @anthropic-ai/claude-code`<br>等待安装完成。| `step-cli-claude-install-mac.png` |
| ⑦ | 下载并配置 Codex Switch |  下载 Codex Switch macOS 版 → 安装 → 填入 API Key → 点击"启动代理"。<br>进入 Codex Switch **设置 **，找到 "Claude Code CLI"，点击**"保存并应用"**按钮完成配置。 | `step-config-switch.png` |
| ⑧ | 验证 | 终端执行 `claude`，确认能进入交互界面。 | `step-cli-claude-verify.png` |

### 5.2 Claude Code CLI — Windows

| 步骤 | 标题 | 内容 | 截图 |
|------|------|------|------|
| ① | 获取 DeepSeek API Key |  同上 | `step-apikey.png` |
| ② | 安装 git | 访问 https://git-scm.com/install/windows → 下载安装。<br>**一直点 "Next / 下一步"**，不调整任何配置。<br>安装完在开始菜单搜索 **"Git Bash"**。 | `step-cli-git-install.png` |
| ③ | 安装 Node.js | 访问 https://nodejs.org/zh-cn/download → 下载 Windows 版（LTS）。<br>**一直点 "Next / 下一步"**。 | `step-cli-node-install.png` |
| ④ | 安装 Python | 访问 https://pythonlang.cn/downloads/ → 下载 Windows 版。<br>**勾选 "Add Python to PATH"**，其余一直点 Next。 | `step-cli-python-install.png` |
| ⑤ | 验证环境 + 找到 Git Bash | 打开 **Git Bash**（开始菜单搜索 "Git Bash"）：<br>执行 `node --version` / `git --version` / `python --version`<br><br>**怎么找到 Git Bash？**<br>① 开始菜单搜 "Git Bash"<br>② 文件夹空白处右键 → "Git Bash Here"<br>③ 路径：C:\Program Files\Git\git-bash.exe | `step-cli-verify-win.png` |
| ⑥ | 安装 Claude Code CLI | 在 **Git Bash** 中执行：<br>`npm install -g @anthropic-ai/claude-code`<br>等待完成。 | `step-cli-claude-install-win.png` |
| ⑦ | 下载并配置 Codex Switch |  下载 Codex Switch Windows 版 → 安装 → 填入 API Key → 点击"启动代理"。<br>进入 Codex Switch **设置**，找到 "Claude Code CLI"，点击**"保存并应用"**按钮完成配置。 | `step-config-switch.png` |
| ⑧ | 验证 | 在 Git Bash 中执行 `claude`，确认能进入交互界面。 | `step-cli-claude-verify.png` |

---

## 6. Codex Switch 统一配置架构

```
┌─────────────────────────────────────────────────┐
│                   Codex Switch                    │
│                                                   │
│  ┌─────────────────────────────────────────────┐ │
│  │  设置页面                                    │ │
│  │                                             │ │
│  │  API Key: [sk-xxxx_______]                  │ │
│  │  模型:    [DeepSeek V4 Flash ▼]             │ │
│  │  代理:    ● 运行中  http://127.0.0.1:11435   │ │
│  │                                             │ │
│  │  工具连接状态                                   │ │
│  │  ☑ Codex CLI    已检测 ✓ 自动配置           │ │
│  │  ☑ Claude Code CLI  已检测 ✓ 自动配置       │ │
│  └─────────────────────────────────────────────┘ │
│                                                   │
│  用户只需：                                       │
│  1. 填入 DeepSeek API Key                         │
│  2. 选模型                                        │
│  3. 点"启动代理"                                  │
│  4. Codex Switch 自动检测并配置所有 CLI 工具       │
└─────────────────────────────────────────────────┘
```

> **不需要**手动编辑 `~/.claude/settings.json`  
> **不需要**手动设置 `ANTHROPIC_BASE_URL` 环境变量  
> **不需要**执行 `codex config set` 命令  
> **一切由 Codex Switch 自动完成**

---

## 7. Windows CLI 安装流程总览（关键）

Windows 用户安装 CLI 工具的**统一流程**：

```
git → Node.js → Python → (Codex CLI / Claude Code CLI) → Codex Switch
│        │         │              │                            │
│        │         │              │                    填入 Key + 启动代理
│        │         │              │                    CLI 管理自动检测并配置
│        │         │              │
│        │         │              └─ 在 Git Bash 中执行 npm install -g
│        │         │                   @openai/codex 或 @anthropic-ai/claude-code
│        │         │
│        │         └─ 勾选 "Add Python to PATH"，其余 Next
│        │
│        └─ 一直 Next，不需要调任何配置
│
└─ 一直 Next，不需要调任何配置
   安装后记住怎么找到 Git Bash

macOS 用户：
  先检查 git/python 是否已安装 → 已装跳过，未装才装 → 再装 Node.js → npm install -g
```

**重要提醒**：
- 后续所有命令操作都使用 **Git Bash**，不使用 PowerShell 或 cmd
- git、Node.js、Python 安装时**全部默认选项**，一直 Next/下一步即可
- 唯一例外：Python 安装时记得**勾选 "Add Python to PATH"**
- 安装完 git 后一定要教用户**怎么找到 Git Bash**

---

## 8. 完整截图清单

目录：`src/static/images/guide/`

### 已有截图（桌面版 + 通用，复用）

| 文件名 | 场景 |
|--------|------|
| `step-apikey.png` | DeepSeek API Key 创建 |
| `step-config-switch.png` | Codex Switch 配置界面 |

### 新增 CLI 截图（macOS，6 张）

| 文件名 | 截图内容 |
|--------|---------|
| `step-cli-git-check-mac.png` | macOS 终端执行 `git --version` 的结果，或执行 `xcode-select --install` 的弹窗 |
| `step-cli-python-check-mac.png` | macOS 终端执行 `python3 --version` 的结果，或 pythonlang.cn 下载页面 |
| `step-cli-node-mac.png` | macOS Node.js 安装包下载页面或安装界面 |
| `step-cli-verify-mac.png` | macOS 终端执行三条验证命令（git / python3 / node）全部通过 |
| `step-cli-codex-install-mac.png` | macOS 终端执行 `npm install -g @openai/codex` |
| `step-cli-claude-install-mac.png` | macOS 终端执行 `npm install -g @anthropic-ai/claude-code` |

### 新增 CLI 截图（Windows，8 张）

| 文件名 | 截图内容 |
|--------|---------|
| `step-cli-git-install.png` | git-scm.com 下载页面 或 git 安装向导（一直点 Next） |
| `step-cli-node-install.png` | nodejs.org 下载页面 或 Node.js 安装向导（一直点 Next） |
| `step-cli-python-install.png` | pythonlang.cn 下载页面 或 Python 安装向导（勾选 Add to PATH） |
| `step-cli-verify-win.png` | **Git Bash** 中执行三个验证命令的输出 |
| `step-cli-codex-install-win.png` | **Git Bash** 中执行 `npm install -g @openai/codex` |
| `step-cli-claude-install-win.png` | **Git Bash** 中执行 `npm install -g @anthropic-ai/claude-code` |
| `step-cli-codex-verify.png` | Git Bash 执行 `codex hello` 的对话截图 |
| `step-cli-claude-verify.png` | Git Bash 执行 `claude` 进入交互界面的截图 |

### 总计

| 分类 | 数量 |
|------|------|
| 复用已有 | 2 张 |
| macOS CLI 新增 | 6 张 |
| Windows CLI 新增 | 8 张 |
| **合计需要截图** | **14 张新增 + 2 张复用 = 16 张** |

---

## 9. 技术实现要点（供后续开发参考）

### 9.1 不引入新的后端依赖

- CLI 工具安装通过 npm / 官方安装包，不需要 admin/packages 上传
- Codex Switch 下载复用步骤④现有的动态下载
- 所有截图放 `src/static/images/guide/`

### 9.2 guide.html 改动

- `selTool` 新增 `'codex-cli'` 和 `'claude-cli'`
- 工具选择卡片扩展为 4 个（2×2 网格）
- `renderGuide()` 新增 4 个分支的步骤内容
- CLI 场景渲染 6-8 个步骤（Windows 比 macOS 多 git/Python 步骤）
- 步骤④（下载 Codex Switch）复用现有 `loadDownloads()` 逻辑

### 9.3 各场景步骤数

| 场景 | 步骤数 | 说明 |
|------|--------|------|
| Codex CLI macOS | 8 | 检查 git → 检查 python → 装 node → 验证 → 装 codex → 装 Switch → 验证 |
| Codex CLI Windows | 8 | 装 git → 装 node → 装 python → 验证 → 装 codex → 装 Switch → 验证 |
| Claude CLI macOS | 8 | 同上结构 |
| Claude CLI Windows | 8 | 同上结构 |

> macOS 场景的"检查 git / python"步骤：已安装则跳过，未安装则安装。比 Windows 更灵活。

---

## 10. 待确认

1. Codex Switch CLI 管理功能的具体界面截图（功能已实现，后续补充截图）

---

## 11. 门户首页调整设计

### 11.1 背景

当前首页结构（从上到下）：

```
Hero（下载按钮）
下载 AI 编程工具（安装包卡片）
为什么选择 Codex Switch？（功能介绍）
用户评价
底部 CTA
```

**问题**：使用指南是目前用户访问最多的页面，但在首页没有任何入口提示。用户需要先注意到导航栏的"指南"链接才能找到。

### 11.2 目标

将使用指南提升为首页的核心入口，让用户一进入网站就知道"从指南开始"。

### 11.3 新首页布局

```
┌──────────────────────────────────────────────────┐
│ 导航栏 [Logo]                    [下载] [指南] [GitHub] │
├──────────────────────────────────────────────────┤
│                                                    │
│  Hero 区域                                         │
│  ┌────────────────────────────────────────────┐    │
│  │  让 AI 编程触手可及                          │    │
│  │  Codex Switch 帮你接入 DeepSeek              │    │
│  │                                            │    │
│  │  ┌────────────────┐ ┌──────────────────┐   │    │
│  │  │ 查看安装指南 →  │ │ 直接下载 →       │   │    │
│  │  │ 4 步完成安装    │ │ 选择平台版本      │   │    │
│  │  └────────────────┘ └──────────────────┘   │    │
│  └────────────────────────────────────────────┘    │
│                                                    │
│  安装指南（快速入口）                                │
│  ┌────────────────────────────────────────────┐    │
│  │  选择你要安装的工具                          │    │
│  │                                            │    │
│  │  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────┐ │
│  │  │ Codex    │ │ Claude   │ │ Codex  │ │Claude│ │
│  │  │ Desktop  │ │ Desktop  │ │ CLI    │ │ CLI  │ │
│  │  └──────────┘ └──────────┘ └────────┘ └──────┘ │
│  │                                            │    │
│  │  点击任一工具 → 跳转到使用指南               │    │
│  └────────────────────────────────────────────┘    │
│                                                    │
│  下载 AI 编程工具（安装包）                          │
│  ┌──────────────┐ ┌──────────────┐                │
│  │ Codex Desktop│ │Claude Desktop│                │
│  │ [下载 455MB] │ │ [下载 295MB] │                │
│  └──────────────┘ └──────────────┘                │
│                                                    │
│  为什么选择 Codex Switch？                          │
│  （功能介绍，保持现有内容）                           │
│                                                    │
│  页脚                                              │
└──────────────────────────────────────────────────┘
```

### 11.4 关键改动

| 序号 | 改动 | 说明 |
|------|------|------|
| 1 | **Hero 双按钮** | 将原来的"下载 macOS 版 / Windows 版"改为"查看安装指南 / 直接下载"，指南放在左侧更醒目位置 |
| 2 | **新增"安装指南快速入口"区块** | Hero 正下方，4 张工具卡片，点击直接跳转到 `/guide` 并预选对应工具 |
| 3 | **下载区块下移** | Codex Desktop / Claude Desktop 安装包下载放到指南入口下方 |
| 4 | 功能介绍保持 | "为什么选择"区块内容不变，位置下移 |

### 11.5 Hero 按钮交互

| 按钮 | 文案 | 点击行为 |
|------|------|---------|
| 主按钮（蓝） | "查看安装指南 →" | 跳转 `/guide` |
| 次按钮（线框） | "直接下载 →" | 跳转 `/download` |

### 11.6 指南快捷入口卡片

点击卡片跳转到 `/guide`，通过 URL 参数预选工具：

| 卡片 | URL |
|------|-----|
| Codex Desktop | `/guide?tool=codex` |
| Claude Desktop | `/guide?tool=claude` |
| Codex CLI | `/guide?tool=codex-cli` |
| Claude Code CLI | `/guide?tool=claude-cli` |

> `/guide` 页面读取 URL 参数 `?tool=xxx`，如果存在则自动跳过"选择工具"步骤，直接进入"选择平台"。

### 11.7 截图（2 张）

| 文件名 | 截图内容 |
|--------|---------|
| `homepage-hero.png` | 首页 Hero 区域，双按钮 + 指南快捷入口 |
| `homepage-full.png` | 首页完整截图（Hero + 指南入口 + 下载 + 功能介绍） |

---

## 12. 分步开发计划

### Phase 1：门户首页调整（0.5h）

- [ ] `index.html` Hero 按钮改为双按钮
- [ ] 新增"安装指南快速入口"4 卡片区块
- [ ] CSS 适配
- [ ] 测试

### Phase 2：CLI 指南开发（1h）

- [ ] `guide.html` 工具选择区扩展为 4 卡片（2×2 网格）
- [ ] `renderGuide()` 新增 4 个 CLI 场景分支
- [ ] URL 参数 `?tool=xxx` 支持预选工具
- [ ] CSS 适配 CLI 卡片样式

### Phase 3：截图补充 + 联动调试（0.5h）

- [ ] 用户提供 16 张截图，放入 `src/static/images/guide/`
- [ ] 首页截图 2 张
- [ ] 端到端测试 8 个场景的完整流程

### Phase 4：部署上线（0.25h）

- [ ] 测试通过 → commit → push → 生产部署

| Phase | 内容 | 预估 |
|-------|------|------|
| Phase 1 | 首页调整 | 0.5h |
| Phase 2 | CLI 指南 | 1h |
| Phase 3 | 截图 + 调试 | 0.5h |
| Phase 4 | 部署 | 0.25h |
| **合计** | | **约 2.25h** |

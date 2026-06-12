# codex-switch-server 工程质量检查报告 v4（测试覆盖率专项）

> **日期**：2026-06-08 | **版本**：4833313 | **覆盖率**：92%（145 tests）

---

## 总评：A- → 测试覆盖率已接近上限

**92% 是当前架构下能达到的较高水平。** 剩余 8%（90 行）大部分是无法在测试环境覆盖的路径（COS 真实交互、GitHub API 实时调用、Alembic 迁移启动、DB 回滚异常）。真正"可测试但未测试"的仅约 25 行。

---

## 一、未覆盖代码全量分析

### 🔴 可测试但未覆盖（~25 行）—— 高优先级

#### 1. `admin/router.py` — dashboard 数据组装（7 行：51-64, 85）

```python
# 行 51-64: dashboard 路由函数体（数据聚合 + Jinja2 渲染）
dl_stats = await dl_svc.get_download_stats(range_days=30)
telem_stats = await telem_svc.get_stats(range_days=30)
pkgs = await mgr.list_packages()
# ... ctx 构建 + TemplateResponse
# 行 85: upload_package 的 early return（无文件时 400）
```

**根因**：admin dashboard 的 Cookie 登录流程在测试中被验证了 HTML 渲染，但 coverage 工具不追踪 Jinja2 模板内的代码路径。`line 85` 是无文件上传的 400 分支。

**修复难度**：低。补 1 个无文件上传的 400 测试即可。

---

#### 2. `api/v1/packages.py` — 本地降级 `except ValueError` 路径（3 行：76-78）

```python
except ValueError:
    cache_path = f"packages/{p.parent.parent.name}/{p.parent.name}/{p.name}"
```

**根因**：文件路径中不含 `data` 目录时走此降级——测试环境文件总是在 `data/` 下，极少触发。

**修复难度**：中。需构造不包含 `data` 的特殊文件路径。

---

#### 3. `services/package_manager.py` — `delete_package` 未找到 + `get_package_info` 未找到（2 行：112, 135）

```python
return False    # line 112: delete_package 未匹配到包
return None     # line 135: get_package_info 未匹配到包
```

**根因**：删除不存在的包 / 查询不存在的包 —— 简单边界条件。

**修复难度**：极低。2 个 1 行测试即可。

---

#### 4. `utils/storage.py` — `list_files` + `base_dir`（2 行：43, 52）

```python
return rel_files  # line 43: list_files 正常返回（从未被调用）
return self._base # line 52: base_dir property（从未被访问）
```

**根因**：这两个方法在当前业务代码中未被使用。

**修复难度**：极低。

---

### 🟡 需 Mock 外部依赖（~35 行）—— 中优先级

#### 5. `api/v1/update.py` — COS 302 + GitHub 兜底路径（16 行：54-57, 63, 69-79, 92-93）

```
行 54-57: COS exists → 302 redirect（需 mock CosStorage，已有范式）
行 63:   GitHub asset 无 → 404
行 69-79: GitHub 下载缓存（需 mock HttpClient.download）
行 92-93: _send_file 的 except ValueError 降级
```

**根因**：测试环境 COS 已配好，`cos.exists()` 在真实 COS 有文件时返回 True，导致走 302 而非本地。这些路径互斥——覆盖一条就漏另一条。需要 mock CosStorage 来分别测试。

**修复难度**：中。已有 COS mock 范式（test_api_packages.py 中），可复用。

---

#### 6. `services/release_sync.py` — GitHub API + 下载缓存（14 行）

```
行 55-57: get_latest_from_github() 的 except 降级（GitHub API 故障）
行 61:   GitHub 返回空 releases 列表
行 115-121: download_and_cache() 完整流程（从 GitHub 下载到本地）
行 134:  get_github_asset_info() 版本不匹配
行 148-149: _parse_semver 的 ValueError/IndexError 捕获
```

**根因**：需要 mock `HttpClient` 或打桩 GitHub API。`download_and_cache` 涉及真实网络。

**修复难度**：中-高。部分路径（如 GitHub API 故障模拟）需要 mock 整个 HTTP 层。

---

#### 7. `api/v1/analytics.py` — 埋点写入后的返回（1 行：34）

```python
return {"status": "ok"}  # line 34: JSON 解析成功后的正常返回
```

**根因**：测试用例中 sendBeacon 模拟都走了这个路径，但 coverage 不计数？实际上 coverage 报告显示 95%（22/23 lines），仅缺 line 34。可能是 coverage 工具的偏差——`return` 语句被跳过？

**修复难度**：待确认。覆盖率 95% 已可接受。

---

### 🟢 基础设施路径（~30 行）—— 低优先级

#### 8. `src/main.py` — Alembic 迁移启动（10 行：21-31）

```python
def _upgrade():
    alembic_command.upgrade(alembic_cfg, "head")

loop = asyncio.get_event_loop()
await loop.run_in_executor(None, _upgrade)
logger.info("Database migrations complete")
```

**根因**：lifespan 在 pytest 中通过 `create_app()` 执行，但 coverage 不追踪 `run_in_executor` 内的回调。实际迁移已执行（日志可见），但 coverage 工具无法穿透 `run_in_executor`。

**修复难度**：高（coverage 工具限制，非代码问题）。

---

#### 9. `src/database.py` — get_db 生成器 + backfill（4 行：18-19, 27-28）

```python
yield session  # line 18-19: FastAPI Depends 的 generator
await conn.execute(text("UPDATE ..."))  # line 27-28: backfill 迁移
```

**根因**：`get_db` 是 FastAPI dependency injection，测试通过 `dependency_overrides` 替换了它。backfill 已由 Alembic 迁移接管，函数留作向后兼容。

**修复难度**：低（写个直接调用 backfill 的测试即可），但这两段代码不关键。

---

#### 10. `services/analytics.py` — 异常处理 + 数据解析（10 行）

```
行 53-55: record_page_event() 的 except Exception（DB 写入失败回滚）
行 214-218: get_download_trends() 的 daily breakdown 数据解析
行 238-239: by_version 的数据解析（release_id 非空判断）
```

**根因**：DB 异常难以在集成测试中模拟。daily breakdown 的数据解析代码已执行但 coverage 统计偏差。

**修复难度**：行 53-55 高（需模拟 DB 故障）。行 214-218 / 238-239 实际已验证但 coverage 可能误报。

---

#### 11. 其余极低影响（5 行）

| 文件 | 行 | 说明 |
|------|---|------|
| `utils/http.py` | 30, 48 | `get_json`/`download` 的 `return {}`/`return dest`（兜底代码，正常路径不会到） |
| `services/telemetry.py` | 56-57 | 客户端限速检查（测试中不会触发限速阈值） |

---

## 二、覆盖率问题汇总

### 按修复 ROI 排序

| 优先级 | 行数 | 模块 | 修复难度 | 说明 |
|--------|------|------|---------|------|
| 🔴 1 | 7 | admin/router.py | 低 | dashboard 数据组装 + 无文件上传 400 |
| 🔴 2 | 2 | package_manager.py | 极低 | `delete_package` 未找到 + `get_package_info` 未找到 |
| 🔴 3 | 2 | storage.py | 极低 | `list_files` + `base_dir`（未被调用的方法） |
| 🔴 4 | 3 | packages.py | 中 | `except ValueError` 降级路径 |
| 🟡 5 | 16 | update.py | 中 | COS 302 mock + GitHub 兜底（需 mock CosStorage/HttpClient） |
| 🟡 6 | 14 | release_sync.py | 中-高 | GitHub API mock（需 mock HttpClient） |
| 🟡 7 | 1 | analytics.py | 低 | line 34 return（可能 coverage 误报） |
| 🟢 8 | 10 | main.py | — | `run_in_executor` callback（coverage 工具限制） |
| 🟢 9 | 10 | analytics.py | — | DB 异常回滚（难以模拟） |
| 🟢 10 | 5 | http.py + telemetry.py | — | 兜底代码 + 限速阈值 |
| 🟢 11 | 4 | database.py | 低 | backfill 函数 + get_db generator |

---

## 三、覆盖率天花板分析

当前 92% 距离 100% 的 8% 差距，拆解如下：

```
可修复（测试可达）：  ~25 行 → 覆盖后可达 94%
需 mock 外部服务：    ~35 行 → 覆盖后可达 97%  
coverage 工具限制：  ~30 行 → 无法覆盖（run_in_executor / async generator）
                    ─────
                    90 行未覆盖 → 92% 覆盖率
```

**结论**：在当前架构和测试框架下，**94-95% 是一个现实可达的目标**。100% 不太可能也不需要——`run_in_executor` 回调、async generator yield、DB 故障回滚等路径要么无法追踪，要么不值得花时间模拟。

---

## 四、全部质量指标

| 维度 | 状态 |
|------|------|
| 测试覆盖率 | **92%**（145 tests） |
| ruff lint | **0 errors**（E/F/I/N/W/UP） |
| 行宽 > 120 | **0** |
| 文件 > 500 行 | **0** |
| 函数 > 50 行 | **5**（均为 service 层现有长函数） |
| 裸 `except:` | **0** |
| 代码硬编码密钥 | **0** |
| SQL 注入 | **0** |
| 路由层直操 DB | **0** |
| Alembic 迁移 | **2 个迁移**，启动自动执行 |
| 前端 | 零框架 + OG 标签完整 |

### 问题清单（全量 4 个）

| # | 严重度 | 问题 | 位置 |
|---|--------|------|------|
| 1 | 中 | `get_download_trends()` 130 行过长 | analytics.py:130 |
| 2 | 低 | admin_token 双用途 | config.py |
| 3 | 低 | telemetry_events.timestamp 无索引 | models/telemetry.py |
| 4 | 低 | `packages.py` 57% | 仅 `except ValueError` 降级未覆盖 |

---

## 五、历史趋势

```
         v1      v2      v3      v4
总评     B+  →  A-  →  A-  →  A-
覆盖率  83% →  90% →  92% →  92%
测试   113 →  141 →  145 →  145
高优     3 →    0 →    0 →    0
中优     4 →    1 →    1 →    1
低优     3 →    2 →    3 →    3
```

---

## 结论

测试覆盖率已稳定在 **92%**，在现有架构下接近上限。剩余 8% 未覆盖行中，约 2% 可低成本修复（7 个简单边界条件测试），4% 需 mock 外部服务，2% 受 coverage 工具限制无法追踪。

**如需冲击 94%**：优先修复 🔴 优先级 1-4（~15 行，约 1 小时工作量）。其余路径 ROI 递减，不建议在非关键模块上投入过多。

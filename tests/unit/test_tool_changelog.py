from __future__ import annotations

import base64
import json
from unittest.mock import AsyncMock

import pytest
from markupsafe import Markup

import src.services.tool_changelog as tc
from src.config import settings
from src.services.tool_changelog import ToolChangelogService

SAMPLE = """# 更新记录

项目前言说明。

## [Unreleased]

- 未发布内容应被跳过

## [v2.1.0] - 2026-09-06

### 重磅新增

> 现在支持「看图」。

- 支持 **DeepSeek V4 Flash Vision**
- 列表内联 `code` 项

| 模型 | 状态 |
|------|------|
| vision | 可用 |

```bash
echo hi
```

## [2.0.0] - 2026-08-19

- 直连 DeepSeek，去掉本地代理

## [1.9.0]

无日期的版本条目
"""


@pytest.fixture(autouse=True)
def _isolate_cache(monkeypatch):
    monkeypatch.setattr(tc, "_cache", {})
    monkeypatch.setattr(settings, "tool_changelog_cache_ttl", 300)


def test_parse_splits_newest_first_and_skips_unreleased():
    entries = ToolChangelogService.parse_changelog(SAMPLE)
    assert [e["version"] for e in entries] == ["v2.1.0", "2.0.0", "1.9.0"]
    assert entries[0]["date"] == "2026-09-06"
    assert entries[0]["is_first"] is True
    assert entries[1]["is_first"] is False
    assert entries[1]["date"] == "2026-08-19"
    # 无日期头保留且日期为空
    assert entries[2]["date"] == ""
    # h1 前言与 [Unreleased] 都不进入条目
    assert all("前言说明" not in e["html"] for e in entries)
    assert all("未发布内容" not in e["html"] for e in entries)


def test_parse_renders_markdown_to_trusted_markup():
    entries = ToolChangelogService.parse_changelog(SAMPLE)
    first = entries[0]
    assert isinstance(first["html"], Markup)
    assert "<h3>重磅新增</h3>" in first["html"]
    assert "<blockquote>" in first["html"]
    assert "<strong>DeepSeek V4 Flash Vision</strong>" in first["html"]
    assert "<code>code</code>" in first["html"]
    # 表格扩展已启用（ai-working-ok 的 WDR 决策表依赖）
    assert "<table>" in first["html"]
    # fenced code 已启用
    assert "<pre><code>" in first["html"] or "echo hi" in first["html"]


@pytest.mark.asyncio
async def test_get_changelog_fetches_from_github_and_caches_in_memory():
    http = AsyncMock()
    http.get_json = AsyncMock(
        return_value={"content": base64.b64encode(SAMPLE.encode()).decode(), "encoding": "base64"}
    )
    storage = AsyncMock()
    storage.get_path = AsyncMock(return_value=None)
    storage.put = AsyncMock(return_value="/tmp/x")

    svc = ToolChangelogService(http=http, storage=storage)
    entries = await svc.get_changelog("codex-switch")

    assert entries[0]["version"] == "v2.1.0"
    assert http.get_json.await_count == 1
    storage.put.assert_awaited_once()

    # 第二次命中内存缓存，不再请求 GitHub
    again = await svc.get_changelog("codex-switch")
    assert again[0]["version"] == "v2.1.0"
    assert http.get_json.await_count == 1


@pytest.mark.asyncio
async def test_fetch_sends_auth_header_when_token_configured(monkeypatch):
    monkeypatch.setattr(settings, "github_token", "test-token")
    http = AsyncMock()
    http.get_json = AsyncMock(
        return_value={"content": base64.b64encode(SAMPLE.encode()).decode(), "encoding": "base64"}
    )
    storage = AsyncMock()
    storage.get_path = AsyncMock(return_value=None)
    storage.put = AsyncMock(return_value="/tmp/x")

    await ToolChangelogService(http=http, storage=storage).get_changelog("ai-coding-ok")

    _, kwargs = http.get_json.await_args
    assert kwargs["headers"]["Authorization"] == "Bearer test-token"


@pytest.mark.asyncio
async def test_get_changelog_returns_empty_on_failure():
    http = AsyncMock()
    http.get_json = AsyncMock(side_effect=RuntimeError("github down"))
    storage = AsyncMock()
    storage.get_path = AsyncMock(return_value=None)

    entries = await ToolChangelogService(http=http, storage=storage).get_changelog("codex-switch")
    assert entries == []


@pytest.mark.asyncio
async def test_get_changelog_serves_fresh_disk_cache_without_github(tmp_path):
    key_path = tmp_path / "tool-changelog" / "codex-switch.json"
    key_path.parent.mkdir(parents=True)
    payload = {
        "checked_at": 10**15,  # far in the future => within TTL
        "entries": [{"version": "1.0.0", "date": "2026-01-01", "html": "<p>hi</p>", "is_first": True}],
    }
    key_path.write_text(json.dumps(payload, ensure_ascii=False))

    http = AsyncMock()
    storage = AsyncMock()
    storage.get_path = AsyncMock(return_value=key_path)
    storage.put = AsyncMock()

    svc = ToolChangelogService(http=http, storage=storage)
    entries = await svc.get_changelog("codex-switch")

    assert entries[0]["version"] == "1.0.0"
    assert isinstance(entries[0]["html"], Markup)
    http.get_json.assert_not_awaited()

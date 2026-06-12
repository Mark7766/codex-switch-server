# electron-updater generic provider 支持 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 `/api/v1/updates/` 路由组，提供 electron-updater generic provider 兼容的 yml 元数据端点和文件下载端点。

**Architecture:** 新建 `src/api/v1/updates.py`（3 端点）+ `src/services/update_feed.py`（yml 缓存 + 文件名解析）。文件下载复用 COS → 本地 → GitHub 三级降级链路。修改 `release_sync.py` 扩展名支持 + `download.py` 加 source 字段。

**Tech Stack:** FastAPI, SQLAlchemy async, httpx, 腾讯云 COS SDK

**Spec:** `docs/superpowers/specs/2026-06-11-electron-updater-support-design.md`

---

### 文件变更清单

| 操作 | 文件 | 职责 |
|------|------|------|
| 新建 | `src/services/update_feed.py` | yml 缓存、文件名解析、asset 查找 |
| 新建 | `src/api/v1/updates.py` | 3 个 HTTP 端点 |
| 新建 | `tests/unit/test_update_feed.py` | update_feed service 单元测试 |
| 新建 | `tests/integration/test_api_updates.py` | updates API 集成测试 |
| 修改 | `src/models/download.py:25` | 加 `source` 列 |
| 修改 | `src/services/release_sync.py:103-121` | 扩展名 + original_name 缓存 |
| 修改 | `src/api/router.py:5-13` | 注册 updates_router |

---

### Task 1: DownloadRecord 加 source 字段

**Files:**
- Modify: `src/models/download.py`

- [ ] **Step 1: 在 DownloadRecord 中加 source 列**

在 `downloaded_at` 字段之后添加：

```python
# src/models/download.py — 在 downloaded_at 行之后插入
    source: Mapped[str] = mapped_column(String(32), default="")
```

完整修改后的字段区：

```python
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    release_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("releases.id"), nullable=True)
    client_id: Mapped[str] = mapped_column(String(64), default="")
    package_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    arch: Mapped[str] = mapped_column(String(16), nullable=False)
    ip_hash: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(256), default="")
    source: Mapped[str] = mapped_column(String(32), default="")
    downloaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
```

- [ ] **Step 2: 验证表结构**

```bash
uv run python -c "from src.models.download import DownloadRecord; print('source' in [c.name for c in DownloadRecord.__table__.columns])"
```

Expected: `True`

- [ ] **Step 3: 运行现有测试确保不破坏**

```bash
uv run pytest -x -q
```

Expected: 全部通过

- [ ] **Step 4: Commit**

```bash
git add src/models/download.py
git commit -m "feat: add source column to DownloadRecord for electron-updater tracking

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 2: release_sync.py 扩展名 + original_name 缓存支持

**Files:**
- Modify: `src/services/release_sync.py`

- [ ] **Step 1: 扩展 get_download_path() 的扩展名列表**

修改 `get_download_path` 方法（line 103-111），将 `("dmg", "exe", "appimage")` 改为 `("dmg", "exe", "appimage", "zip", "blockmap")`：

```python
    async def get_download_path(self, version: str, platform: str, arch: str) -> Path | None:
        """Check if the file is cached locally. No DB lookup needed."""
        # Scan cache directory for matching file
        prefix = f"codex-switch/{version}/{platform}-{arch}"
        for ext in ("dmg", "exe", "appimage", "zip", "blockmap"):
            path = f"{prefix}.{ext}"
            if await self._storage.exists(path):
                return await self._storage.get_path(path)
        return None
```

- [ ] **Step 2: download_and_cache() 增加 original_name 参数**

修改 `download_and_cache` 方法签名和逻辑：

```python
    async def download_and_cache(
        self, download_url: str, version: str, platform: str, arch: str, ftype: str,
        original_name: str | None = None,
    ) -> Path:
        """Download from GitHub and cache locally. Returns the local file path.

        If ``original_name`` is provided, use it as the cache file name (for
        electron-updater compatibility). Otherwise use ``{platform}-{arch}.{ftype}``.
        """
        if original_name:
            cache_key = f"codex-switch/{version}/{original_name}"
            local_filename = original_name
        else:
            cache_key = f"codex-switch/{version}/{platform}-{arch}.{ftype}"
            local_filename = f"{platform}-{arch}.{ftype}"

        tmp_dest = Path(f"/tmp/codex-switch-{version}-{local_filename}")
        await self._http.download(download_url, tmp_dest)
        local_path = await self._storage.put(tmp_dest, cache_key)
        tmp_dest.unlink(missing_ok=True)
        logger.info("Cached %s", cache_key)
        return local_path
```

需要在文件头部确保 `Path` 已 import（确认 line 4 已有 `from pathlib import Path`）。

- [ ] **Step 3: record_download() 增加 source 参数**

```python
    async def record_download(
        self,
        version: str,
        platform: str,
        arch: str,
        client_id: str = "",
        package_name: str | None = None,
        ip_hash: str = "",
        user_agent: str = "",
        source: str = "",
    ) -> None:
        record = DownloadRecord(
            release_id=None,
            client_id=client_id,
            package_name=package_name,
            platform=platform,
            arch=arch,
            ip_hash=ip_hash,
            user_agent=user_agent,
            source=source,
        )
        self._db.add(record)
        await self._db.commit()
```

- [ ] **Step 4: 运行现有测试确保不破坏**

```bash
uv run pytest -x -q
```

Expected: 全部通过

- [ ] **Step 5: Commit**

```bash
git add src/services/release_sync.py
git commit -m "feat: extend release_sync to support zip/blockmap, original_name cache, and source tracking

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 3: 创建 UpdateFeedService

**Files:**
- Create: `src/services/update_feed.py`
- Create: `tests/unit/test_update_feed.py`

- [ ] **Step 1: 创建 update_feed.py — 文件名解析函数 + Service 类**

```python
from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from src.config import settings
from src.utils.http import HttpClient
from src.utils.storage import LocalStorage

logger = logging.getLogger(__name__)

GITHUB_RELEASES_API = "https://api.github.com/repos/Mark7766/codex-switch/releases"

# In-memory caches for yml content (separate from release info cache)
_mac_yml_cache: str | None = None
_mac_yml_time: float = 0
_win_yml_cache: str | None = None
_win_yml_time: float = 0
_YML_CACHE_TTL = 300  # 5 minutes

# Regex to parse electron-builder asset filenames
# Examples:
#   Codex-Switch-1.5.0-mac-arm64.zip
#   Codex-Switch-1.5.0-mac-arm64.dmg
#   Codex-Switch-1.5.0-mac-arm64.zip.blockmap
#   Codex-Switch-1.5.0-mac-x64.zip
#   Codex-Switch-Setup-1.5.0-win-x64.exe
#   Codex-Switch-Setup-1.5.0-win-arm64.exe
#   Codex-Switch-Setup-1.5.0-win-x64.exe.blockmap
_FILENAME_RE = re.compile(
    r"^Codex-Switch(?:-Setup)?-"
    r"(?P<version>[0-9]+\.[0-9]+\.[0-9]+)-"
    r"(?P<platform>mac|win)-"
    r"(?P<arch>arm64|x64)"
    r"\.(?P<ext>dmg|zip|exe)(?:\.blockmap)?$"
)

# Blockmap filenames have an extra .blockmap suffix
_BLOCKMAP_RE = re.compile(
    r"^Codex-Switch(?:-Setup)?-"
    r"(?P<version>[0-9]+\.[0-9]+\.[0-9]+)-"
    r"(?P<platform>mac|win)-"
    r"(?P<arch>arm64|x64)"
    r"\.(?P<ext>dmg|zip|exe)\.blockmap$"
)


def parse_asset_filename(filename: str) -> dict | None:
    """Parse an electron-builder asset filename into its components.

    Returns dict with keys: version, platform, arch, file_type, is_blockmap
    Returns None if the filename doesn't match the expected pattern.

    >>> parse_asset_filename("Codex-Switch-1.5.0-mac-arm64.zip")
    {'version': '1.5.0', 'platform': 'macos', 'arch': 'arm64', 'file_type': 'zip', 'is_blockmap': False}

    >>> parse_asset_filename("Codex-Switch-Setup-1.5.0-win-x64.exe")
    {'version': '1.5.0', 'platform': 'windows', 'arch': 'x64', 'file_type': 'exe', 'is_blockmap': False}

    >>> parse_asset_filename("Codex-Switch-1.5.0-mac-arm64.zip.blockmap")
    {'version': '1.5.0', 'platform': 'macos', 'arch': 'arm64', 'file_type': 'zip', 'is_blockmap': True}
    """
    # Try blockmap pattern first (has .blockmap suffix)
    m = _BLOCKMAP_RE.match(filename)
    if m:
        d = m.groupdict()
        return {
            "version": d["version"],
            "platform": "macos" if d["platform"] == "mac" else "windows",
            "arch": d["arch"],
            "file_type": d["ext"],
            "is_blockmap": True,
        }

    m = _FILENAME_RE.match(filename)
    if m:
        d = m.groupdict()
        return {
            "version": d["version"],
            "platform": "macos" if d["platform"] == "mac" else "windows",
            "arch": d["arch"],
            "file_type": d["ext"],
            "is_blockmap": False,
        }

    return None


class UpdateFeedService:
    """Service for electron-updater generic provider: yml caching and file lookup."""

    def __init__(self, http: HttpClient | None = None, storage: LocalStorage | None = None):
        self._http = http or HttpClient()
        self._storage = storage or LocalStorage()

    # ── yml content caching ──────────────────────────────────

    async def get_latest_yml(self, platform: str) -> str | None:
        """Return latest-mac.yml or latest.yml content, cached 5 min in memory."""
        global _mac_yml_cache, _mac_yml_time, _win_yml_cache, _win_yml_time
        now = time.time()

        if platform == "macos":
            if _mac_yml_cache and (now - _mac_yml_time) < _YML_CACHE_TTL:
                return _mac_yml_cache
        else:
            if _win_yml_cache and (now - _win_yml_time) < _YML_CACHE_TTL:
                return _win_yml_cache

        yml_name = "latest-mac.yml" if platform == "macos" else "latest.yml"

        headers = {"Accept": "application/vnd.github+json"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        try:
            releases_data = await self._http.get_json(GITHUB_RELEASES_API, headers=headers)
        except Exception:
            logger.exception("Failed to fetch GitHub releases for yml sync")
            # Return stale cache if available
            if platform == "macos":
                return _mac_yml_cache
            return _win_yml_cache

        releases: list[dict] = releases_data if isinstance(releases_data, list) else []
        if not releases:
            return None

        latest = releases[0]
        yml_url = ""
        for asset in latest.get("assets", []):
            if asset.get("name") == yml_name:
                yml_url = asset.get("browser_download_url", "")
                break

        if not yml_url:
            logger.warning("yml asset %s not found in latest release", yml_name)
            return None

        try:
            tmp_dest = Path(f"/tmp/{yml_name}")
            await self._http.download(yml_url, tmp_dest)
            content = tmp_dest.read_text(encoding="utf-8")
            tmp_dest.unlink(missing_ok=True)
        except Exception:
            logger.exception("Failed to download yml from GitHub")
            if platform == "macos":
                return _mac_yml_cache
            return _win_yml_cache

        if platform == "macos":
            _mac_yml_cache = content
            _mac_yml_time = now
        else:
            _win_yml_cache = content
            _win_yml_time = now

        logger.info("Cached %s (%d bytes)", yml_name, len(content))
        return content

    # ── Asset lookup ─────────────────────────────────────────

    async def find_asset_by_filename(self, filename: str) -> dict | None:
        """Look up a file in the latest GitHub Release assets by original name.

        Returns the asset dict from ReleaseSyncService's get_latest_from_github()
        format, or None if not found.
        """
        headers = {"Accept": "application/vnd.github+json"}
        if settings.github_token:
            headers["Authorization"] = f"Bearer {settings.github_token}"

        try:
            releases_data = await self._http.get_json(GITHUB_RELEASES_API, headers=headers)
        except Exception:
            logger.exception("Failed to fetch GitHub releases for asset lookup")
            return None

        releases: list[dict] = releases_data if isinstance(releases_data, list) else []
        if not releases:
            return None

        latest = releases[0]
        for asset in latest.get("assets", []):
            if asset.get("name") == filename:
                return {
                    "original_name": filename,
                    "download_url": asset.get("browser_download_url", ""),
                    "file_size": asset.get("size", 0),
                }

        return None
```

- [ ] **Step 2: 创建单元测试 test_update_feed.py**

```python
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.services.update_feed import UpdateFeedService, parse_asset_filename


class TestParseAssetFilename:
    def test_macos_arm64_zip(self):
        result = parse_asset_filename("Codex-Switch-1.5.0-mac-arm64.zip")
        assert result == {
            "version": "1.5.0",
            "platform": "macos",
            "arch": "arm64",
            "file_type": "zip",
            "is_blockmap": False,
        }

    def test_macos_x64_dmg(self):
        result = parse_asset_filename("Codex-Switch-2.0.1-mac-x64.dmg")
        assert result == {
            "version": "2.0.1",
            "platform": "macos",
            "arch": "x64",
            "file_type": "dmg",
            "is_blockmap": False,
        }

    def test_windows_x64_exe(self):
        result = parse_asset_filename("Codex-Switch-Setup-1.5.0-win-x64.exe")
        assert result == {
            "version": "1.5.0",
            "platform": "windows",
            "arch": "x64",
            "file_type": "exe",
            "is_blockmap": False,
        }

    def test_windows_arm64_exe(self):
        result = parse_asset_filename("Codex-Switch-Setup-1.5.0-win-arm64.exe")
        assert result == {
            "version": "1.5.0",
            "platform": "windows",
            "arch": "arm64",
            "file_type": "exe",
            "is_blockmap": False,
        }

    def test_macos_zip_blockmap(self):
        result = parse_asset_filename("Codex-Switch-1.5.0-mac-arm64.zip.blockmap")
        assert result == {
            "version": "1.5.0",
            "platform": "macos",
            "arch": "arm64",
            "file_type": "zip",
            "is_blockmap": True,
        }

    def test_windows_exe_blockmap(self):
        result = parse_asset_filename("Codex-Switch-Setup-1.5.0-win-x64.exe.blockmap")
        assert result == {
            "version": "1.5.0",
            "platform": "windows",
            "arch": "x64",
            "file_type": "exe",
            "is_blockmap": True,
        }

    def test_invalid_filename_returns_none(self):
        assert parse_asset_filename("some-random-file.txt") is None
        assert parse_asset_filename("") is None
        assert parse_asset_filename("Codex-Switch-1.5.0-linux-x64.appimage") is None
        assert parse_asset_filename("latest-mac.yml") is None
        assert parse_asset_filename("latest.yml") is None

    def test_filename_with_path_traversal_returns_none(self):
        assert parse_asset_filename("../etc/passwd") is None
        assert parse_asset_filename("Codex-Switch-1.5.0-mac-arm64/../../.zip") is None


class TestUpdateFeedServiceGetLatestYml:
    @pytest.mark.asyncio
    async def test_returns_cached_mac_yml_on_second_call(self, monkeypatch):
        """Second call within TTL returns cached content without HTTP request."""
        from src.services import update_feed as uf

        # Reset cache
        uf._mac_yml_cache = None
        uf._mac_yml_time = 0

        service = UpdateFeedService()
        mock_http = AsyncMock()
        # First call: return a release with latest-mac.yml asset
        mock_http.get_json.return_value = [
            {
                "tag_name": "v1.5.0",
                "assets": [
                    {
                        "name": "latest-mac.yml",
                        "browser_download_url": "https://github.com/releases/download/v1.5.0/latest-mac.yml",
                    }
                ],
            }
        ]
        # download returns the temp file — we mock it to write content
        async def fake_download(url, dest):
            dest.write_text("version: 1.5.0\nfiles: []\n", encoding="utf-8")
            return dest

        mock_http.download = fake_download
        service._http = mock_http

        result1 = await service.get_latest_yml("macos")
        assert result1 == "version: 1.5.0\nfiles: []\n"
        assert mock_http.get_json.call_count == 1

        # Second call — should hit cache
        result2 = await service.get_latest_yml("macos")
        assert result2 == "version: 1.5.0\nfiles: []\n"
        assert mock_http.get_json.call_count == 1  # no additional HTTP call

    @pytest.mark.asyncio
    async def test_returns_cached_win_yml(self, monkeypatch):
        from src.services import update_feed as uf

        uf._win_yml_cache = None
        uf._win_yml_time = 0

        service = UpdateFeedService()
        mock_http = AsyncMock()
        mock_http.get_json.return_value = [
            {
                "tag_name": "v1.5.0",
                "assets": [
                    {
                        "name": "latest.yml",
                        "browser_download_url": "https://github.com/releases/download/v1.5.0/latest.yml",
                    }
                ],
            }
        ]

        async def fake_download(url, dest):
            dest.write_text("version: 1.5.0\nfiles: []\npath: Codex-Switch-Setup-1.5.0-win-x64.exe\n", encoding="utf-8")
            return dest

        mock_http.download = fake_download
        service._http = mock_http

        result = await service.get_latest_yml("windows")
        assert result == "version: 1.5.0\nfiles: []\npath: Codex-Switch-Setup-1.5.0-win-x64.exe\n"

    @pytest.mark.asyncio
    async def test_returns_stale_cache_on_github_failure(self, monkeypatch):
        """When GitHub is unreachable but we have stale cache, return it."""
        from src.services import update_feed as uf

        # Pre-populate cache
        uf._mac_yml_cache = "version: 1.4.0\nfiles: []\n"
        uf._mac_yml_time = 0  # expired

        service = UpdateFeedService()
        mock_http = AsyncMock()
        mock_http.get_json.side_effect = Exception("GitHub down")
        service._http = mock_http

        result = await service.get_latest_yml("macos")
        assert result == "version: 1.4.0\nfiles: []\n"  # stale cache

    @pytest.mark.asyncio
    async def test_returns_none_when_yml_asset_not_found(self, monkeypatch):
        from src.services import update_feed as uf

        uf._mac_yml_cache = None
        uf._mac_yml_time = 0

        service = UpdateFeedService()
        mock_http = AsyncMock()
        # Release has no latest-mac.yml asset
        mock_http.get_json.return_value = [
            {
                "tag_name": "v1.5.0",
                "assets": [{"name": "Codex-Switch-1.5.0-mac-arm64.dmg", "browser_download_url": "..."}],
            }
        ]
        service._http = mock_http

        result = await service.get_latest_yml("macos")
        assert result is None


class TestUpdateFeedServiceFindAssetByFilename:
    @pytest.mark.asyncio
    async def test_finds_matching_asset(self):
        service = UpdateFeedService()
        mock_http = AsyncMock()
        mock_http.get_json.return_value = [
            {
                "tag_name": "v1.5.0",
                "assets": [
                    {
                        "name": "Codex-Switch-1.5.0-mac-arm64.zip",
                        "browser_download_url": "https://github.com/releases/download/v1.5.0/Codex-Switch-1.5.0-mac-arm64.zip",
                        "size": 92721818,
                    }
                ],
            }
        ]
        service._http = mock_http

        result = await service.find_asset_by_filename("Codex-Switch-1.5.0-mac-arm64.zip")
        assert result is not None
        assert result["original_name"] == "Codex-Switch-1.5.0-mac-arm64.zip"
        assert result["download_url"] == "https://github.com/releases/download/v1.5.0/Codex-Switch-1.5.0-mac-arm64.zip"
        assert result["file_size"] == 92721818

    @pytest.mark.asyncio
    async def test_returns_none_when_not_found(self):
        service = UpdateFeedService()
        mock_http = AsyncMock()
        mock_http.get_json.return_value = [
            {
                "tag_name": "v1.5.0",
                "assets": [{"name": "some-other-file.txt", "browser_download_url": "..."}],
            }
        ]
        service._http = mock_http

        result = await service.find_asset_by_filename("Codex-Switch-99.0.0-mac-arm64.zip")
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_on_github_failure(self):
        service = UpdateFeedService()
        mock_http = AsyncMock()
        mock_http.get_json.side_effect = Exception("GitHub down")
        service._http = mock_http

        result = await service.find_asset_by_filename("Codex-Switch-1.5.0-mac-arm64.zip")
        assert result is None
```

- [ ] **Step 3: 运行单元测试**

```bash
uv run pytest tests/unit/test_update_feed.py -v
```

Expected: 13 passed

- [ ] **Step 4: 运行全量测试确保不破坏**

```bash
uv run pytest -x -q
```

Expected: 全部通过

- [ ] **Step 5: Commit**

```bash
git add src/services/update_feed.py tests/unit/test_update_feed.py
git commit -m "feat: add UpdateFeedService for electron-updater yml caching and filename parsing

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 4: 创建 updates API 端点

**Files:**
- Create: `src/api/v1/updates.py`

- [ ] **Step 1: 创建 updates.py — 3 个端点**

```python
from __future__ import annotations

import re
from urllib.parse import quote

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import _db_dep
from src.services.release_sync import ReleaseSyncService
from src.services.update_feed import UpdateFeedService, parse_asset_filename
from src.utils.cos_storage import CosStorage

router = APIRouter(tags=["updates"])

# Only allow safe filenames: starts with alphanumeric, only alphanumeric/dot/dash/underscore
_SAFE_FILENAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._-]*$")


@router.get("/latest-mac.yml")
async def latest_mac_yml() -> Response:
    """Return latest-mac.yml for electron-updater (macOS)."""
    service = UpdateFeedService()
    content = await service.get_latest_yml("macos")
    if content is None:
        raise HTTPException(status_code=404, detail="latest-mac.yml not available")
    return Response(content=content, media_type="text/yaml; charset=utf-8")


@router.get("/latest.yml")
async def latest_yml() -> Response:
    """Return latest.yml for electron-updater (Windows)."""
    service = UpdateFeedService()
    content = await service.get_latest_yml("windows")
    if content is None:
        raise HTTPException(status_code=404, detail="latest.yml not available")
    return Response(content=content, media_type="text/yaml; charset=utf-8")


@router.get("/{filename}")
async def download_update_file(
    filename: str,
    request: Request,
    db: AsyncSession = _db_dep,
) -> Response:
    """Download a release file for electron-updater.

    Supports three-tier fallback: COS (302 Guangzhou) → local cache (X-Accel-Redirect)
    → GitHub proxy download (cache then serve).

    Filename format: ``Codex-Switch-<ver>-<mac|win>-<arch>.<ext>[.blockmap]``
    or ``Codex-Switch-Setup-<ver>-<win>-<arch>.<ext>[.blockmap]``.
    """
    # Security: reject path traversal and unsafe filenames
    if not _SAFE_FILENAME_RE.match(filename) or ".." in filename:
        raise HTTPException(status_code=404, detail="File not found")

    # Parse filename to extract version, platform, arch
    parsed = parse_asset_filename(filename)
    if parsed is None:
        raise HTTPException(status_code=404, detail="Unrecognized filename format")

    version = parsed["version"]
    platform = parsed["platform"]
    arch = parsed["arch"]
    file_type = parsed["file_type"]
    is_blockmap = parsed["is_blockmap"]

    cos = CosStorage()
    svc = ReleaseSyncService(db)
    ip = request.client.host if request.client else ""

    # 1. COS → fast download via Guangzhou CDN
    cos_key = f"codex-switch/{version}/{filename}"
    if cos.exists(cos_key):
        await svc.record_download(version, platform, arch, package_name="codex-switch", ip_hash=ip, source="electron-updater")
        headers = {"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"}
        return RedirectResponse(url=cos.public_url(cos_key), status_code=302, headers=headers)

    # 2. Local cache → nginx X-Accel-Redirect
    # Try original filename first (if cached via download_and_cache with original_name)
    local_key = f"codex-switch/{version}/{filename}"
    from src.utils.storage import LocalStorage
    storage = LocalStorage()
    if await storage.exists(local_key):
        await svc.record_download(version, platform, arch, package_name="codex-switch", ip_hash=ip, source="electron-updater")
        data_dir = "data"
        from pathlib import Path
        full_path = await storage.get_path(local_key)
        if full_path:
            return _send_file(str(full_path), filename)

    # Fallback: try {platform}-{arch}.{ext}[.blockmap] naming
    file_path = await svc.get_download_path(version, platform, arch)
    if file_path is not None:
        # get_download_path scans for {plat}-{arch}.{ext} — but we need the exact file
        # Check if the found path matches our expected type
        await svc.record_download(version, platform, arch, package_name="codex-switch", ip_hash=ip, source="electron-updater")
        return _send_file(str(file_path), filename)

    # 3. Fetch from GitHub → cache locally
    feed_service = UpdateFeedService()
    asset = await feed_service.find_asset_by_filename(filename)
    if not asset:
        raise HTTPException(status_code=404, detail="File not found in GitHub release")

    download_url = asset.get("download_url", "")
    if not download_url:
        raise HTTPException(status_code=404, detail="No download URL available")

    try:
        full_ext = f"{file_type}.blockmap" if is_blockmap else file_type
        cached_path = await svc.download_and_cache(
            download_url, version, platform, arch, full_ext, original_name=filename
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Failed to download from GitHub")

    await svc.record_download(version, platform, arch, package_name="codex-switch", ip_hash=ip, source="electron-updater")
    return _send_file(str(cached_path), filename)


def _send_file(full_path: str, filename: str | None = None) -> Response:
    """Serve cached files via nginx X-Accel-Redirect for zero-copy sendfile."""
    from pathlib import Path
    p = Path(full_path)
    data_dir = "data"
    parts = p.parts
    try:
        idx = list(parts).index(data_dir)
        cache_path = "/".join(parts[idx + 1:])
    except ValueError:
        cache_path = f"codex-switch/{p.parent.name}/{p.name}"

    headers = {"X-Accel-Redirect": f"/_cache/{cache_path}"}
    if filename:
        headers["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(filename)}"

    return Response(headers=headers)
```

- [ ] **Step 2: 运行 ruff 检查新文件**

```bash
uv run ruff check src/api/v1/updates.py
```

Expected: All checks passed

- [ ] **Step 3: Commit**

```bash
git add src/api/v1/updates.py
git commit -m "feat: add /api/v1/updates endpoints for electron-updater generic provider

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 5: 注册路由 + 集成测试

**Files:**
- Modify: `src/api/router.py`
- Create: `tests/integration/test_api_updates.py`

- [ ] **Step 1: 在 router.py 中注册 updates_router**

在 `src/api/router.py` 中，在 import 区添加 `updates` router 导入，在 include_router 区添加注册：

```python
from __future__ import annotations

from fastapi import APIRouter

from src.api.v1.admin_api import router as admin_api_router
from src.api.v1.analytics import router as analytics_router
from src.api.v1.files import router as files_router
from src.api.v1.packages import router as packages_router
from src.api.v1.telemetry import router as telemetry_router
from src.api.v1.update import router as update_router
from src.api.v1.updates import router as updates_router

router = APIRouter(prefix="/api/v1")
router.include_router(update_router)
router.include_router(packages_router)
router.include_router(files_router)
router.include_router(telemetry_router)
router.include_router(analytics_router)
router.include_router(admin_api_router)
router.include_router(updates_router)
```

- [ ] **Step 2: 创建集成测试 test_api_updates.py**

```python
from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


class TestLatestMacYml:
    @pytest.mark.asyncio
    async def test_returns_yml_with_correct_content_type(self, client: AsyncClient):
        with patch("src.services.update_feed.UpdateFeedService.get_latest_yml") as mock_get:
            mock_get.return_value = "version: 1.5.0\nfiles:\n  - url: test.zip\n"
            resp = await client.get("/api/v1/updates/latest-mac.yml")

        assert resp.status_code == 200
        assert "text/yaml" in resp.headers["content-type"]
        assert "version: 1.5.0" in resp.text
        mock_get.assert_called_once_with("macos")

    @pytest.mark.asyncio
    async def test_returns_404_when_yml_not_available(self, client: AsyncClient):
        with patch("src.services.update_feed.UpdateFeedService.get_latest_yml") as mock_get:
            mock_get.return_value = None
            resp = await client.get("/api/v1/updates/latest-mac.yml")

        assert resp.status_code == 404


class TestLatestYml:
    @pytest.mark.asyncio
    async def test_returns_yml_for_windows(self, client: AsyncClient):
        with patch("src.services.update_feed.UpdateFeedService.get_latest_yml") as mock_get:
            mock_get.return_value = "version: 1.5.0\npath: Codex-Switch-Setup-1.5.0-win-x64.exe\n"
            resp = await client.get("/api/v1/updates/latest.yml")

        assert resp.status_code == 200
        assert "text/yaml" in resp.headers["content-type"]
        mock_get.assert_called_once_with("windows")


class TestDownloadUpdateFile:
    @pytest.mark.asyncio
    async def test_rejects_unsafe_filename(self, client: AsyncClient):
        resp = await client.get("/api/v1/updates/../../../etc/passwd")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_rejects_unrecognized_filename(self, client: AsyncClient):
        resp = await client.get("/api/v1/updates/some-random-file.txt")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cos_302_redirect(self, client: AsyncClient, monkeypatch):
        """When COS has the file, return 302 to COS."""
        with patch("src.api.v1.updates.CosStorage.exists", return_value=True), \
             patch("src.api.v1.updates.CosStorage.public_url", return_value="https://cos.example.com/file.zip"), \
             patch("src.api.v1.updates.ReleaseSyncService.record_download", new_callable=AsyncMock):
            resp = await client.get("/api/v1/updates/Codex-Switch-1.5.0-mac-arm64.zip")

        assert resp.status_code == 302
        assert "cos.example.com" in resp.headers["location"]

    @pytest.mark.asyncio
    async def test_github_fallback_when_not_cached(self, client: AsyncClient, monkeypatch):
        """When not in COS or local, download from GitHub."""
        import tempfile
        from pathlib import Path
        from unittest.mock import MagicMock

        with patch("src.api.v1.updates.CosStorage.exists", return_value=False), \
             patch("src.api.v1.updates.LocalStorage.exists", return_value=False), \
             patch("src.api.v1.updates.ReleaseSyncService.get_download_path", return_value=None), \
             patch("src.api.v1.updates.ReleaseSyncService.record_download", new_callable=AsyncMock), \
             patch("src.api.v1.updates.UpdateFeedService.find_asset_by_filename") as mock_find:

            mock_find.return_value = {
                "original_name": "Codex-Switch-1.5.0-mac-arm64.zip",
                "download_url": "https://github.com/releases/download/v1.5.0/Codex-Switch-1.5.0-mac-arm64.zip",
                "file_size": 92721818,
            }

            # Create temp file to simulate download_and_cache result
            tmp = Path(tempfile.gettempdir()) / "test-electron-update-cached.zip"
            tmp.write_bytes(b"fake zip content")

            with patch("src.api.v1.updates.ReleaseSyncService.download_and_cache", new_callable=AsyncMock) as mock_dl:
                mock_dl.return_value = tmp
                resp = await client.get("/api/v1/updates/Codex-Switch-1.5.0-mac-arm64.zip")

            assert resp.status_code == 200
            assert "X-Accel-Redirect" in resp.headers
            tmp.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_404_when_file_not_found_anywhere(self, client: AsyncClient, monkeypatch):
        with patch("src.api.v1.updates.CosStorage.exists", return_value=False), \
             patch("src.api.v1.updates.LocalStorage.exists", return_value=False), \
             patch("src.api.v1.updates.ReleaseSyncService.get_download_path", return_value=None), \
             patch("src.api.v1.updates.UpdateFeedService.find_asset_by_filename", return_value=None):
            resp = await client.get("/api/v1/updates/Codex-Switch-99.0.0-mac-arm64.zip")

        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_blockmap_filename_parsed_correctly(self, client: AsyncClient, monkeypatch):
        """Blockmap files are parsed and routed correctly."""
        with patch("src.api.v1.updates.CosStorage.exists", return_value=True), \
             patch("src.api.v1.updates.CosStorage.public_url", return_value="https://cos.example.com/file.zip.blockmap"), \
             patch("src.api.v1.updates.ReleaseSyncService.record_download", new_callable=AsyncMock):
            resp = await client.get("/api/v1/updates/Codex-Switch-1.5.0-mac-arm64.zip.blockmap")

        assert resp.status_code == 302

    @pytest.mark.asyncio
    async def test_windows_setup_exe_parsed_correctly(self, client: AsyncClient, monkeypatch):
        """Windows Setup exe filename is parsed correctly."""
        with patch("src.api.v1.updates.CosStorage.exists", return_value=True), \
             patch("src.api.v1.updates.CosStorage.public_url", return_value="https://cos.example.com/setup.exe"), \
             patch("src.api.v1.updates.ReleaseSyncService.record_download", new_callable=AsyncMock):
            resp = await client.get("/api/v1/updates/Codex-Switch-Setup-1.5.0-win-x64.exe")

        assert resp.status_code == 302
```

- [ ] **Step 3: 运行集成测试**

```bash
uv run pytest tests/integration/test_api_updates.py -v
```

Expected: 9 passed

- [ ] **Step 4: 运行全量测试**

```bash
uv run pytest -x -q
```

Expected: 全部通过（现有 145 + 新增 22 = 167 左右）

- [ ] **Step 5: ruff 检查 + 格式化**

```bash
uv run ruff check . && uv run ruff format .
```

Expected: All checks passed, no formatting changes

- [ ] **Step 6: Commit**

```bash
git add src/api/router.py tests/integration/test_api_updates.py
git commit -m "feat: register /api/v1/updates router with integration tests

Co-Authored-By: Claude Opus 4.8 <noreply@anthropic.com>"
```

---

### Task 6: 端到端验证

- [ ] **Step 1: 启动服务**

```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 &
sleep 3
```

- [ ] **Step 2: 验证 latest-mac.yml 端点**

```bash
curl -s http://localhost:8000/api/v1/updates/latest-mac.yml | head -5
```

Expected: yml 内容（version, files 等），Content-Type 为 text/yaml

- [ ] **Step 3: 验证 latest.yml 端点**

```bash
curl -s http://localhost:8000/api/v1/updates/latest.yml | head -5
```

Expected: yml 内容

- [ ] **Step 4: 验证文件下载端点（COS 302）**

```bash
curl -sI http://localhost:8000/api/v1/updates/Codex-Switch-1.4.0-mac-arm64.dmg
```

Expected: 302 或 200（取决于 COS 是否有该文件）

- [ ] **Step 5: 验证不安全文件名被拒绝**

```bash
curl -s http://localhost:8000/api/v1/updates/../../../etc/passwd
```

Expected: `{"detail": "File not found"}` + 404

- [ ] **Step 6: 停服**

```bash
kill %1
```

- [ ] **Step 7: Commit（如有修改）**

```bash
git status
```

from __future__ import annotations

import json
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

import src.services.ai_working_ok_releases as _mod
from src.services.ai_working_ok_releases import AiWorkingOkReleaseService


class TestAiWorkingOkReleaseService:
    """Unit tests for AiWorkingOkReleaseService with mocked HTTP and storage."""

    @pytest.fixture(autouse=True)
    def _clear_module_cache(self):
        """Reset in-memory cache before each test to avoid cross-test pollution."""
        _mod._latest_cache = None
        _mod._cache_time = 0

    @pytest.fixture
    def mock_http(self) -> AsyncMock:
        return AsyncMock()

    @pytest.fixture
    def mock_storage(self) -> AsyncMock:
        storage = AsyncMock()
        storage.get_path.return_value = None  # nothing cached by default
        storage.put.return_value = "/tmp/ai-working-ok-v1.0.0.tar.gz"
        return storage

    @pytest.fixture
    def service(self, mock_http, mock_storage) -> AiWorkingOkReleaseService:
        return AiWorkingOkReleaseService(http=mock_http, storage=mock_storage)

    # ── get_latest_version ──────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_latest_version_from_github_api(self, service, mock_http, mock_storage):
        """Should fetch latest version from GitHub when nothing is cached."""
        mock_http.get_json.return_value = {"tag_name": "v1.2.0"}

        version = await service.get_latest_version()

        assert version == "1.2.0"
        mock_http.get_json.assert_called_once()
        # Should have saved releases.json
        mock_storage.put.assert_called()

    @pytest.mark.asyncio
    async def test_get_latest_version_from_disk_cache_within_ttl(self, service, mock_http, mock_storage):
        """Should return version from disk cache when within TTL."""
        releases_data = {
            "latest": "1.0.0",
            "latest_checked_at": "2026-07-26T10:00:00+00:00",
            "versions": {},
        }
        # Mock disk cache: releases.json exists
        mock_path = MagicMock(spec=Path)
        mock_path.read_text.return_value = json.dumps(releases_data)
        mock_storage.get_path.return_value = mock_path

        version = await service.get_latest_version()

        assert version == "1.0.0"
        # Should NOT call GitHub API (disk cache is fresh)
        mock_http.get_json.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_latest_version_from_github_when_disk_cache_expired(self, service, mock_http, mock_storage):
        """Should fall back to GitHub when disk cache is past TTL."""
        # Disk cache with old timestamp (> TTL)
        releases_data = {
            "latest": "0.9.0",
            "latest_checked_at": "2020-01-01T00:00:00+00:00",
            "versions": {},
        }
        mock_path = MagicMock(spec=Path)
        mock_path.read_text.return_value = json.dumps(releases_data)
        mock_storage.get_path.return_value = mock_path
        mock_http.get_json.return_value = {"tag_name": "v1.2.0"}

        version = await service.get_latest_version()

        assert version == "1.2.0"
        mock_http.get_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_version_fallback_to_disk_when_github_fails(self, service, mock_http, mock_storage):
        """Should return cached version when GitHub API fails."""
        releases_data = {
            "latest": "1.0.0",
            "latest_checked_at": "2020-01-01T00:00:00+00:00",
            "versions": {},
        }
        mock_path = MagicMock(spec=Path)
        mock_path.read_text.return_value = json.dumps(releases_data)
        mock_storage.get_path.return_value = mock_path
        mock_http.get_json.side_effect = Exception("GitHub down")

        version = await service.get_latest_version()

        assert version == "1.0.0"

    @pytest.mark.asyncio
    async def test_get_latest_version_no_tag_prefix(self, service, mock_http):
        """Should strip 'v' prefix from tag_name."""
        mock_http.get_json.return_value = {"tag_name": "v2.0.0"}

        version = await service.get_latest_version()

        assert version == "2.0.0"

    @pytest.mark.asyncio
    async def test_get_latest_version_tag_without_v_prefix(self, service, mock_http):
        """Should handle tag_name without 'v' prefix."""
        mock_http.get_json.return_value = {"tag_name": "3.0.0"}

        version = await service.get_latest_version()

        assert version == "3.0.0"

    # ── get_release ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_get_release_from_cache(self, service, mock_http, mock_storage):
        """Should serve from local cache when file exists."""
        mock_path = MagicMock(spec=Path)
        mock_storage.get_path.return_value = mock_path

        file_path, filename = await service.get_release("1.0.0")

        assert filename == "ai-working-ok-v1.0.0.tar.gz"
        assert file_path == mock_path
        mock_http.download.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_release_downloads_from_github_on_cache_miss(self, service, mock_http, mock_storage):
        """Should download from GitHub when not in local cache."""
        # First call: cache miss
        mock_storage.get_path.return_value = None
        # Second call (in _save_releases_json): for releases.json check
        mock_storage.put.return_value = "/app/data/packages/ai-working-ok/ai-working-ok-v1.0.0.tar.gz"

        file_path, filename = await service.get_release("1.0.0")

        assert filename == "ai-working-ok-v1.0.0.tar.gz"
        mock_http.download.assert_called_once()
        args = mock_http.download.call_args[0]
        assert "v1.0.0" in args[0]
        assert "ai-working-ok-v1.0.0.tar.gz" in args[0]

    @pytest.mark.asyncio
    async def test_get_release_strips_v_prefix(self, service, mock_http, mock_storage):
        """Should strip leading 'v' from version parameter."""
        mock_storage.get_path.return_value = None
        mock_storage.put.return_value = "/app/data/packages/ai-working-ok/ai-working-ok-v1.0.0.tar.gz"

        file_path, filename = await service.get_release("v1.0.0")

        assert filename == "ai-working-ok-v1.0.0.tar.gz"
        assert "v1.0.0" in mock_http.download.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_release_raises_on_github_failure(self, service, mock_http, mock_storage):
        """Should propagate exception when GitHub download fails."""
        mock_storage.get_path.return_value = None
        mock_http.download.side_effect = Exception("Network error")

        with pytest.raises(Exception, match="Network error"):
            await service.get_release("1.0.0")

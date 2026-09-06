from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

import src.services.update_feed as _update_feed_module
from src.services.update_feed import (
    UpdateFeedService,
    _parse_filename_to_cache_key,
)


class TestParseFilenameToCacheKey:
    """Unit tests for _parse_filename_to_cache_key."""

    @pytest.mark.parametrize(
        "filename, expected",
        [
            # macOS
            ("Codex-Switch-1.5.0-mac-arm64.zip", ("1.5.0", "macos", "arm64", "zip")),
            ("Codex-Switch-1.5.0-mac-arm64.dmg", ("1.5.0", "macos", "arm64", "dmg")),
            ("Codex-Switch-1.5.0-mac-arm64.zip.blockmap", ("1.5.0", "macos", "arm64", "zip.blockmap")),
            ("Codex-Switch-1.5.0-mac-x64.zip", ("1.5.0", "macos", "x64", "zip")),
            ("Codex-Switch-2.0.0-mac-arm64.zip", ("2.0.0", "macos", "arm64", "zip")),
            # Windows (Setup variant)
            ("Codex-Switch-Setup-1.5.0-win-x64.exe", ("1.5.0", "windows", "x64", "exe")),
            ("Codex-Switch-Setup-1.5.0-win-arm64.exe", ("1.5.0", "windows", "arm64", "exe")),
            ("Codex-Switch-Setup-1.5.0-win-x64.zip", ("1.5.0", "windows", "x64", "zip")),
            ("Codex-Switch-Setup-2.1.0-win-arm64.exe", ("2.1.0", "windows", "arm64", "exe")),
            # Linux
            ("Codex-Switch-1.5.0-linux-x64.appimage", ("1.5.0", "linux", "x64", "appimage")),
            # aarch64
            ("Codex-Switch-1.5.0-mac-aarch64.dmg", ("1.5.0", "macos", "arm64", "dmg")),
            # amd64
            ("Codex-Switch-1.5.0-linux-amd64.appimage", ("1.5.0", "linux", "x64", "appimage")),
        ],
    )
    def test_valid_filenames(self, filename, expected):
        result = _parse_filename_to_cache_key(filename)
        assert result == expected

    @pytest.mark.parametrize(
        "filename",
        [
            "",  # empty
            "not-matching.exe",  # completely different
            "Codex-Switch-exe",  # missing version
            "Codex-Switch-1.0.0.exe",  # missing platform-arch
            "some-other-tool-1.0.0-mac-arm64.zip",  # wrong prefix
            "../Codex-Switch-1.0.0-mac-arm64.zip",  # path traversal
            "Codex-Switch-1.0.0-unknown-arm64.zip",  # unknown platform
        ],
    )
    def test_invalid_filenames_return_none(self, filename):
        assert _parse_filename_to_cache_key(filename) is None


class TestUpdateFeedService:
    """Unit tests for UpdateFeedService with mocked GitHub API."""

    def setup_method(self):
        """Clear module-level yml caches before each test to avoid pollution."""
        _update_feed_module._mac_yml_cache = None
        _update_feed_module._mac_yml_cache_time = 0
        _update_feed_module._win_yml_cache = None
        _update_feed_module._win_yml_cache_time = 0

    @pytest.mark.asyncio
    async def test_get_latest_yml_mac_happy_path(self):
        """get_latest_yml('mac') fetches latest-mac.yml content from GitHub."""
        fake_releases = [
            {
                "tag_name": "v1.5.0",
                "assets": [
                    {"name": "latest-mac.yml", "browser_download_url": "https://example.com/latest-mac.yml"},
                    {
                        "name": "Codex-Switch-1.5.0-mac-arm64.zip",
                        "browser_download_url": "https://example.com/file.zip",
                    },
                ],
            }
        ]

        mock_http = AsyncMock()
        mock_http.get_json.return_value = fake_releases

        svc = UpdateFeedService(http=mock_http)

        with patch("src.services.update_feed.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.text = "version: 1.5.0\nfiles:\n  - url: Codex-Switch-1.5.0-mac-arm64.zip\n"
            mock_resp.raise_for_status = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            content = await svc.get_latest_yml("mac")

            assert content is not None
            assert "version: 1.5.0" in content
            # Verify GitHub API was called
            mock_http.get_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_yml_win_happy_path(self):
        """get_latest_yml('win') fetches latest.yml content from GitHub."""
        fake_releases = [
            {
                "tag_name": "v1.5.0",
                "assets": [
                    {"name": "latest.yml", "browser_download_url": "https://example.com/latest.yml"},
                ],
            }
        ]

        mock_http = AsyncMock()
        mock_http.get_json.return_value = fake_releases

        svc = UpdateFeedService(http=mock_http)

        with patch("src.services.update_feed.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.text = "version: 1.5.0\nfiles:\n  - url: Codex-Switch-Setup-1.5.0-win-x64.exe\n"
            mock_resp.raise_for_status = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            content = await svc.get_latest_yml("win")

            assert content is not None
            assert "version: 1.5.0" in content

    @pytest.mark.asyncio
    async def test_get_latest_yml_returns_cache_on_second_call(self):
        """Second call to get_latest_yml returns cached content without GitHub API call."""
        fake_releases = [
            {
                "tag_name": "v1.5.0",
                "assets": [
                    {"name": "latest-mac.yml", "browser_download_url": "https://example.com/latest-mac.yml"},
                ],
            }
        ]

        mock_http = AsyncMock()
        mock_http.get_json.return_value = fake_releases

        svc = UpdateFeedService(http=mock_http)

        with patch("src.services.update_feed.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.text = "version: 1.5.0\n"
            mock_resp.raise_for_status = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            # First call — fetches from GitHub
            await svc.get_latest_yml("mac")
            assert mock_http.get_json.call_count == 1

            # Second call — should be from cache
            content2 = await svc.get_latest_yml("mac")
            assert content2 is not None
            assert mock_http.get_json.call_count == 1  # No additional API call

    @pytest.mark.asyncio
    async def test_get_latest_yml_returns_stale_cache_on_github_failure(self):
        """When GitHub API fails, returns stale cache if available."""
        mock_http = AsyncMock()
        # First call: success
        mock_http.get_json.return_value = [
            {
                "tag_name": "v1.5.0",
                "assets": [
                    {"name": "latest-mac.yml", "browser_download_url": "https://example.com/latest-mac.yml"},
                ],
            }
        ]

        svc = UpdateFeedService(http=mock_http)

        with patch("src.services.update_feed.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.text = "cached content"
            mock_resp.raise_for_status = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            # First call: populate cache
            await svc.get_latest_yml("mac")

            # Second call: GitHub fails, should return stale cache
            mock_http.get_json.side_effect = Exception("GitHub down")

            content = await svc.get_latest_yml("mac")
            assert content == "cached content"

    @pytest.mark.asyncio
    async def test_get_latest_yml_returns_none_when_no_yml_asset(self):
        """When latest release has no yml asset, returns None (or stale cache)."""
        mock_http = AsyncMock()
        mock_http.get_json.return_value = [
            {
                "tag_name": "v1.5.0",
                "assets": [
                    {
                        "name": "Codex-Switch-1.5.0-mac-arm64.zip",
                        "browser_download_url": "https://example.com/file.zip",
                    },
                ],
            }
        ]

        svc = UpdateFeedService(http=mock_http)

        # No prior cache → should return None
        content = await svc.get_latest_yml("mac")
        assert content is None

    @pytest.mark.asyncio
    async def test_get_latest_yml_prefers_cos_when_present(self):
        """When a COS stable feed key exists, yml is served from COS and GitHub is not hit."""

        class _FakeCos:
            async def get_bytes(self, key):  # noqa: ANN001
                assert key == "codex-switch/latest/latest-mac.yml"
                return b"version: 2.1.0\nfiles:\n  - url: Codex-Switch-2.1.0-mac-arm64.zip\n"

        mock_http = AsyncMock()
        svc = UpdateFeedService(http=mock_http, cos=_FakeCos())

        content = await svc.get_latest_yml("mac")

        assert content is not None
        assert "version: 2.1.0" in content
        mock_http.get_json.assert_not_called()  # COS path must not hit GitHub

    @pytest.mark.asyncio
    async def test_get_latest_yml_prefers_cos_for_win(self):
        """Windows feed (latest.yml) also prefers the COS stable key."""

        class _FakeCos:
            async def get_bytes(self, key):  # noqa: ANN001
                assert key == "codex-switch/latest/latest.yml"
                return b"version: 2.1.0\nfiles:\n  - url: Codex-Switch-Setup-2.1.0-win-x64.exe\n"

        svc = UpdateFeedService(http=AsyncMock(), cos=_FakeCos())

        content = await svc.get_latest_yml("win")
        assert content is not None
        assert "version: 2.1.0" in content

    @pytest.mark.asyncio
    async def test_get_latest_yml_falls_back_to_github_when_cos_missing(self):
        """When COS object is missing (returns None), falls back to the GitHub release asset."""

        class _FakeCos:
            async def get_bytes(self, key):  # noqa: ANN001
                return None

        fake_releases = [
            {
                "tag_name": "v1.5.0",
                "assets": [{"name": "latest-mac.yml", "browser_download_url": "https://example.com/latest-mac.yml"}],
            }
        ]
        mock_http = AsyncMock()
        mock_http.get_json.return_value = fake_releases

        svc = UpdateFeedService(http=mock_http, cos=_FakeCos())

        with patch("src.services.update_feed.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_resp = AsyncMock()
            mock_resp.text = "version: 1.5.0\nfiles:\n  - url: Codex-Switch-1.5.0-mac-arm64.zip\n"
            mock_resp.raise_for_status = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value.__aenter__.return_value = mock_client

            content = await svc.get_latest_yml("mac")

            assert content is not None
            assert "version: 1.5.0" in content
            mock_http.get_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_latest_yml_returns_stale_cache_when_cos_and_github_fail(self):
        """When COS is missing and GitHub fails, returns the stale in-memory cache."""
        _update_feed_module._mac_yml_cache = "stale 2.0.0 content"
        _update_feed_module._mac_yml_cache_time = 0  # force TTL expiry

        mock_http = AsyncMock()
        mock_http.get_json.side_effect = Exception("GitHub down")

        svc = UpdateFeedService(http=mock_http)  # cos=None → COS skipped

        content = await svc.get_latest_yml("mac")
        assert content == "stale 2.0.0 content"

    @pytest.mark.asyncio
    async def test_get_latest_yml_returns_none_when_no_source_and_no_cache(self):
        """No COS, GitHub down, and no prior cache → returns None."""
        mock_http = AsyncMock()
        mock_http.get_json.side_effect = Exception("GitHub down")

        svc = UpdateFeedService(http=mock_http)  # cos=None
        assert await svc.get_latest_yml("win") is None

    @pytest.mark.asyncio
    async def test_find_asset_by_filename_found(self):
        """find_asset_by_filename returns asset info when filename matches."""
        fake_releases = [
            {
                "tag_name": "v1.5.0",
                "assets": [
                    {
                        "name": "Codex-Switch-1.5.0-mac-arm64.zip",
                        "browser_download_url": "https://example.com/dl.zip",
                        "size": 50000000,
                    },
                ],
            }
        ]

        mock_http = AsyncMock()
        mock_http.get_json.return_value = fake_releases

        svc = UpdateFeedService(http=mock_http)
        result = await svc.find_asset_by_filename("Codex-Switch-1.5.0-mac-arm64.zip")

        assert result is not None
        assert result["name"] == "Codex-Switch-1.5.0-mac-arm64.zip"
        assert result["download_url"] == "https://example.com/dl.zip"
        assert result["file_size"] == 50000000

    @pytest.mark.asyncio
    async def test_find_asset_by_filename_not_found(self):
        """find_asset_by_filename returns None when filename doesn't match."""
        mock_http = AsyncMock()
        mock_http.get_json.return_value = [
            {
                "tag_name": "v1.5.0",
                "assets": [
                    {"name": "Codex-Switch-1.5.0-mac-arm64.zip", "browser_download_url": "https://example.com/dl.zip"},
                ],
            }
        ]

        svc = UpdateFeedService(http=mock_http)
        result = await svc.find_asset_by_filename("Codex-Switch-1.5.0-win-x64.exe")
        assert result is None

    @pytest.mark.asyncio
    async def test_find_asset_by_filename_github_failure(self):
        """find_asset_by_filename returns None on GitHub API failure."""
        mock_http = AsyncMock()
        mock_http.get_json.side_effect = Exception("GitHub API error")

        svc = UpdateFeedService(http=mock_http)
        result = await svc.find_asset_by_filename("Codex-Switch-1.5.0-mac-arm64.zip")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_cached_path_found(self):
        """get_cached_path returns path when file exists in cache."""
        from pathlib import Path

        cache_dir = Path("data/codex-switch/1.5.0")
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_file = cache_dir / "Codex-Switch-1.5.0-mac-arm64.zip"
        cache_file.write_bytes(b"fake-zip-content")

        try:
            svc = UpdateFeedService()
            path = await svc.get_cached_path("1.5.0", "Codex-Switch-1.5.0-mac-arm64.zip")
            assert path is not None
            assert "Codex-Switch-1.5.0-mac-arm64.zip" in path
        finally:
            cache_file.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_get_cached_path_not_found(self):
        """get_cached_path returns None when file doesn't exist."""
        svc = UpdateFeedService()
        path = await svc.get_cached_path("9.9.9", "nonexistent.zip")
        assert path is None

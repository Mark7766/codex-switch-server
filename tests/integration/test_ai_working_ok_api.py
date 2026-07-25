from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


class TestAiWorkingOkApi:
    """Integration tests for ai-working-ok download API endpoints."""

    @pytest.mark.asyncio
    async def test_download_latest_returns_file(self, client: AsyncClient):
        """Should return a tarball file for latest version."""
        with (
            patch(
                "src.services.ai_working_ok_releases.AiWorkingOkReleaseService.get_latest_version",
                new_callable=AsyncMock,
            ) as mock_latest,
            patch(
                "src.services.ai_working_ok_releases.AiWorkingOkReleaseService.get_release",
                new_callable=AsyncMock,
            ) as mock_release,
        ):
            mock_latest.return_value = "1.0.0"
            mock_release.return_value = (
                "/app/data/packages/ai-working-ok/ai-working-ok-v1.0.0.tar.gz",
                "ai-working-ok-v1.0.0.tar.gz",
            )

            resp = await client.get("/api/v1/packages/ai-working-ok/latest")

            assert resp.status_code == 200
            assert resp.headers["content-disposition"] == ("attachment; filename*=UTF-8''ai-working-ok-v1.0.0.tar.gz")
            mock_latest.assert_called_once()

    @pytest.mark.asyncio
    async def test_download_latest_502_when_github_fails(self, client: AsyncClient):
        """Should return 502 when GitHub API fails for latest check."""
        with patch(
            "src.services.ai_working_ok_releases.AiWorkingOkReleaseService.get_latest_version",
            new_callable=AsyncMock,
        ) as mock_latest:
            mock_latest.side_effect = Exception("GitHub API error")

            resp = await client.get("/api/v1/packages/ai-working-ok/latest")

            assert resp.status_code == 502
            assert "Failed to fetch latest version" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_download_specific_version(self, client: AsyncClient):
        """Should download a specific version by tag."""
        with patch(
            "src.services.ai_working_ok_releases.AiWorkingOkReleaseService.get_release",
            new_callable=AsyncMock,
        ) as mock_release:
            mock_release.return_value = (
                "/app/data/packages/ai-working-ok/ai-working-ok-v1.0.0.tar.gz",
                "ai-working-ok-v1.0.0.tar.gz",
            )

            resp = await client.get("/api/v1/packages/ai-working-ok/releases/v1.0.0")

            assert resp.status_code == 200
            assert "attachment" in resp.headers["content-disposition"]
            assert "ai-working-ok-v1.0.0.tar.gz" in resp.headers["content-disposition"]

    @pytest.mark.asyncio
    async def test_download_specific_version_502_when_download_fails(self, client: AsyncClient):
        """Should return 502 when GitHub download fails."""
        with patch(
            "src.services.ai_working_ok_releases.AiWorkingOkReleaseService.get_release",
            new_callable=AsyncMock,
        ) as mock_release:
            mock_release.side_effect = Exception("Download failed")

            resp = await client.get("/api/v1/packages/ai-working-ok/releases/v1.0.0")

            assert resp.status_code == 502
            assert "Failed to download from GitHub" in resp.json()["detail"]

    @pytest.mark.asyncio
    async def test_latest_route_accessible(self, client: AsyncClient):
        """Smoke test: /ai-working-ok/latest returns a proper HTTP response."""
        with (
            patch(
                "src.services.ai_working_ok_releases.AiWorkingOkReleaseService.get_latest_version",
                new_callable=AsyncMock,
            ) as mock_latest,
            patch(
                "src.services.ai_working_ok_releases.AiWorkingOkReleaseService.get_release",
                new_callable=AsyncMock,
            ) as mock_release,
        ):
            mock_latest.return_value = "1.0.0"
            mock_release.return_value = (
                "/app/data/packages/ai-working-ok/ai-working-ok-v1.0.0.tar.gz",
                "ai-working-ok-v1.0.0.tar.gz",
            )

            resp = await client.get("/api/v1/packages/ai-working-ok/latest")

            assert resp.status_code == 200
            assert "content-disposition" in resp.headers

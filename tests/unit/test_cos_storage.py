from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.utils.cos_storage import CosStorage


class TestCosStorageDisabled:
    """When COS is not configured, all operations should be no-ops."""

    @pytest.fixture(autouse=True)
    def _setup(self, monkeypatch):
        monkeypatch.setattr("src.utils.cos_storage.settings.cos_secret_id", "")
        monkeypatch.setattr("src.utils.cos_storage.settings.cos_bucket", "")

    def test_enabled_returns_false(self):
        cos = CosStorage()
        assert cos.enabled is False

    async def test_put_returns_none_when_disabled(self):
        cos = CosStorage()
        result = await cos.put(Path("/tmp/test.bin"), "key/test.bin")
        assert result is None

    def test_exists_returns_false_when_disabled(self):
        cos = CosStorage()
        assert cos.exists("key/test.bin") is False

    def test_delete_returns_false_when_disabled(self):
        cos = CosStorage()
        assert cos.delete("key/test.bin") is False


class TestCosStorageEnabled:
    """When COS is configured, operations should interact with COS client."""

    @pytest.fixture(autouse=True)
    def _setup(self, monkeypatch):
        monkeypatch.setattr("src.utils.cos_storage.settings.cos_secret_id", "test-id")
        monkeypatch.setattr("src.utils.cos_storage.settings.cos_secret_key", "test-key")
        monkeypatch.setattr("src.utils.cos_storage.settings.cos_bucket", "test-bucket-1250000000")
        monkeypatch.setattr("src.utils.cos_storage.settings.cos_region", "ap-guangzhou")

    def test_enabled_returns_true(self):
        cos = CosStorage()
        assert cos.enabled is True

    def test_public_url_format(self):
        cos = CosStorage()
        url = cos.public_url("packages/test/latest/file.dmg")
        assert url == "https://test-bucket-1250000000.cos.ap-guangzhou.myqcloud.com/packages/test/latest/file.dmg"

    async def test_put_uploads_and_returns_url(self):
        cos = CosStorage()
        mock_client = MagicMock()
        cos._client = mock_client

        result = await cos.put(Path("/tmp/test.bin"), "key/test.bin")
        assert result == "https://test-bucket-1250000000.cos.ap-guangzhou.myqcloud.com/key/test.bin"
        mock_client.put_object_from_local_file.assert_called_once()
        call_kwargs = mock_client.put_object_from_local_file.call_args[1]
        assert call_kwargs["Bucket"] == "test-bucket-1250000000"
        assert call_kwargs["Key"] == "key/test.bin"
        assert "ContentDisposition" not in call_kwargs

    async def test_put_with_content_disposition(self):
        cos = CosStorage()
        mock_client = MagicMock()
        cos._client = mock_client

        result = await cos.put(
            Path("/tmp/test.bin"),
            "key/test.bin",
            content_disposition="attachment; filename*=UTF-8''test.dmg",
        )
        assert result is not None
        call_kwargs = mock_client.put_object_from_local_file.call_args[1]
        assert call_kwargs["ContentDisposition"] == "attachment; filename*=UTF-8''test.dmg"

    async def test_put_returns_none_on_exception(self):
        cos = CosStorage()
        mock_client = MagicMock()
        mock_client.put_object_from_local_file.side_effect = RuntimeError("COS error")
        cos._client = mock_client

        result = await cos.put(Path("/tmp/test.bin"), "key/test.bin")
        assert result is None

    def test_exists_returns_true_when_key_found(self):
        cos = CosStorage()
        mock_client = MagicMock()
        cos._client = mock_client

        assert cos.exists("key/test.bin") is True
        mock_client.head_object.assert_called_once_with(Bucket="test-bucket-1250000000", Key="key/test.bin")

    def test_exists_returns_false_when_key_not_found(self):
        cos = CosStorage()
        mock_client = MagicMock()
        mock_client.head_object.side_effect = Exception("NoSuchKey")
        cos._client = mock_client

        assert cos.exists("key/missing.bin") is False

    def test_delete_returns_true_on_success(self):
        cos = CosStorage()
        mock_client = MagicMock()
        cos._client = mock_client

        assert cos.delete("key/test.bin") is True
        mock_client.delete_object.assert_called_once_with(Bucket="test-bucket-1250000000", Key="key/test.bin")

    def test_delete_returns_false_on_exception(self):
        cos = CosStorage()
        mock_client = MagicMock()
        mock_client.delete_object.side_effect = Exception("Delete failed")
        cos._client = mock_client

        assert cos.delete("key/test.bin") is False

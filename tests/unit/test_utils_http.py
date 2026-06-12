from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from src.utils.http import HttpClient


def _patch_async_client(get_side_effect=None, stream_side_effect=None):
    """Patch httpx.AsyncClient so that client.get() and client.stream() can be
    controlled synchronously via side_effect lists.

    Returns the patcher for use with ``with``.
    """
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock()
    mock_client.__aexit__ = AsyncMock(return_value=None)

    inner = mock_client.__aenter__.return_value
    if get_side_effect is not None:
        inner.get = AsyncMock(side_effect=get_side_effect)
    if stream_side_effect is not None:
        inner.stream = MagicMock(side_effect=stream_side_effect)

    return patch("httpx.AsyncClient", return_value=mock_client)


def _make_resp(data: dict) -> MagicMock:
    """Return a sync MagicMock that behaves like an httpx Response."""
    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.json = MagicMock(return_value=data)
    return resp


def _make_stream_resp(content: bytes):
    """Return a context manager mock that yields a streaming response."""

    async def aiter_chunks():
        yield content

    resp = MagicMock()
    resp.raise_for_status = MagicMock()
    resp.aiter_bytes = MagicMock(return_value=aiter_chunks())

    ctx = MagicMock()
    ctx.__aenter__ = AsyncMock(return_value=resp)
    ctx.__aexit__ = AsyncMock(return_value=None)
    return ctx


class TestGetJson:
    async def test_success(self):
        http = HttpClient(base_url="https://api.example.com")
        resp = _make_resp({"key": "value"})

        with _patch_async_client(get_side_effect=[resp]):
            result = await http.get_json("/test")
        assert result == {"key": "value"}

    async def test_retry_then_success(self):
        http = HttpClient(base_url="https://api.example.com", max_retries=3)
        resp = _make_resp({"ok": True})

        with _patch_async_client(
            get_side_effect=[
                httpx.HTTPError("fail1"),
                httpx.HTTPError("fail2"),
                resp,
            ]
        ):
            result = await http.get_json("/test")
        assert result == {"ok": True}

    async def test_all_retries_exhausted_raises(self):
        http = HttpClient(base_url="https://api.example.com", max_retries=2)

        with _patch_async_client(
            get_side_effect=[
                httpx.HTTPError("fail1"),
                httpx.HTTPError("fail2"),
            ]
        ):
            with pytest.raises(httpx.HTTPError):
                await http.get_json("/test")


class TestDownload:
    async def test_success(self, tmp_path):
        http = HttpClient(max_retries=1)
        dest = tmp_path / "test.bin"
        content = b"downloaded content"
        ctx = _make_stream_resp(content)

        with _patch_async_client(stream_side_effect=[ctx]):
            result = await http.download("https://example.com/f.bin", dest)
        assert result == dest
        assert dest.read_bytes() == content

    async def test_creates_parent_dirs(self, tmp_path):
        http = HttpClient(max_retries=1)
        dest = tmp_path / "a" / "b" / "f.bin"
        ctx = _make_stream_resp(b"x")

        with _patch_async_client(stream_side_effect=[ctx]):
            await http.download("https://example.com/f.bin", dest)
        assert dest.parent.exists()
        assert dest.exists()

    async def test_retry_then_success(self, tmp_path):
        http = HttpClient(max_retries=3)
        dest = tmp_path / "retry.bin"
        ctx = _make_stream_resp(b"ok after retry")

        with _patch_async_client(
            stream_side_effect=[
                httpx.HTTPError("fail1"),
                httpx.HTTPError("fail2"),
                ctx,
            ]
        ):
            result = await http.download("https://example.com/f.bin", dest)
        assert result == dest

    async def test_all_retries_exhausted_raises(self, tmp_path):
        http = HttpClient(max_retries=2)
        dest = tmp_path / "fail.bin"

        with _patch_async_client(
            stream_side_effect=[
                httpx.HTTPError("fail1"),
                httpx.HTTPError("fail2"),
            ]
        ):
            with pytest.raises(httpx.HTTPError):
                await http.download("https://example.com/f.bin", dest)

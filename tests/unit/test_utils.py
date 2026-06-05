from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.utils.storage import LocalStorage


@pytest.mark.asyncio
async def test_local_storage_put_and_get():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "store"
        storage = LocalStorage(str(base))

        src_file = Path(td) / "test.txt"
        src_file.write_text("hello")

        remote = await storage.put(src_file, "files/test.txt")
        assert remote.endswith("test.txt")

        found = await storage.get_path("files/test.txt")
        assert found is not None
        assert found.read_text() == "hello"


@pytest.mark.asyncio
async def test_local_storage_exists():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "store"
        storage = LocalStorage(str(base))
        src = Path(td) / "a.txt"
        src.write_text("data")
        await storage.put(src, "a.txt")

        assert await storage.exists("a.txt") is True
        assert await storage.exists("missing.txt") is False


@pytest.mark.asyncio
async def test_local_storage_delete():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "store"
        storage = LocalStorage(str(base))
        src = Path(td) / "x.txt"
        src.write_text("bye")
        await storage.put(src, "x.txt")

        assert await storage.delete("x.txt") is True
        assert await storage.exists("x.txt") is False
        assert await storage.delete("nonexistent") is False


@pytest.mark.asyncio
async def test_local_storage_list_files():
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "store"
        storage = LocalStorage(str(base))
        for name in ["a.txt", "b.txt", "sub/c.txt"]:
            src = Path(td) / name.replace("/", "_")
            src.write_text("x")
            await storage.put(src, name)

        files = await storage.list_files()
        assert len(files) == 3

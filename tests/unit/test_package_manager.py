from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from src.services.package_manager import PackageManager
from src.utils.storage import LocalStorage


@pytest.fixture
def storage():
    with tempfile.TemporaryDirectory() as td:
        yield LocalStorage(str(Path(td) / "data"))


@pytest.mark.asyncio
async def test_list_empty(storage: LocalStorage):
    mgr = PackageManager(storage)
    pkgs = await mgr.list_packages()
    assert pkgs == []


@pytest.mark.asyncio
async def test_add_and_list(storage: LocalStorage):
    mgr = PackageManager(storage)
    src = Path(tempfile.gettempdir()) / "test_add.bin"
    src.write_bytes(b"hello")

    await mgr.add_package(
        "claude-desktop", "Claude Desktop", "1.2.0", "macos", "arm64", "desc", src, "Claude-1.2.0-arm64.dmg"
    )

    pkgs = await mgr.list_packages()
    assert len(pkgs) == 1
    assert pkgs[0]["name"] == "claude-desktop"
    assert pkgs[0]["platforms"][0]["platform"] == "macos"
    assert pkgs[0]["platforms"][0]["arch"] == "arm64"
    assert pkgs[0]["platforms"][0]["original_filename"] == "Claude-1.2.0-arm64.dmg"


@pytest.mark.asyncio
async def test_add_same_name_second_platform(storage: LocalStorage):
    mgr = PackageManager(storage)
    src = Path(tempfile.gettempdir()) / "test_add2.bin"
    src.write_bytes(b"world")

    await mgr.add_package("claude-desktop", "Claude Desktop", "1.2.0", "macos", "arm64", "desc", src, "C-mac.dmg")
    await mgr.add_package("claude-desktop", "Claude Desktop", "1.2.0", "windows", "x64", "desc", src, "C-win.exe")

    pkgs = await mgr.list_packages()
    assert len(pkgs) == 1
    assert len(pkgs[0]["platforms"]) == 2


@pytest.mark.asyncio
async def test_get_download_path(storage: LocalStorage):
    mgr = PackageManager(storage)
    src = Path(tempfile.gettempdir()) / "test_dl.bin"
    src.write_bytes(b"data")

    await mgr.add_package("claude-desktop", "Claude Desktop", "1.0", "macos", "x64", "desc", src, "c.dmg")

    path = await mgr.get_download_path("claude-desktop", "macos", "x64")
    assert path is not None
    assert path.read_bytes() == b"data"

    missing = await mgr.get_download_path("nonexistent", "macos", "x64")
    assert missing is None


@pytest.mark.asyncio
async def test_delete_package(storage: LocalStorage):
    mgr = PackageManager(storage)
    src = Path(tempfile.gettempdir()) / "test_del.bin"
    src.write_bytes(b"del")

    await mgr.add_package("test-pkg", "Test", "1.0", "macos", "x64", "desc", src, "t.dmg")
    assert await mgr.delete_package("test-pkg") is True
    assert await mgr.list_packages() == []


@pytest.mark.asyncio
async def test_delete_single_platform(storage: LocalStorage):
    mgr = PackageManager(storage)
    src = Path(tempfile.gettempdir()) / "test_plat.bin"
    src.write_bytes(b"p")

    await mgr.add_package("multi", "Multi", "1.0", "macos", "x64", "desc", src, "m.dmg")
    await mgr.add_package("multi", "Multi", "1.0", "windows", "x64", "desc", src, "w.exe")

    assert await mgr.delete_package("multi", "macos", "x64") is True
    pkgs = await mgr.list_packages()
    assert len(pkgs[0]["platforms"]) == 1
    assert pkgs[0]["platforms"][0]["platform"] == "windows"

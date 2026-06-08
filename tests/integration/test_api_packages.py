from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient

from src.services.package_manager import PackageManager
from src.utils.storage import LocalStorage


@pytest.mark.asyncio
async def test_list_packages_returns_200(client: AsyncClient):
    resp = await client.get("/api/v1/packages")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert isinstance(data["data"]["packages"], list)


@pytest.mark.asyncio
async def test_list_packages_has_expected_structure(client: AsyncClient):
    resp = await client.get("/api/v1/packages")
    data = resp.json()
    for pkg in data["data"]["packages"]:
        assert "name" in pkg
        assert "display_name" in pkg
        assert "latest_version" in pkg
        assert isinstance(pkg.get("platforms"), list)


@pytest.mark.asyncio
async def test_download_package_not_found_returns_404(client: AsyncClient):
    resp = await client.get("/api/v1/packages/unknown/1.0.0/macos-arm64")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_package_manager_add_list_roundtrip(tmp_path: Path):
    """Add → list → verify package in registry."""
    storage = LocalStorage(base_dir=str(tmp_path / "data"))
    # Create source file OUTSIDE storage dir — add_package will copy it in
    src_file = tmp_path / "source.dmg"
    src_file.write_bytes(b"roundtrip-content")

    mgr = PackageManager(storage=storage)
    await mgr.add_package(
        name="roundtrip", display_name="Roundtrip", version="1.0",
        platform="macos", arch="arm64", description="test",
        local_file=src_file, original_filename="Roundtrip.dmg",
    )

    pkgs = await mgr.list_packages()
    found = [p for p in pkgs if p["name"] == "roundtrip"]
    assert len(found) == 1
    assert found[0]["display_name"] == "Roundtrip"
    assert found[0]["platforms"][0]["original_filename"] == "Roundtrip.dmg"


@pytest.mark.asyncio
async def test_package_manager_delete_removes_entry(tmp_path: Path):
    """Add → delete → verify gone."""
    storage = LocalStorage(base_dir=str(tmp_path / "data"))
    src_file = tmp_path / "temp.dmg"
    src_file.write_bytes(b"temp-content")

    mgr = PackageManager(storage=storage)
    await mgr.add_package(
        name="temp", display_name="Temp", version="1.0",
        platform="macos", arch="arm64", description="test",
        local_file=src_file, original_filename="Temp.dmg",
    )
    result = await mgr.delete_package("temp", "macos", "arm64")
    assert result is True

    pkgs = await mgr.list_packages()
    assert not any(p["name"] == "temp" for p in pkgs)


@pytest.mark.asyncio
async def test_package_manager_get_download_path(tmp_path: Path):
    """get_download_path_with_name returns file path and original filename."""
    storage = LocalStorage(base_dir=str(tmp_path / "data"))
    src_file = tmp_path / "app.dmg"
    src_file.write_bytes(b"app-content")

    mgr = PackageManager(storage=storage)
    await mgr.add_package(
        name="myapp", display_name="My App", version="1.0",
        platform="macos", arch="arm64", description="test",
        local_file=src_file, original_filename="MyApp-Installer.dmg",
    )

    path, fname = await mgr.get_download_path_with_name("myapp", "macos", "arm64")
    assert path is not None
    assert fname == "MyApp-Installer.dmg"


@pytest.mark.asyncio
async def test_package_manager_update_existing_package(tmp_path: Path):
    """Re-uploading the same package platform updates version."""
    storage = LocalStorage(base_dir=str(tmp_path / "data"))
    for ver in ("1.0", "2.0"):
        src_file = tmp_path / f"app-{ver}.dmg"
        src_file.write_bytes(b"v" + ver.encode())
        mgr = PackageManager(storage=storage)
        await mgr.add_package(
            name="myapp", display_name="My App", version=ver,
            platform="macos", arch="arm64", description="test",
            local_file=src_file, original_filename=f"MyApp-{ver}.dmg",
        )

    pkgs = await mgr.list_packages()
    found = [p for p in pkgs if p["name"] == "myapp"]
    assert len(found) == 1
    assert found[0]["latest_version"] == "2.0"


@pytest.mark.asyncio
async def test_download_package_http_local_cache(client: AsyncClient, monkeypatch, tmp_path):
    """HTTP download of an existing package → X-Accel-Redirect (COS disabled)."""
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_secret_id", "")
    monkeypatch.setattr("src.utils.cos_storage.settings.cos_bucket", "")

    # Create source file OUTSIDE data/ so add_package can copy it in
    from src.services.package_manager import PackageManager

    src_file = tmp_path / "http-test-source.dmg"
    src_file.write_bytes(b"http-test-content")

    mgr = PackageManager()
    try:
        await mgr.add_package(
            name="http-test", display_name="HTTP Test", version="1.0",
            platform="macos", arch="arm64", description="test",
            local_file=src_file, original_filename="HttpTest.dmg",
        )

        resp = await client.get("/api/v1/packages/http-test/1.0/macos-arm64")
        assert resp.status_code == 200
        assert "x-accel-redirect" in resp.headers
        assert "HttpTest.dmg" in resp.headers.get("content-disposition", "")
    finally:
        await mgr.delete_package("http-test", "macos", "arm64")

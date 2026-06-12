from __future__ import annotations

from pathlib import Path

import pytest
from httpx import AsyncClient


async def _login(client: AsyncClient) -> str:
    resp = await client.post("/admin/login", data={"token": "change-me"}, follow_redirects=False)
    return resp.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_packages_page_requires_auth(client: AsyncClient):
    resp = await client.get("/admin/packages")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_packages_page_with_auth(client: AsyncClient):
    cookie = await _login(client)
    resp = await client.get("/admin/packages", headers={"Cookie": cookie})
    assert resp.status_code == 200
    assert "安装包管理" in resp.text


@pytest.mark.asyncio
async def test_upload_without_auth_returns_401(client: AsyncClient):
    resp = await client.post("/admin/packages/upload")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_package_with_auth(client: AsyncClient, tmp_path: Path):
    """Upload a package file via admin form → redirects to /admin/packages."""
    cookie = await _login(client)

    # Create a temp file to upload
    test_file = tmp_path / "test-upload.dmg"
    test_file.write_bytes(b"mock-dmg-content")

    with open(test_file, "rb") as f:
        resp = await client.post(
            "/admin/packages/upload",
            headers={"Cookie": cookie},
            data={
                "name": "test-upload-app",
                "display_name": "Test Upload",
                "version": "1.0",
                "platform": "macos",
                "arch": "arm64",
                "description": "test upload",
            },
            files={"file": ("test-upload.dmg", f, "application/octet-stream")},
            follow_redirects=False,
        )
    assert resp.status_code == 302
    assert resp.headers["location"] == "/admin/packages"

    # Clean up
    from src.services.package_manager import PackageManager

    mgr = PackageManager()
    await mgr.delete_package("test-upload-app", "macos", "arm64")


@pytest.mark.asyncio
async def test_delete_package_with_auth(client: AsyncClient, tmp_path: Path):
    """Delete a package via admin form → redirects to /admin/packages."""
    from src.services.package_manager import PackageManager

    # First create a package to delete
    src_file = tmp_path / "to-delete.dmg"
    src_file.write_bytes(b"delete-me")
    mgr = PackageManager()
    await mgr.add_package(
        name="to-delete",
        display_name="To Delete",
        version="1.0",
        platform="macos",
        arch="arm64",
        description="test",
        local_file=src_file,
        original_filename="ToDelete.dmg",
    )

    cookie = await _login(client)
    resp = await client.post(
        "/admin/packages/delete",
        headers={"Cookie": cookie},
        data={"name": "to-delete", "platform": "macos", "arch": "arm64"},
        follow_redirects=False,
    )
    assert resp.status_code == 302

    # Verify deleted
    pkgs = await mgr.list_packages()
    assert not any(p["name"] == "to-delete" for p in pkgs)


@pytest.mark.asyncio
async def test_delete_without_auth_returns_401(client: AsyncClient):
    """Delete endpoint should require authentication."""
    resp = await client.post("/admin/packages/delete", data={"name": "x"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_api_packages_returns_real_data(client: AsyncClient):
    resp = await client.get("/api/v1/packages")
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert "packages" in data["data"]

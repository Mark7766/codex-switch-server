from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from src.utils.storage import LocalStorage

REGISTRY_PATH = "packages/registry.json"


class PackageManager:
    def __init__(self, storage: LocalStorage | None = None):
        self._storage = storage or LocalStorage()

    async def _load_registry(self) -> dict:
        path = await self._storage.get_path(REGISTRY_PATH)
        if path is None:
            return {"packages": []}
        return json.loads(path.read_text())

    async def _save_registry(self, data: dict) -> None:
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            tmp = Path(f.name)
        await self._storage.put(tmp, REGISTRY_PATH)
        tmp.unlink(missing_ok=True)

    async def list_packages(self) -> list[dict]:
        registry = await self._load_registry()
        return registry.get("packages", [])

    async def add_package(
        self,
        name: str,
        display_name: str,
        version: str,
        platform: str,
        arch: str,
        description: str,
        local_file: Path,
        original_filename: str,
    ) -> dict:
        ext = original_filename.rsplit(".", 1)[-1] if "." in original_filename else "bin"
        remote_key = f"packages/{name}/{version}/{platform}-{arch}.{ext}"
        await self._storage.put(local_file, remote_key)

        file_size = local_file.stat().st_size

        registry = await self._load_registry()
        packages: list[dict] = registry.get("packages", [])

        for pkg in packages:
            if pkg["name"] == name:
                platforms: list[dict] = pkg.get("platforms", [])
                for plat in platforms:
                    if plat["platform"] == platform and plat["arch"] == arch:
                        plat["version"] = version
                        plat["file_size"] = file_size
                        plat["file_type"] = ext
                        plat["path"] = remote_key
                        plat["original_filename"] = original_filename
                        plat["uploaded_at"] = datetime.now(UTC).isoformat()
                        break
                else:
                    entry = self._make_platform_entry(
                        version, platform, arch, ext, remote_key, original_filename, file_size
                    )
                    platforms.append(entry)
                pkg["platforms"] = platforms
                if version > pkg.get("latest_version", ""):
                    pkg["latest_version"] = version
                await self._save_registry(registry)
                return pkg

        new_pkg = {
            "name": name,
            "display_name": display_name,
            "description": description,
            "latest_version": version,
            "platforms": [
                self._make_platform_entry(version, platform, arch, ext, remote_key, original_filename, file_size)
            ],
        }
        packages.append(new_pkg)
        await self._save_registry(registry)
        return new_pkg

    async def delete_package(self, name: str, platform: str = "", arch: str = "") -> bool:
        registry = await self._load_registry()
        packages: list[dict] = registry.get("packages", [])

        for pkg in packages:
            if pkg["name"] == name:
                if platform and arch:
                    platforms: list[dict] = pkg.get("platforms", [])
                    for plat in platforms:
                        if plat["platform"] == platform and plat["arch"] == arch:
                            await self._storage.delete(plat["path"])
                            platforms.remove(plat)
                            break
                    if not platforms:
                        packages.remove(pkg)
                else:
                    for plat in pkg.get("platforms", []):
                        await self._storage.delete(plat["path"])
                    packages.remove(pkg)
                await self._save_registry(registry)
                return True
        return False

    async def get_download_path(self, name: str, platform: str, arch: str) -> Path | None:
        path, _ = await self.get_download_path_with_name(name, platform, arch)
        return path

    async def get_download_path_with_name(self, name: str, platform: str, arch: str) -> tuple[Path | None, str | None]:
        registry = await self._load_registry()
        for pkg in registry.get("packages", []):
            if pkg["name"] == name:
                for plat in pkg.get("platforms", []):
                    if plat["platform"] == platform and plat["arch"] == arch:
                        path = await self._storage.get_path(plat["path"])
                        return path, plat.get("original_filename")
        return None, None

    async def get_package_info(self, name: str, platform: str, arch: str) -> dict | None:
        registry = await self._load_registry()
        for pkg in registry.get("packages", []):
            if pkg["name"] == name:
                for plat in pkg.get("platforms", []):
                    if plat["platform"] == platform and plat["arch"] == arch:
                        return plat
        return None

    def _make_platform_entry(
        self, version: str, platform: str, arch: str, ext: str, remote_key: str, original_filename: str, file_size: int
    ) -> dict:
        return {
            "version": version,
            "platform": platform,
            "arch": arch,
            "file_type": ext,
            "file_size": file_size,
            "path": remote_key,
            "original_filename": original_filename,
            "uploaded_at": datetime.now(UTC).isoformat(),
        }

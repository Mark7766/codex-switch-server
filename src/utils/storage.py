from __future__ import annotations

import shutil
from pathlib import Path


class LocalStorage:
    def __init__(self, base_dir: str = "data"):
        self._base = Path(base_dir).resolve()
        self._base.mkdir(parents=True, exist_ok=True)

    async def put(self, local_path: Path, remote_key: str) -> str:
        dest = self._base / remote_key
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(local_path, dest)
        return str(dest)

    async def get_path(self, remote_key: str) -> Path | None:
        p = self._base / remote_key
        if p.exists() and p.is_file():
            return p
        return None

    async def delete(self, remote_key: str) -> bool:
        p = self._base / remote_key
        if p.exists() and p.is_file():
            p.unlink()
            return True
        return False

    async def exists(self, remote_key: str) -> bool:
        return (self._base / remote_key).is_file()

    async def list_files(self, prefix: str = "") -> list[str]:
        target = self._base / prefix if prefix else self._base
        if not target.exists():
            return []
        rel_files: list[str] = []
        for f in target.rglob("*"):
            if f.is_file():
                rel_files.append(str(f.relative_to(self._base)))
        return rel_files

    @property
    def base_dir(self) -> Path:
        return self._base

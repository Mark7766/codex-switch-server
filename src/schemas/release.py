from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel


class APIResponse[T](BaseModel):
    code: int = 0
    message: str = "ok"
    data: T | None = None


class ReleaseFile(BaseModel):
    platform: str
    arch: str
    file_size: int
    sha256: str = ""
    file_type: str = ""
    path: str = ""


class ReleaseRead(BaseModel):
    id: int
    version: str
    release_date: date
    release_notes: str = ""
    is_critical: bool = False
    files: list[dict[str, Any]] = []
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class UpdateCheckRequest(BaseModel):
    current_version: str
    platform: str
    arch: str
    client_id: str = ""


class UpdateCheckResponse(BaseModel):
    has_update: bool
    latest_version: str = ""
    release_date: str = ""
    release_notes: str = ""
    download_url: str = ""
    file_size: int = 0
    sha256: str = ""
    is_critical: bool = False


class PackageInfo(BaseModel):
    name: str
    display_name: str
    description: str
    latest_version: str
    platforms: list[dict[str, Any]] = []


class PackageListData(BaseModel):
    packages: list[PackageInfo] = []


class DownloadStats(BaseModel):
    total_downloads: int = 0
    active_users: int = 0
    today_events: int = 0
    download_trend: list[dict[str, Any]] = []
    platform_distribution: list[dict[str, Any]] = []

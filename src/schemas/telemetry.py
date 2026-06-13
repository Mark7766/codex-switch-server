from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

VALID_EVENT_TYPES = frozenset(
    {
        "app_start",
        "app_close",
        "proxy_start",
        "proxy_stop",
        "proxy_error",
        "model_call",
        "config_write",
        "tool_install",
        "tool_install_fail",
        "update_check",
        "update_download",
        "error",
    }
)


class TelemetryEventIn(BaseModel):
    event_type: str
    timestamp: datetime
    properties: dict[str, Any] = Field(default_factory=dict)
    # model_call aggregation fields (optional, backward-compatible)
    count: int = 1  # number of calls this event represents
    period_start: int | None = None  # unix timestamp of aggregation window start
    period_end: int | None = None  # unix timestamp of aggregation window end


class TelemetryPayload(BaseModel):
    client_id: str
    app_version: str = ""
    platform: str = ""
    arch: str = ""
    os_version: str = ""
    install_source: str = ""  # "" = unknown, "portal" = from codexswtich.cloud, "github" = from GitHub Releases
    events: list[TelemetryEventIn] = Field(default_factory=list, max_length=100)


class IngestResult(BaseModel):
    accepted: int
    rejected: int


class EventTypeCount(BaseModel):
    event_type: str
    count: int


class DailyTrend(BaseModel):
    date: str
    count: int


class VersionItem(BaseModel):
    version: str
    user_count: int
    event_count: int
    last_seen: str


class OsItem(BaseModel):
    platform: str  # "darwin" / "win32"
    platform_name: str  # "Mac" / "Windows"
    user_count: int
    event_count: int
    percentage: str  # "60%"


class VersionOsItem(BaseModel):
    version: str
    mac_users: int
    win_users: int


class TelemetryStats(BaseModel):
    total_events: int = 0
    today_events: int = 0
    active_users: int = 0
    model_call_total: int = 0  # today's real model_call count (SUM of properties.count)
    install_success_rate: str = "—"  # "85%" or "—" if no data
    latest_version: str = ""  # latest from GitHub, e.g. "1.8.0"
    version_coverage: str = "—"  # e.g. "67%"
    version_insight: list[VersionItem] = []
    os_insight: list[OsItem] = []
    version_os_cross: list[VersionOsItem] = []
    event_type_counts: list[EventTypeCount] = []
    daily_trend: list[DailyTrend] = []
    recent_events: list[dict[str, Any]] = []

from __future__ import annotations

from src.config import Settings


def test_settings_defaults():
    s = Settings()
    # database_url may be overridden by env (e.g. CI sets DATABASE_URL)
    assert "sqlite+aiosqlite" in s.database_url
    assert s.admin_token == "change-me"
    # github_token may be set via .env — just verify type
    assert isinstance(s.github_token, str)
    assert s.cos_region == "ap-guangzhou"
    assert s.telemetry_max_events_per_minute == 60
    assert s.telemetry_retention_days == 90


def test_settings_override_from_env(monkeypatch):
    monkeypatch.setenv("ADMIN_TOKEN", "secret123")
    monkeypatch.setenv("GITHUB_TOKEN", "ghp_test")
    s = Settings()
    assert s.admin_token == "secret123"
    assert s.github_token == "ghp_test"

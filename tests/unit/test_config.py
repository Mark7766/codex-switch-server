from __future__ import annotations

from src.config import Settings


def test_settings_defaults():
    s = Settings()
    assert s.database_url == "sqlite+aiosqlite:///data/app.db"
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

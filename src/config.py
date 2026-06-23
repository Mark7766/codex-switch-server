from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite+aiosqlite:///data/app.db"
    admin_token: str = "change-me"
    github_token: str = ""

    # COS (optional)
    cos_secret_id: str = ""
    cos_secret_key: str = ""
    cos_bucket: str = ""
    cos_region: str = "ap-guangzhou"

    # Telemetry
    telemetry_max_events_per_minute: int = 60
    telemetry_retention_days: int = 90

    # ICP filing (China mainland)
    icp_filing_number: str = ""

    # PSB filing (China mainland)
    psb_filing_number: str = ""


settings = Settings()

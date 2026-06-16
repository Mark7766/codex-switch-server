from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class DownloadRecord(Base):
    __tablename__ = "download_records"
    __table_args__ = (Index("ix_downloads_time_pkg", "downloaded_at", "package_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    release_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("releases.id"), nullable=True)
    client_id: Mapped[str] = mapped_column(String(64), default="")
    package_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    arch: Mapped[str] = mapped_column(String(16), nullable=False)
    ip_hash: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(256), default="")
    source: Mapped[str] = mapped_column(String(32), default="")  # '' = portal, 'electron-updater' = auto-update
    delivery: Mapped[str] = mapped_column(String(16), default="")  # 'cos' / 'local' / 'github'
    downloaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

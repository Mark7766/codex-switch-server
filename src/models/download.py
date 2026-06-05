from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class DownloadRecord(Base):
    __tablename__ = "download_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    release_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("releases.id"), nullable=True)
    client_id: Mapped[str] = mapped_column(String(64), default="")
    package_name: Mapped[str | None] = mapped_column(String(64), nullable=True)
    platform: Mapped[str] = mapped_column(String(16), nullable=False)
    arch: Mapped[str] = mapped_column(String(16), nullable=False)
    ip_hash: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(256), default="")
    downloaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

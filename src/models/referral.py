from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    inviter_client_id: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    invitee_client_id: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    ip_hash: Mapped[str] = mapped_column(String(64), default="")
    matched_page_event_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    platform: Mapped[str] = mapped_column(String(10), default="")
    arch: Mapped[str] = mapped_column(String(10), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

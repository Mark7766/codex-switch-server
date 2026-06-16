from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class PageEvent(Base):
    __tablename__ = "page_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)  # 'pageview' | 'click'
    page: Mapped[str] = mapped_column(String(128), nullable=False, index=True)  # '/' | '/download' | '/guide'
    element_id: Mapped[str | None] = mapped_column(String(64), nullable=True)  # click element id, null for pageviews
    ip_hash: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(256), default="")
    ref: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)  # inviter clientId from ?ref=
    visitor_id: Mapped[str] = mapped_column(String(16), default="", index=True)  # SHA256(ip+ua)[:16]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

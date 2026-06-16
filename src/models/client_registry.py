from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base


class ClientRegistry(Base):
    __tablename__ = "client_registry"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # client_number
    client_id: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

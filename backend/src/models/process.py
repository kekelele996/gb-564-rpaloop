from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class Process(Base, TimestampMixin):
    __tablename__ = "processes"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    matter_type: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)
    step_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    archived_versions: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    owner: Mapped[str] = mapped_column(String(64), default="苏城企服 RPA 组", nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

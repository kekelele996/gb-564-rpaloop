from datetime import datetime

from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class Run(Base, TimestampMixin):
    __tablename__ = "runs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    run_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    process_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    process_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    material_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    robot_name: Mapped[str] = mapped_column(String(32), default="SU-BOT-01", nullable=False)
    trigger: Mapped[str] = mapped_column(String(20), default="manual", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="queued", nullable=False, index=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_steps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    success_steps: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    attempt_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    execution_sequence: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    skipped_steps: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    compensation: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    log_text: Mapped[str] = mapped_column(Text, default="", nullable=False)
    active_lock: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)

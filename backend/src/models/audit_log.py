from sqlalchemy import JSON, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class AuditLog(Base, TimestampMixin):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor_email: Mapped[str] = mapped_column(String(128), default="anonymous", nullable=False, index=True)
    actor_role: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    resource: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    resource_id: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    method: Mapped[str] = mapped_column(String(10), default="", nullable=False)
    path: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    detail: Mapped[str] = mapped_column(Text, default="", nullable=False)

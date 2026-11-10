from datetime import date

from sqlalchemy import Boolean, Date, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class Material(Base, TimestampMixin):
    __tablename__ = "materials"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    credit_code: Mapped[str] = mapped_column(String(18), nullable=False, index=True)
    contact: Mapped[str] = mapped_column(String(64), default="", nullable=False)
    attachments: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    validity_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    missing_flags: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    credit_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    credit_reason: Mapped[str] = mapped_column(String(255), default="", nullable=False)

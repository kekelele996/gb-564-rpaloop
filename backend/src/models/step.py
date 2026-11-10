from sqlalchemy import Float, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from src.models.base import Base, TimestampMixin


class Step(Base, TimestampMixin):
    __tablename__ = "steps"
    __table_args__ = (UniqueConstraint("process_id", "seq", name="uq_step_process_seq"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    process_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    target_desc: Mapped[str] = mapped_column(String(255), nullable=False)
    locator_candidates: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    locator_scores: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    robustness_score: Mapped[float] = mapped_column(Float, default=50.0, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(10), default="medium", nullable=False)
    risk_reason: Mapped[str] = mapped_column(Text, default="", nullable=False)
    timeout_ms: Mapped[int] = mapped_column(Integer, default=15000, nullable=False)
    max_retries: Mapped[int] = mapped_column(Integer, default=2, nullable=False)
    depends_on: Mapped[list] = mapped_column(JSON, default=list, nullable=False)
    assert_rule: Mapped[str | None] = mapped_column(String(255), nullable=True)

"""initial schema baseline (rpaloop)

Revision ID: 0001_initial
Revises:
Create Date: 2026-11-10

The initial schema is created from the SQLAlchemy metadata so that models stay
the single source of truth for this demo deployment.
"""
from alembic import op

from src.config.database import Base
import src.models  # noqa: F401

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())

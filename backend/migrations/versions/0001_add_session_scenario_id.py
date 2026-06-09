"""Add scenario_id to session for per-session scenario selection

Replaces the process-global "current scenario" with a scenario selection
stored on each chat session.

This migration is defensive because fresh databases get their full schema
(including this column) from SQLModel.metadata.create_all() at app startup:
- If the session table doesn't exist yet, this is a fresh database and the
  migration no-ops.
- If the column already exists, the migration no-ops.

Revision ID: 0001
Revises:
Create Date: 2026-06-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _session_columns(inspector: sa.engine.reflection.Inspector) -> set[str]:
    return {column["name"] for column in inspector.get_columns("session")}


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if "session" not in inspector.get_table_names():
        # Fresh database: create_all() will create the table with the column.
        return

    if "scenario_id" not in _session_columns(inspector):
        op.add_column("session", sa.Column("scenario_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if "session" in inspector.get_table_names() and "scenario_id" in _session_columns(inspector):
        op.drop_column("session", "scenario_id")

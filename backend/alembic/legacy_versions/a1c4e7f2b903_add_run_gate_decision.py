"""Add gate decision columns to runs

Revision ID: a1c4e7f2b903
Revises: 49333067fd05
Create Date: 2026-10-11 20:00:00

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "a1c4e7f2b903"
down_revision: Union[str, None] = "49333067fd05"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("runs", sa.Column("gate_decision", sa.String(length=16), nullable=True))
    op.add_column("runs", sa.Column("gate_summary", sa.Text(), nullable=True))
    op.create_index("ix_runs_gate_decision", "runs", ["gate_decision"])


def downgrade() -> None:
    op.drop_index("ix_runs_gate_decision", table_name="runs")
    op.drop_column("runs", "gate_summary")
    op.drop_column("runs", "gate_decision")

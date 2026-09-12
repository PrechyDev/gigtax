"""add discarded_at to transactions

Revision ID: 1c34255f0b55
Revises: 875487d09a8b
Create Date: 2026-09-12 00:05:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1c34255f0b55'
down_revision: Union[str, Sequence[str], None] = '875487d09a8b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Set when a transaction's review_status is set to REJECTED (a "discard"),
    cleared when it moves away from REJECTED again (a "restore") — see
    api/routes/transactions.py's _apply_review_status. Indexed because the daily
    scheduled cleanup job (core/scheduled_cleanup.py) filters on it to find
    transactions past their 30-day recovery window.
    """
    op.add_column("transactions", sa.Column("discarded_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index("ix_transactions_discarded_at", "transactions", ["discarded_at"])


def downgrade() -> None:
    op.drop_index("ix_transactions_discarded_at", table_name="transactions")
    op.drop_column("transactions", "discarded_at")

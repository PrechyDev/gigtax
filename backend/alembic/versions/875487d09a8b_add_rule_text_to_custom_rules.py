"""add rule_text to custom_rules and make assigned_category nullable

Revision ID: 875487d09a8b
Revises: 16b955c25b3b
Create Date: 2026-09-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '875487d09a8b'
down_revision: Union[str, Sequence[str], None] = '16b955c25b3b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """A custom rule now has two authoring modes: assigned_category (existing, exact
    category mapping) or rule_text (new, freeform natural-language instruction handed
    to the categorization prompt as-is). Exactly one is required at the schema level
    (see schemas/custom_rule.py's validator) — assigned_category can no longer be
    NOT NULL at the DB level since a freeform rule leaves it unset.
    """
    op.add_column("custom_rules", sa.Column("rule_text", sa.String(length=1000), nullable=True))
    op.alter_column("custom_rules", "assigned_category", existing_type=sa.String(length=100), nullable=True)


def downgrade() -> None:
    op.alter_column("custom_rules", "assigned_category", existing_type=sa.String(length=100), nullable=False)
    op.drop_column("custom_rules", "rule_text")

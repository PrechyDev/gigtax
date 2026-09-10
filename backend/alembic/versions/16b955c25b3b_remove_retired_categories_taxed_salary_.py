"""remove retired categories taxed_salary_paye and relief_residential_rent

Revision ID: 16b955c25b3b
Revises: ec07c7fb03d6
Create Date: 2026-09-11 00:08:46.931586

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '16b955c25b3b'
down_revision: Union[str, Sequence[str], None] = 'ec07c7fb03d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add Category.is_active and retire the two categories dropped from
    db/seed_data/categories.json in earlier work. A hard delete isn't safe here — any
    transaction already categorized against one of these still holds a foreign key to
    it — so this deactivates them instead: the row (and any transaction referencing it)
    stays intact, but GET /categories stops offering it for new selection.
    """
    op.add_column("categories", sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"))
    op.execute(
        "UPDATE categories SET is_active = false "
        "WHERE developer_slug IN ('taxed_salary_paye', 'relief_residential_rent')"
    )


def downgrade() -> None:
    op.drop_column("categories", "is_active")

"""add knowledge_chunks table for RAG advisor

Revision ID: 3283021eeafe
Revises: a8eb50becc79
Create Date: 2026-09-10 10:11:15.400984

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = '3283021eeafe'
down_revision: Union[str, Sequence[str], None] = 'a8eb50becc79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Must run before the table below — the `embedding` column's type depends on it.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table('knowledge_chunks',
    sa.Column('chunk_id', sa.UUID(), nullable=False),
    sa.Column('source_title', sa.String(length=255), nullable=False),
    sa.Column('citation', sa.String(length=100), nullable=False),
    sa.Column('chunk_index', sa.Integer(), nullable=False),
    sa.Column('content', sa.Text(), nullable=False),
    sa.Column('embedding', Vector(3072), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
    sa.PrimaryKeyConstraint('chunk_id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('knowledge_chunks')
    # Deliberately not dropping the `vector` extension — other tables/future
    # migrations may still depend on it, and dropping an extension is a bigger,
    # less reversible action than dropping one table.

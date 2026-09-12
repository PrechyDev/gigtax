"""add annual_tax_profiles, move rent/home-office off users to be per-tax-year

Revision ID: efe05f7451d6
Revises: 1c34255f0b55
Create Date: 2026-09-12 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'efe05f7451d6'
down_revision: Union[str, Sequence[str], None] = '1c34255f0b55'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rent paid and home-office claim genuinely change year to year (a new lease, a
    bigger/smaller home-office share) — they can't stay a single static value on the
    user row the way TIN or state of residence can, or last year's numbers silently
    drift whenever this year's setting changes. See models/annual_tax_profile.py.
    """
    op.create_table(
        "annual_tax_profiles",
        sa.Column("annual_tax_profile_id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.user_id"), nullable=False),
        sa.Column("tax_year", sa.String(length=4), nullable=False),
        sa.Column("annual_rent_paid", sa.Float(), nullable=True),
        sa.Column("has_home_office", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("home_office_percentage", sa.Float(), nullable=False, server_default="0.0"),
        sa.UniqueConstraint("user_id", "tax_year", name="uq_annual_tax_profile_user_year"),
    )

    # Carry over any existing profile-level rent/home-office data into a row for that
    # user's current tax_year setting (or this calendar year if that field was never
    # set) — a one-time best-effort default the user can then edit or add more years
    # to, rather than silently losing what was already entered.
    op.execute(
        """
        INSERT INTO annual_tax_profiles
            (annual_tax_profile_id, user_id, tax_year, annual_rent_paid, has_home_office, home_office_percentage)
        SELECT
            gen_random_uuid(),
            user_id,
            COALESCE(NULLIF(tax_year, ''), EXTRACT(YEAR FROM CURRENT_DATE)::text),
            annual_rent_paid,
            has_home_office,
            home_office_percentage
        FROM users
        WHERE annual_rent_paid IS NOT NULL OR has_home_office = true
        """
    )

    op.drop_column("users", "annual_rent_paid")
    op.drop_column("users", "has_home_office")
    op.drop_column("users", "home_office_percentage")


def downgrade() -> None:
    op.add_column("users", sa.Column("has_home_office", sa.Boolean(), nullable=True, server_default="false"))
    op.add_column("users", sa.Column("home_office_percentage", sa.Float(), nullable=True, server_default="0.0"))
    op.add_column("users", sa.Column("annual_rent_paid", sa.Float(), nullable=True))

    # Best-effort, lossy if a user has rows for more than one tax year — picks one
    # arbitrarily, since the column being restored can only hold a single value again.
    op.execute(
        """
        UPDATE users
        SET annual_rent_paid = p.annual_rent_paid,
            has_home_office = p.has_home_office,
            home_office_percentage = p.home_office_percentage
        FROM (
            SELECT DISTINCT ON (user_id) user_id, annual_rent_paid, has_home_office, home_office_percentage
            FROM annual_tax_profiles
            ORDER BY user_id, tax_year DESC
        ) p
        WHERE users.user_id = p.user_id
        """
    )

    op.drop_table("annual_tax_profiles")

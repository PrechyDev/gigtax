"""Loads a user's APPROVED transactions for a tax year out of the DB and flattens
them into the engine's ORM-independent CategorizedTransaction shape. Keeps the pure
engine (engine.py) from knowing anything about SQLAlchemy.
"""
from datetime import datetime
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.orm import Session

from models.annual_tax_profile import AnnualTaxProfile
from models.asset import Asset
from models.category import Category
from models.transaction import Transaction
from models.user import User
from modules.tax_computation.capital_allowances import (
    ASSET_CLASS_RATES,
    CapitalAsset,
    allowance_for_year,
    total_capital_allowances,
)
from modules.tax_computation.engine import RENT_RELIEF_SLUG, CategorizedTransaction

# Synthetic category for the home-office share of rent — not a real seeded Category
# row (rent is a profile field, not a ledger transaction), so callers that display
# category names need to special-case this slug. See _rent_categorized_transactions.
RENT_HOME_OFFICE_SLUG = "rent_home_office_expense"

# Display names for slugs that don't correspond to a seeded Category row — the two
# rent-derived synthetic entries above, plus relief_residential_rent itself, which
# was retired from seed data (see db/seed_data/categories.json) now that rent is a
# profile field rather than a manually-selectable category.
SYNTHETIC_CATEGORY_LABELS: dict[str, str] = {
    RENT_HOME_OFFICE_SLUG: "Rent (Home Office Portion)",
    RENT_RELIEF_SLUG: "Rent Relief",
}


def load_annual_tax_profile(db: Session, user_id: UUID, tax_year: str) -> AnnualTaxProfile | None:
    """Rent paid and home-office claim are scoped to a single tax year (see
    models/annual_tax_profile.py) — this is the one place that query lives, shared by
    the rent-relief calculation below, ingestion's home-office deductibility stamping
    (modules/ingestion/persistence.py), and manual entry / recategorization
    (api/routes/transactions.py), so all three agree on "which year's row applies."
    """
    return (
        db.query(AnnualTaxProfile)
        .filter(AnnualTaxProfile.user_id == user_id, AnnualTaxProfile.tax_year == tax_year)
        .first()
    )


def _rent_categorized_transactions(annual_profile: AnnualTaxProfile | None) -> list[CategorizedTransaction]:
    """Rent is a per-year profile field, not a transaction — the user's home-office
    percentage for that year splits it at computation time rather than requiring them
    to manually enter two separate ledger records. The home-office share becomes a
    Business Expense; the remainder feeds the existing rent-relief handling in
    engine.py (which itself applies the 20%/cap rule) unchanged.
    """
    if annual_profile is None or not annual_profile.annual_rent_paid or annual_profile.annual_rent_paid <= 0:
        return []

    home_office_share = annual_profile.annual_rent_paid * (annual_profile.home_office_percentage or 0.0) / 100.0
    remainder = annual_profile.annual_rent_paid - home_office_share

    synthesized = []
    if home_office_share > 0:
        synthesized.append(CategorizedTransaction(
            amount=home_office_share,
            classification="Expense",
            category_slug=RENT_HOME_OFFICE_SLUG,
            tax_treatment="100_percent_deductible_home_office",
        ))
    if remainder > 0:
        synthesized.append(CategorizedTransaction(
            amount=remainder,
            classification="Relief",
            category_slug=RENT_RELIEF_SLUG,
            tax_treatment="deductible_relief_capped",
        ))
    return synthesized


def load_categorized_transactions(db: Session, user: User, tax_year: str) -> list[CategorizedTransaction]:
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user.user_id,
            Transaction.review_status == "APPROVED",
            Transaction.date >= f"{tax_year}-01-01",
            Transaction.date <= f"{tax_year}-12-31T23:59:59",
        )
        .all()
    )

    category_ids = {tx.user_category_id or tx.ai_category_id for tx in transactions if (tx.user_category_id or tx.ai_category_id)}
    categories_by_id = {
        c.category_id: c
        for c in db.query(Category).filter(Category.category_id.in_(category_ids)).all()
    } if category_ids else {}

    annual_profile = load_annual_tax_profile(db, user.user_id, tax_year)

    result = []
    for tx in transactions:
        effective_category_id = tx.user_category_id or tx.ai_category_id
        category = categories_by_id.get(effective_category_id)
        
        tax_treatment = tx.tax_treatment
        if tax_treatment == "100_percent_deductible_home_office":
            if annual_profile and annual_profile.has_home_office:
                deductibility = annual_profile.home_office_percentage
            else:
                deductibility = 100.0
        else:
            deductibility = getattr(tx, "deductibility_percentage", 100.0) or 100.0

        result.append(CategorizedTransaction(
            amount=tx.amount,
            classification=category.classification if category else "Unknown",
            category_slug=category.developer_slug if category else None,
            tax_treatment=tax_treatment,
            deductibility_percentage=deductibility,
        ))
    result.extend(_rent_categorized_transactions(annual_profile))
    return result


def get_records_period(db: Session, user: User, tax_year: str) -> tuple[datetime | None, datetime | None]:
    """The actual span of dates covered by this year's APPROVED records — the
    earliest and latest transaction date on file, not just the calendar
    Jan 1 - Dec 31 boundary used to filter them. Report headers use this so a user
    who, say, only has records from March onward sees that reflected honestly
    rather than implying a full-year's records exist. Returns (None, None) when
    there are no APPROVED transactions for the year.
    """
    earliest, latest = (
        db.query(func.min(Transaction.date), func.max(Transaction.date))
        .filter(
            Transaction.user_id == user.user_id,
            Transaction.review_status == "APPROVED",
            Transaction.date >= f"{tax_year}-01-01",
            Transaction.date <= f"{tax_year}-12-31T23:59:59",
        )
        .one()
    )
    return earliest, latest


def load_capital_allowances_for_year(db: Session, user_id: UUID, tax_year: str) -> float:
    """Capital allowances depend on an asset's whole ownership history, not just
    transactions dated within `tax_year` — an asset bought in 2024 can still be
    depreciating in 2026 with no 2026 transaction of its own. So this loads every
    non-disposed-before-this-year asset the user owns, not a date-filtered query.
    """
    assets = db.query(Asset).filter(Asset.user_id == user_id).all()

    capital_assets = [
        CapitalAsset(
            cost=asset.cost,
            asset_class=asset.asset_class,
            acquired_year=asset.purchase_date.year,
            disposed_year=asset.disposed_date.year if (asset.disposed and asset.disposed_date) else None,
        )
        for asset in assets
    ]
    return total_capital_allowances(capital_assets, int(tax_year))


def load_capital_allowance_items(db: Session, user_id: UUID, tax_year: str) -> list[dict]:
    """Per-asset breakdown for report itemization — mirrors
    load_capital_allowances_for_year's query, but keeps each asset's own allowance
    instead of summing them, and drops assets with nothing to claim this year
    (not yet owned, disposed of, or fully written down).
    """
    assets = db.query(Asset).filter(Asset.user_id == user_id).all()
    tax_year_int = int(tax_year)

    items = []
    for asset in assets:
        capital_asset = CapitalAsset(
            cost=asset.cost,
            asset_class=asset.asset_class,
            acquired_year=asset.purchase_date.year,
            disposed_year=asset.disposed_date.year if (asset.disposed and asset.disposed_date) else None,
        )
        amount = allowance_for_year(capital_asset, tax_year_int)
        if amount > 0:
            items.append({
                "category_name": asset.description,
                "amount": amount,
                "rate": ASSET_CLASS_RATES[asset.asset_class] * 100,
                "gross_amount": asset.cost,
            })
    return items

"""Loads a user's APPROVED transactions for a tax year out of the DB and flattens
them into the engine's ORM-independent CategorizedTransaction shape. Keeps the pure
engine (engine.py) from knowing anything about SQLAlchemy.
"""
from uuid import UUID

from sqlalchemy.orm import Session

from models.asset import Asset
from models.category import Category
from models.transaction import Transaction
from modules.tax_computation.capital_allowances import CapitalAsset, total_capital_allowances
from modules.tax_computation.engine import CategorizedTransaction


def load_categorized_transactions(db: Session, user_id: UUID, tax_year: str) -> list[CategorizedTransaction]:
    transactions = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
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

    result = []
    for tx in transactions:
        effective_category_id = tx.user_category_id or tx.ai_category_id
        category = categories_by_id.get(effective_category_id)
        result.append(CategorizedTransaction(
            amount=tx.amount,
            classification=category.classification if category else "Unknown",
            category_slug=category.developer_slug if category else None,
            tax_treatment=tx.tax_treatment,
            deductibility_percentage=getattr(tx, "deductibility_percentage", 100.0) or 100.0,
        ))
    return result


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

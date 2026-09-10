"""Keeps the `assets` table in sync with whatever category a transaction currently
has. Shared by every write path that can set/change a transaction's category:
AI ingestion, manual entry, and a human correcting a category during review —
capital items must always have exactly one linked Asset row, and a transaction
that's no longer categorized as an Asset must not leave a stale one behind.
"""
from sqlalchemy.orm import Session

from models.asset import Asset
from models.category import Category
from models.transaction import Transaction


def sync_asset_for_transaction(db: Session, transaction: Transaction, category: Category | None) -> None:
    """`transaction` must already have a persisted `transaction_id` (flush first if
    it was just created in this same session).
    """
    existing_asset = (
        db.query(Asset).filter(Asset.transaction_id == transaction.transaction_id).first()
    )
    is_asset_category = category is not None and category.classification == "Asset"

    if is_asset_category and existing_asset is None:
        db.add(Asset(
            user_id=transaction.user_id,
            transaction_id=transaction.transaction_id,
            description=transaction.description,
            cost=transaction.amount,
            purchase_date=transaction.date,
            asset_class=category.asset_class,
        ))
    elif not is_asset_category and existing_asset is not None:
        # Re-categorized away from an asset class — it's a normal expense now.
        db.delete(existing_asset)
    elif is_asset_category and existing_asset is not None and existing_asset.asset_class != category.asset_class:
        existing_asset.asset_class = category.asset_class

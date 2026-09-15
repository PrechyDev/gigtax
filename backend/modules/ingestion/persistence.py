"""Turns a `ParsedTransaction` (the AI categorization pipeline's output shape) into a
persisted `IncomeRecord`/`ExpenseRecord` row. Kept separate from the pipeline itself —
the pipeline knows nothing about the database, this module knows nothing about LLMs.
"""
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from models.category import Category
from models.transaction import ExpenseRecord, IncomeRecord, Transaction
from models.user import User
from modules.ai_categorization.schemas import ParsedTransaction
from modules.ingestion.asset_sync import sync_asset_for_transaction
from modules.tax_computation.loader import load_annual_tax_profile

UNCATEGORIZED_SLUG = "uncategorized"
HOME_OFFICE_TAX_TREATMENT = "100_percent_deductible_home_office"


def _parse_transaction_date(date_str: str) -> datetime:
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        # A malformed/missing date from the LLM shouldn't drop the transaction — surface
        # it for review (today's date is an obvious placeholder a user will notice and fix).
        return datetime.now(timezone.utc)


def _resolve_category(db: Session, category_slug: str | None) -> Category | None:
    category = None
    if category_slug:
        category = db.query(Category).filter(Category.developer_slug == category_slug).first()
    if category is None:
        category = db.query(Category).filter(Category.developer_slug == UNCATEGORIZED_SLUG).first()
    return category


def persist_parsed_transaction(
    db: Session,
    parsed: ParsedTransaction,
    user: User,
    statement_id: UUID | None,
) -> Transaction:
    category = _resolve_category(db, parsed.category_slug)
    transaction_date = _parse_transaction_date(parsed.date)

    common_kwargs = dict(
        user_id=user.user_id,
        statement_id=statement_id,
        date=transaction_date,
        description=parsed.description,
        amount=parsed.amount,
        ai_category_id=category.category_id if category else None,
        confidence_score=parsed.confidence_score,
        review_status="PENDING",
        tax_treatment=category.tax_treatment if category else None,
    )

    if parsed.transaction_type.lower() == "income":
        record = IncomeRecord(**common_kwargs, income_source=parsed.income_source)
    else:
        record = ExpenseRecord(**common_kwargs, merchant_name=parsed.merchant_name)

    db.add(record)
    db.flush()  # assigns record.transaction_id, needed by sync_asset_for_transaction
    sync_asset_for_transaction(db, record, category)

    return record

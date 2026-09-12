from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from api.deps import get_current_user
from db.session import get_db
from models.asset import Asset
from models.category import Category
from models.transaction import ExpenseRecord, IncomeRecord, Transaction
from models.user import User
from modules.ingestion.asset_sync import sync_asset_for_transaction
from modules.ingestion.persistence import HOME_OFFICE_TAX_TREATMENT, UNCATEGORIZED_SLUG
from modules.tax_computation.loader import load_annual_tax_profile
from schemas.transaction import (
    BulkTransactionDelete,
    BulkTransactionReview,
    ManualTransactionCreate,
    TransactionOut,
    TransactionReviewUpdate,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _home_office_deductibility(db: Session, user_id, year: int, category: Category | None) -> float:
    """The % of a home-office-treated expense that's actually deductible, scoped to
    the tax year the expense's own date falls in (not "whatever's set right now") —
    see models/annual_tax_profile.py. Anything not home-office-treated is fully
    deductible, same as the ExpenseRecord.deductibility_percentage column default.
    """
    if not category or category.tax_treatment != HOME_OFFICE_TAX_TREATMENT:
        return 100.0
    annual_profile = load_annual_tax_profile(db, user_id, str(year))
    if annual_profile and annual_profile.has_home_office:
        return annual_profile.home_office_percentage
    return 100.0


@router.post("", response_model=TransactionOut, status_code=status.HTTP_201_CREATED)
def create_manual_transaction(
    payload: ManualTransactionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Manual entry bypasses the AI pipeline entirely, so there's no AI category to
    review — the user is already the source of truth for something they typed in
    themselves, so it's created straight into APPROVED rather than PENDING review.
    """
    category = None
    if payload.category_slug:
        category = db.query(Category).filter(Category.developer_slug == payload.category_slug).first()
        if category is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown category_slug")

    common_kwargs = dict(
        user_id=current_user.user_id,
        statement_id=None,
        date=payload.date,
        description=payload.description,
        amount=payload.amount,
        currency=payload.currency,
        ai_category_id=None,
        user_category_id=category.category_id if category else None,
        confidence_score=None,
        review_status="APPROVED",
        tax_treatment=category.tax_treatment if category else None,
    )

    if payload.transaction_type == "income":
        record = IncomeRecord(**common_kwargs, income_source=payload.income_source)
    else:
        record = ExpenseRecord(**common_kwargs, merchant_name=payload.merchant_name)
        record.deductibility_percentage = _home_office_deductibility(db, current_user.user_id, payload.date.year, category)

    db.add(record)
    db.flush()  # assigns record.transaction_id, needed by sync_asset_for_transaction
    sync_asset_for_transaction(db, record, category)
    db.commit()
    db.refresh(record)
    return record


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    review_status: str | None = Query(default=None),
    tax_year: str | None = Query(default=None),
    transaction_type: str | None = Query(default=None, description="'income' or 'expense'"),
    category_slug: str | None = Query(
        default=None,
        description="Filters to transactions currently resolved to this category (user_category_id if set, else ai_category_id) — e.g. 'uncategorized' to find AI-flagged personal/unclear transactions needing a decision.",
    ),
    exclude_uncategorized: bool = Query(
        default=False,
        description="Excludes transactions resolved to the 'uncategorized' fallback category — used by the Pending Review bucket to stay disjoint from the Uncategorized bucket (see category_slug='uncategorized').",
    ),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = (
        db.query(Transaction)
        .options(joinedload(Transaction.statement))
        .filter(Transaction.user_id == current_user.user_id)
    )
    if review_status:
        query = query.filter(Transaction.review_status == review_status.upper())
    if transaction_type:
        query = query.filter(Transaction.type == transaction_type.lower())
    if tax_year:
        query = query.filter(
            Transaction.date >= f"{tax_year}-01-01", Transaction.date <= f"{tax_year}-12-31"
        )
    if category_slug:
        category = db.query(Category).filter(Category.developer_slug == category_slug).first()
        category_id = category.category_id if category else None
        # An unknown slug should return zero rows, not "no filter" — compare against a
        # sentinel that can never match a real category_id rather than skipping the filter.
        query = query.filter(
            func.coalesce(Transaction.user_category_id, Transaction.ai_category_id) == category_id
        )
    if exclude_uncategorized:
        uncategorized = db.query(Category).filter(Category.developer_slug == UNCATEGORIZED_SLUG).first()
        if uncategorized:
            resolved_category = func.coalesce(Transaction.user_category_id, Transaction.ai_category_id)
            # A transaction with no resolved category at all isn't the "flagged personal"
            # case this excludes — it should stay visible here, not silently disappear.
            query = query.filter(or_(resolved_category != uncategorized.category_id, resolved_category.is_(None)))
    return query.order_by(Transaction.date.desc()).offset(offset).limit(limit).all()


def _apply_review_status(transaction: Transaction, review_status: str) -> None:
    """Setting REJECTED is a *discard*, not a delete — it stamps discarded_at so the
    scheduled cleanup job (core/scheduled_cleanup.py) knows when the 30-day recovery
    window started. Moving away from REJECTED (restoring to PENDING/APPROVED) clears
    it again, so a restored transaction is no longer on the purge clock.
    """
    transaction.review_status = review_status
    transaction.discarded_at = datetime.now(timezone.utc) if review_status == "REJECTED" else None


def _hard_delete_transaction(db: Session, transaction: Transaction) -> None:
    """Permanent delete — used by the single/bulk DELETE endpoints (reachable from the
    Discarded tab's "delete now" for a user who wants to skip the 30-day wait) and by
    the scheduled purge job once that window has passed.
    """
    # A capital-item purchase has a linked Asset row (see modules/ingestion/asset_sync.py) —
    # remove it first, or the DB's foreign key rejects the delete outright.
    linked_asset = db.query(Asset).filter(Asset.transaction_id == transaction.transaction_id).first()
    if linked_asset is not None:
        db.delete(linked_asset)
    db.delete(transaction)


@router.patch("/bulk-review", response_model=list[TransactionOut])
def bulk_review_transactions(
    payload: BulkTransactionReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Bulk approve/discard/restore in one round trip and one commit — the ids-only
    payload keeps this a single request regardless of selection size, unlike looping
    the single-item PATCH below. Ids that don't exist or aren't this user's are
    silently skipped rather than failing the whole batch.

    Registered ahead of the "/{transaction_id}" PATCH route below — FastAPI/Starlette
    matches routes in registration order, so a literal path segment like this one must
    come before a parameterized "/{transaction_id}" route or requests here would be
    swallowed by that route instead (with "bulk-review" failing UUID validation).
    """
    transactions = (
        db.query(Transaction)
        .filter(Transaction.transaction_id.in_(payload.transaction_ids), Transaction.user_id == current_user.user_id)
        .all()
    )
    for transaction in transactions:
        _apply_review_status(transaction, payload.review_status)
    db.commit()
    for transaction in transactions:
        db.refresh(transaction)
    return transactions


@router.delete("/bulk", status_code=status.HTTP_204_NO_CONTENT)
def bulk_delete_transactions(
    payload: BulkTransactionDelete,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Same registration-order note as bulk_review_transactions above applies here —
    must come before the "/{transaction_id}" DELETE route.
    """
    transactions = (
        db.query(Transaction)
        .filter(Transaction.transaction_id.in_(payload.transaction_ids), Transaction.user_id == current_user.user_id)
        .all()
    )
    for transaction in transactions:
        _hard_delete_transaction(db, transaction)
    db.commit()


@router.patch("/{transaction_id}", response_model=TransactionOut)
def review_transaction(
    transaction_id: UUID,
    payload: TransactionReviewUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = (
        db.query(Transaction)
        .filter(Transaction.transaction_id == transaction_id, Transaction.user_id == current_user.user_id)
        .first()
    )
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    if payload.category_slug is not None:
        category = db.query(Category).filter(Category.developer_slug == payload.category_slug).first()
        if category is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unknown category_slug")
        transaction.user_category_id = category.category_id
        transaction.tax_treatment = category.tax_treatment
        # Keep the assets table in sync — this correction might turn a normal expense
        # into a capital item (or vice versa) if the AI mis-tagged it originally.
        sync_asset_for_transaction(db, transaction, category)
        # Same correction for deductibility: a category change into or out of the
        # home-office treatment must re-derive the % (ingestion only stamps this once,
        # at creation time — a later recategorization was previously left stale at
        # whatever it started as, silently understating or overstating the deduction).
        if isinstance(transaction, ExpenseRecord):
            transaction.deductibility_percentage = _home_office_deductibility(
                db, current_user.user_id, transaction.date.year, category
            )

    if payload.review_status is not None:
        _apply_review_status(transaction, payload.review_status)

    if payload.description is not None:
        transaction.description = payload.description

    db.commit()
    db.refresh(transaction)
    return transaction


@router.delete("/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(
    transaction_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transaction = (
        db.query(Transaction)
        .filter(Transaction.transaction_id == transaction_id, Transaction.user_id == current_user.user_id)
        .first()
    )
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found")

    _hard_delete_transaction(db, transaction)
    db.commit()

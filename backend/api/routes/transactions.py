from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models.category import Category
from models.transaction import ExpenseRecord, IncomeRecord, Transaction
from models.user import User
from modules.ingestion.asset_sync import sync_asset_for_transaction
from schemas.transaction import ManualTransactionCreate, TransactionOut, TransactionReviewUpdate

router = APIRouter(prefix="/transactions", tags=["transactions"])


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
        if category and category.tax_treatment == "100_percent_deductible_home_office" and current_user.has_home_office:
            record.deductibility_percentage = current_user.home_office_percentage

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
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Transaction).filter(Transaction.user_id == current_user.user_id)
    if review_status:
        query = query.filter(Transaction.review_status == review_status.upper())
    if transaction_type:
        query = query.filter(Transaction.type == transaction_type.lower())
    if tax_year:
        query = query.filter(
            Transaction.date >= f"{tax_year}-01-01", Transaction.date <= f"{tax_year}-12-31"
        )
    return query.order_by(Transaction.date.desc()).all()


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

    if payload.review_status is not None:
        transaction.review_status = payload.review_status

    db.commit()
    db.refresh(transaction)
    return transaction

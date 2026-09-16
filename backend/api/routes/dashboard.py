from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models.category import Category
from models.receipt import Receipt
from models.statement import ParsingStatus, StatementUpload
from models.transaction import ExpenseRecord, Transaction
from models.user import User
from modules.ingestion.persistence import UNCATEGORIZED_SLUG
from modules.tax_computation.engine import compute_tax
from modules.tax_computation.loader import load_capital_allowances_for_year, load_categorized_transactions
from schemas.dashboard import ActionItemOut, DashboardOut

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

# Deliberately generic rather than a specific date: actual filing deadlines are set by
# each State Internal Revenue Service (and by the Nigeria Tax Administration Act, a
# separate instrument from the NTA 2025 this project implements) — asserting a specific
# day/month here without having verified it against that Act would risk misleading a
# user about a real compliance deadline.
FILING_GUIDANCE = (
    "Filing deadlines and procedures are set by your State Internal Revenue Service — "
    "check your state's portal (e.g. LIRS eTax for Lagos, FCT-IRS Taxportal, RIVTAMIS for "
    "Rivers) for this year's deadline."
)


@router.get("", response_model=DashboardOut)
def get_dashboard(
    tax_year: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transactions = load_categorized_transactions(db, current_user, tax_year)
    capital_allowances = load_capital_allowances_for_year(db, current_user.user_id, tax_year)
    result = compute_tax(transactions, capital_allowances_this_year=capital_allowances)

    year_start, year_end = f"{tax_year}-01-01", f"{tax_year}-12-31T23:59:59"

    # Split into two counts matching the Ledger's own two buckets — "Pending Review"
    # (a real/AI-assigned category, just needs confirming) and "Uncategorized" (the AI
    # flagged it personal/unclear and never assigned a real category at all). See
    # api/routes/transactions.py's exclude_uncategorized/category_slug filters, which
    # this mirrors so the dashboard's counts always match what each Ledger tab shows.
    uncategorized_category = db.query(Category).filter(Category.developer_slug == UNCATEGORIZED_SLUG).first()
    resolved_category = func.coalesce(Transaction.user_category_id, Transaction.ai_category_id)

    pending_base_query = db.query(Transaction).filter(
        Transaction.user_id == current_user.user_id,
        Transaction.review_status == "PENDING",
        Transaction.date >= year_start,
        Transaction.date <= year_end,
    )

    if uncategorized_category:
        pending_review_count = pending_base_query.filter(
            or_(resolved_category != uncategorized_category.category_id, resolved_category.is_(None))
        ).count()
        uncategorized_count = pending_base_query.filter(
            resolved_category == uncategorized_category.category_id
        ).count()
    else:
        pending_review_count = pending_base_query.count()
        uncategorized_count = 0

    locked_statements_count = (
        db.query(StatementUpload)
        .filter(
            StatementUpload.user_id == current_user.user_id,
            StatementUpload.parsing_status == ParsingStatus.LOCKED,
        )
        .count()
    )

    approved_expense_ids = [
        row[0] for row in (
            db.query(ExpenseRecord.transaction_id)
            .filter(
                ExpenseRecord.user_id == current_user.user_id,
                ExpenseRecord.review_status == "APPROVED",
                ExpenseRecord.date >= year_start,
                ExpenseRecord.date <= year_end,
            )
            .all()
        )
    ]
    receipted_ids = set()
    if approved_expense_ids:
        receipted_ids = {
            row[0] for row in (
                db.query(Receipt.transaction_id)
                .filter(Receipt.transaction_id.in_(approved_expense_ids))
                .all()
            )
        }
    missing_receipts_count = len(set(approved_expense_ids) - receipted_ids)

    outstanding_actions = []
    if not current_user.google_drive_connected:
        outstanding_actions.append(ActionItemOut(
            message="Connect Google Drive to enable receipt uploads and backups.", href="/settings",
        ))
    if pending_review_count:
        outstanding_actions.append(ActionItemOut(
            message=f"{pending_review_count} transaction(s) awaiting your review.", href="/ledger?tab=pending",
        ))
    if uncategorized_count:
        outstanding_actions.append(ActionItemOut(
            message=f"{uncategorized_count} transaction(s) flagged as personal or unclear.",
            href="/ledger?tab=uncategorized",
        ))
    if locked_statements_count:
        outstanding_actions.append(ActionItemOut(
            message=f"{locked_statements_count} uploaded statement(s) need a password.", href="/ingestion",
        ))
    if missing_receipts_count:
        outstanding_actions.append(ActionItemOut(
            message=f"{missing_receipts_count} approved expense(s) have no receipt attached.", href="/ledger",
        ))

    return DashboardOut(
        tax_year=tax_year,
        total_income=result.total_income,
        total_deductions=result.total_deductions,
        total_reliefs=result.total_reliefs,
        total_capital_allowances=result.total_capital_allowances,
        estimated_tax_owed=result.net_tax,
        approved_transactions_count=len(transactions),
        pending_review_count=pending_review_count,
        uncategorized_count=uncategorized_count,
        locked_statements_count=locked_statements_count,
        missing_receipts_count=missing_receipts_count,
        google_drive_connected=current_user.google_drive_connected,
        filing_guidance=FILING_GUIDANCE,
        outstanding_actions=outstanding_actions,
    )

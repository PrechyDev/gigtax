from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models.category import Category
from models.tax import TaxComputation
from models.user import User
from modules.tax_computation.engine import (
    EXCLUDED_INCOME_TREATMENTS,
    NATIONAL_MINIMUM_WAGE_ANNUAL,
    RENT_RELIEF_SLUG,
    CategorizedTransaction,
    apply_fourth_schedule,
    compute_tax,
    rent_relief_amount,
)
from modules.tax_computation.loader import (
    SYNTHETIC_CATEGORY_LABELS,
    load_capital_allowance_items,
    load_capital_allowances_for_year,
    load_categorized_transactions,
)
from schemas.tax import TaxComputationOut

router = APIRouter(prefix="/tax-computations", tags=["tax-computations"])

EMPTY_ITEMS = {
    "income_items": [],
    "deduction_items": [],
    "relief_items": [],
    "capital_allowance_items": [],
}


def _category_label(slug: str | None, categories_by_slug: dict[str, Category]) -> str:
    if slug is None:
        return "Uncategorized"
    if slug in SYNTHETIC_CATEGORY_LABELS:
        return SYNTHETIC_CATEGORY_LABELS[slug]
    category = categories_by_slug.get(slug)
    return category.category_name if category else slug


def _build_itemized_breakdown(
    db: Session, transactions: list[CategorizedTransaction], capital_allowance_items: list[dict]
) -> dict:
    """Mirrors engine.compute_tax's own per-transaction logic exactly, so each list's
    total reconciles with the corresponding total_* figure returned alongside it.
    """
    slugs = {tx.category_slug for tx in transactions if tx.category_slug}
    categories_by_slug = {
        c.developer_slug: c for c in db.query(Category).filter(Category.developer_slug.in_(slugs)).all()
    } if slugs else {}

    income_totals: dict[str, float] = defaultdict(float)
    deduction_totals: dict[str, float] = defaultdict(float)
    relief_totals: dict[str, float] = defaultdict(float)

    for tx in transactions:
        label = _category_label(tx.category_slug, categories_by_slug)
        if tx.classification == "Income":
            if tx.tax_treatment not in EXCLUDED_INCOME_TREATMENTS:
                income_totals[label] += tx.amount
        elif tx.classification == "Expense":
            deduction_totals[label] += tx.amount * (tx.deductibility_percentage / 100.0)
        elif tx.classification == "Relief":
            amount = rent_relief_amount(tx.amount) if tx.category_slug == RENT_RELIEF_SLUG else tx.amount
            relief_totals[label] += amount

    def _to_items(totals: dict[str, float]) -> list[dict]:
        return [{"category_name": name, "amount": amount} for name, amount in totals.items() if amount > 0]

    return {
        "income_items": _to_items(income_totals),
        "deduction_items": _to_items(deduction_totals),
        "relief_items": _to_items(relief_totals),
        "capital_allowance_items": capital_allowance_items,
    }


def _get_or_create_computation(db: Session, user: User, tax_year: str) -> TaxComputation:
    computation = (
        db.query(TaxComputation)
        .filter(TaxComputation.user_id == user.user_id, TaxComputation.tax_year == tax_year)
        .first()
    )
    if computation is None:
        computation = TaxComputation(user_id=user.user_id, tax_year=tax_year)
        db.add(computation)
    return computation


@router.post("/{tax_year}/compute", response_model=TaxComputationOut)
def compute_tax_for_year(
    tax_year: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transactions = load_categorized_transactions(db, current_user, tax_year)
    capital_allowances = load_capital_allowances_for_year(db, current_user.user_id, tax_year)
    capital_allowance_items = load_capital_allowance_items(db, current_user.user_id, tax_year)
    result = compute_tax(transactions, capital_allowances_this_year=capital_allowances)
    items = _build_itemized_breakdown(db, transactions, capital_allowance_items)

    computation = _get_or_create_computation(db, current_user, tax_year)
    computation.total_income = result.total_income
    computation.total_deductions = result.total_deductions
    computation.total_reliefs = result.total_reliefs
    computation.total_capital_allowances = result.total_capital_allowances
    computation.taxable_income = result.chargeable_income
    computation.estimated_tax_owed = result.net_tax
    computation.items = items
    db.commit()
    db.refresh(computation)

    return TaxComputationOut(
        tax_year=tax_year,
        total_income=computation.total_income,
        total_deductions=computation.total_deductions,
        total_reliefs=computation.total_reliefs,
        total_capital_allowances=computation.total_capital_allowances,
        taxable_income=computation.taxable_income,
        estimated_tax_owed=computation.estimated_tax_owed,
        minimum_wage_exempt=result.minimum_wage_exempt,
        band_breakdown=[b.__dict__ for b in result.band_breakdown],
        **items,
        last_updated=computation.last_updated,
    )


@router.get("/{tax_year}", response_model=TaxComputationOut)
def get_tax_computation(
    tax_year: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    computation = (
        db.query(TaxComputation)
        .filter(TaxComputation.user_id == current_user.user_id, TaxComputation.tax_year == tax_year)
        .first()
    )
    if computation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No tax computation for {tax_year} yet — POST to /tax-computations/{tax_year}/compute first.",
        )

    minimum_wage_exempt = computation.total_income <= NATIONAL_MINIMUM_WAGE_ANNUAL
    _, band_breakdown = (0.0, []) if minimum_wage_exempt else apply_fourth_schedule(computation.taxable_income)
    # Rows computed before the itemized breakdown was introduced have items=None.
    items = computation.items or EMPTY_ITEMS

    return TaxComputationOut(
        tax_year=tax_year,
        total_income=computation.total_income,
        total_deductions=computation.total_deductions,
        total_reliefs=computation.total_reliefs,
        total_capital_allowances=computation.total_capital_allowances,
        taxable_income=computation.taxable_income,
        estimated_tax_owed=computation.estimated_tax_owed,
        minimum_wage_exempt=minimum_wage_exempt,
        band_breakdown=[b.__dict__ for b in band_breakdown],
        **items,
        last_updated=computation.last_updated,
    )

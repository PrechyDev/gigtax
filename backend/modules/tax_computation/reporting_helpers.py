"""Itemized category breakdown shared by the web Reports page (tax_computations.py)
and the downloadable PDF (reports.py) — extracted so neither route imports from the
other.
"""
from collections import defaultdict

from sqlalchemy.orm import Session

from models.category import Category
from modules.tax_computation.engine import EXCLUDED_INCOME_TREATMENTS, RENT_RELIEF_SLUG, CategorizedTransaction, rent_relief_amount
from modules.tax_computation.loader import SYNTHETIC_CATEGORY_LABELS


def category_label(slug: str | None, categories_by_slug: dict[str, Category]) -> str:
    if slug is None:
        return "Uncategorized"
    if slug in SYNTHETIC_CATEGORY_LABELS:
        return SYNTHETIC_CATEGORY_LABELS[slug]
    category = categories_by_slug.get(slug)
    return category.category_name if category else slug


def build_itemized_breakdown(
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
        label = category_label(tx.category_slug, categories_by_slug)
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

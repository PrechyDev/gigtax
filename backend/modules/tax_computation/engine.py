"""Deterministic Personal Income Tax computation under the Nigeria Tax Act 2025,
scoped to this project's Direct Assessment target population (spec §6).

Pure module: no DB, no HTTP, no LLM calls. Takes a flat, ORM-independent view of
already-*approved* transactions and returns a fully-worked breakdown. Correctness
here is verified entirely by tests/test_tax_engine.py against hand-computed
scenarios — there is no AI involved anywhere in this file.
"""
from dataclasses import dataclass, field
from typing import Sequence

# --- Legally-sourced constants (update these two if the law changes; nothing else
# in this module should need to change alongside them) --------------------------

# Fourth Schedule (NTA 2025 s.58): progressive bands applied sequentially to
# chargeable income. Each tuple is (width of this band, rate).
FOURTH_SCHEDULE_BANDS: list[tuple[float, float]] = [
    (800_000, 0.00),
    (2_200_000, 0.15),
    (9_000_000, 0.18),
    (13_000_000, 0.21),
    (25_000_000, 0.23),
    (float("inf"), 0.25),
]

# National Minimum Wage (2024 Act): income at/below this is fully exempt regardless
# of the bands above (NTA 2025 s.58 / s.162(1)(t)).
NATIONAL_MINIMUM_WAGE_MONTHLY = 70_000
NATIONAL_MINIMUM_WAGE_ANNUAL = NATIONAL_MINIMUM_WAGE_MONTHLY * 12

# Rent relief (NTA 2025 s.30(2)(a)(vi)): 20% of annual rent paid, capped.
RENT_RELIEF_SLUG = "relief_residential_rent"
RENT_RELIEF_RATE = 0.20
RENT_RELIEF_CAP = 500_000

# Income tax_treatment values that must NOT count toward taxable total income —
# already-PAYE-taxed salary (out of this system's scope but still tracked for
# context) and genuinely non-taxable inflows (e.g. selling a personal item).
EXCLUDED_INCOME_TREATMENTS = {"excluded_from_progressive_tax", "non_taxable"}


@dataclass
class CategorizedTransaction:
    """The minimal, ORM-independent shape the engine needs from a Transaction row."""
    amount: float
    classification: str  # "Income" | "Expense" | "Relief" | "Asset" | "Unknown"
    category_slug: str | None
    tax_treatment: str | None
    deductibility_percentage: float = 100.0


@dataclass
class BandResult:
    rate: float
    amount_in_band: float
    tax: float


@dataclass
class TaxComputationResult:
    total_income: float
    total_deductions: float
    total_reliefs: float
    total_capital_allowances: float
    chargeable_income: float
    net_tax: float
    minimum_wage_exempt: bool
    band_breakdown: list[BandResult] = field(default_factory=list)


def rent_relief_amount(annual_rent_paid: float) -> float:
    return min(RENT_RELIEF_RATE * annual_rent_paid, RENT_RELIEF_CAP)


def apply_fourth_schedule(chargeable_income: float) -> tuple[float, list[BandResult]]:
    band_breakdown: list[BandResult] = []
    remaining = chargeable_income
    net_tax = 0.0

    for width, rate in FOURTH_SCHEDULE_BANDS:
        if remaining <= 0:
            break
        amount_in_band = min(remaining, width)
        tax_for_band = amount_in_band * rate
        band_breakdown.append(BandResult(rate=rate, amount_in_band=amount_in_band, tax=tax_for_band))
        net_tax += tax_for_band
        remaining -= amount_in_band

    return net_tax, band_breakdown


def compute_tax(
    transactions: Sequence[CategorizedTransaction],
    capital_allowances_this_year: float = 0.0,
) -> TaxComputationResult:
    """`capital_allowances_this_year` is computed separately (see
    modules/tax_computation/capital_allowances.py + loader.py) because it depends on
    an asset's full ownership history, not just this year's transactions — an asset
    bought in 2024 can still be depreciating in 2026 with no 2026 transaction at all.

    Transactions classified "Asset" are deliberately excluded from total_deductions
    below (they fall through every branch untouched) — a capital item's cost is never
    a normal one-year expense; only its calculated allowance is.
    """
    total_income = 0.0
    total_deductions = 0.0
    total_reliefs = 0.0

    for tx in transactions:
        if tx.classification == "Income":
            if tx.tax_treatment not in EXCLUDED_INCOME_TREATMENTS:
                total_income += tx.amount
        elif tx.classification == "Expense":
            total_deductions += tx.amount * (tx.deductibility_percentage / 100.0)
        elif tx.classification == "Relief":
            if tx.category_slug == RENT_RELIEF_SLUG:
                total_reliefs += rent_relief_amount(tx.amount)
            else:
                total_reliefs += tx.amount
        # "Asset"-classified rows and "Unknown"-classified (uncategorized/needs-review)
        # rows are deliberately ignored here — Assets are handled via
        # capital_allowances_this_year instead, and Unknown rows shouldn't have
        # reached the engine as APPROVED in the first place.

    chargeable_income = max(
        0.0, total_income - total_deductions - total_reliefs - capital_allowances_this_year
    )
    minimum_wage_exempt = total_income <= NATIONAL_MINIMUM_WAGE_ANNUAL

    if minimum_wage_exempt:
        return TaxComputationResult(
            total_income=total_income,
            total_deductions=total_deductions,
            total_reliefs=total_reliefs,
            total_capital_allowances=capital_allowances_this_year,
            chargeable_income=chargeable_income,
            net_tax=0.0,
            minimum_wage_exempt=True,
        )

    net_tax, band_breakdown = apply_fourth_schedule(chargeable_income)
    return TaxComputationResult(
        total_income=total_income,
        total_deductions=total_deductions,
        total_reliefs=total_reliefs,
        total_capital_allowances=capital_allowances_this_year,
        chargeable_income=chargeable_income,
        net_tax=net_tax,
        minimum_wage_exempt=False,
        band_breakdown=band_breakdown,
    )

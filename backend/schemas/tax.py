from datetime import datetime

from pydantic import BaseModel


class BandBreakdownItem(BaseModel):
    rate: float
    amount_in_band: float
    tax: float


class CategoryAmountItem(BaseModel):
    category_name: str
    amount: float
    # Only populated for deduction_items and capital_allowance_items — the
    # pre-deduction amount and the effective rate applied to reach `amount`
    # (e.g. 100% for a normal expense, a user's home-office percentage for
    # utilities, or a First Schedule capital allowance class rate).
    gross_amount: float | None = None
    rate: float | None = None


class TaxComputationOut(BaseModel):
    tax_year: str
    total_income: float
    total_deductions: float
    total_reliefs: float
    total_capital_allowances: float
    taxable_income: float
    estimated_tax_owed: float
    minimum_wage_exempt: bool
    band_breakdown: list[BandBreakdownItem]
    income_items: list[CategoryAmountItem] = []
    deduction_items: list[CategoryAmountItem] = []
    relief_items: list[CategoryAmountItem] = []
    capital_allowance_items: list[CategoryAmountItem] = []
    last_updated: datetime | None

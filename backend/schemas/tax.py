from datetime import datetime

from pydantic import BaseModel


class BandBreakdownItem(BaseModel):
    rate: float
    amount_in_band: float
    tax: float


class CategoryAmountItem(BaseModel):
    category_name: str
    amount: float


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

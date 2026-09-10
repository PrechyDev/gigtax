from datetime import datetime

from pydantic import BaseModel


class BandBreakdownItem(BaseModel):
    rate: float
    amount_in_band: float
    tax: float


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
    last_updated: datetime | None

from pydantic import BaseModel


class ActionItemOut(BaseModel):
    message: str
    href: str


class DashboardOut(BaseModel):
    tax_year: str
    total_income: float
    total_deductions: float
    total_reliefs: float
    total_capital_allowances: float
    estimated_tax_owed: float
    approved_transactions_count: int
    pending_review_count: int
    uncategorized_count: int
    locked_statements_count: int
    missing_receipts_count: int
    google_drive_connected: bool
    filing_guidance: str
    outstanding_actions: list[ActionItemOut]

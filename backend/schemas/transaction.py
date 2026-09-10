from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ManualTransactionCreate(BaseModel):
    # max_length values mirror the DB columns in models/transaction.py — validated here
    # so an over-long value gets a clean 422 instead of a raw DB-constraint 500.
    transaction_type: str = Field(description="'income' or 'expense'")
    date: datetime
    description: str = Field(max_length=500)
    amount: float
    currency: str = Field(default="NGN", max_length=3)
    category_slug: str | None = None
    income_source: str | None = Field(default=None, max_length=255)
    merchant_name: str | None = Field(default=None, max_length=255)

    @field_validator("transaction_type")
    @classmethod
    def _validate_type(cls, value: str) -> str:
        if value.lower() not in ("income", "expense"):
            raise ValueError("transaction_type must be 'income' or 'expense'")
        return value.lower()


class TransactionReviewUpdate(BaseModel):
    review_status: str | None = None  # "APPROVED" | "REJECTED"
    category_slug: str | None = None  # corrects user_category_id when provided

    @field_validator("review_status")
    @classmethod
    def _validate_review_status(cls, value: str | None) -> str | None:
        if value is not None and value.upper() not in ("APPROVED", "REJECTED", "PENDING"):
            raise ValueError("review_status must be one of APPROVED, REJECTED, PENDING")
        return value.upper() if value else value


class TransactionOut(BaseModel):
    transaction_id: UUID
    statement_id: UUID | None
    type: str
    date: datetime
    description: str
    amount: float
    currency: str
    ai_category_id: UUID | None
    user_category_id: UUID | None
    confidence_score: float | None
    review_status: str
    tax_treatment: str | None

    model_config = {"from_attributes": True}

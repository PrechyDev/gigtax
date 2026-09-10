from typing import List
from pydantic import BaseModel, Field

class ParsedTransaction(BaseModel):
    date: str = Field(description="Date of the transaction in YYYY-MM-DD format")
    description: str = Field(description="Description of the transaction")
    amount: float = Field(description="Amount of the transaction")
    category_slug: str = Field(description="Assigned category developer_slug based on rules")
    transaction_type: str = Field(description="Type of transaction (Income/Expense)")
    confidence_score: float = Field(description="Confidence level of the categorization between 0.0 and 1.0")
    merchant_name: str | None = Field(default=None, description="The name of the merchant (only if it is an Expense)")
    income_source: str | None = Field(default=None, description="The source of the income (only if it is an Income)")

class TransactionExtraction(BaseModel):
    transactions: List[ParsedTransaction]

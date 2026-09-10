from uuid import UUID

from pydantic import BaseModel, Field


class CustomRuleCreate(BaseModel):
    # max_length mirrors models/custom_rule.py's DB columns.
    keyword_pattern: str = Field(max_length=255)
    assigned_category: str = Field(max_length=100)


class CustomRuleOut(BaseModel):
    rule_id: UUID
    keyword_pattern: str
    assigned_category: str
    is_active: bool

    model_config = {"from_attributes": True}

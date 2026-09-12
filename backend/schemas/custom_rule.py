from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class CustomRuleCreate(BaseModel):
    # max_length mirrors models/custom_rule.py's DB columns.
    keyword_pattern: str = Field(max_length=255)
    # Exactly one of these two must be set — assigned_category for the quick
    # "map this keyword to a specific category" flow, rule_text for a freeform
    # natural-language instruction handed straight to the categorization prompt.
    assigned_category: str | None = Field(default=None, max_length=100)
    rule_text: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _exactly_one_of_category_or_text(self) -> "CustomRuleCreate":
        if bool(self.assigned_category) == bool(self.rule_text):
            raise ValueError("Provide exactly one of assigned_category or rule_text")
        return self


class CustomRuleOut(BaseModel):
    rule_id: UUID
    keyword_pattern: str
    assigned_category: str | None
    rule_text: str | None
    is_active: bool

    model_config = {"from_attributes": True}

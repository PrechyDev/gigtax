from pydantic import BaseModel, Field


class AnnualTaxProfileOut(BaseModel):
    tax_year: str
    annual_rent_paid: float | None
    has_home_office: bool
    home_office_percentage: float

    model_config = {"from_attributes": True}


class AnnualTaxProfileUpdate(BaseModel):
    annual_rent_paid: float | None = Field(default=None, ge=0)
    has_home_office: bool = False
    home_office_percentage: float = Field(default=0.0, ge=0, le=100)

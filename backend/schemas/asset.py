from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AssetOut(BaseModel):
    asset_id: UUID
    transaction_id: UUID | None
    description: str
    cost: float
    purchase_date: datetime
    asset_class: str
    disposed: bool
    disposed_date: datetime | None
    current_year_allowance: float  # computed on read, not stored

    model_config = {"from_attributes": True}


class AssetDisposeUpdate(BaseModel):
    disposed_date: datetime

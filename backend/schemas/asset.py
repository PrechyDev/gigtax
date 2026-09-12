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
    cumulative_allowance_claimed: float  # sum of every year's allowance to date, computed on read
    remaining_value: float  # cost minus cumulative_allowance_claimed, floored at 0, computed on read

    model_config = {"from_attributes": True}


class AssetDisposeUpdate(BaseModel):
    disposed_date: datetime

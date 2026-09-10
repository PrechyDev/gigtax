from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ReceiptOut(BaseModel):
    receipt_id: UUID
    transaction_id: UUID | None
    storage_path: str
    file_type: str | None
    upload_date: datetime

    model_config = {"from_attributes": True}

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class StatementFileResult(BaseModel):
    statement_id: UUID
    file_name: str
    status: str  # matches ParsingStatus values
    transactions_created: int = 0
    requires_password: bool = False
    error: str | None = None


class StatementBatchResponse(BaseModel):
    results: list[StatementFileResult]


class StatementListItem(BaseModel):
    statement_id: UUID
    file_name: str
    source_type: str | None
    parsing_status: str
    upload_date: datetime
    transactions_created: int = 0
    error_message: str | None = None

    model_config = {"from_attributes": True}

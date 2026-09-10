from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class AdvisoryHistoryItem(BaseModel):
    query_id: UUID
    query_text: str
    response_text: str
    sources: list[str]
    timestamp: datetime


class AdvisoryQueryRequest(BaseModel):
    question: str = Field(min_length=1, max_length=1000)
    # Omit on the first message of a new chat; the response's session_id then
    # identifies that conversation — pass it back on every follow-up in the same chat
    # so the advisor has context. A different/omitted session_id starts a fresh chat
    # with no memory of any other conversation.
    session_id: UUID | None = None


class AdvisoryQueryResponse(BaseModel):
    query_id: UUID
    session_id: UUID
    answer: str
    sources: list[str]

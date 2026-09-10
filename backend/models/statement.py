import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import enum
from db.base_class import Base

class ParsingStatus(str, enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    LOCKED = "LOCKED"  # password-protected PDF awaiting a retry with a password


class StatementUpload(Base):
    __tablename__ = "statement_uploads"

    statement_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    upload_date = Column(DateTime(timezone=True), nullable=False)
    parsing_status = Column(Enum(ParsingStatus), default=ParsingStatus.PENDING)
    source_type = Column(String(20))  # "pdf" | "csv" | "excel" | "image"
    # Set alongside parsing_status whenever it becomes FAILED — the same user-safe
    # string already returned in StatementFileResult.error, just persisted so it
    # survives past the initial synchronous response (background failures were
    # otherwise only ever logged server-side and lost).
    error_message = Column(String(500), nullable=True)
    # Nullable: raw statement bytes are processed in memory and never persisted
    # (see .agents/AGENTS.md privacy rule), so most uploads have no storage_path at all.
    storage_path = Column(String(500), nullable=True)

    # Relationships
    user = relationship("User", back_populates="statements")
    transactions = relationship("Transaction", back_populates="statement")

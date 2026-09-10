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

class StatementUpload(Base):
    __tablename__ = "statement_uploads"

    statement_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    file_name = Column(String(255), nullable=False)
    upload_date = Column(DateTime(timezone=True), nullable=False)
    parsing_status = Column(Enum(ParsingStatus), default=ParsingStatus.PENDING)
    storage_path = Column(String(500), nullable=False)

    # Relationships
    user = relationship("User", back_populates="statements")

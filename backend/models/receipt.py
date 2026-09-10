import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from db.base_class import Base

class Receipt(Base):
    __tablename__ = "receipts"

    receipt_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    transaction_id = Column(UUID(as_uuid=True), ForeignKey("transactions.transaction_id"), nullable=True)
    storage_path = Column(String(500), nullable=False)
    upload_date = Column(DateTime(timezone=True), server_default=func.now())
    file_type = Column(String(50))

    # Relationships
    transaction = relationship("Transaction", back_populates="receipts")

import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from db.base_class import Base

class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    date = Column(DateTime(timezone=True), nullable=False)
    description = Column(String(500), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="NGN")
    ai_category_id = Column(UUID(as_uuid=True), ForeignKey("categories.category_id"))
    user_category_id = Column(UUID(as_uuid=True), ForeignKey("categories.category_id"))
    confidence_score = Column(Float)
    review_status = Column(String(20), default="PENDING")
    tax_treatment = Column(String(50))
    
    # Polymorphic identity column
    type = Column(String(50))

    __mapper_args__ = {
        "polymorphic_identity": "transaction",
        "polymorphic_on": type
    }

    # Relationships
    user = relationship("User", back_populates="transactions")
    receipts = relationship("Receipt", back_populates="transaction", cascade="all, delete-orphan")


class IncomeRecord(Transaction):
    __mapper_args__ = {
        "polymorphic_identity": "income",
    }
    income_source = Column(String(255))


class ExpenseRecord(Transaction):
    __mapper_args__ = {
        "polymorphic_identity": "expense",
    }
    merchant_name = Column(String(255))
    deductibility_percentage = Column(Float, default=100.0)

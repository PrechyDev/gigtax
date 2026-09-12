import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from db.base_class import Base

class Transaction(Base):
    __tablename__ = "transactions"

    transaction_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    statement_id = Column(UUID(as_uuid=True), ForeignKey("statement_uploads.statement_id"), nullable=True)
    date = Column(DateTime(timezone=True), nullable=False)
    description = Column(String(500), nullable=False)
    amount = Column(Float, nullable=False)
    currency = Column(String(3), default="NGN")
    ai_category_id = Column(UUID(as_uuid=True), ForeignKey("categories.category_id"))
    user_category_id = Column(UUID(as_uuid=True), ForeignKey("categories.category_id"))
    confidence_score = Column(Float)
    review_status = Column(String(20), default="PENDING")
    tax_treatment = Column(String(50))
    # Set when review_status is set to REJECTED (a "discard"), cleared when it moves
    # away from REJECTED again (a "restore"). Lets the scheduled cleanup job
    # (core/scheduled_cleanup.py) permanently purge a discarded transaction 30 days
    # after the discard, while it stays recoverable up to that point.
    discarded_at = Column(DateTime(timezone=True), nullable=True)
    
    # Polymorphic identity column
    type = Column(String(50))

    __mapper_args__ = {
        "polymorphic_identity": "transaction",
        "polymorphic_on": type
    }

    # Relationships
    user = relationship("User", back_populates="transactions")
    receipts = relationship("Receipt", back_populates="transaction", cascade="all, delete-orphan")
    statement = relationship("StatementUpload", back_populates="transactions")

    @property
    def source(self) -> str:
        """Displayed in the ledger so a user can tell a manually-typed record apart
        from one that came out of an uploaded statement. Eager-load `statement` (see
        list_transactions) to avoid an N+1 query per row.
        """
        return self.statement.file_name if self.statement_id and self.statement else "Manual Entry"


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

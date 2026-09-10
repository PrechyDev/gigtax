import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, Float, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from db.base_class import Base

class TaxComputation(Base):
    __tablename__ = "tax_computations"

    computation_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    tax_year = Column(String(4), nullable=False)
    total_income = Column(Float, default=0.0)
    total_deductions = Column(Float, default=0.0)
    total_reliefs = Column(Float, default=0.0)
    total_capital_allowances = Column(Float, default=0.0)
    taxable_income = Column(Float, default=0.0)
    estimated_tax_owed = Column(Float, default=0.0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="computations")
    report = relationship("TaxReport", back_populates="computation", uselist=False, cascade="all, delete-orphan")


class TaxReport(Base):
    __tablename__ = "tax_reports"

    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    computation_id = Column(UUID(as_uuid=True), ForeignKey("tax_computations.computation_id"), unique=True, nullable=False)
    generation_date = Column(DateTime(timezone=True), server_default=func.now())
    format = Column(String(50), default="PDF")
    # Nullable: reports are generated on demand and only persisted to Drive (storing the file id
    # here) when the user has connected Google Drive — see docs/BUILD_PLAN.md reporting phase.
    storage_path = Column(String(500), nullable=True)

    # Relationships
    computation = relationship("TaxComputation", back_populates="report")

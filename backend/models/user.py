import uuid
from sqlalchemy import Column, String, DateTime, func, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.base_class import Base

class User(Base):
    __tablename__ = "users"

    user_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    occupation_type = Column(String(50))
    state_residence = Column(String(50))
    tax_year = Column(String(4))
    tin = Column(String(20), nullable=True)  # Tax Identification Number
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Google Drive BYOS (Bring Your Own Storage)
    google_drive_connected = Column(Boolean, default=False)
    google_refresh_token_encrypted = Column(String(500), nullable=True)
    google_drive_folder_id = Column(String(255), nullable=True)

    # Relationships
    statements = relationship("StatementUpload", back_populates="user", cascade="all, delete-orphan")
    custom_rules = relationship("CustomRule", back_populates="user", cascade="all, delete-orphan")
    computations = relationship("TaxComputation", back_populates="user", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="user", cascade="all, delete-orphan")
    advisory_queries = relationship("AIAdvisoryQuery", back_populates="user", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="user", cascade="all, delete-orphan")
    annual_tax_profiles = relationship("AnnualTaxProfile", back_populates="user", cascade="all, delete-orphan")

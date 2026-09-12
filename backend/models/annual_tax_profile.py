import uuid

from sqlalchemy import Boolean, Column, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from db.base_class import Base


class AnnualTaxProfile(Base):
    """Rent paid and home-office claim, scoped to a single tax year — these genuinely
    change year to year (a new lease, a bigger/smaller home-office share), so they
    can't live as a single static value on the User row the way TIN or state of
    residence can. See modules/tax_computation/loader.py for how a year's row feeds
    the rent-relief calculation, and modules/ingestion/persistence.py for how it feeds
    the home-office deductibility percentage stamped onto an expense at ingestion time.
    """
    __tablename__ = "annual_tax_profiles"
    __table_args__ = (UniqueConstraint("user_id", "tax_year", name="uq_annual_tax_profile_user_year"),)

    annual_tax_profile_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    tax_year = Column(String(4), nullable=False)
    annual_rent_paid = Column(Float, nullable=True)
    has_home_office = Column(Boolean, default=False, nullable=False)
    home_office_percentage = Column(Float, default=0.0, nullable=False)

    user = relationship("User", back_populates="annual_tax_profiles")

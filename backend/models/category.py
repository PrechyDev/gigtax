import uuid
from sqlalchemy import Boolean, Column, String
from sqlalchemy.dialects.postgresql import UUID
from db.base_class import Base

class Category(Base):
    __tablename__ = "categories"

    category_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    classification = Column(String(50), nullable=False)
    category_name = Column(String(100), nullable=False)
    developer_slug = Column(String(100), unique=True, nullable=False)
    description = Column(String(255))
    tax_treatment = Column(String(255))
    # Only meaningful when classification == "Asset": which First Schedule capital
    # allowance class (and therefore annual write-down rate) this category maps to.
    # See modules/tax_computation/capital_allowances.py for the class -> rate table.
    asset_class = Column(String(20), nullable=True)
    # False for a category retired from db/seed_data/categories.json (e.g. PAYE income,
    # the old standalone rent-relief category) — the row stays so any transaction that
    # already references it keeps working, but GET /categories stops offering it for new
    # selection. scripts/seed_categories.py always sets this True for anything still
    # present in the JSON; it's never flipped back on automatically otherwise.
    is_active = Column(Boolean, default=True, nullable=False, server_default="true")

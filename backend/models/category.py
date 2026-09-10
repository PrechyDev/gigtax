import uuid
from sqlalchemy import Column, String
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

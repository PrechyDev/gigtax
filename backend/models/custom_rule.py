import uuid
from sqlalchemy import Column, String, Boolean, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from db.base_class import Base

class CustomRule(Base):
    __tablename__ = "custom_rules"

    rule_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    keyword_pattern = Column(String(255), nullable=False)
    # Exactly one of these two is set (enforced in schemas/custom_rule.py, not here):
    # assigned_category for the quick "map this keyword to a specific category" flow,
    # rule_text for a freeform natural-language instruction (e.g. "these are personal
    # transactions, exclude them from business income/expense"). See
    # modules/ingestion/prompt_context.py:build_custom_rules_text for how each renders
    # into the categorization prompt.
    assigned_category = Column(String(100), nullable=True)
    rule_text = Column(String(1000), nullable=True)
    is_active = Column(Boolean, default=True)

    # Relationships
    user = relationship("User", back_populates="custom_rules")

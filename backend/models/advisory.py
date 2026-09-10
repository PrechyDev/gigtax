import uuid
from sqlalchemy import Column, String, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from db.base_class import Base

class AIAdvisoryQuery(Base):
    __tablename__ = "advisory_queries"

    query_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.user_id"), nullable=False)
    query_text = Column(String(1000), nullable=False)
    response_text = Column(String(5000), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    retrieved_sources = Column(String(2000)) # Can be JSON string or array of links

    # Relationships
    user = relationship("User", back_populates="advisory_queries")

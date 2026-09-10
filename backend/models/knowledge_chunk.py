import uuid

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID

from db.base_class import Base
from services.llm_service import EMBEDDING_DIMENSIONS


class KnowledgeChunk(Base):
    """One chunk of a statutory/supporting document, embedded for RAG retrieval by
    the AI advisor. `source_title` + `citation` identify where an answer's grounding
    came from (e.g. source_title="Nigeria Tax Act 2025", citation="p.42"); re-running
    the ingestion script for a given source_title replaces its chunks, so adding a new
    supporting document later never requires a schema change here.
    """
    __tablename__ = "knowledge_chunks"

    chunk_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_title = Column(String(255), nullable=False)
    citation = Column(String(100), nullable=False)  # e.g. "p.42"
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    embedding = Column(Vector(EMBEDDING_DIMENSIONS), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

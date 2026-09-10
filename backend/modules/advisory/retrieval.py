from sqlalchemy.orm import Session

from models.knowledge_chunk import KnowledgeChunk
from services.llm_service import llm_service


def retrieve_relevant_chunks(db: Session, question: str, k: int = 5) -> list[KnowledgeChunk]:
    """Embeds the question and returns the k closest chunks by cosine distance.

    No ANN index (ivfflat/HNSW) yet — exact search is fast enough at this corpus size
    (a single Act's worth of chunks); add one if/when the knowledge base grows large
    enough for it to matter.
    """
    query_embedding = llm_service.generate_embedding(question)
    return (
        db.query(KnowledgeChunk)
        .order_by(KnowledgeChunk.embedding.cosine_distance(query_embedding))
        .limit(k)
        .all()
    )

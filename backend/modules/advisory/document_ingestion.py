"""Extracts, chunks, and embeds a source document (e.g. the NTA 2025 gazette PDF)
into the `knowledge_chunks` table for RAG retrieval by the AI advisor.

Re-running `ingest_document` for a given `source_title` replaces its existing chunks
first — safe to re-run whenever a document is updated, and this is exactly how new
supporting documents get added later: run this again with a different file/title,
no schema change needed.
"""
import pdfplumber
import pymupdf
from sqlalchemy.orm import Session

from models.knowledge_chunk import KnowledgeChunk
from services.llm_service import llm_service

CHUNK_SIZE_CHARS = 2000
CHUNK_OVERLAP_CHARS = 200


def extract_pdf_pages(file_path: str) -> list[str]:
    """One string per page. pdfplumber first (better layout fidelity for a dense
    legal document); pymupdf fills in any page pdfplumber came back empty on.
    """
    pages: list[str | None] = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            pages.append(text if text.strip() else None)

    if any(p is None for p in pages):
        doc = pymupdf.open(file_path)
        for i in range(len(pages)):
            if pages[i] is None and i < len(doc):
                pages[i] = doc[i].get_text() or ""

    return [p or "" for p in pages]


def chunk_page(page_text: str, chunk_size: int = CHUNK_SIZE_CHARS, overlap: int = CHUNK_OVERLAP_CHARS) -> list[str]:
    """Fixed-size chunking with overlap, kept within a single page so each chunk's
    citation (its page number) stays exact rather than spanning two pages.
    """
    text = page_text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def ingest_document(db: Session, file_path: str, source_title: str, commit_every: int = 20) -> int:
    """Returns the number of chunks stored.

    Commits periodically (every `commit_every` chunks) rather than once at the end —
    a document like the full NTA 2025 gazette makes hundreds of sequential embedding
    calls, and a transient failure partway through shouldn't throw away everything
    embedded so far. Progress is also printed so a long-running ingestion isn't a
    silent black box.
    """
    db.query(KnowledgeChunk).filter(KnowledgeChunk.source_title == source_title).delete()
    db.commit()

    pages = extract_pdf_pages(file_path)
    total_chunks_expected = sum(len(chunk_page(p)) for p in pages)
    chunk_index = 0
    for page_number, page_text in enumerate(pages, start=1):
        for chunk_text in chunk_page(page_text):
            embedding_vector = llm_service.generate_embedding(chunk_text)
            db.add(KnowledgeChunk(
                source_title=source_title,
                citation=f"p.{page_number}",
                chunk_index=chunk_index,
                content=chunk_text,
                embedding=embedding_vector,
            ))
            chunk_index += 1

            if chunk_index % commit_every == 0:
                db.commit()
                print(f"  ...{chunk_index}/{total_chunks_expected} chunks embedded", flush=True)

    db.commit()
    return chunk_index

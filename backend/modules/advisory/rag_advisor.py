"""Real RAG-based tax advisor: retrieves grounded passages from the knowledge_chunks
table (populated by modules/advisory/document_ingestion.py) and answers using only
that retrieved context. Supersedes the previous build's static-context placeholder.
"""
from dataclasses import dataclass

from sqlalchemy.orm import Session

from modules.advisory.retrieval import retrieve_relevant_chunks
from services.llm_service import llm_service

SYSTEM_PROMPT_TEMPLATE = (
    "You are a plain-language tax guidance assistant for Nigerian freelancers, remote "
    "workers, and sole traders filing under the Nigeria Tax Act 2025's Direct Assessment "
    "regime. Answer using ONLY the statutory passages provided below — do not use "
    "outside knowledge. If the passages don't cover the question, say so plainly rather "
    "than guessing, and suggest the user consult a licensed tax professional or their "
    "State Internal Revenue Service. Keep answers concise and in plain English.\n\n"
    "--- RETRIEVED PASSAGES ---\n{context}"
)

NO_KNOWLEDGE_BASE_ANSWER = (
    "I don't have any statutory material loaded yet to answer that — please consult a "
    "licensed tax professional or your State Internal Revenue Service in the meantime."
)


@dataclass
class AdvisoryAnswer:
    answer: str
    sources: list[str]  # e.g. ["Nigeria Tax Act 2025 (p.42)"]


def answer_question(db: Session, question: str) -> AdvisoryAnswer:
    chunks = retrieve_relevant_chunks(db, question)

    if not chunks:
        return AdvisoryAnswer(answer=NO_KNOWLEDGE_BASE_ANSWER, sources=[])

    context = "\n\n".join(f"[{c.source_title}, {c.citation}]\n{c.content}" for c in chunks)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)

    answer = llm_service.generate_text(prompt=question, system_prompt=system_prompt)
    sources = sorted({f"{c.source_title} ({c.citation})" for c in chunks})
    return AdvisoryAnswer(answer=answer, sources=sources)

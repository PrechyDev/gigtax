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
    "regime. Ground every answer in the statutory passages below and/or what was already "
    "established earlier in this conversation — never introduce information from outside "
    "either of those. If neither covers the question, say so plainly rather than guessing, "
    "and suggest the user consult a licensed tax professional or their State Internal "
    "Revenue Service. Keep answers concise and in plain English.\n\n"
    "--- RETRIEVED PASSAGES ---\n{context}"
)

# How many of the most recent user messages (this one plus prior ones) to fold into
# the retrieval query — a short follow-up like "is it capped?" has no keywords of its
# own to embed well, so recent topic context goes with it. Kept small and cheap (no
# extra LLM call to "rewrite" the query) rather than the whole conversation.
RETRIEVAL_CONTEXT_WINDOW = 2

NO_KNOWLEDGE_BASE_ANSWER = (
    "I don't have any statutory material loaded yet to answer that — please consult a "
    "licensed tax professional or your State Internal Revenue Service in the meantime."
)


@dataclass
class AdvisoryAnswer:
    answer: str
    sources: list[str]  # e.g. ["Nigeria Tax Act 2025 (p.42)"]


def _build_retrieval_query(question: str, conversation_history: list[dict] | None) -> str:
    """A bare follow-up ("is it capped?") has no keywords of its own to embed well —
    fold in the last couple of user turns so retrieval has the topic to search on,
    without a separate LLM call to rewrite the question.
    """
    if not conversation_history:
        return question

    recent_user_turns = [m["content"] for m in conversation_history if m["role"] == "user"][-RETRIEVAL_CONTEXT_WINDOW:]
    return "\n".join([*recent_user_turns, question])


def answer_question(
    db: Session,
    question: str,
    conversation_history: list[dict] | None = None,
) -> AdvisoryAnswer:
    """`conversation_history` is prior turns in this chat session, oldest first, as
    [{"role": "user"/"assistant", "content": "..."}] — see api/routes/advisory.py for
    how it's loaded (bounded to the last few turns) and threaded through per-session.
    """
    retrieval_query = _build_retrieval_query(question, conversation_history)
    chunks = retrieve_relevant_chunks(db, retrieval_query)

    if not chunks:
        return AdvisoryAnswer(answer=NO_KNOWLEDGE_BASE_ANSWER, sources=[])

    context = "\n\n".join(f"[{c.source_title}, {c.citation}]\n{c.content}" for c in chunks)
    system_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context)

    answer = llm_service.generate_text(prompt=question, system_prompt=system_prompt, history=conversation_history)
    sources = sorted({f"{c.source_title} ({c.citation})" for c in chunks})
    return AdvisoryAnswer(answer=answer, sources=sources)

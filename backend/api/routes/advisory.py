import json
import uuid
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps import get_current_user
from core.logger import get_logger
from db.session import get_db
from models.advisory import AIAdvisoryQuery
from models.user import User
from modules.advisory.rag_advisor import answer_question
from schemas.advisory import (
    AdvisoryHistoryItem,
    AdvisoryQueryRequest,
    AdvisoryQueryResponse,
    AdvisorySessionSummary,
)

router = APIRouter(prefix="/advisory", tags=["advisory"])
logger = get_logger("api.advisory")

AI_SERVICE_UNAVAILABLE_MESSAGE = (
    "Our AI advisor is temporarily unavailable. Please try again in a few minutes."
)

# How many prior turns (each turn = one user question + one assistant answer) to
# include as context — bounded rather than the whole conversation, so prompt size
# stays predictable regardless of how long a chat runs.
MAX_HISTORY_TURNS = 6


def _load_conversation_history(db: Session, user_id, session_id) -> list[dict]:
    prior_turns = (
        db.query(AIAdvisoryQuery)
        .filter(AIAdvisoryQuery.user_id == user_id, AIAdvisoryQuery.session_id == session_id)
        .order_by(AIAdvisoryQuery.timestamp.desc())
        .limit(MAX_HISTORY_TURNS)
        .all()
    )
    prior_turns.reverse()  # oldest first, so the model reads the conversation in order

    history = []
    for turn in prior_turns:
        history.append({"role": "user", "content": turn.query_text})
        history.append({"role": "assistant", "content": turn.response_text})
    return history


@router.post("/query", response_model=AdvisoryQueryResponse)
def query_advisor(
    payload: AdvisoryQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session_id = payload.session_id or uuid.uuid4()
    history = _load_conversation_history(db, current_user.user_id, session_id) if payload.session_id else []

    try:
        result = answer_question(db, payload.question, conversation_history=history)
    except Exception:
        logger.exception("Advisory query failed (embedding/retrieval/generation)")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=AI_SERVICE_UNAVAILABLE_MESSAGE)

    log = AIAdvisoryQuery(
        user_id=current_user.user_id,
        session_id=session_id,
        query_text=payload.question,
        response_text=result.answer[:5000],
        retrieved_sources=json.dumps(result.sources),
        # Set explicitly (microsecond precision) rather than relying on the column's
        # server_default=func.now() — SQLite's CURRENT_TIMESTAMP only has *second*
        # resolution, so rapid successive turns in the same session can otherwise
        # collide and make history ordering unstable (harmless on Postgres, which
        # doesn't have this problem, but this keeps behavior identical on both).
        timestamp=datetime.now(timezone.utc),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return AdvisoryQueryResponse(
        query_id=log.query_id,
        session_id=session_id,
        answer=result.answer,
        sources=result.sources,
    )


@router.get("/history", response_model=list[AdvisoryHistoryItem])
def get_history(
    session_id: UUID = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Restores a chat session's prior turns — lets the frontend reload a conversation
    on page refresh instead of always starting blank.
    """
    turns = (
        db.query(AIAdvisoryQuery)
        .filter(AIAdvisoryQuery.user_id == current_user.user_id, AIAdvisoryQuery.session_id == session_id)
        .order_by(AIAdvisoryQuery.timestamp.asc())
        .all()
    )
    return [
        AdvisoryHistoryItem(
            query_id=turn.query_id,
            query_text=turn.query_text,
            response_text=turn.response_text,
            sources=json.loads(turn.retrieved_sources) if turn.retrieved_sources else [],
            timestamp=turn.timestamp,
        )
        for turn in turns
    ]


@router.get("/sessions", response_model=list[AdvisorySessionSummary])
def list_advisory_sessions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """One row per distinct chat session the user has had, most-recently-active
    first — lets the frontend show a session list to reopen or clear an old chat.
    Grouped in Python rather than a DB-side window function so this behaves
    identically on Postgres (prod) and SQLite (tests).
    """
    turns = (
        db.query(AIAdvisoryQuery)
        .filter(AIAdvisoryQuery.user_id == current_user.user_id)
        .order_by(AIAdvisoryQuery.timestamp.asc())
        .all()
    )
    sessions: dict[UUID, AdvisorySessionSummary] = {}
    for turn in turns:
        existing = sessions.get(turn.session_id)
        if existing is None:
            sessions[turn.session_id] = AdvisorySessionSummary(
                session_id=turn.session_id,
                label=turn.query_text[:80],
                last_active=turn.timestamp,
            )
        else:
            existing.last_active = turn.timestamp
    return sorted(sessions.values(), key=lambda s: s.last_active, reverse=True)


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_advisory_session(
    session_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.query(AIAdvisoryQuery).filter(
        AIAdvisoryQuery.user_id == current_user.user_id, AIAdvisoryQuery.session_id == session_id
    ).delete(synchronize_session=False)
    db.commit()

import json
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models.advisory import AIAdvisoryQuery
from models.user import User
from modules.advisory.rag_advisor import answer_question
from schemas.advisory import AdvisoryQueryRequest, AdvisoryQueryResponse

router = APIRouter(prefix="/advisory", tags=["advisory"])

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

    result = answer_question(db, payload.question, conversation_history=history)

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

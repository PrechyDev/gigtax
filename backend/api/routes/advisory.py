import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models.advisory import AIAdvisoryQuery
from models.user import User
from modules.advisory.rag_advisor import answer_question
from schemas.advisory import AdvisoryQueryRequest, AdvisoryQueryResponse

router = APIRouter(prefix="/advisory", tags=["advisory"])


@router.post("/query", response_model=AdvisoryQueryResponse)
def query_advisor(
    payload: AdvisoryQueryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = answer_question(db, payload.question)

    log = AIAdvisoryQuery(
        user_id=current_user.user_id,
        query_text=payload.question,
        response_text=result.answer[:5000],
        retrieved_sources=json.dumps(result.sources),
    )
    db.add(log)
    db.commit()
    db.refresh(log)

    return AdvisoryQueryResponse(query_id=log.query_id, answer=result.answer, sources=result.sources)

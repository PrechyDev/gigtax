from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models.custom_rule import CustomRule
from models.user import User
from schemas.custom_rule import CustomRuleCreate, CustomRuleOut

router = APIRouter(prefix="/custom-rules", tags=["custom-rules"])


@router.post("", response_model=CustomRuleOut, status_code=status.HTTP_201_CREATED)
def create_custom_rule(
    payload: CustomRuleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rule = CustomRule(
        user_id=current_user.user_id,
        keyword_pattern=payload.keyword_pattern,
        assigned_category=payload.assigned_category,
    )
    db.add(rule)
    db.commit()
    db.refresh(rule)
    return rule


@router.get("", response_model=list[CustomRuleOut])
def list_custom_rules(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return (
        db.query(CustomRule)
        .filter(CustomRule.user_id == current_user.user_id)
        .order_by(CustomRule.keyword_pattern)
        .all()
    )


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_custom_rule(
    rule_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    rule = (
        db.query(CustomRule)
        .filter(CustomRule.rule_id == rule_id, CustomRule.user_id == current_user.user_id)
        .first()
    )
    if rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom rule not found")
    db.delete(rule)
    db.commit()

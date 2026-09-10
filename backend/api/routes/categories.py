from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models.category import Category
from models.user import User
from schemas.category import CategoryOut

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=list[CategoryOut])
def list_categories(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The category taxonomy is global (not user-specific) but still requires auth,
    like every other endpoint — powers every category dropdown in the frontend
    (manual entry, ledger correction, custom rules).
    """
    return (
        db.query(Category)
        .filter(Category.is_active.is_(True))
        .order_by(Category.classification, Category.category_name)
        .all()
    )

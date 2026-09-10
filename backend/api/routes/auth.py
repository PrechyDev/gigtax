from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps import get_current_user
from core.security import create_access_token, hash_password, verify_password
from db.session import get_db
from models.user import User
from schemas.user import TokenResponse, UserLogin, UserProfile, UserRegister, UserUpdate

router = APIRouter(prefix="/auth", tags=["auth"])


def _default_name_from_email(email: str) -> str:
    """Registration only collects email + password — a real name is asked for right
    after, on the onboarding step. Until then, derive something more presentable than
    a blank field from the email's local part (e.g. "jane.doe" -> "Jane Doe").
    """
    local_part = email.split("@", 1)[0]
    words = [w for w in local_part.replace(".", " ").replace("_", " ").replace("-", " ").split(" ") if w]
    return " ".join(w.capitalize() for w in words) if words else "New User"


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(payload: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == payload.email).first():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        name=payload.name or _default_name_from_email(payload.email),
        email=payload.email,
        password_hash=hash_password(payload.password),
        occupation_type=payload.occupation_type,
        state_residence=payload.state_residence,
        tax_year=payload.tax_year,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user.user_id))


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")
    return TokenResponse(access_token=create_access_token(user.user_id))


@router.get("/me", response_model=UserProfile)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/me", response_model=UserProfile)
def update_me(
    payload: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(current_user, field, value)
    db.commit()
    db.refresh(current_user)
    return current_user

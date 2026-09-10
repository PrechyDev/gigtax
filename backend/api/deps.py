from uuid import UUID

import jwt
from fastapi import Depends, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from core.security import decode_access_token
from db.session import get_db
from models.user import User

_bearer_scheme = HTTPBearer(auto_error=False)

_UNAUTHORIZED = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Not authenticated",
    headers={"WWW-Authenticate": "Bearer"},
)


def _resolve_user(token: str | None, db: Session) -> User:
    if token is None:
        raise _UNAUTHORIZED
    try:
        user_id = decode_access_token(token)
    except jwt.PyJWTError:
        raise _UNAUTHORIZED

    user = db.query(User).filter(User.user_id == UUID(user_id)).first()
    if user is None:
        raise _UNAUTHORIZED
    return user


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    return _resolve_user(credentials.credentials if credentials else None, db)


def get_current_user_allow_query_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    token: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> User:
    """Same as get_current_user, but also accepts the JWT as a `?token=` query param.

    Used ONLY by the Google Drive OAuth connect redirect
    (api/routes/google_drive.py) — a top-level browser navigation to a redirect
    endpoint can't set an Authorization header, so there's no other way for that one
    request to identify the user. Every other endpoint uses plain get_current_user.
    """
    return _resolve_user(credentials.credentials if credentials else token, db)

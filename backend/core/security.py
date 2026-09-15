from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
import jwt

from core.config import settings


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user_id: UUID, expires_minutes: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes if expires_minutes is not None else settings.JWT_EXPIRE_MINUTES
    )
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> str:
    """Returns the user_id (as a string) encoded in the token's `sub` claim.

    Raises jwt.PyJWTError (or a subclass) if the token is invalid/expired — callers
    are expected to catch that and translate it into an HTTP 401.
    """
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    
    # Explicitly reject tokens meant only for OAuth state
    if payload.get("purpose") == "google_oauth_state":
        raise jwt.PyJWTError("OAuth state tokens cannot be used as API access tokens")
        
    return payload["sub"]


def create_oauth_state_token(user_id: UUID, expires_minutes: int) -> str:
    """Creates a short-lived token specifically for maintaining state in an OAuth flow.
    Includes a 'purpose' claim so it cannot be misused as an API access token.
    """
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes)
    payload = {"sub": str(user_id), "exp": expire, "purpose": "google_oauth_state"}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_oauth_state_token(token: str) -> str:
    """Decodes a token and verifies it was specifically issued for OAuth state."""
    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("purpose") != "google_oauth_state":
        raise jwt.PyJWTError("Invalid token purpose")
    return payload["sub"]

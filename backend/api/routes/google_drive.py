from uuid import UUID

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from api.deps import get_current_user_allow_query_token
from core.config import settings
from core.crypto import encrypt_token
from core.logger import get_logger
from core.security import create_access_token, decode_access_token
from db.session import get_db
from models.user import User
from services.drive_service import DriveService, build_auth_flow

router = APIRouter(prefix="/auth/google", tags=["google-drive"])
logger = get_logger(__name__)

# Short-lived, but 10 minutes turned out too tight in production: on Render's free
# tier a cold-started backend (plus the Alembic check that now runs on every start)
# eats real time before /connect even redirects, and a first-time consent on an
# OAuth client still in Google's "Testing" publishing status adds an "unverified app"
# interstitial the user has to click through — the combined round trip through
# Google's consent screen comfortably exceeded 10 minutes and failed at /callback
# with "Invalid or expired state" even though nothing was actually wrong. Still
# short-lived, just no longer tight enough to fail on a normal first connection.
STATE_TOKEN_EXPIRE_MINUTES = 30


@router.get("/connect")
def connect(current_user: User = Depends(get_current_user_allow_query_token)):
    # This endpoint's whole contract is "redirect the browser somewhere" — so on any
    # unexpected failure (e.g. misconfigured OAuth client secrets) it must still
    # redirect, with an error flag the frontend can show a friendly banner for,
    # rather than leaving the user staring at a raw 500 mid-flow.
    if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
        # build_auth_flow doesn't raise for a missing client id/secret — it silently
        # builds a URL with "client_id=None" that Google is guaranteed to reject. Catch
        # it here, before ever redirecting, rather than sending the user to a dead page.
        logger.error(
            "Google Drive OAuth is not configured (missing client id/secret) — refusing to redirect user_id=%s",
            current_user.user_id,
        )
        return RedirectResponse(f"{settings.FRONTEND_URL}/settings?drive=error")

    try:
        # The callback is a plain browser redirect from Google with no Authorization
        # header, so we can't rely on get_current_user there — instead we smuggle the
        # user's identity through the OAuth `state` param, signed with the same JWT
        # mechanism as login tokens.
        state = create_access_token(current_user.user_id, expires_minutes=STATE_TOKEN_EXPIRE_MINUTES)
        flow = build_auth_flow(state=state)
        authorization_url, _ = flow.authorization_url(
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
        )
    except Exception:
        logger.exception("Failed to start Google Drive OAuth flow for user_id=%s", current_user.user_id)
        return RedirectResponse(f"{settings.FRONTEND_URL}/settings?drive=error")

    return RedirectResponse(authorization_url)


@router.get("/callback")
def callback(code: str, state: str, db: Session = Depends(get_db)):
    try:
        user_id = decode_access_token(state)
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or expired state")

    user = db.query(User).filter(User.user_id == UUID(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    flow = build_auth_flow(state=state)
    flow.fetch_token(code=code)
    credentials = flow.credentials

    if not credentials.refresh_token:
        # Shouldn't happen given access_type=offline + prompt=consent, but Google's the
        # source of truth here, not us — fail loudly rather than silently "connecting"
        # with nothing usable.
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google did not return a refresh token; please try connecting again.",
        )

    # Persist the token before touching the Drive API, so a folder-creation hiccup
    # doesn't throw away a token we already have.
    user.google_refresh_token_encrypted = encrypt_token(credentials.refresh_token)
    db.commit()

    folder_id = DriveService(user).ensure_app_folder()
    user.google_drive_folder_id = folder_id
    user.google_drive_connected = True
    db.commit()

    return RedirectResponse(f"{settings.FRONTEND_URL}/settings?drive=connected")

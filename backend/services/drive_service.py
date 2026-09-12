"""Google Drive BYOS (Bring Your Own Storage) facade.

Everything that talks to the Google Drive API goes through this one module — no other
file should import `googleapiclient`/`google_auth_oauthlib` directly. Uses the narrow
`drive.file` scope only: the app can only see/manage files it creates itself, never the
user's existing Drive contents.
"""
import io

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

from core.config import settings
from core.crypto import decrypt_token
from models.user import User

SCOPES = ["https://www.googleapis.com/auth/drive.file"]
APP_FOLDER_NAME = "GigTax Documents"
TOKEN_URI = "https://oauth2.googleapis.com/token"


def build_auth_flow(state: str | None = None) -> Flow:
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": TOKEN_URI,
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }
    # PKCE is off deliberately, not an oversight: /auth/google/connect and
    # /auth/google/callback each build a brand-new Flow object (separate HTTP
    # requests), so a code_verifier auto-generated on the /connect Flow instance
    # never reaches the /callback Flow instance that needs it for the token
    # exchange — google-auth-oauthlib >=1.2 defaults autogenerate_code_verifier to
    # True, which surfaces as "InvalidGrantError: Missing code verifier" from
    # Google's token endpoint. PKCE exists to protect public clients that can't
    # hold a secret; this is a confidential server-side "web" client already
    # authenticated by GOOGLE_CLIENT_SECRET on every token exchange, so it adds no
    # real protection here — only re-enable it if the two legs ever share a
    # verifier (e.g. by threading it through the `state` JWT).
    flow = Flow.from_client_config(
        client_config, scopes=SCOPES, state=state, autogenerate_code_verifier=False
    )
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    return flow


class DriveService:
    """Instantiate per-request from an authenticated User with a connected Drive account."""

    def __init__(self, user: User):
        if not user.google_refresh_token_encrypted:
            raise ValueError("User has not connected Google Drive.")

        refresh_token = decrypt_token(user.google_refresh_token_encrypted)
        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri=TOKEN_URI,
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=SCOPES,
        )
        self._client = build("drive", "v3", credentials=credentials)

    def ensure_app_folder(self) -> str:
        """Returns the id of the app's dedicated Drive folder, creating it if needed."""
        query = (
            f"mimeType='application/vnd.google-apps.folder' "
            f"and name='{APP_FOLDER_NAME}' and trashed=false"
        )
        results = self._client.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
        files = results.get("files", [])
        if files:
            return files[0]["id"]

        folder = self._client.files().create(
            body={"name": APP_FOLDER_NAME, "mimeType": "application/vnd.google-apps.folder"},
            fields="id",
        ).execute()
        return folder["id"]

    def upload(self, file_bytes: bytes, filename: str, mime_type: str, folder_id: str) -> str:
        """Uploads bytes into the given folder, returning the new file's Drive id."""
        media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type, resumable=False)
        file = self._client.files().create(
            body={"name": filename, "parents": [folder_id]},
            media_body=media,
            fields="id",
        ).execute()
        return file["id"]

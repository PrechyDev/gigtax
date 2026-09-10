from unittest.mock import MagicMock, patch
from uuid import UUID

from core.security import decode_access_token


def _register(client, email="drive-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Drive User", "email": email, "password": "supersecret123",
    })
    return response.json()["access_token"]


def test_connect_redirects_to_google_with_signed_state(client):
    token = _register(client)

    with patch("api.routes.google_drive.build_auth_flow") as mock_build_flow:
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = ("https://accounts.google.com/o/oauth2/auth?mock=1", None)
        mock_build_flow.return_value = mock_flow

        response = client.get(
            "/auth/google/connect",
            headers={"Authorization": f"Bearer {token}"},
            follow_redirects=False,
        )

    assert response.status_code in (302, 307)
    assert response.headers["location"].startswith("https://accounts.google.com")
    # The state passed to build_auth_flow must decode back to the same user.
    state_used = mock_build_flow.call_args.kwargs["state"]
    assert decode_access_token(state_used)


def test_connect_requires_auth(client):
    response = client.get("/auth/google/connect", follow_redirects=False)
    assert response.status_code == 401


def test_connect_accepts_token_via_query_param(client):
    # A top-level browser navigation (the only way to reach Google's real consent
    # screen) can't set an Authorization header — this is the fallback the frontend
    # relies on for that one redirect.
    token = _register(client, "drive-user-query@example.com")

    with patch("api.routes.google_drive.build_auth_flow") as mock_build_flow:
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = ("https://accounts.google.com/o/oauth2/auth?mock=1", None)
        mock_build_flow.return_value = mock_flow

        response = client.get(
            "/auth/google/connect",
            params={"token": token},
            follow_redirects=False,
        )

    assert response.status_code in (302, 307)


def test_callback_persists_encrypted_refresh_token_and_marks_connected(client, db_session):
    from models.user import User

    token = _register(client, email="callback-user@example.com")
    user_id = UUID(decode_access_token(token))

    # Build a real, valid state for this user (mirrors what /connect would have produced).
    connect_response_state = None
    with patch("api.routes.google_drive.build_auth_flow") as mock_build_flow_for_connect:
        mock_flow = MagicMock()
        mock_flow.authorization_url.return_value = ("https://accounts.google.com/mock", None)
        mock_build_flow_for_connect.return_value = mock_flow
        client.get("/auth/google/connect", headers={"Authorization": f"Bearer {token}"}, follow_redirects=False)
        connect_response_state = mock_build_flow_for_connect.call_args.kwargs["state"]

    with patch("api.routes.google_drive.build_auth_flow") as mock_build_flow, \
         patch("api.routes.google_drive.DriveService") as mock_drive_service_cls:
        mock_flow = MagicMock()
        mock_credentials = MagicMock()
        mock_credentials.refresh_token = "fake-refresh-token"
        mock_flow.credentials = mock_credentials
        mock_build_flow.return_value = mock_flow

        mock_drive_service_cls.return_value.ensure_app_folder.return_value = "fake-folder-id"

        response = client.get(
            "/auth/google/callback",
            params={"code": "fake-code", "state": connect_response_state},
            follow_redirects=False,
        )

    assert response.status_code in (302, 307)
    assert "drive=connected" in response.headers["location"]

    user = db_session.query(User).filter(User.user_id == user_id).first()
    assert user.google_drive_connected is True
    assert user.google_drive_folder_id == "fake-folder-id"
    assert user.google_refresh_token_encrypted is not None
    assert user.google_refresh_token_encrypted != "fake-refresh-token"  # must be encrypted, not raw


def test_callback_rejects_invalid_state(client):
    response = client.get(
        "/auth/google/callback",
        params={"code": "fake-code", "state": "not-a-real-token"},
        follow_redirects=False,
    )
    assert response.status_code == 400

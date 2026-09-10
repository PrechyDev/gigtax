import io
from unittest.mock import MagicMock, patch


def _auth_header(client, email="receipt-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Receipt User", "email": email, "password": "supersecret123",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_transaction(client, headers):
    response = client.post("/transactions", json={
        "transaction_type": "expense",
        "date": "2026-02-01T00:00:00Z",
        "description": "Laptop stand",
        "amount": 15000,
    }, headers=headers)
    return response.json()["transaction_id"]


def test_upload_receipt_requires_drive_connection(client):
    headers = _auth_header(client)
    transaction_id = _create_transaction(client, headers)

    response = client.post(
        f"/transactions/{transaction_id}/receipts",
        files={"file": ("receipt.jpg", io.BytesIO(b"fake-image-bytes"), "image/jpeg")},
        headers=headers,
    )
    assert response.status_code == 400
    assert "Google Drive" in response.json()["detail"]


@patch("api.routes.receipts.DriveService")
def test_upload_receipt_succeeds_when_drive_connected(mock_drive_service_cls, client, db_session):
    from models.user import User

    headers = _auth_header(client, "receipt-user2@example.com")
    transaction_id = _create_transaction(client, headers)

    user = db_session.query(User).filter(User.email == "receipt-user2@example.com").first()
    user.google_drive_connected = True
    user.google_drive_folder_id = "fake-folder-id"
    user.google_refresh_token_encrypted = "fake-encrypted-token"
    db_session.commit()

    mock_drive_service_cls.return_value.upload.return_value = "fake-drive-file-id"

    response = client.post(
        f"/transactions/{transaction_id}/receipts",
        files={"file": ("receipt.jpg", io.BytesIO(b"fake-image-bytes"), "image/jpeg")},
        headers=headers,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["storage_path"] == "fake-drive-file-id"

    listing = client.get(f"/transactions/{transaction_id}/receipts", headers=headers)
    assert len(listing.json()) == 1


def test_receipts_scoped_to_owning_user(client):
    headers_a = _auth_header(client, "receipt-a@example.com")
    headers_b = _auth_header(client, "receipt-b@example.com")
    transaction_id = _create_transaction(client, headers_a)

    response = client.get(f"/transactions/{transaction_id}/receipts", headers=headers_b)
    assert response.status_code == 404

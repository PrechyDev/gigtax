from unittest.mock import patch


def _auth_header(client, email="report-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Report User", "email": email, "password": "supersecret123",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_download_report_returns_a_pdf(client):
    headers = _auth_header(client)
    client.post("/transactions", json={
        "transaction_type": "income", "date": "2026-03-01T00:00:00Z",
        "description": "Payment", "amount": 3_000_000, "category_slug": "freelance_gig_fees",
    }, headers=headers)

    response = client.get("/tax-computations/2026/report", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_report_works_even_with_zero_transactions(client):
    headers = _auth_header(client, "report-user2@example.com")
    response = client.get("/tax-computations/2026/report", headers=headers)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")


@patch("api.routes.reports.DriveService")
def test_report_backs_up_to_drive_when_connected(mock_drive_service_cls, client, db_session):
    from models.user import User

    headers = _auth_header(client, "report-user3@example.com")
    user = db_session.query(User).filter(User.email == "report-user3@example.com").first()
    user.google_drive_connected = True
    user.google_drive_folder_id = "fake-folder-id"
    db_session.commit()

    mock_drive_service_cls.return_value.upload.return_value = "fake-report-file-id"

    client.post("/transactions", json={
        "transaction_type": "income", "date": "2026-03-01T00:00:00Z",
        "description": "Payment", "amount": 1_000_000, "category_slug": "freelance_gig_fees",
    }, headers=headers)
    client.post("/tax-computations/2026/compute", headers=headers)

    response = client.get("/tax-computations/2026/report", headers=headers)
    assert response.status_code == 200
    mock_drive_service_cls.return_value.upload.assert_called_once()

    from models.tax import TaxReport
    report = db_session.query(TaxReport).first()
    assert report.storage_path == "fake-report-file-id"


@patch("api.routes.reports.DriveService")
def test_report_still_returns_pdf_if_drive_backup_fails(mock_drive_service_cls, client, db_session):
    from models.user import User

    headers = _auth_header(client, "report-user4@example.com")
    user = db_session.query(User).filter(User.email == "report-user4@example.com").first()
    user.google_drive_connected = True
    user.google_drive_folder_id = "fake-folder-id"
    db_session.commit()

    mock_drive_service_cls.side_effect = Exception("Drive is down")

    response = client.get("/tax-computations/2026/report", headers=headers)
    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")

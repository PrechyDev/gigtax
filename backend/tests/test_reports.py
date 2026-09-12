import io
from unittest.mock import patch

import pdfplumber


def _auth_header(client, email="report-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Report User", "email": email, "password": "Supersecret123!",
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


def test_report_still_shows_summary_and_items_when_minimum_wage_exempt(client):
    """The web Reports page shows the exemption banner ABOVE its Tax Summary table,
    never instead of it (see ReportsPage.tsx) — the PDF must match rather than
    stopping at the exemption sentence. Only the band-by-band section is expected to
    be genuinely absent, since no band actually applied.
    """
    headers = _auth_header(client, "report-user8@example.com")
    client.post("/transactions", json={
        "transaction_type": "income", "date": "2026-03-01T00:00:00Z",
        "description": "Small gig", "amount": 100_000, "category_slug": "freelance_gig_fees",
    }, headers=headers)
    client.post("/transactions", json={
        "transaction_type": "expense", "date": "2026-03-01T00:00:00Z",
        "description": "Adobe subscription", "amount": 10_000, "category_slug": "exp_software_subscriptions",
    }, headers=headers)

    response = client.get("/tax-computations/2026/report", headers=headers)
    assert response.status_code == 200

    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    assert "fully exempt" in text
    assert "Total Income" in text
    assert "Net Tax Payable" in text
    assert "Itemized Breakdown" in text
    assert "Software & Subscriptions" in text  # the category, not the raw description
    assert "Band-by-band computation" not in text


def test_report_includes_itemized_category_breakdown(client):
    headers = _auth_header(client, "report-user5@example.com")
    client.post("/transactions", json={
        "transaction_type": "income", "date": "2026-03-01T00:00:00Z",
        "description": "Payment", "amount": 2_000_000, "category_slug": "freelance_gig_fees",
    }, headers=headers)
    client.post("/transactions", json={
        "transaction_type": "expense", "date": "2026-03-01T00:00:00Z",
        "description": "Adobe subscription", "amount": 50_000, "category_slug": "exp_software_subscriptions",
    }, headers=headers)

    response = client.get("/tax-computations/2026/report", headers=headers)
    assert response.status_code == 200

    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    assert "Itemized Breakdown" in text
    assert "Professional Gig Fees" in text
    assert "Software & Subscriptions" in text


def test_report_includes_profile_fields_and_records_period(client):
    headers = _auth_header(client, "report-user6@example.com")
    client.patch("/auth/me", json={
        "tin": "TIN-12345", "state_residence": "Lagos", "occupation_type": "Freelance Developer",
    }, headers=headers)
    client.post("/transactions", json={
        "transaction_type": "income", "date": "2026-02-10T00:00:00Z",
        "description": "Payment", "amount": 2_000_000, "category_slug": "freelance_gig_fees",
    }, headers=headers)
    client.post("/transactions", json={
        "transaction_type": "income", "date": "2026-11-20T00:00:00Z",
        "description": "Payment", "amount": 1_000_000, "category_slug": "freelance_gig_fees",
    }, headers=headers)

    response = client.get("/tax-computations/2026/report", headers=headers)
    assert response.status_code == 200

    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    assert "TIN-12345" in text
    assert "Lagos" in text
    assert "Freelance Developer" in text
    assert "10 Feb 2026" in text
    assert "20 Nov 2026" in text


def test_report_shows_deduction_rate_for_home_office_expense(client):
    headers = _auth_header(client, "report-user7@example.com")
    client.put("/tax-computations/2026/annual-profile", json={
        "annual_rent_paid": None, "has_home_office": True, "home_office_percentage": 30,
    }, headers=headers)
    client.post("/transactions", json={
        "transaction_type": "income", "date": "2026-03-01T00:00:00Z",
        "description": "Payment", "amount": 2_000_000, "category_slug": "freelance_gig_fees",
    }, headers=headers)
    client.post("/transactions", json={
        "transaction_type": "expense", "date": "2026-03-01T00:00:00Z",
        "description": "PHCN bill", "amount": 100_000, "category_slug": "exp_power_utilities",
    }, headers=headers)

    response = client.get("/tax-computations/2026/report", headers=headers)
    assert response.status_code == 200

    with pdfplumber.open(io.BytesIO(response.content)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    assert "Gross Amount" in text
    assert "30%" in text


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

import io
from unittest.mock import patch

from modules.ai_categorization.parsing import ParsingError, PasswordRequiredError
from modules.ai_categorization.schemas import ParsedTransaction


def _auth_header(client, email="stmt-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Statement User", "email": email, "password": "supersecret123",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _csv_file(name="statement.csv"):
    return (name, io.BytesIO(b"Date,Description,Amount\n2026-01-05,Client payment,50000\n"), "text/csv")


@patch("api.routes.statements.process_bank_statement")
def test_upload_single_file_persists_transactions(mock_process, client):
    headers = _auth_header(client)
    mock_process.return_value = [
        ParsedTransaction(
            date="2026-01-05", description="Client payment", amount=50000,
            category_slug="freelance_gig_fees", transaction_type="Income",
            confidence_score=0.9, income_source="Direct client",
        )
    ]

    response = client.post(
        "/statements",
        files={"files": _csv_file()},
        headers=headers,
    )

    assert response.status_code == 201
    results = response.json()["results"]
    assert len(results) == 1
    assert results[0]["status"] == "COMPLETED"
    assert results[0]["transactions_created"] == 1

    listing = client.get("/transactions", headers=headers).json()
    assert len(listing) == 1
    assert listing[0]["review_status"] == "PENDING"  # AI-categorized, awaiting human review


@patch("api.routes.statements.process_bank_statement")
def test_upload_multiple_files_one_locked_does_not_fail_batch(mock_process, client):
    headers = _auth_header(client, "stmt-user2@example.com")

    def side_effect(*args, **kwargs):
        if kwargs["filename"] == "locked.pdf":
            raise PasswordRequiredError("needs a password")
        return [
            ParsedTransaction(
                date="2026-01-05", description="Sale", amount=1000,
                category_slug="sales_of_products", transaction_type="Income",
                confidence_score=0.8,
            )
        ]

    mock_process.side_effect = side_effect

    response = client.post(
        "/statements",
        files=[
            ("files", _csv_file("ok.csv")),
            ("files", ("locked.pdf", io.BytesIO(b"%PDF-fake"), "application/pdf")),
        ],
        headers=headers,
    )

    assert response.status_code == 201
    results = {r["file_name"]: r for r in response.json()["results"]}
    assert results["ok.csv"]["status"] == "COMPLETED"
    assert results["locked.pdf"]["status"] == "LOCKED"
    assert results["locked.pdf"]["requires_password"] is True


@patch("api.routes.statements.process_bank_statement")
def test_upload_parsing_error_marks_file_failed_not_whole_batch(mock_process, client):
    headers = _auth_header(client, "stmt-user3@example.com")
    mock_process.side_effect = ParsingError("corrupt file")

    response = client.post("/statements", files={"files": _csv_file("bad.csv")}, headers=headers)

    assert response.status_code == 201
    result = response.json()["results"][0]
    assert result["status"] == "FAILED"
    assert "corrupt file" in result["error"]


@patch("api.routes.statements.process_bank_statement")
def test_retry_with_correct_password_completes(mock_process, client):
    headers = _auth_header(client, "stmt-user4@example.com")
    mock_process.side_effect = PasswordRequiredError("locked")

    upload_response = client.post(
        "/statements",
        files={"files": ("locked.pdf", io.BytesIO(b"%PDF-fake"), "application/pdf")},
        headers=headers,
    )
    statement_id = upload_response.json()["results"][0]["statement_id"]

    mock_process.side_effect = None
    mock_process.return_value = [
        ParsedTransaction(
            date="2026-01-05", description="Payment", amount=2000,
            category_slug="freelance_gig_fees", transaction_type="Income",
            confidence_score=0.9,
        )
    ]

    retry_response = client.post(
        f"/statements/{statement_id}/retry",
        data={"password": "correct-password"},
        files={"file": ("locked.pdf", io.BytesIO(b"%PDF-fake"), "application/pdf")},
        headers=headers,
    )

    assert retry_response.status_code == 200
    assert retry_response.json()["status"] == "COMPLETED"


@patch("api.routes.statements.process_bank_statement")
def test_retry_with_still_wrong_password_returns_423(mock_process, client):
    headers = _auth_header(client, "stmt-user5@example.com")
    mock_process.side_effect = PasswordRequiredError("locked")

    upload_response = client.post(
        "/statements",
        files={"files": ("locked.pdf", io.BytesIO(b"%PDF-fake"), "application/pdf")},
        headers=headers,
    )
    statement_id = upload_response.json()["results"][0]["statement_id"]

    retry_response = client.post(
        f"/statements/{statement_id}/retry",
        data={"password": "still-wrong"},
        files={"file": ("locked.pdf", io.BytesIO(b"%PDF-fake"), "application/pdf")},
        headers=headers,
    )

    assert retry_response.status_code == 423


def test_statements_require_auth(client):
    response = client.post("/statements", files={"files": _csv_file()})
    assert response.status_code == 401

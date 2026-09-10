import io
from unittest.mock import patch

from modules.ai_categorization.parsing import ParsingError, PasswordRequiredError
from modules.ai_categorization.schemas import ParsedTransaction


def _auth_header(client, email="stmt-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Statement User", "email": email, "password": "Supersecret123!",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _csv_file(name="statement.csv"):
    return (name, io.BytesIO(b"Date,Description,Amount\n2026-01-05,Client payment,50000\n"), "text/csv")


def _statement_by_name(client, headers, file_name):
    return next(s for s in client.get("/statements", headers=headers).json() if s["file_name"] == file_name)


@patch("api.routes.statements.process_bank_statement")
def test_upload_accepts_immediately_then_processes_in_background(mock_process, client, run_background_inline):
    headers = _auth_header(client)
    mock_process.return_value = [
        ParsedTransaction(
            date="2026-01-05", description="Client payment", amount=50000,
            category_slug="freelance_gig_fees", transaction_type="Income",
            confidence_score=0.9, income_source="Direct client",
        )
    ]

    response = client.post("/statements", files={"files": _csv_file()}, headers=headers)

    # The endpoint itself must return immediately with an acceptance status, not the
    # final outcome — processing happens on the (here, inlined-for-testing) background thread.
    assert response.status_code == 202
    assert response.json()["results"][0]["status"] == "PROCESSING"

    # By the time we get here, run_background_inline has already run the real
    # processing function synchronously, so the eventual state is visible immediately.
    statement = _statement_by_name(client, headers, "statement.csv")
    assert statement["parsing_status"] == "COMPLETED"
    assert statement["transactions_created"] == 1

    listing = client.get("/transactions", headers=headers).json()
    assert len(listing) == 1
    assert listing[0]["review_status"] == "PENDING"  # AI-categorized, awaiting human review


@patch("api.routes.statements.process_bank_statement")
def test_upload_multiple_files_one_locked_does_not_fail_batch(mock_process, client, run_background_inline):
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
    assert response.status_code == 202

    assert _statement_by_name(client, headers, "ok.csv")["parsing_status"] == "COMPLETED"
    assert _statement_by_name(client, headers, "locked.pdf")["parsing_status"] == "LOCKED"


@patch("api.routes.statements.process_bank_statement")
def test_upload_parsing_error_marks_file_failed_not_whole_batch(mock_process, client, run_background_inline):
    headers = _auth_header(client, "stmt-user3@example.com")
    mock_process.side_effect = ParsingError("corrupt file")

    response = client.post("/statements", files={"files": _csv_file("bad.csv")}, headers=headers)
    assert response.status_code == 202

    statement = _statement_by_name(client, headers, "bad.csv")
    assert statement["parsing_status"] == "FAILED"
    assert statement["error_message"] == "corrupt file"


@patch("api.routes.statements.process_bank_statement")
def test_upload_generic_llm_failure_marks_failed_with_friendly_message(mock_process, client, run_background_inline):
    headers = _auth_header(client, "stmt-user3b@example.com")
    mock_process.side_effect = RuntimeError("litellm.ServiceUnavailableError: 503 high demand")

    client.post("/statements", files={"files": _csv_file("overloaded.csv")}, headers=headers)

    statement = _statement_by_name(client, headers, "overloaded.csv")
    assert statement["parsing_status"] == "FAILED"
    # Never leak the raw provider error — same friendly message shown to the user.
    assert statement["error_message"] == "Our document processing service is temporarily unavailable. Please try again in a few minutes."


@patch("api.routes.statements.process_bank_statement")
def test_retry_with_correct_password_completes(mock_process, client, run_background_inline):
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
def test_retry_with_still_wrong_password_returns_423(mock_process, client, run_background_inline):
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

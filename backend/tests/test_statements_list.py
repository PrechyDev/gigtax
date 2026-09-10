import io
from unittest.mock import patch

from modules.ai_categorization.parsing import ParsingError
from modules.ai_categorization.schemas import ParsedTransaction


def _auth_header(client, email="stmt-list-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Statement List User", "email": email, "password": "supersecret123",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_statements_empty_for_new_user(client):
    headers = _auth_header(client)
    response = client.get("/statements", headers=headers)
    assert response.status_code == 200
    assert response.json() == []


@patch("api.routes.statements.process_bank_statement")
def test_list_statements_reflects_uploaded_files(mock_process, client):
    headers = _auth_header(client, "stmt-list-user2@example.com")
    mock_process.return_value = [
        ParsedTransaction(
            date="2026-01-05", description="Payment", amount=1000,
            category_slug="freelance_gig_fees", transaction_type="Income", confidence_score=0.9,
        )
    ]
    client.post(
        "/statements",
        files={"files": ("statement.csv", io.BytesIO(b"data"), "text/csv")},
        headers=headers,
    )

    response = client.get("/statements", headers=headers)
    assert response.status_code == 200
    items = response.json()
    assert len(items) == 1
    assert items[0]["file_name"] == "statement.csv"
    assert items[0]["parsing_status"] == "COMPLETED"
    assert items[0]["source_type"] == "csv"


@patch("api.routes.statements.process_bank_statement")
def test_a_generic_llm_failure_marks_file_failed_with_friendly_message_not_a_500(mock_process, client):
    headers = _auth_header(client, "stmt-list-user3@example.com")
    mock_process.side_effect = RuntimeError("litellm.APIConnectionError: 429 rate limit exceeded, quota exhausted")

    response = client.post(
        "/statements",
        files={"files": ("statement.csv", io.BytesIO(b"data"), "text/csv")},
        headers=headers,
    )

    assert response.status_code == 201  # the batch endpoint itself still succeeds
    result = response.json()["results"][0]
    assert result["status"] == "FAILED"
    assert "429" not in result["error"]
    assert "rate limit" not in result["error"].lower()
    assert "temporarily unavailable" in result["error"]


def test_list_statements_scoped_to_owning_user(client):
    headers_a = _auth_header(client, "stmt-list-a@example.com")
    headers_b = _auth_header(client, "stmt-list-b@example.com")

    with patch("api.routes.statements.process_bank_statement") as mock_process:
        mock_process.side_effect = ParsingError("bad file")
        client.post("/statements", files={"files": ("a.csv", io.BytesIO(b"x"), "text/csv")}, headers=headers_a)

    assert client.get("/statements", headers=headers_b).json() == []


def test_list_statements_requires_auth(client):
    response = client.get("/statements")
    assert response.status_code == 401

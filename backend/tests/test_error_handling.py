from unittest.mock import patch


def _auth_header(client, email="error-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Error User", "email": email, "password": "Supersecret123!",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_unhandled_exception_returns_generic_safe_message_not_a_stack_trace(client):
    headers = _auth_header(client)

    # Simulate a totally generic, unanticipated failure somewhere with no
    # endpoint-specific try/except of its own — the global handler must still
    # produce a clean, safe response rather than leaking internals or crashing
    # the test process.
    with patch("api.routes.custom_rules.CustomRule", side_effect=RuntimeError("unexpected DB driver internals: connection pool exhausted at 0x7f3a")):
        response = client.post("/custom-rules", json={
            "keyword_pattern": "UBER", "assigned_category": "exp_travel",
        }, headers=headers)

    assert response.status_code == 500
    body = response.json()
    assert body["detail"] == "Something went wrong on our end. Please try again shortly."
    assert "0x7f3a" not in body["detail"]
    assert "connection pool" not in body["detail"]

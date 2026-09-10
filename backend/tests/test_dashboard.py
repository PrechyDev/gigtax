import io


def _auth_header(client, email="dash-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Dash User", "email": email, "password": "supersecret123",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_dashboard_reflects_live_computation_without_needing_compute_call(client):
    headers = _auth_header(client)
    client.post("/transactions", json={
        "transaction_type": "income", "date": "2026-03-01T00:00:00Z",
        "description": "Payment", "amount": 2_000_000, "category_slug": "freelance_gig_fees",
    }, headers=headers)

    response = client.get("/dashboard", params={"tax_year": "2026"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_income"] == 2_000_000
    assert body["estimated_tax_owed"] == 180_000  # 800k@0% + 1.2M@15%


def test_dashboard_flags_drive_not_connected(client):
    headers = _auth_header(client, "dash-user2@example.com")
    response = client.get("/dashboard", params={"tax_year": "2026"}, headers=headers)
    body = response.json()
    assert body["google_drive_connected"] is False
    assert any("Google Drive" in action for action in body["outstanding_actions"])


def test_dashboard_counts_pending_review_items(client):
    headers = _auth_header(client, "dash-user3@example.com")
    create = client.post("/transactions", json={
        "transaction_type": "expense", "date": "2026-03-01T00:00:00Z",
        "description": "Tool", "amount": 5000,
    }, headers=headers)
    transaction_id = create.json()["transaction_id"]
    client.patch(f"/transactions/{transaction_id}", json={"review_status": "pending"}, headers=headers)

    response = client.get("/dashboard", params={"tax_year": "2026"}, headers=headers)
    assert response.json()["pending_review_count"] == 1
    assert any("awaiting your review" in action for action in response.json()["outstanding_actions"])


def test_dashboard_counts_approved_expenses_missing_receipts(client):
    headers = _auth_header(client, "dash-user4@example.com")
    client.post("/transactions", json={
        "transaction_type": "expense", "date": "2026-03-01T00:00:00Z",
        "description": "Laptop stand", "amount": 15000, "category_slug": "exp_software_subscriptions",
    }, headers=headers)

    response = client.get("/dashboard", params={"tax_year": "2026"}, headers=headers)
    assert response.json()["missing_receipts_count"] == 1

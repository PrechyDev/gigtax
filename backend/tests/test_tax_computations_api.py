def _auth_header(client, email="tax-api-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Tax API User", "email": email, "password": "Supersecret123!",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _approved_income(client, headers, amount, date="2026-03-01T00:00:00Z"):
    response = client.post("/transactions", json={
        "transaction_type": "income",
        "date": date,
        "description": "Client payment",
        "amount": amount,
        "category_slug": "freelance_gig_fees",
    }, headers=headers)
    assert response.status_code == 201


def test_compute_uses_only_approved_transactions_for_the_year(client):
    headers = _auth_header(client)
    _approved_income(client, headers, 5_000_000, date="2026-03-01T00:00:00Z")
    _approved_income(client, headers, 1_000_000, date="2025-03-01T00:00:00Z")  # different tax year

    response = client.post("/tax-computations/2026/compute", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["total_income"] == 5_000_000
    assert body["estimated_tax_owed"] == 690_000


def test_get_before_compute_returns_404(client):
    headers = _auth_header(client, "tax-api-user2@example.com")
    response = client.get("/tax-computations/2026", headers=headers)
    assert response.status_code == 404


def test_get_after_compute_returns_stored_breakdown(client):
    headers = _auth_header(client, "tax-api-user3@example.com")
    _approved_income(client, headers, 2_000_000)
    client.post("/tax-computations/2026/compute", headers=headers)

    response = client.get("/tax-computations/2026", headers=headers)
    assert response.status_code == 200
    assert response.json()["taxable_income"] == 2_000_000
    assert len(response.json()["band_breakdown"]) == 2


def test_recompute_updates_existing_row_rather_than_duplicating(client):
    headers = _auth_header(client, "tax-api-user4@example.com")
    _approved_income(client, headers, 1_000_000)
    first = client.post("/tax-computations/2026/compute", headers=headers).json()

    _approved_income(client, headers, 1_000_000)  # a second approved transaction
    second = client.post("/tax-computations/2026/compute", headers=headers).json()

    assert first["total_income"] == 1_000_000
    assert second["total_income"] == 2_000_000


def test_pending_transactions_are_excluded_from_computation(client):
    headers = _auth_header(client, "tax-api-user5@example.com")
    # A statement-sourced (PENDING) transaction should not count until reviewed —
    # simulate via manual entry then forcing it back to PENDING through a PATCH.
    create = client.post("/transactions", json={
        "transaction_type": "income", "date": "2026-03-01T00:00:00Z",
        "description": "Unreviewed", "amount": 9_000_000,
    }, headers=headers)
    transaction_id = create.json()["transaction_id"]
    client.patch(f"/transactions/{transaction_id}", json={"review_status": "pending"}, headers=headers)

    response = client.post("/tax-computations/2026/compute", headers=headers)
    assert response.json()["total_income"] == 0


def test_compute_returns_itemized_breakdown_by_category(client):
    headers = _auth_header(client, "tax-api-user6@example.com")
    _approved_income(client, headers, 2_000_000)
    client.post("/transactions", json={
        "transaction_type": "expense", "date": "2026-03-01T00:00:00Z",
        "description": "Adobe subscription", "amount": 50_000,
        "category_slug": "exp_software_subscriptions",
    }, headers=headers)

    response = client.post("/tax-computations/2026/compute", headers=headers)
    body = response.json()

    assert body["income_items"] == [{"category_name": "Professional Gig Fees", "amount": 2_000_000}]
    assert body["deduction_items"] == [{"category_name": "Software & Subscriptions", "amount": 50_000}]
    assert body["relief_items"] == []
    assert body["capital_allowance_items"] == []


def test_get_returns_the_same_itemized_breakdown_computed_earlier(client):
    headers = _auth_header(client, "tax-api-user7@example.com")
    _approved_income(client, headers, 2_000_000)
    client.post("/tax-computations/2026/compute", headers=headers)

    response = client.get("/tax-computations/2026", headers=headers)
    assert response.json()["income_items"] == [{"category_name": "Professional Gig Fees", "amount": 2_000_000}]

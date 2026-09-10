def _auth_header(client, email="tx-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Tx User", "email": email, "password": "supersecret123",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_manual_income_is_auto_approved(client):
    headers = _auth_header(client)
    response = client.post("/transactions", json={
        "transaction_type": "income",
        "date": "2026-02-01T00:00:00Z",
        "description": "Freelance web design project",
        "amount": 150000,
        "category_slug": "freelance_gig_fees",
        "income_source": "Direct client",
    }, headers=headers)

    assert response.status_code == 201
    body = response.json()
    assert body["review_status"] == "APPROVED"
    assert body["type"] == "income"


def test_create_manual_expense_rejects_unknown_category(client):
    headers = _auth_header(client, "tx-user2@example.com")
    response = client.post("/transactions", json={
        "transaction_type": "expense",
        "date": "2026-02-01T00:00:00Z",
        "description": "Random purchase",
        "amount": 5000,
        "category_slug": "not_a_real_category",
    }, headers=headers)
    assert response.status_code == 400


def test_list_transactions_filters_by_review_status(client):
    headers = _auth_header(client, "tx-user3@example.com")
    client.post("/transactions", json={
        "transaction_type": "income",
        "date": "2026-02-01T00:00:00Z",
        "description": "Gig payment",
        "amount": 20000,
    }, headers=headers)

    response = client.get("/transactions", params={"review_status": "approved"}, headers=headers)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["review_status"] == "APPROVED"

    response_pending = client.get("/transactions", params={"review_status": "pending"}, headers=headers)
    assert response_pending.json() == []


def test_patch_transaction_approves_and_recategorizes(client):
    headers = _auth_header(client, "tx-user4@example.com")
    create_response = client.post("/transactions", json={
        "transaction_type": "expense",
        "date": "2026-02-01T00:00:00Z",
        "description": "Some tool",
        "amount": 3000,
    }, headers=headers)
    transaction_id = create_response.json()["transaction_id"]

    patch_response = client.patch(f"/transactions/{transaction_id}", json={
        "category_slug": "exp_software_subscriptions",
        "review_status": "approved",
    }, headers=headers)

    assert patch_response.status_code == 200
    body = patch_response.json()
    assert body["review_status"] == "APPROVED"
    assert body["tax_treatment"] == "100_percent_deductible"


def test_transactions_require_auth(client):
    response = client.get("/transactions")
    assert response.status_code == 401

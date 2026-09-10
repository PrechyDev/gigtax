from unittest.mock import patch

from modules.ai_categorization.schemas import ParsedTransaction


def _auth_header(client, email="asset-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Asset User", "email": email, "password": "supersecret123",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_manual_asset_purchase_creates_linked_asset_not_a_full_expense_deduction(client):
    headers = _auth_header(client)
    response = client.post("/transactions", json={
        "transaction_type": "expense",
        "date": "2026-03-01T00:00:00Z",
        "description": "MacBook Pro for client work",
        "amount": 1_500_000,
        "category_slug": "asset_computer_equipment",
    }, headers=headers)
    assert response.status_code == 201

    assets = client.get("/assets", params={"tax_year": 2026}, headers=headers).json()
    assert len(assets) == 1
    assert assets[0]["cost"] == 1_500_000
    assert assets[0]["asset_class"] == "class_2"
    assert assets[0]["current_year_allowance"] == 300_000  # 20% of 1,500,000


@patch("api.routes.statements.process_bank_statement")
def test_ai_categorized_asset_purchase_also_creates_linked_asset(mock_process, client):
    headers = _auth_header(client, "asset-user2@example.com")
    mock_process.return_value = [
        ParsedTransaction(
            date="2026-01-10", description="Camera equipment", amount=400_000,
            category_slug="asset_computer_equipment", transaction_type="Expense",
            confidence_score=0.85, merchant_name="Camera Store",
        )
    ]

    import io
    client.post(
        "/statements",
        files={"files": ("statement.csv", io.BytesIO(b"dummy"), "text/csv")},
        headers=headers,
    )

    assets = client.get("/assets", headers=headers).json()
    assert len(assets) == 1
    assert assets[0]["cost"] == 400_000


def test_recategorizing_a_normal_expense_to_asset_creates_one(client):
    headers = _auth_header(client, "asset-user3@example.com")
    create = client.post("/transactions", json={
        "transaction_type": "expense", "date": "2026-03-01T00:00:00Z",
        "description": "Equipment", "amount": 200_000,
        "category_slug": "exp_software_subscriptions",  # initially mis-tagged as a normal expense
    }, headers=headers)
    transaction_id = create.json()["transaction_id"]
    assert client.get("/assets", headers=headers).json() == []

    client.patch(f"/transactions/{transaction_id}", json={
        "category_slug": "asset_other_capital",
    }, headers=headers)

    assets = client.get("/assets", headers=headers).json()
    assert len(assets) == 1
    assert assets[0]["asset_class"] == "class_3"


def test_recategorizing_an_asset_back_to_a_normal_expense_removes_it(client):
    headers = _auth_header(client, "asset-user4@example.com")
    create = client.post("/transactions", json={
        "transaction_type": "expense", "date": "2026-03-01T00:00:00Z",
        "description": "Laptop", "amount": 500_000,
        "category_slug": "asset_computer_equipment",
    }, headers=headers)
    transaction_id = create.json()["transaction_id"]
    assert len(client.get("/assets", headers=headers).json()) == 1

    client.patch(f"/transactions/{transaction_id}", json={
        "category_slug": "exp_software_subscriptions",
    }, headers=headers)

    assert client.get("/assets", headers=headers).json() == []


def test_dispose_asset_stops_future_allowance(client):
    headers = _auth_header(client, "asset-user5@example.com")
    create = client.post("/transactions", json={
        "transaction_type": "expense", "date": "2026-03-01T00:00:00Z",
        "description": "Laptop", "amount": 300_000,
        "category_slug": "asset_computer_equipment",
    }, headers=headers)
    asset_id = client.get("/assets", headers=headers).json()[0]["asset_id"]

    dispose_response = client.patch(f"/assets/{asset_id}/dispose", json={
        "disposed_date": "2027-06-01T00:00:00Z",
    }, headers=headers)
    assert dispose_response.status_code == 200
    assert dispose_response.json()["disposed"] is True

    assets_2027 = client.get("/assets", params={"tax_year": 2027}, headers=headers).json()
    assert assets_2027[0]["current_year_allowance"] == 0  # disposed this year


def test_tax_computation_uses_capital_allowance_not_full_asset_cost(client):
    headers = _auth_header(client, "asset-user6@example.com")
    client.post("/transactions", json={
        "transaction_type": "income", "date": "2026-03-01T00:00:00Z",
        "description": "Payment", "amount": 3_000_000, "category_slug": "freelance_gig_fees",
    }, headers=headers)
    client.post("/transactions", json={
        "transaction_type": "expense", "date": "2026-03-01T00:00:00Z",
        "description": "Laptop", "amount": 1_000_000,
        "category_slug": "asset_computer_equipment",
    }, headers=headers)

    response = client.post("/tax-computations/2026/compute", headers=headers)
    body = response.json()
    assert body["total_deductions"] == 0  # the 1,000,000 must NOT appear here
    assert body["total_capital_allowances"] == 200_000  # 20% of 1,000,000
    assert body["taxable_income"] == 2_800_000  # 3,000,000 - 200,000


def test_assets_require_auth(client):
    response = client.get("/assets")
    assert response.status_code == 401

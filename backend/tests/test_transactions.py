def _auth_header(client, email="tx-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Tx User", "email": email, "password": "Supersecret123!",
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


def test_exclude_uncategorized_separates_pending_review_from_uncategorized_bucket(client):
    """Pending Review and Uncategorized must be disjoint buckets — see
    api/routes/transactions.py's exclude_uncategorized filter, which the Ledger's
    "Pending Review" tab uses to stay separate from its "Uncategorized" tab
    (category_slug=uncategorized).
    """
    headers = _auth_header(client, "tx-user-exclude-uncat@example.com")

    real_category = client.post("/transactions", json={
        "transaction_type": "expense", "date": "2026-02-01T00:00:00Z",
        "description": "Software", "amount": 5000, "category_slug": "exp_software_subscriptions",
    }, headers=headers).json()
    client.patch(f"/transactions/{real_category['transaction_id']}", json={"review_status": "pending"}, headers=headers)

    uncategorized = client.post("/transactions", json={
        "transaction_type": "expense", "date": "2026-02-02T00:00:00Z",
        "description": "Transfer to self", "amount": 3000, "category_slug": "exp_software_subscriptions",
    }, headers=headers).json()
    client.patch(
        f"/transactions/{uncategorized['transaction_id']}",
        json={"review_status": "pending", "category_slug": "uncategorized"},
        headers=headers,
    )

    pending_review = client.get(
        "/transactions", params={"review_status": "pending", "exclude_uncategorized": True}, headers=headers
    ).json()
    assert [t["description"] for t in pending_review] == ["Software"]

    uncategorized_bucket = client.get(
        "/transactions", params={"review_status": "pending", "category_slug": "uncategorized"}, headers=headers
    ).json()
    assert [t["description"] for t in uncategorized_bucket] == ["Transfer to self"]


def test_exclude_uncategorized_keeps_transactions_with_no_category_at_all(client):
    """A transaction with no category (e.g. manual entry with no category_slug) isn't
    the "AI flagged this as personal" case exclude_uncategorized targets — it must stay
    visible in Pending Review, not silently disappear.
    """
    headers = _auth_header(client, "tx-user-exclude-uncat-null@example.com")
    create = client.post("/transactions", json={
        "transaction_type": "expense", "date": "2026-02-01T00:00:00Z",
        "description": "No category set", "amount": 1000,
    }, headers=headers).json()
    client.patch(f"/transactions/{create['transaction_id']}", json={"review_status": "pending"}, headers=headers)

    response = client.get(
        "/transactions", params={"review_status": "pending", "exclude_uncategorized": True}, headers=headers
    ).json()
    assert [t["description"] for t in response] == ["No category set"]


def test_list_transactions_respects_limit_and_offset(client):
    headers = _auth_header(client, "tx-user-paging@example.com")
    for i in range(5):
        client.post("/transactions", json={
            "transaction_type": "income",
            "date": f"2026-02-0{i + 1}T00:00:00Z",
            "description": f"Payment {i}",
            "amount": 1000 * (i + 1),
        }, headers=headers)

    first_page = client.get("/transactions", params={"limit": 2}, headers=headers).json()
    assert len(first_page) == 2
    # Newest first (order_by date desc) — page 1 is the two most recent.
    assert [t["description"] for t in first_page] == ["Payment 4", "Payment 3"]

    second_page = client.get("/transactions", params={"limit": 2, "offset": 2}, headers=headers).json()
    assert [t["description"] for t in second_page] == ["Payment 2", "Payment 1"]

    third_page = client.get("/transactions", params={"limit": 2, "offset": 4}, headers=headers).json()
    assert [t["description"] for t in third_page] == ["Payment 0"]


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


def test_manual_home_office_expense_applies_that_years_deductibility_percentage(client):
    headers = _auth_header(client, "tx-user-hoexp@example.com")
    client.put("/tax-computations/2026/annual-profile", json={
        "annual_rent_paid": None, "has_home_office": True, "home_office_percentage": 40,
    }, headers=headers)
    client.post("/transactions", json={
        "transaction_type": "expense", "date": "2026-03-01T00:00:00Z",
        "description": "PHCN bill", "amount": 100_000, "category_slug": "exp_power_utilities",
    }, headers=headers)

    response = client.post("/tax-computations/2026/compute", headers=headers)
    assert response.json()["total_deductions"] == 40_000  # 40% of 100,000


def test_recategorizing_into_home_office_applies_that_years_percentage(client):
    """Previously, correcting a transaction's category to a home-office one after the
    fact left its deductibility stuck at whatever it started as (100%, since ingestion
    only stamps this once, at creation) — the correction below must actually apply the
    right rate, not silently leave it fully deductible.
    """
    headers = _auth_header(client, "tx-user-hoexp2@example.com")
    client.put("/tax-computations/2026/annual-profile", json={
        "annual_rent_paid": None, "has_home_office": True, "home_office_percentage": 30,
    }, headers=headers)
    create = client.post("/transactions", json={
        "transaction_type": "expense", "date": "2026-03-01T00:00:00Z",
        "description": "Utility bill", "amount": 100_000, "category_slug": "exp_software_subscriptions",
    }, headers=headers).json()
    client.patch(f"/transactions/{create['transaction_id']}", json={
        "category_slug": "exp_power_utilities",
    }, headers=headers)

    response = client.post("/tax-computations/2026/compute", headers=headers)
    assert response.json()["total_deductions"] == 30_000


def test_recategorizing_out_of_home_office_resets_deductibility_to_full(client):
    headers = _auth_header(client, "tx-user-hoexp3@example.com")
    client.put("/tax-computations/2026/annual-profile", json={
        "annual_rent_paid": None, "has_home_office": True, "home_office_percentage": 30,
    }, headers=headers)
    create = client.post("/transactions", json={
        "transaction_type": "expense", "date": "2026-03-01T00:00:00Z",
        "description": "Power bill", "amount": 100_000, "category_slug": "exp_power_utilities",
    }, headers=headers).json()
    client.patch(f"/transactions/{create['transaction_id']}", json={
        "category_slug": "exp_software_subscriptions",
    }, headers=headers)

    response = client.post("/tax-computations/2026/compute", headers=headers)
    assert response.json()["total_deductions"] == 100_000


def test_transactions_require_auth(client):
    response = client.get("/transactions")
    assert response.status_code == 401


def test_patch_transaction_updates_description(client):
    headers = _auth_header(client, "tx-user5@example.com")
    create_response = client.post("/transactions", json={
        "transaction_type": "expense",
        "date": "2026-02-01T00:00:00Z",
        "description": "Vague description",
        "amount": 3000,
    }, headers=headers)
    transaction_id = create_response.json()["transaction_id"]

    patch_response = client.patch(f"/transactions/{transaction_id}", json={
        "description": "Adobe Creative Cloud subscription",
    }, headers=headers)

    assert patch_response.status_code == 200
    assert patch_response.json()["description"] == "Adobe Creative Cloud subscription"


def test_manual_transaction_source_is_manual_entry(client):
    headers = _auth_header(client, "tx-user6@example.com")
    response = client.post("/transactions", json={
        "transaction_type": "income",
        "date": "2026-02-01T00:00:00Z",
        "description": "Gig payment",
        "amount": 20000,
    }, headers=headers)
    assert response.json()["source"] == "Manual Entry"


def test_delete_transaction_removes_it(client):
    headers = _auth_header(client, "tx-user7@example.com")
    create_response = client.post("/transactions", json={
        "transaction_type": "expense",
        "date": "2026-02-01T00:00:00Z",
        "description": "Some tool",
        "amount": 3000,
    }, headers=headers)
    transaction_id = create_response.json()["transaction_id"]

    delete_response = client.delete(f"/transactions/{transaction_id}", headers=headers)
    assert delete_response.status_code == 204

    list_response = client.get("/transactions", headers=headers)
    assert list_response.json() == []


def test_delete_transaction_removes_its_linked_asset_too(client):
    headers = _auth_header(client, "tx-user10@example.com")
    create_response = client.post("/transactions", json={
        "transaction_type": "expense",
        "date": "2026-02-01T00:00:00Z",
        "description": "New laptop",
        "amount": 500000,
        "category_slug": "asset_computer_equipment",
    }, headers=headers)
    transaction_id = create_response.json()["transaction_id"]
    assert client.get("/assets", headers=headers).json() != []

    delete_response = client.delete(f"/transactions/{transaction_id}", headers=headers)
    assert delete_response.status_code == 204

    assert client.get("/transactions", headers=headers).json() == []
    assert client.get("/assets", headers=headers).json() == []


def test_delete_transaction_requires_ownership(client):
    headers_a = _auth_header(client, "tx-user8@example.com")
    headers_b = _auth_header(client, "tx-user9@example.com")
    create_response = client.post("/transactions", json={
        "transaction_type": "expense",
        "date": "2026-02-01T00:00:00Z",
        "description": "Some tool",
        "amount": 3000,
    }, headers=headers_a)
    transaction_id = create_response.json()["transaction_id"]

    delete_response = client.delete(f"/transactions/{transaction_id}", headers=headers_b)
    assert delete_response.status_code == 404


def test_delete_transaction_requires_auth(client):
    response = client.delete("/transactions/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 401

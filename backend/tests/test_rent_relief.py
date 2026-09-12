"""Rent is a per-tax-year field (AnnualTaxProfile), not a ledger transaction — the
loader synthesizes an Expense (home-office share) and a Relief (remainder, capped at
20%/500k by the existing engine logic) entry from it at computation time. See
modules/tax_computation/loader.py::_rent_categorized_transactions.
"""


def _auth_header(client, email="rent-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Rent User", "email": email, "password": "Supersecret123!",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _set_annual_profile(client, headers, tax_year="2026", **kwargs):
    payload = {"annual_rent_paid": None, "has_home_office": False, "home_office_percentage": 0.0}
    payload.update(kwargs)
    response = client.put(f"/tax-computations/{tax_year}/annual-profile", json=payload, headers=headers)
    assert response.status_code == 200
    return response


def _approved_income(client, headers, amount, date="2026-03-01T00:00:00Z"):
    response = client.post("/transactions", json={
        "transaction_type": "income",
        "date": date,
        "description": "Client payment",
        "amount": amount,
        "category_slug": "freelance_gig_fees",
    }, headers=headers)
    assert response.status_code == 201


def test_rent_with_no_home_office_goes_entirely_to_relief(client):
    headers = _auth_header(client)
    _set_annual_profile(client, headers, annual_rent_paid=1_000_000, has_home_office=False)
    _approved_income(client, headers, 5_000_000)

    response = client.post("/tax-computations/2026/compute", headers=headers)
    body = response.json()
    # 20% of 1,000,000 = 200,000, under the 500,000 cap
    assert body["total_reliefs"] == 200_000
    assert body["total_deductions"] == 0


def test_rent_splits_between_home_office_expense_and_relief(client):
    headers = _auth_header(client, "rent-user2@example.com")
    _set_annual_profile(client, headers, annual_rent_paid=1_000_000, has_home_office=True, home_office_percentage=25)
    _approved_income(client, headers, 5_000_000)

    response = client.post("/tax-computations/2026/compute", headers=headers)
    body = response.json()
    # 25% of 1,000,000 = 250,000 home-office expense; remainder 750,000 -> 20% = 150,000 relief
    assert body["total_deductions"] == 250_000
    assert body["total_reliefs"] == 150_000


def test_rent_split_appears_in_itemized_breakdown(client):
    headers = _auth_header(client, "rent-user4@example.com")
    _set_annual_profile(client, headers, annual_rent_paid=1_000_000, has_home_office=True, home_office_percentage=25)
    _approved_income(client, headers, 5_000_000)

    response = client.post("/tax-computations/2026/compute", headers=headers)
    body = response.json()
    assert body["deduction_items"] == [
        {
            "category_name": "Rent (Home Office Portion)", "amount": 250_000,
            "gross_amount": 250_000, "rate": 100.0,
        }
    ]
    assert body["relief_items"] == [
        {"category_name": "Rent Relief", "amount": 150_000, "gross_amount": None, "rate": None}
    ]


def test_no_rent_paid_produces_no_synthesized_entries(client):
    headers = _auth_header(client, "rent-user3@example.com")
    _approved_income(client, headers, 5_000_000)

    response = client.post("/tax-computations/2026/compute", headers=headers)
    body = response.json()
    assert body["total_deductions"] == 0
    assert body["total_reliefs"] == 0


def test_rent_profile_is_scoped_to_its_own_tax_year(client):
    """The whole point of moving this off the User row — a home-office % set for one
    year must not leak into another year's computation.
    """
    headers = _auth_header(client, "rent-user5@example.com")
    _set_annual_profile(client, headers, tax_year="2025", annual_rent_paid=1_000_000, has_home_office=True, home_office_percentage=25)
    _approved_income(client, headers, 5_000_000, date="2026-03-01T00:00:00Z")

    response = client.post("/tax-computations/2026/compute", headers=headers)
    body = response.json()
    # 2026 has no annual profile of its own — 2025's rent must not apply here.
    assert body["total_deductions"] == 0
    assert body["total_reliefs"] == 0

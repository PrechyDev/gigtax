def _auth_header(client, email="annual-profile-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Annual Profile User", "email": email, "password": "Supersecret123!",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_get_returns_blank_shape_for_a_year_with_nothing_saved(client):
    headers = _auth_header(client)
    response = client.get("/tax-computations/2026/annual-profile", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body == {
        "tax_year": "2026", "annual_rent_paid": None, "has_home_office": False, "home_office_percentage": 0.0,
    }


def test_put_creates_then_get_reflects_it(client):
    headers = _auth_header(client, "annual-profile-user2@example.com")
    put_response = client.put("/tax-computations/2026/annual-profile", json={
        "annual_rent_paid": 1_200_000, "has_home_office": True, "home_office_percentage": 40,
    }, headers=headers)
    assert put_response.status_code == 200
    assert put_response.json()["annual_rent_paid"] == 1_200_000

    get_response = client.get("/tax-computations/2026/annual-profile", headers=headers)
    body = get_response.json()
    assert body["annual_rent_paid"] == 1_200_000
    assert body["has_home_office"] is True
    assert body["home_office_percentage"] == 40


def test_put_again_updates_the_same_year_rather_than_duplicating(client):
    headers = _auth_header(client, "annual-profile-user3@example.com")
    client.put("/tax-computations/2026/annual-profile", json={
        "annual_rent_paid": 500_000, "has_home_office": False, "home_office_percentage": 0,
    }, headers=headers)
    client.put("/tax-computations/2026/annual-profile", json={
        "annual_rent_paid": 900_000, "has_home_office": True, "home_office_percentage": 50,
    }, headers=headers)

    response = client.get("/tax-computations/2026/annual-profile", headers=headers)
    body = response.json()
    assert body["annual_rent_paid"] == 900_000
    assert body["home_office_percentage"] == 50


def test_two_tax_years_are_independent(client):
    headers = _auth_header(client, "annual-profile-user4@example.com")
    client.put("/tax-computations/2025/annual-profile", json={
        "annual_rent_paid": 500_000, "has_home_office": False, "home_office_percentage": 0,
    }, headers=headers)
    client.put("/tax-computations/2026/annual-profile", json={
        "annual_rent_paid": 900_000, "has_home_office": True, "home_office_percentage": 50,
    }, headers=headers)

    body_2025 = client.get("/tax-computations/2025/annual-profile", headers=headers).json()
    body_2026 = client.get("/tax-computations/2026/annual-profile", headers=headers).json()
    assert body_2025["annual_rent_paid"] == 500_000
    assert body_2025["has_home_office"] is False
    assert body_2026["annual_rent_paid"] == 900_000
    assert body_2026["has_home_office"] is True


def test_home_office_percentage_out_of_range_is_rejected(client):
    headers = _auth_header(client, "annual-profile-user5@example.com")
    response = client.put("/tax-computations/2026/annual-profile", json={
        "annual_rent_paid": None, "has_home_office": True, "home_office_percentage": 150,
    }, headers=headers)
    assert response.status_code == 422


def test_annual_profile_is_scoped_per_user(client):
    headers_a = _auth_header(client, "annual-profile-user6a@example.com")
    headers_b = _auth_header(client, "annual-profile-user6b@example.com")
    client.put("/tax-computations/2026/annual-profile", json={
        "annual_rent_paid": 1_000_000, "has_home_office": True, "home_office_percentage": 30,
    }, headers=headers_a)

    body_b = client.get("/tax-computations/2026/annual-profile", headers=headers_b).json()
    assert body_b["annual_rent_paid"] is None
    assert body_b["has_home_office"] is False


def test_annual_profile_requires_auth(client):
    response = client.get("/tax-computations/2026/annual-profile")
    assert response.status_code == 401

def test_register_creates_user_and_returns_token(client):
    response = client.post("/auth/register", json={
        "name": "Precious Okafor",
        "email": "precious@example.com",
        "password": "Supersecret123!",
        "occupation_type": "freelancer",
        "state_residence": "Lagos",
        "tax_year": "2026",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]


def test_register_rejects_non_4_digit_tax_year_with_422_not_500(client):
    # Regression test: Swagger's default placeholder value ("string") for tax_year
    # used to reach the DB as-is and crash with a raw 500 (StringDataRightTruncation)
    # since the column is varchar(4) — this must be caught as a clean validation error.
    response = client.post("/auth/register", json={
        "name": "Bad Year", "email": "badyear@example.com", "password": "Supersecret123!",
        "tax_year": "string",
    })
    assert response.status_code == 422


def test_register_rejects_password_missing_a_number(client):
    response = client.post("/auth/register", json={
        "name": "Weak Pw", "email": "weakpw1@example.com", "password": "Nodigitshere!",
    })
    assert response.status_code == 422


def test_register_rejects_password_missing_uppercase(client):
    response = client.post("/auth/register", json={
        "name": "Weak Pw", "email": "weakpw2@example.com", "password": "nouppercase123!",
    })
    assert response.status_code == 422


def test_register_rejects_password_missing_special_char(client):
    response = client.post("/auth/register", json={
        "name": "Weak Pw", "email": "weakpw3@example.com", "password": "NoSpecialChar123",
    })
    assert response.status_code == 422


def test_register_accepts_password_meeting_all_rules(client):
    response = client.post("/auth/register", json={
        "name": "Strong Pw", "email": "strongpw@example.com", "password": "Str0ngPassword!",
    })
    assert response.status_code == 201


def test_register_rejects_overlong_name_with_422_not_500(client):
    response = client.post("/auth/register", json={
        "name": "A" * 200, "email": "longname@example.com", "password": "Supersecret123!",
    })
    assert response.status_code == 422


def test_register_rejects_duplicate_email(client):
    payload = {"name": "A", "email": "dupe@example.com", "password": "Supersecret123!"}
    first = client.post("/auth/register", json=payload)
    assert first.status_code == 201

    second = client.post("/auth/register", json=payload)
    assert second.status_code == 409


def test_login_with_correct_credentials(client):
    client.post("/auth/register", json={
        "name": "Login User", "email": "login@example.com", "password": "Supersecret123!",
    })
    response = client.post("/auth/login", json={"email": "login@example.com", "password": "Supersecret123!"})
    assert response.status_code == 200
    assert response.json()["access_token"]


def test_login_with_wrong_password_is_rejected(client):
    client.post("/auth/register", json={
        "name": "Login User", "email": "wrongpw@example.com", "password": "Supersecret123!",
    })
    response = client.post("/auth/login", json={"email": "wrongpw@example.com", "password": "wrong"})
    assert response.status_code == 401


def test_me_requires_a_token(client):
    response = client.get("/auth/me")
    assert response.status_code == 401


def test_me_returns_profile_with_valid_token(client):
    register_response = client.post("/auth/register", json={
        "name": "Profile User", "email": "profile@example.com", "password": "Supersecret123!",
    })
    token = register_response.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "profile@example.com"


def _register_and_get_headers(client, email="update-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Update User", "email": email, "password": "Supersecret123!",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_patch_me_updates_only_supplied_fields(client):
    headers = _register_and_get_headers(client)

    response = client.patch("/auth/me", json={
        "occupation_type": "content creator",
        "tin": "12345678-0001",
        "has_home_office": True,
        "home_office_percentage": 25.0,
    }, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Update User"  # untouched
    assert body["occupation_type"] == "content creator"
    assert body["tin"] == "12345678-0001"
    assert body["has_home_office"] is True
    assert body["home_office_percentage"] == 25.0


def test_patch_me_rejects_invalid_tax_year(client):
    headers = _register_and_get_headers(client, "update-user2@example.com")
    response = client.patch("/auth/me", json={"tax_year": "abcd"}, headers=headers)
    assert response.status_code == 422


def test_patch_me_rejects_home_office_percentage_out_of_range(client):
    headers = _register_and_get_headers(client, "update-user3@example.com")
    response = client.patch("/auth/me", json={"home_office_percentage": 150}, headers=headers)
    assert response.status_code == 422


def test_patch_me_requires_auth(client):
    response = client.patch("/auth/me", json={"name": "Nope"})
    assert response.status_code == 401

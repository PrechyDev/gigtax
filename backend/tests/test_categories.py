def _auth_header(client, email="categories-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Categories User", "email": email, "password": "Supersecret123!",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_list_categories_returns_the_full_seeded_taxonomy(client):
    headers = _auth_header(client)
    response = client.get("/categories", headers=headers)
    assert response.status_code == 200
    slugs = {c["developer_slug"] for c in response.json()}
    assert "freelance_gig_fees" in slugs
    assert "relief_residential_rent" in slugs
    assert "asset_computer_equipment" in slugs


def test_list_categories_requires_auth(client):
    response = client.get("/categories")
    assert response.status_code == 401

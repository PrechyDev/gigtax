def _auth_header(client, email="filing-guidance-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Filing Guidance User", "email": email, "password": "Supersecret123!",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_known_state_returns_its_named_portal(client):
    headers = _auth_header(client)
    response = client.get("/filing-guidance", params={"state": "Lagos"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["state"] == "Lagos"
    assert body["portal_name"] == "LIRS eTax"


def test_unlisted_state_falls_back_to_generic_guidance(client):
    headers = _auth_header(client, "filing-guidance-user2@example.com")
    response = client.get("/filing-guidance", params={"state": "Kwara"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["portal_name"] is None
    assert "State Internal Revenue Service" in body["note"]


def test_missing_state_falls_back_to_generic_guidance(client):
    headers = _auth_header(client, "filing-guidance-user3@example.com")
    response = client.get("/filing-guidance", headers=headers)
    assert response.status_code == 200
    assert response.json()["portal_name"] is None


def test_filing_guidance_requires_auth(client):
    response = client.get("/filing-guidance", params={"state": "Lagos"})
    assert response.status_code == 401

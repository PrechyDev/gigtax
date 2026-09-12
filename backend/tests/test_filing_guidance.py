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
    assert body["portal_url"] == "https://etax.lirs.net"


def test_state_with_no_confirmed_portal_has_no_url(client):
    """Ogun has no independently confirmed live portal (see docs/filing_guidance/ogun.md)
    — portal_url must stay null rather than link somewhere unverified.
    """
    headers = _auth_header(client, "filing-guidance-user4@example.com")
    response = client.get("/filing-guidance", params={"state": "Ogun"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["portal_name"] == "OGIRS"
    assert body["portal_url"] is None


def test_unlisted_state_falls_back_to_generic_guidance(client):
    headers = _auth_header(client, "filing-guidance-user2@example.com")
    response = client.get("/filing-guidance", params={"state": "Kwara"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["portal_name"] is None
    assert "State Internal Revenue Service" in body["note"]
    assert body["guide_markdown"] is None


def test_known_state_includes_full_markdown_walkthrough(client):
    headers = _auth_header(client, "filing-guidance-user5@example.com")
    response = client.get("/filing-guidance", params={"state": "Lagos"}, headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["guide_markdown"] is not None
    assert "LIRS" in body["guide_markdown"]
    assert "Filing Deadline" in body["guide_markdown"]


def test_missing_state_falls_back_to_generic_guidance(client):
    headers = _auth_header(client, "filing-guidance-user3@example.com")
    response = client.get("/filing-guidance", headers=headers)
    assert response.status_code == 200
    assert response.json()["portal_name"] is None


def test_filing_guidance_requires_auth(client):
    response = client.get("/filing-guidance", params={"state": "Lagos"})
    assert response.status_code == 401

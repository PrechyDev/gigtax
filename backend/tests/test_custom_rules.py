def _auth_header(client, email="rules-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Rules User", "email": email, "password": "Supersecret123!",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_and_list_custom_rule(client):
    headers = _auth_header(client)
    create_response = client.post("/custom-rules", json={
        "keyword_pattern": "UBER",
        "assigned_category": "exp_travel",
    }, headers=headers)
    assert create_response.status_code == 201

    list_response = client.get("/custom-rules", headers=headers)
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    assert list_response.json()[0]["keyword_pattern"] == "UBER"


def test_delete_custom_rule(client):
    headers = _auth_header(client, "rules-user2@example.com")
    create_response = client.post("/custom-rules", json={
        "keyword_pattern": "NETFLIX",
        "assigned_category": "exp_software_subscriptions",
    }, headers=headers)
    rule_id = create_response.json()["rule_id"]

    delete_response = client.delete(f"/custom-rules/{rule_id}", headers=headers)
    assert delete_response.status_code == 204

    assert client.get("/custom-rules", headers=headers).json() == []


def test_custom_rules_scoped_per_user(client):
    headers_a = _auth_header(client, "rules-a@example.com")
    headers_b = _auth_header(client, "rules-b@example.com")

    client.post("/custom-rules", json={"keyword_pattern": "X", "assigned_category": "y"}, headers=headers_a)

    assert client.get("/custom-rules", headers=headers_b).json() == []

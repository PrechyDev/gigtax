import json
from unittest.mock import MagicMock, patch


def _auth_header(client, email="advisor-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Advisor User", "email": email, "password": "supersecret123",
    })
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _fake_chunk(source_title="Nigeria Tax Act 2025", citation="p.30", content="Rent relief is 20% of annual rent, capped at N500,000."):
    chunk = MagicMock()
    chunk.source_title = source_title
    chunk.citation = citation
    chunk.content = content
    return chunk


@patch("modules.advisory.rag_advisor.llm_service.generate_text")
@patch("modules.advisory.rag_advisor.retrieve_relevant_chunks")
def test_query_advisor_returns_answer_with_real_citations(mock_retrieve, mock_generate_text, client, db_session):
    from models.advisory import AIAdvisoryQuery

    mock_retrieve.return_value = [_fake_chunk()]
    mock_generate_text.return_value = "Rent relief is 20% of your annual rent, capped at N500,000."
    headers = _auth_header(client)

    response = client.post("/advisory/query", json={
        "question": "How much rent relief can I claim?",
    }, headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert "500,000" in body["answer"]
    assert body["sources"] == ["Nigeria Tax Act 2025 (p.30)"]

    logged = db_session.query(AIAdvisoryQuery).first()
    assert logged.query_text == "How much rent relief can I claim?"
    assert json.loads(logged.retrieved_sources) == ["Nigeria Tax Act 2025 (p.30)"]


@patch("modules.advisory.rag_advisor.llm_service.generate_text")
@patch("modules.advisory.rag_advisor.retrieve_relevant_chunks")
def test_advisor_grounds_the_prompt_in_retrieved_chunks(mock_retrieve, mock_generate_text, client):
    mock_retrieve.return_value = [_fake_chunk(citation="p.42", content="Some retrieved statutory text.")]
    mock_generate_text.return_value = "some answer"
    headers = _auth_header(client, "advisor-user2@example.com")

    client.post("/advisory/query", json={"question": "What are the tax bands?"}, headers=headers)

    _, kwargs = mock_generate_text.call_args
    assert "Some retrieved statutory text." in kwargs["system_prompt"]
    assert "p.42" in kwargs["system_prompt"]


@patch("modules.advisory.rag_advisor.retrieve_relevant_chunks")
def test_advisor_handles_an_empty_knowledge_base_gracefully(mock_retrieve, client):
    mock_retrieve.return_value = []
    headers = _auth_header(client, "advisor-user3@example.com")

    response = client.post("/advisory/query", json={"question": "Anything?"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["sources"] == []
    assert "consult a licensed tax professional" in response.json()["answer"]


def test_advisory_requires_auth(client):
    response = client.post("/advisory/query", json={"question": "Hi"})
    assert response.status_code == 401


def test_advisory_rejects_empty_question(client):
    headers = _auth_header(client, "advisor-user4@example.com")
    response = client.post("/advisory/query", json={"question": ""}, headers=headers)
    assert response.status_code == 422

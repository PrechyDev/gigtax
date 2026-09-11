import json
from unittest.mock import MagicMock, patch


def _auth_header(client, email="advisor-user@example.com"):
    response = client.post("/auth/register", json={
        "name": "Advisor User", "email": email, "password": "Supersecret123!",
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


@patch("modules.advisory.rag_advisor.llm_service.generate_text")
@patch("modules.advisory.rag_advisor.retrieve_relevant_chunks")
def test_advisor_prompt_includes_the_apps_own_category_rules(mock_retrieve, mock_generate_text, client):
    # Regression: the advisor used to only know the raw statute text, so a question the
    # app's own taxonomy already answers (which capital-allowance class a laptop is)
    # got deflected to "consult a professional" instead of a concrete answer.
    mock_retrieve.return_value = [_fake_chunk(citation="p.99", content="Some statutory text about capital allowances.")]
    mock_generate_text.return_value = "some answer"
    headers = _auth_header(client, "advisor-user13@example.com")

    client.post("/advisory/query", json={"question": "What class is a laptop?"}, headers=headers)

    system_prompt = mock_generate_text.call_args.kwargs["system_prompt"]
    assert "THIS APP'S OWN CATEGORY RULES" in system_prompt
    assert "Computers, Cameras & Equipment is Class 2" in system_prompt


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


@patch("modules.advisory.rag_advisor.llm_service.generate_text")
@patch("modules.advisory.rag_advisor.retrieve_relevant_chunks")
def test_bare_follow_up_retrieval_is_grounded_by_prior_question(mock_retrieve, mock_generate_text, client):
    # Regression test: "is it capped?" alone has no keywords to retrieve well against —
    # the prior turn's topic must be folded into what gets embedded for retrieval.
    mock_retrieve.return_value = [_fake_chunk()]
    headers = _auth_header(client, "advisor-user9@example.com")

    mock_generate_text.return_value = "Rent relief is 20%, capped at N500,000."
    first = client.post("/advisory/query", json={"question": "How much rent relief can I claim?"}, headers=headers)
    session_id = first.json()["session_id"]

    mock_generate_text.return_value = "Yes, capped at N500,000."
    client.post("/advisory/query", json={"question": "Is it capped?", "session_id": session_id}, headers=headers)

    retrieval_query = mock_retrieve.call_args.args[1]
    assert "How much rent relief can I claim?" in retrieval_query
    assert "Is it capped?" in retrieval_query


@patch("modules.advisory.rag_advisor.llm_service.generate_text")
@patch("modules.advisory.rag_advisor.retrieve_relevant_chunks")
def test_first_message_gets_a_new_session_id_and_no_history(mock_retrieve, mock_generate_text, client):
    mock_retrieve.return_value = [_fake_chunk()]
    mock_generate_text.return_value = "some answer"
    headers = _auth_header(client, "advisor-user5@example.com")

    response = client.post("/advisory/query", json={"question": "First question"}, headers=headers)

    assert response.status_code == 200
    assert response.json()["session_id"]  # a session_id is always issued
    kwargs = mock_generate_text.call_args.kwargs
    assert kwargs["history"] == []


@patch("modules.advisory.rag_advisor.llm_service.generate_text")
@patch("modules.advisory.rag_advisor.retrieve_relevant_chunks")
def test_follow_up_in_the_same_session_includes_prior_turn_as_history(mock_retrieve, mock_generate_text, client):
    mock_retrieve.return_value = [_fake_chunk()]
    headers = _auth_header(client, "advisor-user6@example.com")

    mock_generate_text.return_value = "Rent relief is 20% capped at N500,000."
    first = client.post("/advisory/query", json={"question": "How much rent relief can I claim?"}, headers=headers)
    session_id = first.json()["session_id"]

    mock_generate_text.return_value = "It's calculated on your annual rent paid."
    client.post("/advisory/query", json={
        "question": "How is that calculated?",
        "session_id": session_id,
    }, headers=headers)

    kwargs = mock_generate_text.call_args.kwargs
    assert kwargs["history"] == [
        {"role": "user", "content": "How much rent relief can I claim?"},
        {"role": "assistant", "content": "Rent relief is 20% capped at N500,000."},
    ]


@patch("modules.advisory.rag_advisor.llm_service.generate_text")
@patch("modules.advisory.rag_advisor.retrieve_relevant_chunks")
def test_a_different_session_has_no_memory_of_another_ones_turns(mock_retrieve, mock_generate_text, client):
    mock_retrieve.return_value = [_fake_chunk()]
    headers = _auth_header(client, "advisor-user7@example.com")

    mock_generate_text.return_value = "answer one"
    client.post("/advisory/query", json={"question": "Question in session A"}, headers=headers)

    mock_generate_text.return_value = "answer two"
    client.post("/advisory/query", json={"question": "Question in session B, no session_id given"}, headers=headers)

    kwargs = mock_generate_text.call_args.kwargs
    assert kwargs["history"] == []  # brand new session — no leakage from session A


@patch("modules.advisory.rag_advisor.llm_service.generate_text")
@patch("modules.advisory.rag_advisor.retrieve_relevant_chunks")
def test_history_is_capped_to_the_most_recent_turns(mock_retrieve, mock_generate_text, client):
    from api.routes.advisory import MAX_HISTORY_TURNS

    mock_retrieve.return_value = [_fake_chunk()]
    headers = _auth_header(client, "advisor-user8@example.com")

    session_id = None
    for i in range(MAX_HISTORY_TURNS + 3):
        mock_generate_text.return_value = f"answer {i}"
        payload = {"question": f"question {i}"}
        if session_id:
            payload["session_id"] = session_id
        response = client.post("/advisory/query", json=payload, headers=headers)
        session_id = response.json()["session_id"]

    kwargs = mock_generate_text.call_args.kwargs
    assert len(kwargs["history"]) == MAX_HISTORY_TURNS * 2  # user+assistant per turn
    # The oldest turns should have been dropped, not the most recent ones.
    assert "question 0" not in [m["content"] for m in kwargs["history"]]


@patch("modules.advisory.rag_advisor.llm_service.generate_text")
@patch("modules.advisory.rag_advisor.retrieve_relevant_chunks")
def test_get_history_returns_turns_in_order_with_sources(mock_retrieve, mock_generate_text, client):
    mock_retrieve.return_value = [_fake_chunk()]
    headers = _auth_header(client, "advisor-user10@example.com")

    mock_generate_text.return_value = "first answer"
    first = client.post("/advisory/query", json={"question": "first question"}, headers=headers)
    session_id = first.json()["session_id"]

    mock_generate_text.return_value = "second answer"
    client.post("/advisory/query", json={"question": "second question", "session_id": session_id}, headers=headers)

    response = client.get("/advisory/history", params={"session_id": session_id}, headers=headers)
    assert response.status_code == 200
    history = response.json()
    assert len(history) == 2
    assert history[0]["query_text"] == "first question"
    assert history[1]["query_text"] == "second question"
    assert history[0]["sources"] == ["Nigeria Tax Act 2025 (p.30)"]


def test_get_history_for_unknown_session_is_empty_not_an_error(client):
    headers = _auth_header(client, "advisor-user11@example.com")
    response = client.get("/advisory/history", params={"session_id": "00000000-0000-0000-0000-000000000000"}, headers=headers)
    assert response.status_code == 200
    assert response.json() == []


def test_get_history_requires_auth(client):
    response = client.get("/advisory/history", params={"session_id": "00000000-0000-0000-0000-000000000000"})
    assert response.status_code == 401


@patch("modules.advisory.rag_advisor.retrieve_relevant_chunks")
def test_advisor_failure_returns_friendly_503_not_a_raw_error(mock_retrieve, client):
    # Simulates an exhausted/failed Gemini call bubbling up from deep inside the RAG
    # pipeline — the client must never see the provider's own error text.
    mock_retrieve.side_effect = RuntimeError("litellm.APIConnectionError: 429 quota exceeded")
    headers = _auth_header(client, "advisor-user12@example.com")

    response = client.post("/advisory/query", json={"question": "Anything?"}, headers=headers)

    assert response.status_code == 503
    assert "429" not in response.json()["detail"]
    assert "temporarily unavailable" in response.json()["detail"]

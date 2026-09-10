from modules.advisory.rag_advisor import RETRIEVAL_CONTEXT_WINDOW, _build_retrieval_query


def test_build_retrieval_query_with_no_history_is_just_the_question():
    assert _build_retrieval_query("How much rent relief can I claim?", None) == "How much rent relief can I claim?"
    assert _build_retrieval_query("How much rent relief can I claim?", []) == "How much rent relief can I claim?"


def test_build_retrieval_query_folds_in_recent_user_turns():
    history = [
        {"role": "user", "content": "How much rent relief can I claim?"},
        {"role": "assistant", "content": "20%, capped at N500,000."},
    ]
    result = _build_retrieval_query("Is it capped?", history)
    assert "How much rent relief can I claim?" in result
    assert "Is it capped?" in result
    assert "20%, capped at N500,000." not in result  # only user turns feed retrieval, not answers


def test_build_retrieval_query_is_bounded_to_the_context_window():
    history = []
    for i in range(RETRIEVAL_CONTEXT_WINDOW + 3):
        history.append({"role": "user", "content": f"question {i}"})
        history.append({"role": "assistant", "content": f"answer {i}"})

    result = _build_retrieval_query("latest question", history)
    assert "question 0" not in result  # oldest dropped
    assert f"question {RETRIEVAL_CONTEXT_WINDOW + 2}" in result  # most recent kept

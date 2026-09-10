from unittest.mock import MagicMock, patch

from modules.advisory.retrieval import retrieve_relevant_chunks


@patch("modules.advisory.retrieval.llm_service.generate_embedding")
def test_retrieve_relevant_chunks_embeds_question_and_queries_top_k(mock_embed):
    mock_embed.return_value = [0.2] * 3072
    mock_db = MagicMock()
    expected_chunks = [MagicMock(), MagicMock()]
    mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = expected_chunks

    result = retrieve_relevant_chunks(mock_db, "How much is rent relief?", k=5)

    mock_embed.assert_called_once_with("How much is rent relief?")
    mock_db.query.return_value.order_by.return_value.limit.assert_called_once_with(5)
    assert result == expected_chunks

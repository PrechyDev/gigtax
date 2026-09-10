from unittest.mock import MagicMock, patch

from modules.advisory.document_ingestion import chunk_page, ingest_document


def test_chunk_page_returns_whole_page_if_under_chunk_size():
    assert chunk_page("short text", chunk_size=2000) == ["short text"]


def test_chunk_page_returns_empty_list_for_blank_page():
    assert chunk_page("   ") == []


def test_chunk_page_splits_long_text_with_overlap():
    text = "A" * 5000
    chunks = chunk_page(text, chunk_size=2000, overlap=200)
    assert len(chunks) == 3
    # Consecutive chunks should overlap by roughly `overlap` characters.
    assert chunks[0][-50:] in chunks[1]


@patch("modules.advisory.document_ingestion.llm_service.generate_embedding")
@patch("modules.advisory.document_ingestion.extract_pdf_pages")
def test_ingest_document_replaces_existing_chunks_for_the_same_title(mock_extract, mock_embed):
    mock_extract.return_value = ["Page one text.", "Page two text."]
    mock_embed.return_value = [0.1] * 3072

    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.delete.return_value = None

    count = ingest_document(mock_db, "fake.pdf", source_title="Nigeria Tax Act 2025")

    assert count == 2  # one chunk per page here since both pages are short
    mock_db.query.return_value.filter.return_value.delete.assert_called_once()
    assert mock_db.add.call_count == 2
    assert mock_db.commit.call_count >= 1  # once after delete, once at the end (below commit_every)

    added_chunks = [call.args[0] for call in mock_db.add.call_args_list]
    assert added_chunks[0].citation == "p.1"
    assert added_chunks[1].citation == "p.2"
    assert added_chunks[0].source_title == "Nigeria Tax Act 2025"

from unittest.mock import patch
import pytest
from modules.ai_categorization.parsing import extract_text, ParsingError

def test_extract_text_unsupported_format():
    with pytest.raises(ParsingError):
        extract_text(b"dummy data", "statement.txt")

def test_extract_text_csv():
    # Simple CSV content
    csv_content = b"Date,Description,Amount\n2023-01-01,Test,100\n"
    result = extract_text(csv_content, "statement.csv")
    assert "2023-01-01" in result
    assert "Test" in result
    assert "100" in result


@patch("services.llm_service.llm_service.generate_vision_text")
def test_extract_text_image_routes_straight_to_gemini_vision(mock_generate_vision_text):
    mock_generate_vision_text.return_value = "2026-01-05 - Sold handmade bags - 15000"

    result = extract_text(b"fake-jpeg-bytes", "handwritten_notes.jpg")

    assert result == "2026-01-05 - Sold handmade bags - 15000"
    mock_generate_vision_text.assert_called_once()
    # No local parsing library should ever see image bytes — confirm the correct
    # image mime type reached the vision call.
    assert mock_generate_vision_text.call_args.kwargs["mime_type"] == "image/jpeg"


@patch("services.llm_service.llm_service.generate_vision_text")
def test_extract_text_png_image_uses_png_mime_type(mock_generate_vision_text):
    mock_generate_vision_text.return_value = "some text"

    extract_text(b"fake-png-bytes", "receipt.png")

    assert mock_generate_vision_text.call_args.kwargs["mime_type"] == "image/png"


@patch("services.llm_service.llm_service.generate_vision_text")
def test_extract_text_image_raises_parsing_error_on_empty_response(mock_generate_vision_text):
    mock_generate_vision_text.return_value = ""

    with pytest.raises(ParsingError):
        extract_text(b"fake-jpeg-bytes", "blank.jpg")

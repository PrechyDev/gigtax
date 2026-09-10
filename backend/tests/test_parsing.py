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

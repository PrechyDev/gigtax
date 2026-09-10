import pytest
from modules.ai_categorization.sanitization import sanitize_text

def test_sanitize_text():
    text_with_pii = "My name is John Doe and I live in New York. My phone number is 555-1234."
    sanitized = sanitize_text(text_with_pii)
    
    # Check that PII is removed
    assert "John Doe" not in sanitized
    assert "New York" not in sanitized
    assert "555-1234" not in sanitized
    
    # Check that placeholders are inserted (e.g., <PERSON>, <LOCATION>)
    assert "<PERSON>" in sanitized or "PERSON" in sanitized

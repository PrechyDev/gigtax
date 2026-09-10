from modules.ai_categorization.sanitization import sanitize_text


def test_sanitize_text_redacts_a_name_only_right_after_an_account_holder_label():
    text = "Account Name: John Doe\nStatement Period: Jan 2026"
    sanitized = sanitize_text(text)

    assert "John Doe" not in sanitized
    assert "PERSON" in sanitized


def test_sanitize_text_redacts_phone_and_email_everywhere_regardless_of_labels():
    text = "Contact us at 0803-555-1234 or support@testbank.com for statement queries."
    sanitized = sanitize_text(text)

    assert "0803-555-1234" not in sanitized
    assert "support@testbank.com" not in sanitized


def test_sanitize_text_preserves_merchant_and_product_names_with_no_header_label():
    """Regression test: a real walkthrough uploaded a short statement PDF with no
    "Account Name"/"Opening Balance"-style header at all. The old position-based split
    silently fell through to scrubbing the entire document (transaction lines included)
    for PERSON entities, mangling ordinary business names into "<PERSON>". None of these
    lines carry an account-holder label, so none of them should be touched at all.
    """
    text = (
        "2026-02-05    Data subscription - Spectranet                  22000   Debit\n"
        "2026-02-14    Canva Pro annual renewal                        55000   Debit\n"
        "2026-02-05    GitHub Pro subscription                         18000   Debit\n"
        "2026-01-05    Payment from Acme Corp - web design project    350000   Credit\n"
    )
    sanitized = sanitize_text(text)

    assert "Data subscription - Spectranet" in sanitized
    assert "Canva Pro annual renewal" in sanitized
    assert "GitHub Pro subscription" in sanitized
    assert "Payment from Acme Corp - web design project" in sanitized


def test_sanitize_text_handles_empty_string():
    assert sanitize_text("") == ""

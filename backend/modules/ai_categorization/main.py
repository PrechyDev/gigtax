from typing import List, Optional
from core.logger import get_logger
from .parsing import extract_text, ParsingError, PasswordRequiredError
from .sanitization import sanitize_text
from .categorization import categorize_transactions
from .schemas import ParsedTransaction

logger = get_logger("ai_categorization.statement_processor")

def process_bank_statement(
    file_bytes: bytes,
    filename: str,
    custom_rules: str,
    predefined_categories: str,
    password: Optional[str] = None,
) -> List[ParsedTransaction]:
    """
    Main entry point for processing a bank statement.
    1. Extracts text from the file (CSV, Excel, PDF, image).
    2. Sanitizes the text by removing PII.
    3. Categorizes the transactions using an LLM and custom rules.

    Returns a list of parsed transactions with categories and confidence levels.

    Deliberately lets `PasswordRequiredError` and `ParsingError` propagate rather than
    swallowing them — callers (e.g. the statements API, handling a multi-file batch)
    need to distinguish "this specific file needs a password" / "this file's parsing
    genuinely failed" from "this file legitimately had zero transactions in it."
    """
    logger.info(f"Starting processing for statement: {filename}")

    logger.info("Extracting text from file...")
    raw_text = extract_text(file_bytes, filename, password=password)

    logger.info("Sanitizing extracted text for PII...")
    sanitized_text = sanitize_text(raw_text)

    logger.info("Categorizing transactions using LLM and custom rules...")
    transactions = categorize_transactions(
        sanitized_text=sanitized_text,
        custom_rules=custom_rules,
        predefined_categories=predefined_categories
    )

    logger.info(f"Successfully processed statement. Found {len(transactions)} transactions.")
    return transactions

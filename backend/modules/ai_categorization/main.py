from typing import List
from core.logger import get_logger
from .parsing import extract_text, ParsingError
from .sanitization import sanitize_text
from .categorization import categorize_transactions
from .schemas import ParsedTransaction

logger = get_logger("ai_categorization.statement_processor")

def process_bank_statement(file_bytes: bytes, filename: str, custom_rules: str, predefined_categories: str) -> List[ParsedTransaction]:
    """
    Main entry point for processing a bank statement.
    1. Extracts text from the file (CSV, Excel, PDF).
    2. Sanitizes the text by removing PII.
    3. Categorizes the transactions using an LLM and custom rules.
    
    Returns a list of parsed transactions with categories and confidence levels.
    """
    logger.info(f"Starting processing for statement: {filename}")
    try:
        # Step 1: Parse the file
        logger.info("Extracting text from file...")
        raw_text = extract_text(file_bytes, filename)
        
        # Step 2: Sanitize PII
        logger.info("Sanitizing extracted text for PII...")
        sanitized_text = sanitize_text(raw_text)
        
        # Step 3: Categorize using LLM
        logger.info("Categorizing transactions using LLM and custom rules...")
        transactions = categorize_transactions(
            sanitized_text=sanitized_text,
            custom_rules=custom_rules,
            predefined_categories=predefined_categories
        )
        
        logger.info(f"Successfully processed statement. Found {len(transactions)} transactions.")
        return transactions
    except ParsingError as e:
        logger.error(f"Failed to process statement (Parsing Error): {e}")
        return []
    except Exception as e:
        logger.exception(f"An unexpected error occurred during statement processing: {e}")
        return []

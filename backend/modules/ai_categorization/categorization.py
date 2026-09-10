from typing import List, Optional
from datetime import date

from modules.ai_categorization.schemas import ParsedTransaction, TransactionExtraction
from core.config import settings
from services.llm_service import llm_service

def categorize_transactions(sanitized_text: str, custom_rules: str, predefined_categories: str, model_name: str | None = None) -> List[ParsedTransaction]:
    """
    Takes sanitized text from a bank statement, applies user rules and categories, 
    and uses an LLM to output a list of categorized transactions.
    """
    prompt = f"""
    You are a financial categorization AI.
    
    Here is a list of sanitized bank transactions:
    {sanitized_text}
    
    Here are the custom rules for categorization:
    {custom_rules}
    
    Here are the predefined categories you must choose from:
    {predefined_categories}
    
    INSTRUCTIONS:
    1. Parse each transaction line.
    2. Extract the date, description, amount. Also extract `merchant_name` (if an Expense) or `income_source` (if an Income).
    3. Apply the custom rules.
    4. Determine the transaction type (Income/Expense).
    5. THE EXPENSE RULE: Categorize personal or non-business expenses (like stamp duty or self-transfers) as 'uncategorized' with a `confidence_score` of 0.0, unless they explicitly fall into an accepted business predefined category. User custom rules override this.
    6. THE GOLDEN RULE (NO OMISSION): You must NEVER ignore or omit personal transactions. You must return ALL transactions in the output, even if they are personal/ignored expenses. Force their `category_slug` to 'uncategorized' and `confidence_score` to 0.0.
    7. For valid business transactions, assign the most appropriate category based on the predefined categories and rules. You MUST use the exact `developer_slug` of the category and output it as `category_slug`.
    8. FALLBACK RULE: If a valid business transaction does not clearly fit into any predefined category, you MUST set the `category_slug` to 'uncategorized' and the `confidence_score` to 0.0.
    9. Estimate your confidence_score (0.0 to 1.0) for the assigned category.
    10. Return the extracted transactions in the specified format.
    """
    
    # Deliberately no try/except here: a failed LLM call must propagate, not come
    # back as "0 transactions found" — that's indistinguishable from a genuinely
    # empty statement. The caller (modules/ai_categorization/main.py's
    # process_bank_statement, and ultimately api/routes/statements.py) is where this
    # gets turned into a proper FAILED status with a friendly message.
    response = llm_service.generate_structured_output(
        prompt=prompt,
        system_prompt="You are a precise financial data extraction API. Be highly deterministic and do not hallucinate.",
        response_model=TransactionExtraction,
        model=model_name
    )
    return response.transactions

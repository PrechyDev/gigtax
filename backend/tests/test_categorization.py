import pytest
from unittest.mock import patch
from modules.ai_categorization.categorization import categorize_transactions
from modules.ai_categorization.schemas import ParsedTransaction, TransactionExtraction

@patch('modules.ai_categorization.categorization.instructor.from_litellm')
def test_categorize_transactions(mock_from_litellm):
    # Setup mock
    mock_client = mock_from_litellm.return_value
    mock_response = TransactionExtraction(
        transactions=[
            ParsedTransaction(
                date="2023-01-01",
                description="Uber Trip",
                amount=-15.00,
                category_slug="exp_software_subscriptions",
                transaction_type="Expense",
                confidence_score=0.95
            )
        ]
    )
    mock_client.chat.completions.create.return_value = mock_response

    # Call function
    sanitized_text = "2023-01-01 Uber Trip $15.00"
    custom_rules = "Ignore personal expenses, map Uber to Travel"
    categories = "Travel, Meals, Office Supplies"
    
    result = categorize_transactions(sanitized_text, custom_rules, categories)
    
    assert len(result) == 1
    assert result[0].description == "Uber Trip"
    assert result[0].category_slug == "exp_software_subscriptions"
    assert result[0].amount == -15.00

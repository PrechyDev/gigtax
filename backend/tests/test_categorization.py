import pytest
from unittest.mock import patch
from modules.ai_categorization.categorization import categorize_transactions
from modules.ai_categorization.schemas import ParsedTransaction, TransactionExtraction

@patch('modules.ai_categorization.categorization.llm_service.generate_structured_output')
def test_categorize_transactions(mock_generate_structured_output):
    # Setup mock — categorize_transactions calls llm_service.generate_structured_output
    # directly (via the llm_service facade), not instructor/litellm at this layer.
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
    mock_generate_structured_output.return_value = mock_response

    # Call function
    sanitized_text = "2023-01-01 Uber Trip $15.00"
    custom_rules = "Ignore personal expenses, map Uber to Travel"
    categories = "Travel, Meals, Office Supplies"
    
    result = categorize_transactions(sanitized_text, custom_rules, categories)
    
    assert len(result) == 1
    assert result[0].description == "Uber Trip"
    assert result[0].category_slug == "exp_software_subscriptions"
    assert result[0].amount == -15.00


@patch('modules.ai_categorization.categorization.llm_service.generate_structured_output')
def test_categorize_transactions_propagates_llm_failures(mock_generate_structured_output):
    # Regression test: this used to be swallowed and return [] — indistinguishable
    # from a genuinely empty statement. It must propagate so the caller can mark the
    # statement FAILED instead of silently "succeeding" with 0 transactions.
    mock_generate_structured_output.side_effect = RuntimeError("litellm.ServiceUnavailableError: 503 high demand")

    with pytest.raises(RuntimeError):
        categorize_transactions("some text", "no rules", "Travel, Meals")

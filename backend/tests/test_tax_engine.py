"""Hand-computed scenarios against the NTA 2025 Fourth Schedule bands and s.30 reliefs.
Pure logic, no DB, no LLM — this is the one module where correctness is the whole point.
"""
from modules.tax_computation.engine import CategorizedTransaction, compute_tax


def _income(amount, tax_treatment="subject_to_progressive_tax"):
    return CategorizedTransaction(amount=amount, classification="Income", category_slug="x", tax_treatment=tax_treatment)


def _expense(amount, deductibility_percentage=100.0):
    return CategorizedTransaction(
        amount=amount, classification="Expense", category_slug="exp_x",
        tax_treatment="100_percent_deductible", deductibility_percentage=deductibility_percentage,
    )


def _relief(amount, slug="relief_pension_voluntary"):
    return CategorizedTransaction(amount=amount, classification="Relief", category_slug=slug, tax_treatment="deductible_relief_capped")


def _asset_purchase(amount):
    # A capital item recorded as a transaction — classification "Asset" so the engine
    # must NOT treat it as a normal 100%-deductible expense.
    return CategorizedTransaction(amount=amount, classification="Asset", category_slug="asset_computer_equipment", tax_treatment="capital_allowance")


def test_income_at_or_below_minimum_wage_is_fully_exempt():
    result = compute_tax([_income(800_000)])
    assert result.minimum_wage_exempt is True
    assert result.net_tax == 0.0


def test_zero_tax_below_first_band_threshold():
    # Above minimum wage but still within the 0% first band.
    result = compute_tax([_income(1_200_000, tax_treatment="subject_to_progressive_tax"), _expense(500_000)])
    assert result.chargeable_income == 700_000
    assert result.net_tax == 0.0
    assert result.minimum_wage_exempt is False


def test_case_spanning_multiple_bands():
    # Chargeable income of 5,000,000: 800k@0% + 2.2M@15% + 2M@18% = 0 + 330,000 + 360,000
    result = compute_tax([_income(5_000_000, tax_treatment="subject_to_progressive_tax")])
    assert result.chargeable_income == 5_000_000
    assert result.net_tax == 690_000


def test_rent_relief_is_capped_at_500k():
    # 20% of 4,000,000 rent = 800,000, capped at 500,000.
    result = compute_tax([
        _income(10_000_000, tax_treatment="subject_to_progressive_tax"),
        _relief(4_000_000, slug="relief_residential_rent"),
    ])
    assert result.total_reliefs == 500_000
    assert result.chargeable_income == 9_500_000


def test_uncapped_relief_counts_in_full():
    result = compute_tax([
        _income(2_000_000, tax_treatment="subject_to_progressive_tax"),
        _relief(200_000, slug="relief_pension_voluntary"),
    ])
    assert result.total_reliefs == 200_000
    assert result.chargeable_income == 1_800_000


def test_excluded_income_treatments_do_not_count_toward_total_income():
    result = compute_tax([
        _income(1_000_000, tax_treatment="excluded_from_progressive_tax"),  # already-PAYE-taxed salary
        _income(500_000, tax_treatment="non_taxable"),  # e.g. sale of a personal item
        _income(3_000_000, tax_treatment="subject_to_progressive_tax"),
    ])
    assert result.total_income == 3_000_000


def test_deductibility_percentage_is_applied_for_home_office_expenses():
    result = compute_tax([
        _income(3_000_000, tax_treatment="subject_to_progressive_tax"),
        _expense(100_000, deductibility_percentage=20.0),
    ])
    assert result.total_deductions == 20_000


def test_chargeable_income_never_goes_negative():
    result = compute_tax([
        _income(1_500_000, tax_treatment="subject_to_progressive_tax"),
        _expense(1_000_000),
        _relief(1_000_000),
    ])
    assert result.chargeable_income == 0.0
    assert result.net_tax == 0.0


def test_band_breakdown_only_lists_bands_actually_reached():
    result = compute_tax([_income(2_000_000, tax_treatment="subject_to_progressive_tax")])
    # Chargeable income 2,000,000 only reaches the first two bands (0% and 15%).
    assert len(result.band_breakdown) == 2
    assert result.band_breakdown[0].rate == 0.0
    assert result.band_breakdown[1].rate == 0.15


def test_a_capital_asset_transaction_is_not_treated_as_a_full_deduction():
    # A laptop bought for 500,000 must NOT reduce total_deductions by 500,000 —
    # only its capital allowance (computed separately, passed in) should count.
    result = compute_tax([
        _income(3_000_000, tax_treatment="subject_to_progressive_tax"),
        _asset_purchase(500_000),
    ])
    assert result.total_deductions == 0.0
    assert result.chargeable_income == 3_000_000


def test_capital_allowances_reduce_chargeable_income_like_a_deduction():
    result = compute_tax(
        [_income(3_000_000, tax_treatment="subject_to_progressive_tax")],
        capital_allowances_this_year=100_000,
    )
    assert result.total_capital_allowances == 100_000
    assert result.chargeable_income == 2_900_000

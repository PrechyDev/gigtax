from modules.tax_computation.capital_allowances import (
    CapitalAsset,
    allowance_for_year,
    total_capital_allowances,
    useful_life_years,
)


def test_class_2_asset_depreciates_over_5_years_at_20_percent():
    # First Schedule Class 2 (plant/equipment/furniture) = 20% per annum.
    asset = CapitalAsset(cost=300_000, asset_class="class_2", acquired_year=2026)
    assert useful_life_years("class_2") == 5
    assert allowance_for_year(asset, 2026) == 60_000
    assert allowance_for_year(asset, 2027) == 60_000
    assert allowance_for_year(asset, 2030) == 60_000  # 5th year, still active
    assert allowance_for_year(asset, 2031) == 0  # fully written down


def test_class_3_asset_depreciates_over_4_years_at_25_percent():
    asset = CapitalAsset(cost=400_000, asset_class="class_3", acquired_year=2026)
    assert useful_life_years("class_3") == 4
    assert allowance_for_year(asset, 2029) == 100_000  # 4th year
    assert allowance_for_year(asset, 2030) == 0


def test_class_1_asset_depreciates_over_10_years_at_10_percent():
    asset = CapitalAsset(cost=1_000_000, asset_class="class_1", acquired_year=2020)
    assert useful_life_years("class_1") == 10
    assert allowance_for_year(asset, 2029) == 100_000  # 10th year
    assert allowance_for_year(asset, 2030) == 0


def test_no_allowance_before_acquisition_year():
    asset = CapitalAsset(cost=300_000, asset_class="class_2", acquired_year=2026)
    assert allowance_for_year(asset, 2025) == 0


def test_disposal_stops_further_allowance_from_disposal_year_onward():
    asset = CapitalAsset(cost=300_000, asset_class="class_2", acquired_year=2026, disposed_year=2028)
    assert allowance_for_year(asset, 2027) == 60_000  # last full year before disposal
    assert allowance_for_year(asset, 2028) == 0  # disposed this year — no allowance
    assert allowance_for_year(asset, 2029) == 0


def test_total_capital_allowances_sums_across_multiple_assets_and_skips_inactive_ones():
    assets = [
        CapitalAsset(cost=300_000, asset_class="class_2", acquired_year=2026),  # 60,000/yr, active
        CapitalAsset(cost=400_000, asset_class="class_3", acquired_year=2024),  # 100,000/yr, still in its 3rd of 4 years
        CapitalAsset(cost=100_000, asset_class="class_2", acquired_year=2027),  # not yet acquired in 2026 -> 0
    ]
    assert total_capital_allowances(assets, 2026) == 160_000

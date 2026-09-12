"""Capital allowance (depreciation) computation for capital assets, per NTA 2025's
First Schedule Table I. Pure module, same spirit as engine.py — no DB, no HTTP.

A capital asset (laptop, camera, equipment, vehicle) is NOT a normal 100%-deductible
expense in its purchase year. Instead, a fixed percentage of its original cost is
deductible each year (straight-line) for a fixed number of years, then it drops out
of the deduction pool entirely (fully written down, or disposed of early).
"""
from dataclasses import dataclass

# First Schedule Table I rates. Real freelancer capital purchases (laptops, cameras,
# general equipment) fall under Class 2; vehicles and other capital expenditure under
# Class 3. Class 1 (buildings, heavy transport) is included for completeness even
# though it's unlikely for this project's target users.
ASSET_CLASS_RATES: dict[str, float] = {
    "class_1": 0.10,  # buildings, agriculture, masts, intangibles, heavy transport
    "class_2": 0.20,  # plant/equipment, furniture, mining, other equipment
    "class_3": 0.25,  # motor vehicles, software, other capital expenditure
}


@dataclass
class CapitalAsset:
    """The minimal, ORM-independent shape the allowance calculation needs."""
    cost: float
    asset_class: str
    acquired_year: int
    disposed_year: int | None = None


def useful_life_years(asset_class: str) -> int:
    """How many years of straight-line allowance fully write down this class."""
    return round(1 / ASSET_CLASS_RATES[asset_class])


def allowance_for_year(asset: CapitalAsset, tax_year: int) -> float:
    if tax_year < asset.acquired_year:
        return 0.0
    if asset.disposed_year is not None and tax_year >= asset.disposed_year:
        return 0.0

    years_elapsed = tax_year - asset.acquired_year
    if years_elapsed >= useful_life_years(asset.asset_class):
        return 0.0

    return asset.cost * ASSET_CLASS_RATES[asset.asset_class]


def total_capital_allowances(assets: list[CapitalAsset], tax_year: int) -> float:
    return sum(allowance_for_year(asset, tax_year) for asset in assets)


def cumulative_allowance_claimed(asset: CapitalAsset, as_of_year: int) -> float:
    """Total allowance claimed across every year from acquisition through as_of_year
    (inclusive). Just a sum over allowance_for_year, so disposal / full-write-down /
    not-yet-acquired cutoffs are automatically respected without duplicating them.
    """
    if as_of_year < asset.acquired_year:
        return 0.0
    return sum(allowance_for_year(asset, year) for year in range(asset.acquired_year, as_of_year + 1))

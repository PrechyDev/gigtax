from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models.annual_tax_profile import AnnualTaxProfile
from models.tax import TaxComputation
from models.user import User
from modules.tax_computation.engine import NATIONAL_MINIMUM_WAGE_ANNUAL, apply_fourth_schedule, compute_tax
from modules.tax_computation.loader import (
    load_capital_allowance_items,
    load_capital_allowances_for_year,
    load_categorized_transactions,
)
from modules.tax_computation.reporting_helpers import build_itemized_breakdown
from schemas.annual_tax_profile import AnnualTaxProfileOut, AnnualTaxProfileUpdate
from schemas.tax import TaxComputationOut

router = APIRouter(prefix="/tax-computations", tags=["tax-computations"])

EMPTY_ITEMS = {
    "income_items": [],
    "deduction_items": [],
    "relief_items": [],
    "capital_allowance_items": [],
}


def _get_or_create_computation(db: Session, user: User, tax_year: str) -> TaxComputation:
    computation = (
        db.query(TaxComputation)
        .filter(TaxComputation.user_id == user.user_id, TaxComputation.tax_year == tax_year)
        .first()
    )
    if computation is None:
        computation = TaxComputation(user_id=user.user_id, tax_year=tax_year)
        db.add(computation)
    return computation


@router.post("/{tax_year}/compute", response_model=TaxComputationOut)
def compute_tax_for_year(
    tax_year: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    transactions = load_categorized_transactions(db, current_user, tax_year)
    capital_allowances = load_capital_allowances_for_year(db, current_user.user_id, tax_year)
    capital_allowance_items = load_capital_allowance_items(db, current_user.user_id, tax_year)
    result = compute_tax(transactions, capital_allowances_this_year=capital_allowances)
    items = build_itemized_breakdown(db, transactions, capital_allowance_items)

    computation = _get_or_create_computation(db, current_user, tax_year)
    computation.total_income = result.total_income
    computation.total_deductions = result.total_deductions
    computation.total_reliefs = result.total_reliefs
    computation.total_capital_allowances = result.total_capital_allowances
    computation.taxable_income = result.chargeable_income
    computation.estimated_tax_owed = result.net_tax
    computation.items = items
    db.commit()
    db.refresh(computation)

    return TaxComputationOut(
        tax_year=tax_year,
        total_income=computation.total_income,
        total_deductions=computation.total_deductions,
        total_reliefs=computation.total_reliefs,
        total_capital_allowances=computation.total_capital_allowances,
        taxable_income=computation.taxable_income,
        estimated_tax_owed=computation.estimated_tax_owed,
        minimum_wage_exempt=result.minimum_wage_exempt,
        band_breakdown=[b.__dict__ for b in result.band_breakdown],
        **items,
        last_updated=computation.last_updated,
    )


@router.get("/{tax_year}/annual-profile", response_model=AnnualTaxProfileOut)
def get_annual_tax_profile(
    tax_year: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Rent paid and home-office claim for this specific year — see
    models/annual_tax_profile.py for why these can't be a single static profile field.
    Returns a blank/default shape (not a 404) when nothing's been saved for this year
    yet — there's nothing wrong with a year having no rent/home-office entry, that's
    just its starting state.
    """
    profile = (
        db.query(AnnualTaxProfile)
        .filter(AnnualTaxProfile.user_id == current_user.user_id, AnnualTaxProfile.tax_year == tax_year)
        .first()
    )
    if profile is None:
        return AnnualTaxProfileOut(
            tax_year=tax_year, annual_rent_paid=None, has_home_office=False, home_office_percentage=0.0
        )
    return AnnualTaxProfileOut(
        tax_year=tax_year,
        annual_rent_paid=profile.annual_rent_paid,
        has_home_office=profile.has_home_office,
        home_office_percentage=profile.home_office_percentage,
    )


@router.put("/{tax_year}/annual-profile", response_model=AnnualTaxProfileOut)
def upsert_annual_tax_profile(
    tax_year: str,
    payload: AnnualTaxProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    profile = (
        db.query(AnnualTaxProfile)
        .filter(AnnualTaxProfile.user_id == current_user.user_id, AnnualTaxProfile.tax_year == tax_year)
        .first()
    )
    if profile is None:
        profile = AnnualTaxProfile(user_id=current_user.user_id, tax_year=tax_year)
        db.add(profile)

    profile.annual_rent_paid = payload.annual_rent_paid
    profile.has_home_office = payload.has_home_office
    profile.home_office_percentage = payload.home_office_percentage
    db.commit()
    db.refresh(profile)

    return AnnualTaxProfileOut(
        tax_year=tax_year,
        annual_rent_paid=profile.annual_rent_paid,
        has_home_office=profile.has_home_office,
        home_office_percentage=profile.home_office_percentage,
    )


@router.get("/{tax_year}", response_model=TaxComputationOut)
def get_tax_computation(
    tax_year: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    computation = (
        db.query(TaxComputation)
        .filter(TaxComputation.user_id == current_user.user_id, TaxComputation.tax_year == tax_year)
        .first()
    )
    if computation is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No tax computation for {tax_year} yet — POST to /tax-computations/{tax_year}/compute first.",
        )

    minimum_wage_exempt = computation.total_income <= NATIONAL_MINIMUM_WAGE_ANNUAL
    _, band_breakdown = (0.0, []) if minimum_wage_exempt else apply_fourth_schedule(computation.taxable_income)
    # Rows computed before the itemized breakdown was introduced have items=None.
    items = computation.items or EMPTY_ITEMS

    return TaxComputationOut(
        tax_year=tax_year,
        total_income=computation.total_income,
        total_deductions=computation.total_deductions,
        total_reliefs=computation.total_reliefs,
        total_capital_allowances=computation.total_capital_allowances,
        taxable_income=computation.taxable_income,
        estimated_tax_owed=computation.estimated_tax_owed,
        minimum_wage_exempt=minimum_wage_exempt,
        band_breakdown=[b.__dict__ for b in band_breakdown],
        **items,
        last_updated=computation.last_updated,
    )

from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.deps import get_current_user
from db.session import get_db
from models.asset import Asset
from models.user import User
from modules.tax_computation.capital_allowances import CapitalAsset, allowance_for_year
from schemas.asset import AssetDisposeUpdate, AssetOut

router = APIRouter(prefix="/assets", tags=["assets"])


def _to_out(asset: Asset, tax_year: int) -> AssetOut:
    capital_asset = CapitalAsset(
        cost=asset.cost,
        asset_class=asset.asset_class,
        acquired_year=asset.purchase_date.year,
        disposed_year=asset.disposed_date.year if (asset.disposed and asset.disposed_date) else None,
    )
    return AssetOut(
        asset_id=asset.asset_id,
        transaction_id=asset.transaction_id,
        description=asset.description,
        cost=asset.cost,
        purchase_date=asset.purchase_date,
        asset_class=asset.asset_class,
        disposed=asset.disposed,
        disposed_date=asset.disposed_date,
        current_year_allowance=allowance_for_year(capital_asset, tax_year),
    )


@router.get("", response_model=list[AssetOut])
def list_assets(
    tax_year: int | None = Query(default=None, description="Defaults to the current calendar year"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists every capital asset the user owns (regardless of which tax year it was
    purchased in — depreciation spans years), each showing its computed allowance for
    the requested (or current) year.
    """
    effective_year = tax_year or datetime.now(timezone.utc).year
    assets = db.query(Asset).filter(Asset.user_id == current_user.user_id).order_by(Asset.purchase_date).all()
    return [_to_out(asset, effective_year) for asset in assets]


@router.patch("/{asset_id}/dispose", response_model=AssetOut)
def dispose_asset(
    asset_id: UUID,
    payload: AssetDisposeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Marks an asset disposed — from `disposed_date`'s year onward it stops
    contributing any further capital allowance (see capital_allowances.py).
    """
    asset = (
        db.query(Asset)
        .filter(Asset.asset_id == asset_id, Asset.user_id == current_user.user_id)
        .first()
    )
    if asset is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found")

    asset.disposed = True
    asset.disposed_date = payload.disposed_date
    db.commit()
    db.refresh(asset)
    return _to_out(asset, datetime.now(timezone.utc).year)

import json
import os

from fastapi import APIRouter, Depends, Query

from api.deps import get_current_user
from models.user import User
from schemas.filing_guidance import FilingGuidanceOut

router = APIRouter(prefix="/filing-guidance", tags=["filing-guidance"])

# Plain, hand-editable JSON rather than a DB table — see the file's own _comment for
# why portal_url is always null (never guessing a government portal's address).
DATA_FILE = os.path.join(os.path.dirname(__file__), "..", "..", "db", "seed_data", "state_filing_portals.json")

with open(DATA_FILE, "r", encoding="utf-8") as f:
    _PORTALS_BY_STATE = json.load(f)


@router.get("", response_model=FilingGuidanceOut)
def get_filing_guidance(
    state: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
):
    entry = _PORTALS_BY_STATE.get(state) if state else None
    if entry is None:
        entry = _PORTALS_BY_STATE["default"]
    return FilingGuidanceOut(state=state, **entry)

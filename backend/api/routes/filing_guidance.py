import json
import os

from fastapi import APIRouter, Depends, Query

from api.deps import get_current_user
from models.user import User
from schemas.filing_guidance import FilingGuidanceOut

router = APIRouter(prefix="/filing-guidance", tags=["filing-guidance"])

# Plain, hand-editable JSON rather than a DB table — see the file's own _comment: a
# state only gets a portal_url once someone has directly fetched and visually
# confirmed it, never guessed from a title or search result. States with no
# confirmed portal keep portal_url null rather than risk serving a stale or wrong
# link with false confidence.
SEED_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "db", "seed_data")
DATA_FILE = os.path.join(SEED_DATA_DIR, "state_filing_portals.json")
GUIDES_DIR = os.path.join(SEED_DATA_DIR, "filing_guides")

with open(DATA_FILE, "r", encoding="utf-8") as f:
    _PORTALS_BY_STATE = json.load(f)


def _load_guide_markdown(guide_file: str | None) -> str | None:
    if not guide_file:
        return None
    path = os.path.join(GUIDES_DIR, guide_file)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


# Read once at import time, same as the JSON above — these are static files bundled
# with the deploy, not something that changes without a code change. Skips
# "_comment", the JSON file's own top-level documentation string, not a state entry.
_GUIDE_MARKDOWN_BY_STATE = {
    state: _load_guide_markdown(entry.get("guide_file"))
    for state, entry in _PORTALS_BY_STATE.items()
    if isinstance(entry, dict)
}


@router.get("", response_model=FilingGuidanceOut)
def get_filing_guidance(
    state: str | None = Query(default=None),
    current_user: User = Depends(get_current_user),
):
    key = state if state in _PORTALS_BY_STATE else "default"
    entry = _PORTALS_BY_STATE[key]
    return FilingGuidanceOut(
        state=state,
        portal_name=entry["portal_name"],
        portal_url=entry["portal_url"],
        note=entry["note"],
        guide_markdown=_GUIDE_MARKDOWN_BY_STATE.get(key),
    )

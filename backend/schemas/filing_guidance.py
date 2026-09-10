from pydantic import BaseModel


class FilingGuidanceOut(BaseModel):
    state: str | None
    portal_name: str | None
    portal_url: str | None
    note: str

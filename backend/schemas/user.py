from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator

# Must mirror the DB column lengths in models/user.py — validated here so a too-long
# value gets a clean 422 instead of surfacing as a raw 500 from a DB constraint.
NAME_MAX_LENGTH = 100
OCCUPATION_MAX_LENGTH = 50
STATE_MAX_LENGTH = 50
TIN_MAX_LENGTH = 20


def _validate_tax_year(value: str | None) -> str | None:
    if value is not None and not (len(value) == 4 and value.isdigit()):
        raise ValueError("tax_year must be a 4-digit year, e.g. '2026'")
    return value


class UserRegister(BaseModel):
    name: str = Field(max_length=NAME_MAX_LENGTH)
    email: EmailStr
    password: str = Field(min_length=8)
    occupation_type: str | None = Field(default=None, max_length=OCCUPATION_MAX_LENGTH)
    state_residence: str | None = Field(default=None, max_length=STATE_MAX_LENGTH)
    tax_year: str | None = None

    @field_validator("tax_year")
    @classmethod
    def _check_tax_year(cls, value: str | None) -> str | None:
        return _validate_tax_year(value)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserUpdate(BaseModel):
    """All fields optional — PATCH semantics, only supplied fields are changed."""
    name: str | None = Field(default=None, max_length=NAME_MAX_LENGTH)
    occupation_type: str | None = Field(default=None, max_length=OCCUPATION_MAX_LENGTH)
    state_residence: str | None = Field(default=None, max_length=STATE_MAX_LENGTH)
    tax_year: str | None = None
    tin: str | None = Field(default=None, max_length=TIN_MAX_LENGTH)
    has_home_office: bool | None = None
    home_office_percentage: float | None = Field(default=None, ge=0, le=100)

    @field_validator("tax_year")
    @classmethod
    def _check_tax_year(cls, value: str | None) -> str | None:
        return _validate_tax_year(value)


class UserProfile(BaseModel):
    user_id: UUID
    name: str
    email: EmailStr
    occupation_type: str | None
    state_residence: str | None
    tax_year: str | None
    tin: str | None
    has_home_office: bool
    home_office_percentage: float
    google_drive_connected: bool

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

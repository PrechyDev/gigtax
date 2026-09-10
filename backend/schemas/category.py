from uuid import UUID

from pydantic import BaseModel


class CategoryOut(BaseModel):
    category_id: UUID
    classification: str
    category_name: str
    developer_slug: str
    description: str | None
    tax_treatment: str | None
    asset_class: str | None

    model_config = {"from_attributes": True}

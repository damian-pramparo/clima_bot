from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class FieldRead(BaseModel):
    id: UUID
    user_id: UUID
    name: str
    latitude: Decimal
    longitude: Decimal

    model_config = {"from_attributes": True}

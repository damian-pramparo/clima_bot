from uuid import UUID

from pydantic import BaseModel


class UserRead(BaseModel):
    id: UUID
    phone_number: str
    name: str

    model_config = {"from_attributes": True}

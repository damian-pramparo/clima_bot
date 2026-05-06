from datetime import datetime, timezone
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.models.enums import WeatherEventType


class WeatherEventCreate(BaseModel):
    field_id: UUID
    event_date: datetime
    event_type: WeatherEventType
    probability: int = Field(ge=0, le=100)
    source: str = "manual"

    @field_validator("event_date")
    @classmethod
    def ensure_timezone(cls, value: datetime) -> datetime:
        """Assume UTC when an incoming event datetime has no timezone."""
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class WeatherEventRead(BaseModel):
    id: UUID
    field_id: UUID
    event_date: datetime
    event_type: WeatherEventType
    probability: int
    source: str

    model_config = {"from_attributes": True}

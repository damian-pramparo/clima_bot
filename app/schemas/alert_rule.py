from __future__ import annotations

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import WeatherEventType


class AlertRuleCreate(BaseModel):
    user_id: UUID
    field_id: UUID
    event_type: WeatherEventType
    threshold: int = Field(ge=0, le=100)
    active: bool = True


class AlertRuleUpdate(BaseModel):
    threshold: Optional[int] = Field(default=None, ge=0, le=100)
    active: Optional[bool] = None


class AlertRuleRead(BaseModel):
    id: UUID
    user_id: UUID
    field_id: UUID
    event_type: WeatherEventType
    threshold: int
    active: bool

    model_config = {"from_attributes": True}

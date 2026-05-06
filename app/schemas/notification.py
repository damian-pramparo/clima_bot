from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import NotificationStatus


class NotificationRead(BaseModel):
    id: UUID
    user_id: UUID
    field_id: UUID
    alert_rule_id: UUID
    weather_event_id: UUID
    status: NotificationStatus
    message: str
    sent_at: datetime
    read_at: Optional[datetime]

    model_config = {"from_attributes": True}

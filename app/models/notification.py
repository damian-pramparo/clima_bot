from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import NotificationStatus


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        UniqueConstraint("alert_rule_id", "weather_event_id", name="uq_notification_rule_weather_event"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    field_id: Mapped[UUID] = mapped_column(ForeignKey("fields.id", ondelete="CASCADE"), index=True)
    alert_rule_id: Mapped[UUID] = mapped_column(ForeignKey("alert_rules.id", ondelete="CASCADE"), index=True)
    weather_event_id: Mapped[UUID] = mapped_column(ForeignKey("weather_events.id", ondelete="CASCADE"), index=True)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status"), default=NotificationStatus.SENT, index=True
    )
    message: Mapped[str] = mapped_column(String(500))
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    read_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="notifications")
    field = relationship("Field", back_populates="notifications")
    alert_rule = relationship("AlertRule", back_populates="notifications")
    weather_event = relationship("WeatherEvent", back_populates="notifications")

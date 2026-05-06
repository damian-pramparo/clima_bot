from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Enum, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import WeatherEventType


class AlertRule(Base):
    __tablename__ = "alert_rules"
    __table_args__ = (
        CheckConstraint("threshold >= 0 AND threshold <= 100", name="ck_alert_rules_threshold"),
        UniqueConstraint("user_id", "field_id", "event_type", name="uq_alert_rule_user_field_type"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    field_id: Mapped[UUID] = mapped_column(ForeignKey("fields.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[WeatherEventType] = mapped_column(Enum(WeatherEventType, name="weather_event_type"))
    threshold: Mapped[int] = mapped_column(Integer)
    active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    user = relationship("User", back_populates="alert_rules")
    field = relationship("Field", back_populates="alert_rules")
    notifications = relationship("Notification", back_populates="alert_rule", cascade="all, delete-orphan")

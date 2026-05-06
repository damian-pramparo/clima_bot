from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import WeatherEventType


class WeatherEvent(Base):
    __tablename__ = "weather_events"
    __table_args__ = (
        CheckConstraint("probability >= 0 AND probability <= 100", name="ck_weather_events_probability"),
        UniqueConstraint("field_id", "event_date", "event_type", name="uq_weather_event_field_date_type"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    field_id: Mapped[UUID] = mapped_column(ForeignKey("fields.id", ondelete="CASCADE"), index=True)
    event_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    event_type: Mapped[WeatherEventType] = mapped_column(Enum(WeatherEventType, name="weather_event_type"))
    probability: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(80), default="mock")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    field = relationship("Field", back_populates="weather_events")
    notifications = relationship("Notification", back_populates="weather_event")

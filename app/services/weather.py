from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.field import Field
from app.models.weather_event import WeatherEvent
from app.schemas.weather_event import WeatherEventCreate


async def create_weather_event(session: AsyncSession, payload: WeatherEventCreate) -> WeatherEvent:
    """Create a weather event or return the existing duplicate-safe record."""
    field = await session.get(Field, payload.field_id)
    if field is None:
        raise ValueError("field_id does not exist")

    existing_event = await _get_existing_weather_event(session, payload)
    if existing_event is not None:
        return existing_event

    event = WeatherEvent(**payload.model_dump())
    session.add(event)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing_event = await _get_existing_weather_event(session, payload)
        if existing_event is not None:
            return existing_event
        raise
    await session.refresh(event)
    return event


async def _get_existing_weather_event(session: AsyncSession, payload: WeatherEventCreate) -> WeatherEvent | None:
    """Find an existing weather event by field, datetime, and event type."""
    stmt = select(WeatherEvent).where(
        WeatherEvent.field_id == payload.field_id,
        WeatherEvent.event_date == payload.event_date,
        WeatherEvent.event_type == payload.event_type,
    )
    return (await session.scalars(stmt)).one_or_none()


async def list_weather_events(session: AsyncSession) -> list[WeatherEvent]:
    """Return weather events ordered chronologically and by type."""
    stmt = select(WeatherEvent).order_by(WeatherEvent.event_date.asc(), WeatherEvent.event_type.asc())
    return list((await session.scalars(stmt)).all())

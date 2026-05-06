from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import Select, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert_rule import AlertRule
from app.models.enums import NotificationStatus
from app.models.field import Field
from app.models.notification import Notification
from app.models.weather_event import WeatherEvent
from app.schemas.alert_rule import AlertRuleCreate, AlertRuleUpdate


async def list_alert_rules(session: AsyncSession, active: Optional[bool] = None) -> list[AlertRule]:
    stmt: Select[tuple[AlertRule]] = select(AlertRule).order_by(AlertRule.created_at.desc())
    if active is not None:
        stmt = stmt.where(AlertRule.active.is_(active))
    return list((await session.scalars(stmt)).all())


async def create_alert_rule(session: AsyncSession, payload: AlertRuleCreate) -> AlertRule:
    field = await session.get(Field, payload.field_id)
    if field is None or field.user_id != payload.user_id:
        raise ValueError("field_id does not belong to user_id")

    existing_alert_rule = await _get_existing_alert_rule(session, payload)
    if existing_alert_rule is not None:
        return existing_alert_rule

    alert_rule = AlertRule(**payload.model_dump())
    session.add(alert_rule)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        existing_alert_rule = await _get_existing_alert_rule(session, payload)
        if existing_alert_rule is not None:
            return existing_alert_rule
        raise
    await session.refresh(alert_rule)
    return alert_rule


async def _get_existing_alert_rule(session: AsyncSession, payload: AlertRuleCreate) -> AlertRule | None:
    stmt = select(AlertRule).where(
        AlertRule.user_id == payload.user_id,
        AlertRule.field_id == payload.field_id,
        AlertRule.event_type == payload.event_type,
    )
    return (await session.scalars(stmt)).one_or_none()


async def update_alert_rule(session: AsyncSession, alert_rule_id: UUID, payload: AlertRuleUpdate) -> Optional[AlertRule]:
    values = payload.model_dump(exclude_unset=True)
    if not values:
        return await session.get(AlertRule, alert_rule_id)

    stmt = (
        update(AlertRule)
        .where(AlertRule.id == alert_rule_id)
        .values(**values)
        .returning(AlertRule)
    )
    alert_rule = (await session.scalars(stmt)).one_or_none()
    await session.commit()
    return alert_rule


async def evaluate_alerts(session: AsyncSession) -> int:
    stmt = (
        select(AlertRule, WeatherEvent)
        .join(WeatherEvent, WeatherEvent.field_id == AlertRule.field_id)
        .where(
            AlertRule.active.is_(True),
            WeatherEvent.event_type == AlertRule.event_type,
            WeatherEvent.probability >= AlertRule.threshold,
            WeatherEvent.event_date >= datetime.now(timezone.utc),
        )
        .options(selectinload(AlertRule.field))
        .order_by(WeatherEvent.event_date.asc())
    )

    created = 0
    for alert_rule, weather_event in (await session.execute(stmt)).all():
        message = (
            f"Alerta climatica para {alert_rule.field.name}: "
            f"{weather_event.event_type.value} con probabilidad {weather_event.probability}% "
            f"el {weather_event.event_date.isoformat()} supera el umbral {alert_rule.threshold}%."
        )
        exists_stmt = select(Notification.id).where(
            Notification.alert_rule_id == alert_rule.id,
            Notification.weather_event_id == weather_event.id,
        )
        if (await session.scalar(exists_stmt)) is not None:
            continue
        session.add(
            Notification(
                user_id=alert_rule.user_id,
                field_id=alert_rule.field_id,
                alert_rule_id=alert_rule.id,
                weather_event_id=weather_event.id,
                status=NotificationStatus.SENT,
                message=message,
            )
        )
        created += 1

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        return await evaluate_alerts(session)
    return created

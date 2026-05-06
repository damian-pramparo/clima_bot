from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.models.enums import NotificationStatus
from app.models.field import Field
from app.models.notification import Notification
from app.models.user import User
from app.schemas.alert_rule import AlertRuleCreate, AlertRuleRead, AlertRuleUpdate
from app.schemas.common import EvaluationResult
from app.schemas.field import FieldRead
from app.schemas.notification import NotificationRead
from app.schemas.user import UserRead
from app.schemas.weather_event import WeatherEventCreate, WeatherEventRead
from app.services.alerts import create_alert_rule, evaluate_alerts, list_alert_rules, update_alert_rule
from app.services.weather import create_weather_event, list_weather_events

router = APIRouter()


@router.get("/health", tags=["system"])
async def health() -> dict[str, str]:
    """Return the API health status."""
    return {"status": "ok"}


@router.get("/health/db", tags=["system"])
async def health_db(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    """Return database connectivity status."""
    await session.execute(text("SELECT 1"))
    return {"status": "ok", "database": "ok"}


@router.get("/users", response_model=list[UserRead], tags=["users"])
async def users(session: AsyncSession = Depends(get_session)) -> list[User]:
    """List registered users ordered by name."""
    return list((await session.scalars(select(User).order_by(User.name.asc()))).all())


@router.get("/fields", response_model=list[FieldRead], tags=["fields"])
async def fields(session: AsyncSession = Depends(get_session)) -> list[Field]:
    """List registered agricultural fields ordered by name."""
    return list((await session.scalars(select(Field).order_by(Field.name.asc()))).all())


@router.get("/weather-events", response_model=list[WeatherEventRead], tags=["weather"])
async def weather_events(session: AsyncSession = Depends(get_session)) -> list:
    """List stored weather events ordered by event date."""
    return await list_weather_events(session)


@router.post(
    "/weather-events",
    response_model=WeatherEventRead,
    status_code=status.HTTP_201_CREATED,
    tags=["weather"],
)
async def post_weather_event(payload: WeatherEventCreate, session: AsyncSession = Depends(get_session)):
    """Create a weather event or return the existing idempotent match."""
    return await create_weather_event(session, payload)


@router.get("/alerts", response_model=list[AlertRuleRead], tags=["alerts"])
async def alerts(
    active: Optional[bool] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """List alert rules, optionally filtered by active status."""
    return await list_alert_rules(session, active=active)


@router.post("/alerts", response_model=AlertRuleRead, status_code=status.HTTP_201_CREATED, tags=["alerts"])
async def post_alert(payload: AlertRuleCreate, session: AsyncSession = Depends(get_session)):
    """Create an alert rule for a user-owned field."""
    return await create_alert_rule(session, payload)


@router.patch("/alerts/{alert_rule_id}", response_model=AlertRuleRead, tags=["alerts"])
async def patch_alert(alert_rule_id: UUID, payload: AlertRuleUpdate, session: AsyncSession = Depends(get_session)):
    """Apply a partial update to an alert rule."""
    alert_rule = await update_alert_rule(session, alert_rule_id, payload)
    if alert_rule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="alert rule not found")
    return alert_rule


@router.post("/alerts/evaluate", response_model=EvaluationResult, tags=["alerts"])
async def run_alert_evaluation(session: AsyncSession = Depends(get_session)) -> EvaluationResult:
    """Run alert evaluation immediately and report created notifications."""
    return EvaluationResult(created_notifications=await evaluate_alerts(session))


@router.get("/notifications", response_model=list[NotificationRead], tags=["notifications"])
async def notifications(
    user_id: Optional[UUID] = None,
    session: AsyncSession = Depends(get_session),
) -> list[Notification]:
    """List notifications, optionally scoped to one user."""
    stmt = select(Notification).order_by(Notification.sent_at.desc())
    if user_id is not None:
        stmt = stmt.where(Notification.user_id == user_id)
    return list((await session.scalars(stmt)).all())


@router.post("/notifications/{notification_id}/read", response_model=NotificationRead, tags=["notifications"])
async def mark_notification_read(notification_id: UUID, session: AsyncSession = Depends(get_session)):
    """Mark a notification as read."""
    stmt = (
        update(Notification)
        .where(Notification.id == notification_id)
        .values(status=NotificationStatus.READ, read_at=datetime.now(timezone.utc))
        .returning(Notification)
    )
    notification = (await session.scalars(stmt)).one_or_none()
    if notification is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="notification not found")
    await session.commit()
    return notification

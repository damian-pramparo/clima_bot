from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.models.alert_rule import AlertRule
from app.models.enums import WeatherEventType
from app.models.field import Field
from app.models.notification import Notification
from app.models.user import User
from app.models.weather_event import WeatherEvent
from app.services.alerts import create_alert_rule, evaluate_alerts
from app.schemas.alert_rule import AlertRuleCreate
from app.services.weather import create_weather_event
from app.schemas.weather_event import WeatherEventCreate


@pytest_asyncio.fixture()
async def session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_evaluate_alerts_creates_notifications_once(session):
    user = User(id=uuid4(), phone_number="+5493515550001", name="Productor")
    field = Field(id=uuid4(), user_id=user.id, name="Lote Norte", latitude=-31.42, longitude=-64.18)
    rule = AlertRule(
        id=uuid4(),
        user_id=user.id,
        field_id=field.id,
        event_type=WeatherEventType.RAIN,
        threshold=60,
        active=True,
    )
    event = WeatherEvent(
        id=uuid4(),
        field_id=field.id,
        event_date=datetime.now(timezone.utc) + timedelta(days=1),
        event_type=WeatherEventType.RAIN,
        probability=70,
        source="test",
    )
    session.add_all([user, field, rule, event])
    await session.commit()

    assert await evaluate_alerts(session) == 1
    assert await evaluate_alerts(session) == 0

    notifications = list((await session.scalars(select(Notification))).all())
    assert len(notifications) == 1
    assert notifications[0].user_id == user.id
    assert "70%" in notifications[0].message


@pytest.mark.asyncio
async def test_evaluate_alerts_ignores_below_threshold(session):
    user = User(id=uuid4(), phone_number="+5493515550002", name="Productor")
    field = Field(id=uuid4(), user_id=user.id, name="Lote Sur", latitude=-32.88, longitude=-68.84)
    rule = AlertRule(
        id=uuid4(),
        user_id=user.id,
        field_id=field.id,
        event_type=WeatherEventType.FROST,
        threshold=50,
        active=True,
    )
    event = WeatherEvent(
        id=uuid4(),
        field_id=field.id,
        event_date=datetime.now(timezone.utc) + timedelta(days=1),
        event_type=WeatherEventType.FROST,
        probability=30,
        source="test",
    )
    session.add_all([user, field, rule, event])
    await session.commit()

    assert await evaluate_alerts(session) == 0
    assert list((await session.scalars(select(Notification))).all()) == []


@pytest.mark.asyncio
async def test_create_weather_event_returns_existing_duplicate(session):
    user = User(id=uuid4(), phone_number="+5493515550003", name="Productor")
    field = Field(id=uuid4(), user_id=user.id, name="Lote Oeste", latitude=-31.42, longitude=-64.18)
    session.add_all([user, field])
    await session.commit()

    payload = WeatherEventCreate(
        field_id=field.id,
        event_date=datetime.now(timezone.utc) + timedelta(days=1),
        event_type=WeatherEventType.STORM,
        probability=80,
        source="test",
    )

    created = await create_weather_event(session, payload)
    duplicate = await create_weather_event(session, payload)

    events = list((await session.scalars(select(WeatherEvent))).all())
    assert len(events) == 1
    assert duplicate.id == created.id


@pytest.mark.asyncio
async def test_create_alert_rule_returns_existing_duplicate(session):
    user = User(id=uuid4(), phone_number="+5493515550004", name="Productor")
    field = Field(id=uuid4(), user_id=user.id, name="Lote Este", latitude=-31.42, longitude=-64.18)
    session.add_all([user, field])
    await session.commit()

    payload = AlertRuleCreate(
        user_id=user.id,
        field_id=field.id,
        event_type=WeatherEventType.STORM,
        threshold=30,
        active=True,
    )

    created = await create_alert_rule(session, payload)
    duplicate = await create_alert_rule(session, payload)

    alert_rules = list((await session.scalars(select(AlertRule))).all())
    assert len(alert_rules) == 1
    assert duplicate.id == created.id

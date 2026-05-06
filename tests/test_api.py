import os
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import httpx
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite://")
os.environ["APP_ENV"] = "test"
os.environ.setdefault("ALERT_EVALUATION_INTERVAL_SECONDS", "60")

from app.db.base import Base
from app.db.session import get_session
from app.main import app
from app.models.field import Field
from app.models.user import User


@pytest_asyncio.fixture()
async def api_client():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async def override_get_session():
        """Yield test-scoped database sessions to API requests."""
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_session] = override_get_session
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, session_factory

    app.dependency_overrides.clear()
    await engine.dispose()


async def _seed_user_and_field(session_factory, user_id=None, field_id=None):
    """Create a user and field pair for API tests."""
    user = User(id=user_id or uuid4(), phone_number=f"+549351{uuid4().int % 1000000:06d}", name="Productor")
    field = Field(
        id=field_id or uuid4(),
        user_id=user.id,
        name="Lote Norte",
        latitude=-31.42,
        longitude=-64.18,
    )
    async with session_factory() as session:
        session.add_all([user, field])
        await session.commit()
    return user, field


@pytest.mark.asyncio
async def test_health_endpoints(api_client):
    client, _ = api_client

    response = await client.get("/health")
    db_response = await client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert db_response.status_code == 200
    assert db_response.json() == {"status": "ok", "database": "ok"}


@pytest.mark.asyncio
async def test_create_alert_rejects_field_owned_by_another_user(api_client):
    client, session_factory = api_client
    owner, field = await _seed_user_and_field(session_factory)
    other_user, _ = await _seed_user_and_field(session_factory)

    response = await client.post(
        "/alerts",
        json={
            "user_id": str(other_user.id),
            "field_id": str(field.id),
            "event_type": "rain",
            "threshold": 60,
            "active": True,
        },
    )

    assert owner.id != other_user.id
    assert response.status_code == 422
    assert response.json() == {"detail": "field_id does not belong to user_id"}


@pytest.mark.asyncio
async def test_create_weather_event_returns_existing_duplicate(api_client):
    client, session_factory = api_client
    _, field = await _seed_user_and_field(session_factory)
    payload = {
        "field_id": str(field.id),
        "event_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
        "event_type": "storm",
        "probability": 80,
        "source": "api_test",
    }

    created = await client.post("/weather-events", json=payload)
    duplicate = await client.post("/weather-events", json=payload)

    assert created.status_code == 201
    assert duplicate.status_code == 201
    assert duplicate.json()["id"] == created.json()["id"]


@pytest.mark.asyncio
async def test_alert_evaluation_is_idempotent_and_notifications_can_be_read(api_client):
    client, session_factory = api_client
    user, field = await _seed_user_and_field(session_factory)
    await client.post(
        "/alerts",
        json={
            "user_id": str(user.id),
            "field_id": str(field.id),
            "event_type": "hail",
            "threshold": 30,
            "active": True,
        },
    )
    await client.post(
        "/weather-events",
        json={
            "field_id": str(field.id),
            "event_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "event_type": "hail",
            "probability": 70,
            "source": "api_test",
        },
    )

    first_evaluation = await client.post("/alerts/evaluate")
    second_evaluation = await client.post("/alerts/evaluate")
    notifications = await client.get(f"/notifications?user_id={user.id}")
    notification = notifications.json()[0]
    read_response = await client.post(f"/notifications/{notification['id']}/read")

    assert first_evaluation.json() == {"created_notifications": 1}
    assert second_evaluation.json() == {"created_notifications": 0}
    assert len(notifications.json()) == 1
    assert notification["user_id"] == str(user.id)
    assert read_response.status_code == 200
    assert read_response.json()["status"] == "read"
    assert read_response.json()["read_at"] is not None


@pytest.mark.asyncio
async def test_alert_and_weather_payload_validation(api_client):
    client, _ = api_client

    alert_response = await client.post(
        "/alerts",
        json={
            "user_id": str(uuid4()),
            "field_id": str(uuid4()),
            "event_type": "rain",
            "threshold": 101,
            "active": True,
        },
    )
    weather_response = await client.post(
        "/weather-events",
        json={
            "field_id": str(uuid4()),
            "event_date": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat(),
            "event_type": "rain",
            "probability": 101,
            "source": "api_test",
        },
    )

    assert alert_response.status_code == 422
    assert weather_response.status_code == 422

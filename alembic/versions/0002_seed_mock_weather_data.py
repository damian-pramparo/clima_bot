"""seed mock weather data

Revision ID: 0002_seed_mock_weather_data
Revises: 0001_create_alerting_schema
Create Date: 2026-05-06
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0002_seed_mock_weather_data"
down_revision: Union[str, None] = "0001_create_alerting_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO users (id, phone_number, name)
        VALUES
          ('11111111-1111-1111-1111-111111111111', '+5493515550001', 'Productor Norte'),
          ('22222222-2222-2222-2222-222222222222', '+5493515550002', 'Productor Sur')
        ON CONFLICT (phone_number) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO fields (id, user_id, name, latitude, longitude)
        VALUES
          ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', 'Lote Maiz', -31.420100, -64.188800),
          ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', '22222222-2222-2222-2222-222222222222', 'Lote Soja', -32.889500, -68.845800)
        ON CONFLICT (id) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO alert_rules (id, user_id, field_id, event_type, threshold, active)
        VALUES
          ('aaaaaaaa-1111-1111-1111-aaaaaaaaaaaa', '11111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'RAIN', 60, TRUE),
          ('bbbbbbbb-2222-2222-2222-bbbbbbbbbbbb', '22222222-2222-2222-2222-222222222222', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'FROST', 40, TRUE)
        ON CONFLICT (user_id, field_id, event_type) DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO weather_events (id, field_id, event_date, event_type, probability, source)
        VALUES
          ('10000000-0000-0000-0000-000000000001', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', CURRENT_TIMESTAMP + INTERVAL '1 day', 'RAIN', 75, 'mock_migration'),
          ('10000000-0000-0000-0000-000000000002', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', CURRENT_TIMESTAMP + INTERVAL '2 days', 'FROST', 20, 'mock_migration'),
          ('10000000-0000-0000-0000-000000000003', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', CURRENT_TIMESTAMP + INTERVAL '1 day', 'FROST', 55, 'mock_migration'),
          ('10000000-0000-0000-0000-000000000004', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', CURRENT_TIMESTAMP + INTERVAL '3 days', 'STORM', 35, 'mock_migration')
        ON CONFLICT (field_id, event_date, event_type) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM notifications
        WHERE alert_rule_id IN (
          'aaaaaaaa-1111-1111-1111-aaaaaaaaaaaa',
          'bbbbbbbb-2222-2222-2222-bbbbbbbbbbbb'
        )
        """
    )
    op.execute("DELETE FROM weather_events WHERE source = 'mock_migration'")
    op.execute(
        """
        DELETE FROM alert_rules WHERE id IN (
          'aaaaaaaa-1111-1111-1111-aaaaaaaaaaaa',
          'bbbbbbbb-2222-2222-2222-bbbbbbbbbbbb'
        )
        """
    )
    op.execute(
        """
        DELETE FROM fields WHERE id IN (
          'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa',
          'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'
        )
        """
    )
    op.execute(
        """
        DELETE FROM users WHERE id IN (
          '11111111-1111-1111-1111-111111111111',
          '22222222-2222-2222-2222-222222222222'
        )
        """
    )

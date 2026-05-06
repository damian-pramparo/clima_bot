"""store weather event datetime

Revision ID: 0003_weather_events_datetime
Revises: 0002_seed_mock_weather_data
Create Date: 2026-05-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0003_weather_events_datetime"
down_revision: Union[str, None] = "0002_seed_mock_weather_data"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "weather_events",
        "event_date",
        existing_type=sa.Date(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        postgresql_using="event_date::timestamp AT TIME ZONE 'UTC'",
    )


def downgrade() -> None:
    op.alter_column(
        "weather_events",
        "event_date",
        existing_type=sa.DateTime(timezone=True),
        type_=sa.Date(),
        existing_nullable=False,
        postgresql_using="event_date::date",
    )

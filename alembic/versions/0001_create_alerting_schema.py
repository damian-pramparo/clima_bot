"""create alerting schema

Revision ID: 0001_create_alerting_schema
Revises:
Create Date: 2026-05-06
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "0001_create_alerting_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

weather_event_type = postgresql.ENUM(
    "FROST",
    "RAIN",
    "HAIL",
    "STORM",
    "HEAT_WAVE",
    name="weather_event_type",
    create_type=False,
)
notification_status = postgresql.ENUM(
    "PENDING",
    "SENT",
    "READ",
    name="notification_status",
    create_type=False,
)


def upgrade() -> None:
    """Create the initial alerting schema and enum types."""
    weather_event_type.create(op.get_bind(), checkfirst=True)
    notification_status.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("phone_number", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_users_phone_number"), "users", ["phone_number"], unique=True)

    op.create_table(
        "fields",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("latitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("longitude", sa.Numeric(precision=9, scale=6), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fields_user_id"), "fields", ["user_id"], unique=False)

    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("field_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", weather_event_type, nullable=False),
        sa.Column("threshold", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("threshold >= 0 AND threshold <= 100", name="ck_alert_rules_threshold"),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "field_id", "event_type", name="uq_alert_rule_user_field_type"),
    )
    op.create_index(op.f("ix_alert_rules_active"), "alert_rules", ["active"], unique=False)
    op.create_index(op.f("ix_alert_rules_field_id"), "alert_rules", ["field_id"], unique=False)
    op.create_index(op.f("ix_alert_rules_user_id"), "alert_rules", ["user_id"], unique=False)

    op.create_table(
        "weather_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("field_id", sa.Uuid(), nullable=False),
        sa.Column("event_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("event_type", weather_event_type, nullable=False),
        sa.Column("probability", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=80), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.CheckConstraint("probability >= 0 AND probability <= 100", name="ck_weather_events_probability"),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("field_id", "event_date", "event_type", name="uq_weather_event_field_date_type"),
    )
    op.create_index(op.f("ix_weather_events_event_date"), "weather_events", ["event_date"], unique=False)
    op.create_index(op.f("ix_weather_events_field_id"), "weather_events", ["field_id"], unique=False)

    op.create_table(
        "notifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("field_id", sa.Uuid(), nullable=False),
        sa.Column("alert_rule_id", sa.Uuid(), nullable=False),
        sa.Column("weather_event_id", sa.Uuid(), nullable=False),
        sa.Column("status", notification_status, nullable=False),
        sa.Column("message", sa.String(length=500), nullable=False),
        sa.Column("sent_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["alert_rule_id"], ["alert_rules.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["field_id"], ["fields.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["weather_event_id"], ["weather_events.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("alert_rule_id", "weather_event_id", name="uq_notification_rule_weather_event"),
    )
    op.create_index(op.f("ix_notifications_alert_rule_id"), "notifications", ["alert_rule_id"], unique=False)
    op.create_index(op.f("ix_notifications_field_id"), "notifications", ["field_id"], unique=False)
    op.create_index(op.f("ix_notifications_status"), "notifications", ["status"], unique=False)
    op.create_index(op.f("ix_notifications_user_id"), "notifications", ["user_id"], unique=False)
    op.create_index(op.f("ix_notifications_weather_event_id"), "notifications", ["weather_event_id"], unique=False)


def downgrade() -> None:
    """Drop the alerting schema and enum types."""
    op.drop_index(op.f("ix_notifications_weather_event_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_user_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_status"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_field_id"), table_name="notifications")
    op.drop_index(op.f("ix_notifications_alert_rule_id"), table_name="notifications")
    op.drop_table("notifications")
    op.drop_index(op.f("ix_weather_events_field_id"), table_name="weather_events")
    op.drop_index(op.f("ix_weather_events_event_date"), table_name="weather_events")
    op.drop_table("weather_events")
    op.drop_index(op.f("ix_alert_rules_user_id"), table_name="alert_rules")
    op.drop_index(op.f("ix_alert_rules_field_id"), table_name="alert_rules")
    op.drop_index(op.f("ix_alert_rules_active"), table_name="alert_rules")
    op.drop_table("alert_rules")
    op.drop_index(op.f("ix_fields_user_id"), table_name="fields")
    op.drop_table("fields")
    op.drop_index(op.f("ix_users_phone_number"), table_name="users")
    op.drop_table("users")
    notification_status.drop(op.get_bind(), checkfirst=True)
    weather_event_type.drop(op.get_bind(), checkfirst=True)

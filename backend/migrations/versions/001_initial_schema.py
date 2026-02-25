"""Initial schema migration.

Revision ID: 001
Revises:
Create Date: 2026-02-25
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Users
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("plan_tier", sa.String(50), nullable=False, server_default="free"),
        sa.Column("auth_provider_id", sa.String(255), unique=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Organizations
    op.create_table(
        "organizations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("owner_id", UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("plan_tier", sa.String(50), nullable=False, server_default="free"),
        sa.Column("stripe_customer_id", sa.String(255)),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Connections
    op.create_table(
        "connections",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("credentials_ref", sa.String(512), nullable=False),
        sa.Column("config", JSONB),
        sa.Column("status", sa.String(50), server_default="pending"),
        sa.Column("last_tested_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    # Monitored Tables
    op.create_table(
        "monitored_tables",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("connection_id", UUID(as_uuid=True), sa.ForeignKey("connections.id"), nullable=False),
        sa.Column("schema_name", sa.String(255), nullable=False),
        sa.Column("table_name", sa.String(255), nullable=False),
        sa.Column("check_frequency", sa.String(50), server_default="daily"),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
        sa.UniqueConstraint("connection_id", "schema_name", "table_name"),
    )

    # Schema Snapshots
    op.create_table(
        "schema_snapshots",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("table_id", UUID(as_uuid=True), sa.ForeignKey("monitored_tables.id"), nullable=False),
        sa.Column("columns_json", JSONB, nullable=False),
        sa.Column("captured_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_schema_snapshots_table_captured", "schema_snapshots", ["table_id", "captured_at"])

    # Check Results
    op.create_table(
        "check_results",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("table_id", UUID(as_uuid=True), sa.ForeignKey("monitored_tables.id"), nullable=False),
        sa.Column("check_type", sa.String(50), nullable=False),
        sa.Column("column_name", sa.String(255)),
        sa.Column("value", sa.Float, nullable=False),
        sa.Column("measured_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_check_results_table_type_measured", "check_results", ["table_id", "check_type", "measured_at"])

    # Alerts
    op.create_table(
        "alerts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("table_id", UUID(as_uuid=True), sa.ForeignKey("monitored_tables.id"), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False, server_default="warning"),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("details_json", JSONB, nullable=False),
        sa.Column("acknowledged_by", UUID(as_uuid=True), sa.ForeignKey("users.id")),
        sa.Column("acknowledged_at", sa.DateTime),
        sa.Column("resolved_at", sa.DateTime),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )
    op.create_index("ix_alerts_table_status", "alerts", ["table_id", "status"])

    # Notification Configs
    op.create_table(
        "notification_configs",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("org_id", UUID(as_uuid=True), sa.ForeignKey("organizations.id"), nullable=False),
        sa.Column("channel", sa.String(50), nullable=False),
        sa.Column("destination", sa.String(512), nullable=False),
        sa.Column("filters", JSONB),
        sa.Column("is_active", sa.Boolean, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("notification_configs")
    op.drop_table("alerts")
    op.drop_table("check_results")
    op.drop_table("schema_snapshots")
    op.drop_table("monitored_tables")
    op.drop_table("connections")
    op.drop_table("organizations")
    op.drop_table("users")

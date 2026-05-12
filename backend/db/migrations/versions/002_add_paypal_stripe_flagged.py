"""Add paypal_connections, stripe_connections, flagged_items tables.

Revision ID: 002_add_paypal_stripe_flagged
Revises: 001_add_integration_tables
Create Date: 2026-05-11
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "002_add_paypal_stripe_flagged"
down_revision = "001_add_integration_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "paypal_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, unique=True),
        sa.Column("client_id", sa.Text, nullable=False),
        sa.Column("client_secret", sa.Text, nullable=False),
        sa.Column("sandbox", sa.Boolean, default=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "stripe_connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False, unique=True),
        sa.Column("api_key", sa.Text, nullable=False),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_table(
        "flagged_items",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("amount", sa.String(50), nullable=True),
        sa.Column("transaction_id", sa.String(255), nullable=True),
        sa.Column("raw", postgresql.JSONB, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("reviewed_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime, nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
    )

    op.create_index("ix_flagged_items_tenant_id", "flagged_items", ["tenant_id"])
    op.create_index("ix_flagged_items_status", "flagged_items", ["status"])


def downgrade() -> None:
    op.drop_table("flagged_items")
    op.drop_table("stripe_connections")
    op.drop_table("paypal_connections")
    op.execute("DROP TYPE IF EXISTS flagged_status")

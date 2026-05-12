"""Add workflow status fields to reports table.

Revision ID: 003_report_workflow_status
Revises: 002_add_paypal_stripe_flagged
Create Date: 2026-05-12
"""

from alembic import op
import sqlalchemy as sa

revision = "003_report_workflow_status"
down_revision = "002_add_paypal_stripe_flagged"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # generated_at already exists from initial migration — only add new columns
    op.add_column("reports", sa.Column("status", sa.String(30), server_default="data_pulled", nullable=False))
    op.add_column("reports", sa.Column("flagged_count", sa.Integer, server_default="0"))
    op.add_column("reports", sa.Column("reviewed_count", sa.Integer, server_default="0"))
    op.add_column("reports", sa.Column("reminder_sent_at", sa.DateTime, nullable=True))
    op.add_column("reports", sa.Column("delivered_at", sa.DateTime, nullable=True))
    op.add_column("reports", sa.Column("created_at", sa.DateTime, server_default=sa.func.now()))
    op.create_index("ix_reports_status", "reports", ["status"])
    op.create_index("ix_reports_tenant_period", "reports", ["tenant_id", "period_end"])


def downgrade() -> None:
    op.drop_index("ix_reports_tenant_period")
    op.drop_index("ix_reports_status")
    op.drop_column("reports", "created_at")
    op.drop_column("reports", "delivered_at")
    op.drop_column("reports", "reminder_sent_at")
    op.drop_column("reports", "reviewed_count")
    op.drop_column("reports", "flagged_count")
    op.drop_column("reports", "status")

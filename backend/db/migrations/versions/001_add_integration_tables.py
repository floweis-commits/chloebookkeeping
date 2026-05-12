"""Add integration tables for QuickBooks and Shopify.

Revision ID: 001_add_integration_tables
Revises:
Create Date: 2024-03-29 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_add_integration_tables'
down_revision = '000_initial_tables'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create quickbooks_connections table
    op.create_table(
        'quickbooks_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('realm_id', sa.String(255), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=False),
        sa.Column('refresh_token', sa.Text(), nullable=False),
        sa.Column('token_expires_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id'),
    )
    op.create_index('ix_quickbooks_connections_tenant_id', 'quickbooks_connections', ['tenant_id'], unique=False)

    # Create shopify_connections table
    op.create_table(
        'shopify_connections',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('store_domain', sa.String(255), nullable=False),
        sa.Column('api_key', sa.Text(), nullable=False),
        sa.Column('api_secret', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id'),
    )
    op.create_index('ix_shopify_connections_tenant_id', 'shopify_connections', ['tenant_id'], unique=False)

    # Add data column to reports table


def downgrade() -> None:
    # Remove data column from reports

    # Drop shopify_connections table
    op.drop_index('ix_shopify_connections_tenant_id', table_name='shopify_connections')
    op.drop_table('shopify_connections')

    # Drop quickbooks_connections table
    op.drop_index('ix_quickbooks_connections_tenant_id', table_name='quickbooks_connections')
    op.drop_table('quickbooks_connections')

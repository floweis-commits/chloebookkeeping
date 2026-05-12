"""Initial schema — all base tables.

Revision ID: 000_initial_tables
Revises: 
Create Date: 2024-01-01 00:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '000_initial_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('phone', sa.String(50), nullable=True),
        sa.Column('timezone', sa.String(50), nullable=True),
        sa.Column('role', sa.Enum('bookkeeper', 'client', 'accountant', name='user_role'), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # ── tenants ────────────────────────────────────────────────────────
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── permissions ────────────────────────────────────────────────────
    op.create_table(
        'permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('access_level', sa.Enum('viewer', 'editor', 'owner', name='access_level'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True),
        sa.Column('granted_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── files ──────────────────────────────────────────────────────────
    op.create_table(
        'files',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(500), nullable=False),
        sa.Column('path', sa.Text(), nullable=False),
        sa.Column('mime_type', sa.String(100), nullable=True),
        sa.Column('size_bytes', sa.Integer(), nullable=True),
        sa.Column('folder', sa.String(500), nullable=True),
        sa.Column('is_folder', sa.Boolean(), nullable=True),
        sa.Column('parent_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('uploaded_by', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_seen', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['parent_id'], ['files.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.ForeignKeyConstraint(['uploaded_by'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
    )

    # ── reports ────────────────────────────────────────────────────────
    op.create_table(
        'reports',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('title', sa.String(255), nullable=False),
        sa.Column('period_start', sa.DateTime(), nullable=False),
        sa.Column('period_end', sa.DateTime(), nullable=False),
        sa.Column('file_path', sa.Text(), nullable=True),
        sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('client_name', sa.String(255), nullable=True),
        sa.Column('bookkeeper_name', sa.String(255), nullable=True),
        sa.Column('logo_path', sa.Text(), nullable=True),
        sa.Column('generated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
    )


def downgrade() -> None:
    op.drop_table('reports')
    op.drop_table('files')
    op.drop_table('permissions')
    op.drop_table('tenants')
    op.drop_index('ix_users_email', table_name='users')
    op.drop_table('users')
    op.execute('DROP TYPE IF EXISTS user_role')
    op.execute('DROP TYPE IF EXISTS access_level')

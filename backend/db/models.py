"""
SQLAlchemy ORM models.

Architect notes:
- tenant_id on most tables prepares for multi-client expansion.
- roles: bookkeeper, client, accountant.
- FileRecord supports nested folders via parent_id.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Column, String, DateTime, ForeignKey, Text, Enum, Boolean, Integer
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from backend.db.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50), nullable=True)
    timezone = Column(String(50), default="America/New_York")
    role = Column(Enum("bookkeeper", "client", "accountant", name="user_role"), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    permissions = relationship("Permission", back_populates="user")


class Tenant(Base):
    """A client business — groups files, reports, and connections."""
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    files = relationship("FileRecord", back_populates="tenant")
    reports = relationship("Report", back_populates="tenant")


class Permission(Base):
    """Maps users → tenants with an access level."""
    __tablename__ = "permissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    access_level = Column(
        Enum("viewer", "editor", "owner", name="access_level"),
        default="viewer",
    )
    is_active = Column(Boolean, default=True)
    granted_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="permissions")
    tenant = relationship("Tenant")


class FileRecord(Base):
    """Metadata for an uploaded/stored file."""
    __tablename__ = "files"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(500), nullable=False)
    path = Column(Text, nullable=False)  # storage path / S3 key
    mime_type = Column(String(100))
    size_bytes = Column(Integer)
    folder = Column(String(500), default="/")  # logical folder, e.g. "2025/Tax Returns"
    is_folder = Column(Boolean, default=False)  # True = folder entry, False = file
    parent_id = Column(UUID(as_uuid=True), ForeignKey("files.id"), nullable=True)
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    is_seen = Column(Boolean, default=False)  # False = show "New" badge
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="files")


class Report(Base):
    """A generated management report."""
    __tablename__ = "reports"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    title = Column(String(255), nullable=False)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    file_path = Column(Text)  # path to generated PDF
    data = Column(JSONB)  # raw sync results from API integrations + KPIs
    client_name = Column(String(255), nullable=True)  # client business name
    bookkeeper_name = Column(String(255), nullable=True)  # bookkeeper full name
    logo_path = Column(Text, nullable=True)  # path to client logo if available
    generated_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant", back_populates="reports")


class QuickBooksConnection(Base):
    """Stores QuickBooks OAuth tokens and realm ID per tenant."""
    __tablename__ = "quickbooks_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True)
    realm_id = Column(String(255), nullable=False)  # QuickBooks Company ID
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_expires_at = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant")


class ShopifyConnection(Base):
    """Stores Shopify API credentials per tenant."""
    __tablename__ = "shopify_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True)
    store_domain = Column(String(255), nullable=False)  # e.g., "store.myshopify.com"
    api_key = Column(Text, nullable=False)  # encrypted
    api_secret = Column(Text, nullable=False)  # encrypted
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant")


class PayPalConnection(Base):
    """Stores PayPal client credentials per tenant."""
    __tablename__ = "paypal_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True)
    client_id = Column(Text, nullable=False)
    client_secret = Column(Text, nullable=False)
    sandbox = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant")


class StripeConnection(Base):
    """Stores Stripe secret API key per tenant."""
    __tablename__ = "stripe_connections"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False, unique=True)
    api_key = Column(Text, nullable=False)  # sk_live_... or sk_test_...
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    tenant = relationship("Tenant")


class FlaggedItem(Base):
    """A transaction or reconciliation discrepancy flagged for bookkeeper review."""
    __tablename__ = "flagged_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    source = Column(String(50), nullable=False)   # "quickbooks" | "paypal" | "stripe" | "shopify"
    type = Column(String(50), nullable=False)      # "unmatched_processor" | "unmatched_qb" | "amount_mismatch" | "low_confidence"
    description = Column(Text, nullable=False)
    amount = Column(String(50), nullable=True)     # string to preserve sign
    transaction_id = Column(String(255), nullable=True)
    raw = Column(JSONB, nullable=True)             # original transaction payload
    status = Column(
        Enum("pending", "approved", "rejected", "corrected", name="flagged_status"),
        default="pending",
        nullable=False,
    )
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    note = Column(Text, nullable=True)             # bookkeeper note when resolving
    created_at = Column(DateTime, default=datetime.utcnow)

    tenant = relationship("Tenant")

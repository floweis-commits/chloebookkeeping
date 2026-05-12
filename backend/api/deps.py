"""
FastAPI dependencies — Supabase JWT verification, role gates, tenant access.

Auth flow:
  Frontend (Supabase browser client) → sends Bearer token (Supabase JWT)
  Backend → verifies JWT against Supabase using the secret key
  Backend → looks up role from JWT claims (user_metadata.role)
"""

from typing import Callable
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.db.database import get_db
from backend.db.models import Permission

bearer_scheme = HTTPBearer()


# ── Supabase JWT verification ─────────────────────────────

class SupabaseUser:
    """Lightweight user object parsed from Supabase JWT claims."""

    def __init__(self, payload: dict):
        self.id: str = payload.get("sub", "")
        self.email: str = payload.get("email", "")
        meta = payload.get("user_metadata", {})
        self.role: str = meta.get("role", "client")
        self.raw = payload


def _verify_supabase_jwt(token: str) -> SupabaseUser:
    """
    Verify a Supabase-issued JWT using the project secret key.
    Raises 401 if invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.supabase_secret_key,
            algorithms=["HS256"],
            options={"verify_aud": False},  # Supabase JWTs use project URL as aud
        )
        return SupabaseUser(payload)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> SupabaseUser:
    """Extract and verify the Supabase JWT from the Authorization header."""
    return _verify_supabase_jwt(credentials.credentials)


def get_db_session():
    """Alias kept for clarity — actual impl is in database.py."""
    return get_db()


# ── Role gate ─────────────────────────────────────────────

def require_role(*allowed_roles: str) -> Callable:
    """
    Dependency factory — ensures the current user has one of the allowed roles.

    Usage:
        @router.post("/bookkeeper-only")
        async def action(_: SupabaseUser = Depends(require_role("bookkeeper"))):
            ...
    """
    async def _check(user: SupabaseUser = Depends(get_current_user)) -> SupabaseUser:
        if user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' not permitted. Required: {allowed_roles}",
            )
        return user

    return _check


# ── Tenant permission gate ────────────────────────────────

ACCESS_HIERARCHY = {"viewer": 0, "editor": 1, "owner": 2}


async def get_tenant_permission(
    tenant_id: UUID,
    user: SupabaseUser,
    db: AsyncSession,
    min_level: str = "viewer",
) -> Permission | None:
    """
    Bookkeepers have implicit access to all tenants.
    Clients need an active Permission row with at least min_level.
    """
    if user.role == "bookkeeper":
        return None

    result = await db.execute(
        select(Permission).where(
            Permission.user_id == UUID(user.id),
            Permission.tenant_id == tenant_id,
            Permission.is_active == True,  # noqa: E712
        )
    )
    perm = result.scalar_one_or_none()

    if perm is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this client's data",
        )

    if ACCESS_HIERARCHY.get(perm.access_level, 0) < ACCESS_HIERARCHY.get(min_level, 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires at least '{min_level}' access",
        )

    return perm

"""
Permission endpoints — invite, revoke, list.
Bookkeeper-only operations for managing client access.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.database import get_db
from backend.db.models import User, Permission, Tenant
from backend.api.deps import require_role

router = APIRouter()


# ── Schemas ───────────────────────────────────────────────

class InviteRequest(BaseModel):
    email: EmailStr
    tenant_id: UUID
    access_level: str = "viewer"


class PermissionOut(BaseModel):
    id: UUID
    user_id: UUID
    user_email: str
    user_name: str
    tenant_id: UUID
    access_level: str
    is_active: bool
    granted_at: str

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────

@router.post("/invite", status_code=status.HTTP_201_CREATED)
async def invite_user(
    body: InviteRequest,
    bookkeeper: User = Depends(require_role("bookkeeper")),
    db: AsyncSession = Depends(get_db),
):
    """
    Grant a user access to a tenant's data.
    Looks up the user by email; if they exist, creates a Permission row.
    """
    # Validate access level
    if body.access_level not in ("viewer", "editor", "owner"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="access_level must be one of: viewer, editor, owner",
        )

    # Verify tenant exists
    tenant_result = await db.execute(select(Tenant).where(Tenant.id == body.tenant_id))
    if tenant_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Look up user by email
    user_result = await db.execute(select(User).where(User.email == body.email))
    user = user_result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No account found for {body.email}. They must register first.",
        )

    # Check for existing active permission
    existing = await db.execute(
        select(Permission).where(
            Permission.user_id == user.id,
            Permission.tenant_id == body.tenant_id,
            Permission.is_active == True,  # noqa: E712
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This user already has active access to this client",
        )

    perm = Permission(
        user_id=user.id,
        tenant_id=body.tenant_id,
        access_level=body.access_level,
    )
    db.add(perm)
    await db.commit()
    await db.refresh(perm)

    return {
        "id": str(perm.id),
        "user_email": user.email,
        "tenant_id": str(perm.tenant_id),
        "access_level": perm.access_level,
        "detail": f"Access granted to {user.email}",
    }


@router.delete("/{permission_id}", status_code=status.HTTP_200_OK)
async def revoke_permission(
    permission_id: UUID,
    bookkeeper: User = Depends(require_role("bookkeeper")),
    db: AsyncSession = Depends(get_db),
):
    """Revoke a permission (soft-delete by setting is_active=False)."""
    result = await db.execute(select(Permission).where(Permission.id == permission_id))
    perm = result.scalar_one_or_none()

    if perm is None:
        raise HTTPException(status_code=404, detail="Permission not found")

    if not perm.is_active:
        raise HTTPException(status_code=400, detail="Permission already revoked")

    perm.is_active = False
    await db.commit()

    return {"detail": "Permission revoked"}


@router.get("/tenant/{tenant_id}", response_model=list[PermissionOut])
async def list_permissions(
    tenant_id: UUID,
    bookkeeper: User = Depends(require_role("bookkeeper")),
    db: AsyncSession = Depends(get_db),
):
    """List all active permissions for a tenant."""
    result = await db.execute(
        select(Permission, User)
        .join(User, Permission.user_id == User.id)
        .where(
            Permission.tenant_id == tenant_id,
            Permission.is_active == True,  # noqa: E712
        )
        .order_by(Permission.granted_at.desc())
    )

    permissions = []
    for perm, user in result.all():
        permissions.append(
            PermissionOut(
                id=perm.id,
                user_id=perm.user_id,
                user_email=user.email,
                user_name=user.full_name,
                tenant_id=perm.tenant_id,
                access_level=perm.access_level,
                is_active=perm.is_active,
                granted_at=perm.granted_at.isoformat(),
            )
        )

    return permissions

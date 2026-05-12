"""
Flagged items API — bookkeeper review queue for reconciliation discrepancies.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import get_db, require_role, SupabaseUser
from backend.db.models import FlaggedItem

router = APIRouter(prefix="/api/flagged", tags=["flagged"])


class FlaggedItemOut(BaseModel):
    id: str
    tenant_id: str
    source: str
    type: str
    description: str
    amount: Optional[str]
    transaction_id: Optional[str]
    status: str
    note: Optional[str]
    created_at: str

    @classmethod
    def from_orm(cls, obj: FlaggedItem) -> "FlaggedItemOut":
        return cls(
            id=str(obj.id),
            tenant_id=str(obj.tenant_id),
            source=obj.source,
            type=obj.type,
            description=obj.description,
            amount=obj.amount,
            transaction_id=obj.transaction_id,
            status=obj.status,
            note=obj.note,
            created_at=obj.created_at.isoformat() if obj.created_at else "",
        )


class ReviewRequest(BaseModel):
    status: str  # "approved" | "rejected" | "corrected"
    note: Optional[str] = None


@router.get("/{tenant_id}")
async def list_flagged(
    tenant_id: str,
    flag_status: Optional[str] = Query(None, alias="status"),
    user: SupabaseUser = Depends(require_role("bookkeeper")),
    db: AsyncSession = Depends(get_db),
) -> List[FlaggedItemOut]:
    """List flagged items for a tenant. Optionally filter by status."""
    q = select(FlaggedItem).where(FlaggedItem.tenant_id == tenant_id)
    if flag_status:
        q = q.where(FlaggedItem.status == flag_status)
    q = q.order_by(FlaggedItem.created_at.desc())

    result = await db.execute(q)
    items = result.scalars().all()
    return [FlaggedItemOut.from_orm(i) for i in items]


@router.patch("/{item_id}/review")
async def review_flagged_item(
    item_id: str,
    body: ReviewRequest,
    user: SupabaseUser = Depends(require_role("bookkeeper")),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Mark a flagged item as approved / rejected / corrected."""
    if body.status not in ("approved", "rejected", "corrected"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="status must be one of: approved, rejected, corrected",
        )

    result = await db.execute(
        select(FlaggedItem).where(FlaggedItem.id == item_id)
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=404, detail="Flagged item not found")

    item.status = body.status
    item.note = body.note
    item.reviewed_by = UUID(user.id)
    item.reviewed_at = datetime.utcnow()
    await db.commit()

    return {"status": "success", "item_id": item_id, "new_status": body.status}


@router.get("/{tenant_id}/summary")
async def flagged_summary(
    tenant_id: str,
    user: SupabaseUser = Depends(require_role("bookkeeper")),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, int]:
    """Count of flagged items by status for the tenant."""
    result = await db.execute(
        select(FlaggedItem).where(FlaggedItem.tenant_id == tenant_id)
    )
    items = result.scalars().all()
    counts: Dict[str, int] = {"pending": 0, "approved": 0, "rejected": 0, "corrected": 0}
    for item in items:
        counts[item.status] = counts.get(item.status, 0) + 1
    return counts

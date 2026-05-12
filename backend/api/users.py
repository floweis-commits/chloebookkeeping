"""
User management endpoints — profile, settings, permissions.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from backend.api.deps import get_current_user
from backend.db.models import User

router = APIRouter()


class UserProfile(BaseModel):
    email: str
    full_name: str
    phone: str | None
    timezone: str
    role: str


@router.get("/me", response_model=UserProfile)
async def get_profile(current_user: User = Depends(get_current_user)):
    """Return the current user's profile."""
    return UserProfile(
        email=current_user.email,
        full_name=current_user.full_name,
        phone=current_user.phone,
        timezone=current_user.timezone,
        role=current_user.role,
    )


@router.put("/me")
async def update_profile(current_user: User = Depends(get_current_user)):
    """Update name, phone, timezone."""
    # TODO: Accept update body, persist changes
    return {"detail": "Not implemented yet"}


@router.post("/me/password")
async def change_password(current_user: User = Depends(get_current_user)):
    """Change the current user's password."""
    # TODO: Verify old password, hash new password, persist
    return {"detail": "Not implemented yet"}

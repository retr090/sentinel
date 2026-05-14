from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.core.database import get_db
from app.core.security import get_current_user, verify_password, hash_password
from app.models.user import User
from app.schemas.user import UserOut, UserMeUpdate, PasswordChange
import structlog

logger = structlog.get_logger()
router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserOut)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/me", response_model=UserOut)
async def update_me(
    body: UserMeUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    values = body.model_dump(exclude_unset=True)
    if not values:
        return current_user

    if "email" in values and values["email"] != current_user.email:
        dup = await db.execute(
            select(User).where(User.email == values["email"], User.id != current_user.id)
        )
        if dup.scalar_one_or_none():
            raise HTTPException(status_code=409, detail="Email already in use")

    await db.execute(update(User).where(User.id == current_user.id).values(**values))
    result = await db.execute(select(User).where(User.id == current_user.id))
    return result.scalar_one()


@router.put("/me/password")
async def update_my_password(
    body: PasswordChange,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    await db.execute(
        update(User).where(User.id == current_user.id).values(
            hashed_password=hash_password(body.new_password),
            force_password_change=False,
        )
    )
    return {"message": "Password updated successfully"}

"""
User management endpoints for admins.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import models, schemas
from app.database.session import get_db
from app.core.security import get_current_active_superuser

router = APIRouter()


@router.get("/", response_model=List[schemas.User])
async def list_users(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_superuser),
    skip: int = 0,
    limit: int = 100,
) -> List[schemas.User]:
    """
    Retrieve all users. Admin only.
    """
    result = await db.execute(
        select(models.User).offset(skip).limit(limit)
    )
    users = result.scalars().all()
    return list(users)


@router.get("/{user_id}", response_model=schemas.User)
async def get_user(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_superuser),
    user_id: int,
) -> schemas.User:
    """
    Get a specific user by ID. Admin only.
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/{user_id}", response_model=schemas.User)
async def update_user(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_superuser),
    user_id: int,
    user_in: schemas.UserUpdate,
) -> schemas.User:
    """
    Update a user. Admin only.
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = user_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "password":
            from app.core.security import get_password_hash
            value = get_password_hash(value)
            field = "hashed_password"
        setattr(user, field, value)

    await db.commit()
    await db.refresh(user)
    return user
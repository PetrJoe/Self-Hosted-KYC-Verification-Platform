"""
Authentication endpoints for user registration and login.
"""

import uuid
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import models, schemas
from app.core import security
from app.core.config import settings
from app.database.session import get_db

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


@router.post("/register", response_model=schemas.User)
async def register(
    *,
    db: AsyncSession = Depends(get_db),
    user_in: schemas.UserCreate,
) -> Any:
    """
    Register a new user/business for the KYC platform.
    """
    # Check if user already exists
    result = await db.execute(
        select(models.User).where(models.User.email == user_in.email)
    )
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists."
        )

    # Create new user
    user = models.User(
        email=user_in.email,
        hashed_password=security.get_password_hash(user_in.password),
        company_name=user_in.company_name,
        full_name=user_in.full_name,
        api_key=str(uuid.uuid4()).replace("-", ""),
        is_active=True,
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Log audit event
    audit_log = models.AuditLog(
        user_id=user.id,
        action="user_registered",
        resource="user",
        details={"email": user.email, "company": user.company_name}
    )
    db.add(audit_log)
    await db.commit()

    return user


@router.post("/login", response_model=schemas.Token)
async def login(
    db: AsyncSession = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login, get an access token for future requests.
    """
    result = await db.execute(
        select(models.User).where(models.User.email == form_data.username)
    )
    user = result.scalars().first()

    if not user or not security.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email or password"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = security.create_access_token(
        user.id, expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.get("/me", response_model=schemas.User)
async def read_users_me(
    current_user: models.User = Depends(security.get_current_user),
) -> Any:
    """
    Get current user information.
    """
    return current_user


@router.post("/generate-api-key", response_model=dict)
async def generate_api_key(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
) -> Any:
    """
    Generate a new API key for the current user.
    """
    # Generate new API key
    new_api_key = security.create_api_key()

    # Update user with new API key
    current_user.api_key = new_api_key
    await db.commit()

    # Log audit event
    audit_log = models.AuditLog(
        user_id=current_user.id,
        action="api_key_generated",
        resource="user",
        details={"user_id": current_user.id}
    )
    db.add(audit_log)
    await db.commit()

    return {"api_key": new_api_key, "message": "New API key generated successfully"}


@router.delete("/api-key")
async def revoke_api_key(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(security.get_current_user),
) -> Any:
    """
    Revoke the current API key (sets it to None).
    """
    current_user.api_key = None
    await db.commit()

    # Log audit event
    audit_log = models.AuditLog(
        user_id=current_user.id,
        action="api_key_revoked",
        resource="user",
        details={"user_id": current_user.id}
    )
    db.add(audit_log)
    await db.commit()

    return {"message": "API key revoked successfully"}




async def get_current_active_superuser(
    current_user: models.User = Depends(security.get_current_user),
) -> models.User:
    """
    Dependency to get the current active superuser.
    """
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=400, detail="The user doesn't have enough privileges"
        )
    return current_user
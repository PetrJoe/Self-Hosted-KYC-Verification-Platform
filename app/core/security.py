"""
Security utilities for password hashing, JWT tokens, and authentication.
"""

from datetime import datetime, timedelta
from typing import Any, Union

import jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from jwt import PyJWTError
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app import models
from app.database.session import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/login")


def get_api_key_from_header(request: Request) -> str:
    """Extract API key from request headers."""
    api_key = request.headers.get("X-API-Key")
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "API-Key"},
        )
    return api_key


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password for storing."""
    return pwd_context.hash(password)


def create_access_token(
    subject: Union[str, Any], expires_delta: timedelta = None
) -> str:
    """Create JWT access token."""
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    to_encode = {"exp": expire, "sub": str(subject)}
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm="HS256")
    return encoded_jwt


async def get_current_user(
    db: AsyncSession = Depends(get_db), token: str = Depends(oauth2_scheme)
) -> models.User:
    """Get current user from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except PyJWTError:
        raise credentials_exception

    result = await db.execute(
        select(models.User).where(models.User.id == username)
    )
    user = result.scalars().first()
    if user is None:
        raise credentials_exception
    return user


def create_api_key() -> str:
    """Generate a new API key."""
    import uuid
    return str(uuid.uuid4()).replace("-", "")


def verify_api_key(api_key: str) -> bool:
    """Verify API key format (basic validation)."""
    import re
    return bool(re.match(r'^[a-f0-9]{32}$', api_key))


async def get_current_user_from_api_key(
    request: Request = None,
    db: AsyncSession = Depends(get_db)
) -> models.User:
    """
    Get current user from API key.
    Use: Depends(get_current_user_from_api_key)
    """
    if request is None:
        raise HTTPException(status_code=400, detail="Request object required")

    api_key = get_api_key_from_header(request)

    # Validate API key format
    if not verify_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid API key format")

    # Find user with this API key
    result = await db.execute(
        select(models.User).where(
            models.User.api_key == api_key,
            models.User.is_active == True
        )
    )
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=401, detail="Invalid API key")

    return user


async def get_current_active_user(
    current_user: models.User = Depends(get_current_user)
) -> models.User:
    """
    Dependency to get the current active user.
    """
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user
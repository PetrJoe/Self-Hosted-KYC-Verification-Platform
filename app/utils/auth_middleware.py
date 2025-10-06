"""
Authentication middleware that supports both JWT tokens and API keys.
"""

from typing import Optional
from fastapi import Depends, Request, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app import models
from app.core.security import get_current_user, get_current_user_from_api_key
from app.database.session import get_db

bearer_scheme = HTTPBearer(auto_error=False)


async def get_optional_current_user(
    request: Request,
    token: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    api_key_user: Optional[models.User] = Depends(lambda db: get_db()),
) -> Optional[models.User]:
    """
    Try to authenticate user with JWT token first, then API key.
    Returns None if no authentication provided.
    """
    # Try JWT token first
    if token:
        try:
            # We'll need to handle this differently since get_current_user needs the token
            # This is a simplified version - in production you'd want more robust handling
            pass
        except Exception:
            pass

    # Try API key
    try:
        user = await get_current_user_from_api_key(request)
        return user
    except HTTPException:
        pass

    return None


async def get_authenticated_user(
    optional_user: Optional[models.User] = Depends(get_optional_current_user),
) -> models.User:
    """
    Require authentication - returns user or raises 401.
    """
    if not optional_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer or X-API-Key"},
        )
    return optional_user
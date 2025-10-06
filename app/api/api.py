"""
Main API router that combines all API endpoints.
"""

from fastapi import APIRouter

from app.api.endpoints import (
    verification,
    auth,
    users,
    metrics,
    health
)

api_router = APIRouter()

# Include all API endpoint routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["authentication"]
)

api_router.include_router(
    verification.router,
    prefix="/verify",
    tags=["verification"]
)

api_router.include_router(
    users.router,
    prefix="/users",
    tags=["users"]
)

api_router.include_router(
    metrics.router,
    prefix="/metrics",
    tags=["metrics"]
)

api_router.include_router(
    health.router,
    prefix="/health",
    tags=["health"]
)
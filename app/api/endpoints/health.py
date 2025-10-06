"""
Health check endpoints.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/", summary="Health Check")
async def health_check():
    """Basic health check endpoint."""
    return {"status": "healthy", "service": "KYC Verification Platform"}
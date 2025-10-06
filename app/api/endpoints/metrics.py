"""
Metrics and analytics endpoints for admin dashboard.
"""

from datetime import datetime, timedelta
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, desc

from app import models
from app.database.session import get_db
from app.core.security import get_current_active_superuser

router = APIRouter()


@router.get("/", summary="Get Platform Metrics")
async def get_metrics(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_superuser),
) -> Dict[str, Any]:
    """
    Get overall platform metrics and analytics.
    Admin endpoint for dashboard statistics.
    """
    # Get total verifications
    total_verifications = await db.execute(
        select(func.count(models.Verification.id))
    )
    total = total_verifications.scalar()

    # Get verifications by status
    status_stats = await db.execute(
        select(
            models.Verification.status,
            func.count(models.Verification.id)
        ).group_by(models.Verification.status)
    )
    status_counts = dict(status_stats.all())

    # Get recent activity (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    recent_verifications = await db.execute(
        select(func.count(models.Verification.id)).where(
            models.Verification.created_at >= thirty_days_ago
        )
    )
    recent_count = recent_verifications.scalar()

    # Average processing time
    avg_processing_time = await db.execute(
        select(func.avg(models.Verification.processing_time)).where(
            models.Verification.processing_time.isnot(None)
        )
    )
    avg_time = avg_processing_time.scalar()

    return {
        "total_verifications": total,
        "verifications_by_status": status_counts,
        "recent_verifications": recent_count,
        "average_processing_time_seconds": round(float(avg_time or 0), 2),
        "timestamp": datetime.utcnow()
    }
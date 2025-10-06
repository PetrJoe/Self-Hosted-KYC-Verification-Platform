"""
KYC verification endpoints for document and biometric verification.
"""

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app import models, schemas
from app.database.session import get_db
from app.services.verification_service import verification_service
from app.services.security_service import security_service
from app.core.security import get_current_active_user
from fastapi import Request

router = APIRouter()


async def process_verification_background(
    verification_id: int,
    id_document,
    selfie_video
):
    """
    Background task to process verification.
    """
    # Create new database session for background task
    db = get_db()  # This gets a new session generator
    async with db as session:
        try:
            # Get verification record
            result = await session.execute(
                select(models.Verification).where(models.Verification.id == verification_id)
            )
            verification = result.scalars().first()

            if not verification:
                return

            # Mark as processing
            verification.status = "processing"
            await session.commit()

            # Process verification
            result = await verification_service.process_verification(
                str(verification.session_id),
                id_document,
                selfie_video
            )

            # Update verification record with results
            verification.status = "completed" if result.get("status") == "completed" else "failed"
            verification.document_valid = result.get("document_valid", False)
            verification.face_match_score = result.get("face_match_score", 0.0)
            verification.liveness_score = result.get("liveness_score", 0.0)
            verification.decision = result.get("decision", "rejected")
            verification.decision_reason = result.get("decision_reason", "")
            verification.processing_time = result.get("processing_time", 0.0)

            # Extract additional data if available
            if "extracted_data" in result:
                verification.extracted_data = result["extracted_data"]

            await session.commit()

            # Log audit event
            audit_log = models.AuditLog(
                user_id=verification.user_id,
                verification_id=verification.id,
                action="verification_completed",
                resource="verification",
                details={
                    "decision": verification.decision,
                    "document_valid": verification.document_valid,
                    "processing_time": verification.processing_time
                }
            )
            session.add(audit_log)
            await session.commit()

        except Exception as e:
            # Update verification status on error
            try:
                verification.status = "failed"
                verification.decision = "rejected"
                verification.decision_reason = f"Processing error: {str(e)}"
                await session.commit()
            except:
                pass


@router.post("/upload", response_model=schemas.Verification)
async def upload_verification_files(
    *,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    background_tasks: BackgroundTasks,
    id_document: UploadFile = File(...),
    selfie_video: UploadFile = File(...),
) -> Any:
    """
    Upload ID document and selfie video for KYC verification.
    """
    # Create verification record
    session_id = str(uuid.uuid4())

    verification = models.Verification(
        session_id=session_id,
        user_id=current_user.id,
        status="processing",
        client_ip=str(request.client.host),
        user_agent=request.headers.get("User-Agent"),
    )

    db.add(verification)
    await db.commit()
    await db.refresh(verification)

    # Audit log the verification creation
    await security_service.audit_log_event(
        "verification_created",
        user_id=current_user.id,
        verification_id=verification.id,
        details={
            "document_filename": id_document.filename,
            "selfie_filename": selfie_video.filename,
            "session_id": session_id
        },
        ip_address=str(request.client.host),
        user_agent=request.headers.get("User-Agent")
    )

    # Add background task for processing verification
    background_tasks.add_task(
        process_verification_background,
        verification.id,
        id_document,
        selfie_video
    )

    return verification


@router.get("/status/{session_id}", response_model=schemas.VerificationResult)
async def get_verification_status(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    session_id: str,
) -> Any:
    """
    Get the status and result of a verification request.
    """
    result = await db.execute(
        select(models.Verification).where(
            models.Verification.session_id == session_id,
            models.Verification.user_id == current_user.id
        )
    )
    verification = result.scalars().first()

    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    return verification


@router.get("/history", response_model=list[schemas.Verification])
async def get_verification_history(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Get verification history for the current user.
    """
    result = await db.execute(
        select(models.Verification).where(
            models.Verification.user_id == current_user.id
        ).offset(skip).limit(limit).order_by(models.Verification.created_at.desc())
    )
    verifications = result.scalars().all()

    return list(verifications)


@router.post("/review/{session_id}", response_model=schemas.Verification)
async def manual_review_verification(
    *,
    db: AsyncSession = Depends(get_db),
    current_user: models.User = Depends(lambda: get_current_active_user()),
    session_id: str,
    review_in: schemas.VerificationUpdate,
) -> Any:
    """
    Manually review a verification request (admin/reviewers only).
    """
    result = await db.execute(
        select(models.Verification).where(models.Verification.session_id == session_id)
    )
    verification = result.scalars().first()

    if not verification:
        raise HTTPException(status_code=404, detail="Verification not found")

    # Update verification with review results
    update_data = review_in.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(verification, field, value)

    verification.reviewer_id = current_user.id
    verification.reviewed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(verification)

    return verification
"""
Pydantic schemas for verification-related API operations.
"""

from datetime import datetime
from typing import Optional, Dict, Any

from pydantic import BaseModel


class VerificationBase(BaseModel):
    document_type: Optional[str] = None


class VerificationCreate(VerificationBase):
    pass


class VerificationUpdate(BaseModel):
    status: Optional[str] = None
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    reviewer_id: Optional[int] = None
    review_notes: Optional[str] = None


class VerificationInDBBase(VerificationBase):
    id: int
    session_id: str
    user_id: int
    document_valid: Optional[bool] = None
    extracted_data: Optional[Dict[str, Any]] = None
    document_confidence: Optional[float] = None
    face_match_score: Optional[float] = None
    liveness_score: Optional[float] = None
    status: str
    decision: Optional[str] = None
    decision_reason: Optional[str] = None
    processing_time: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class Verification(VerificationInDBBase):
    pass


class VerificationResult(VerificationInDBBase):
    """
    Verification result returned to API consumers.
    Includes key decision metrics.
    """
    document_valid: bool = False
    face_match_score: float = 0.0
    liveness_score: float = 0.0
    decision: str = "rejected"


class VerificationUpload(BaseModel):
    """Schema for file upload in verification requests."""
    document_file: bytes
    selfie_video_file: bytes
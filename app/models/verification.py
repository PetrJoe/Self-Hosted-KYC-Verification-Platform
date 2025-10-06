"""
Verification model for KYC verification requests and results.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database.session import Base


class Verification(Base):
    """
    Model for storing KYC verification requests and their processing results.
    """

    __tablename__ = "verifications"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(36), unique=True, index=True, nullable=False)

    # User relationship
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # File storage paths (MinIO/S3)
    id_document_path = Column(String(500), nullable=True)
    selfie_video_path = Column(String(500), nullable=True)
    processed_images_path = Column(JSON, nullable=True)  # Store paths as JSON

    # Document processing results
    document_type = Column(String(50), nullable=True)  # "passport", "drivers_license", "national_id"
    document_valid = Column(Boolean, default=False)
    extracted_data = Column(JSON, nullable=True)  # OCR/MRZ extracted fields
    document_confidence = Column(Float, nullable=True)

    # Face processing results
    face_detected = Column(Boolean, default=False)
    face_embedding = Column(Text, nullable=True)  # Base64 encoded embeddings
    face_match_score = Column(Float, nullable=True)
    face_match_confidence = Column(Float, nullable=True)

    # Liveness detection results
    liveness_score = Column(Float, nullable=True)
    liveness_passed = Column(Boolean, default=False)
    liveness_method = Column(String(50), nullable=True)  # "active", "passive"

    # Final decision
    status = Column(String(20), default="pending")  # "pending", "processing", "verified", "rejected", "manual_review"
    decision = Column(String(20), nullable=True)  # "verified", "rejected", "manual_review"
    decision_reason = Column(Text, nullable=True)

    # Metadata
    client_ip = Column(String(45), nullable=True)  # IPv4/IPv6
    user_agent = Column(Text, nullable=True)
    processing_time = Column(Float, nullable=True)  # seconds

    # Review information (for manual review)
    reviewer_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_notes = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="verifications")
    reviewer = relationship("User", foreign_keys=[reviewer_id])

    def __repr__(self):
        return f"<Verification(id={self.id}, session_id={self.session_id}, status={self.status})>"


class AuditLog(Base):
    """
    Audit log for all verification activities and system events.
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    verification_id = Column(Integer, ForeignKey("verifications.id"), nullable=True)
    action = Column(String(100), nullable=False)  # "created", "processed", "reviewed", etc.
    resource = Column(String(100), nullable=False)  # "verification", "user", "system"
    details = Column(JSON, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", foreign_keys=[user_id])
    verification = relationship("Verification")

    def __repr__(self):
        return f"<AuditLog(action={self.action}, resource={self.resource})>"
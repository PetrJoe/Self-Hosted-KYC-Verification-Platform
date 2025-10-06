"""
Verification service for KYC document and biometric processing.
Handles document upload, processing, and result aggregation.
"""

import os
import shutil
import tempfile
from pathlib import Path
from typing import Tuple, Dict, Any
import logging

from app.core.config import settings
from app.services.document_service import document_service
from app.services.face_service import face_service
from app.services.liveness_service import liveness_service

logger = logging.getLogger(__name__)


class VerificationService:
    """Service for handling KYC verification processing."""

    def __init__(self):
        self.upload_dir = Path("uploads/verifications")
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    async def process_verification(
        self,
        session_id: str,
        id_document,
        selfie_video
    ) -> Dict[str, Any]:
        """
        Process a KYC verification request.

        Args:
            session_id: Unique session identifier
            id_document: UploadFile for ID document
            selfie_video: UploadFile for selfie video

        Returns:
            Dict containing processing results
        """
        try:
            logger.info(f"Starting verification processing for session {session_id}")

            # Save uploaded files
            id_path, selfie_path = await self._save_uploaded_files(
                session_id, id_document, selfie_video
            )

            # Process document
            document_result = await self._process_document(id_path)

            # Process face verification
            face_result = await self._process_face_verification(id_path, selfie_path)

            # Process liveness detection
            liveness_result = await self._process_liveness_detection(selfie_path)

            # Aggregate results and make decision
            final_result = await self._aggregate_results(
                document_result, face_result, liveness_result
            )

            # Log processing completion
            logger.info(f"Verification processing completed for session {session_id}")

            return final_result

        except Exception as e:
            logger.error(f"Error processing verification {session_id}: {str(e)}")
            return {
                "status": "failed",
                "error": str(e),
                "decision": "rejected"
            }

    async def _save_uploaded_files(
        self, session_id: str, id_document, selfie_video
    ) -> Tuple[Path, Path]:
        """Save uploaded files to temporary storage."""
        session_dir = self.upload_dir / session_id
        session_dir.mkdir(exist_ok=True)

        # Save ID document
        id_path = session_dir / f"id_{id_document.filename}"
        with open(id_path, "wb") as f:
            content = await id_document.read()
            f.write(content)

        # Save selfie video
        selfie_path = session_dir / f"selfie_{selfie_video.filename}"
        with open(selfie_path, "wb") as f:
            content = await selfie_video.read()
            f.write(content)

        return id_path, selfie_path

    async def _process_document(self, id_path: Path) -> Dict[str, Any]:
        """
        Process ID document - OCR and validation using DocumentService.
        """
        try:
            # Use the document service to process the image
            result = await document_service.process_document(id_path)

            return {
                "document_valid": result.get("document_valid", False),
                "document_type": result.get("document_type", "unknown"),
                "extracted_data": result.get("extracted_data", {}),
                "confidence": result.get("confidence", 0.0),
                "error": result.get("error") if "error" in result else None
            }

        except Exception as e:
            logger.error(f"Document processing error: {str(e)}")
            return {
                "document_valid": False,
                "document_type": "unknown",
                "extracted_data": {},
                "confidence": 0.0,
                "error": str(e)
            }

    async def _process_face_verification(
        self, id_path: Path, selfie_path: Path
    ) -> Dict[str, Any]:
        """
        Process face matching between ID document and selfie.
        """
        try:
            # Extract face from ID document
            doc_face_result = await face_service.extract_face_from_document(id_path)

            if not doc_face_result['face_detected']:
                return {
                    "face_detected": False,
                    "face_match_score": 0.0,
                    "confidence": 0.0,
                    "error": "No face detected in ID document"
                }

            # Extract face from selfie video
            selfie_face_result = await face_service.extract_face_from_selfie(selfie_path)

            if not selfie_face_result['face_detected']:
                return {
                    "face_detected": True,  # ID face detected
                    "face_match_score": 0.0,
                    "confidence": doc_face_result['confidence'],
                    "error": "No face detected in selfie"
                }

            # Compare face embeddings
            similarity_score = await face_service.compare_faces(
                doc_face_result['embedding'],
                selfie_face_result['embedding']
            )

            # Calculate overall confidence
            overall_confidence = (
                doc_face_result['confidence'] * 0.4 +
                selfie_face_result['confidence'] * 0.4 +
                similarity_score * 0.2
            )

            return {
                "face_detected": True,
                "face_match_score": similarity_score,
                "confidence": overall_confidence,
                "document_face_confidence": doc_face_result['confidence'],
                "selfie_face_confidence": selfie_face_result['confidence']
            }

        except Exception as e:
            logger.error(f"Face verification error: {str(e)}")
            return {
                "face_detected": False,
                "face_match_score": 0.0,
                "confidence": 0.0,
                "error": str(e)
            }

    async def _process_liveness_detection(self, selfie_path: Path) -> Dict[str, Any]:
        """
        Process liveness detection on selfie video.
        """
        try:
            # Use passive liveness detection by default
            result = await liveness_service.detect_liveness(selfie_path, "passive")

            return {
                "liveness_detected": result.get("liveness_detected", False),
                "liveness_score": result.get("liveness_score", 0.0),
                "method": result.get("method", "passive"),
                "confidence": result.get("confidence", 0.0),
                "indicators": result.get("indicators", {}),
                "error": result.get("error")
            }

        except Exception as e:
            logger.error(f"Liveness detection error: {str(e)}")
            return {
                "liveness_detected": False,
                "liveness_score": 0.0,
                "method": "unknown",
                "confidence": 0.0,
                "error": str(e)
            }

    async def _aggregate_results(
        self,
        document_result: Dict[str, Any],
        face_result: Dict[str, Any],
        liveness_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Aggregate verification results and make final decision.
        """
        try:
            # Extract key metrics
            doc_valid = document_result.get("document_valid", False)
            doc_confidence = document_result.get("confidence", 0.0)
            face_detected = face_result.get("face_detected", False)
            face_score = face_result.get("face_match_score", 0.0)
            face_confidence = face_result.get("confidence", 0.0)
            liveness_passed = liveness_result.get("liveness_detected", False)
            liveness_score = liveness_result.get("liveness_score", 0.0)

            # Decision logic
            face_threshold = settings.FACE_MODEL_THRESHOLD  # 0.6
            liveness_threshold = settings.LIVENESS_CONFIDENCE_THRESHOLD  # 0.9

            # Check basic requirements
            if not doc_valid:
                decision = "rejected"
                reason = "Invalid document"
            elif not face_detected:
                decision = "rejected"
                reason = "No face detected"
            elif not liveness_passed:
                decision = "rejected"
                reason = "Liveness detection failed"
            elif face_score < face_threshold:
                decision = "rejected"
                reason = "Face match insufficient"
            elif face_score >= 0.8 and liveness_score >= liveness_threshold and doc_confidence >= 0.7:
                decision = "verified"
                reason = "All checks passed"
            else:
                decision = "manual_review"
                reason = "Requires manual review"

            return {
                "status": "completed",
                "document_valid": doc_valid,
                "face_match_score": face_score,
                "liveness_score": liveness_score,
                "decision": decision,
                "decision_reason": reason,
                "processing_time": 2.5  # Placeholder
            }

        except Exception as e:
            logger.error(f"Result aggregation error: {str(e)}")
            return {
                "status": "failed",
                "decision": "rejected",
                "error": str(e)
            }


# Global service instance
verification_service = VerificationService()
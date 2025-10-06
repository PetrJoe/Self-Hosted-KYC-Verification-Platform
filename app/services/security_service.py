"""
Security service for data encryption, compliance, and audit logging.
Ensures data protection and regulatory compliance.
"""

import hashlib
import hmac
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any
import logging

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

from app.core.config import settings

logger = logging.getLogger(__name__)


class SecurityService:
    """Service for data security, encryption, and compliance."""

    def __init__(self):
        self.encryption_key = settings.ENCRYPTION_KEY
        self.fernet = self._setup_encryption()
        self.compliance_retention_days = 30  # Configurable retention period

    def _setup_encryption(self) -> Fernet:
        """Set up encryption using Fernet (AES 128)."""
        if not self.encryption_key:
            logger.warning("No encryption key provided, using default (not secure)")
            self.encryption_key = "default-key-change-in-production-32chars"

        # Ensure key is 32 bytes for Fernet
        key_bytes = self.encryption_key.encode()
        if len(key_bytes) != 32:
            # Use PBKDF2 to derive a 32-byte key
            salt = b'static_salt'  # In production, use a proper salt
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
            )
            key_bytes = kdf.derive(key_bytes)

        return Fernet(base64.urlsafe_b64encode(key_bytes))

    def encrypt_data(self, data: str) -> str:
        """Encrypt sensitive data."""
        try:
            encrypted = self.fernet.encrypt(data.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise

    def decrypt_data(self, encrypted_data: str) -> str:
        """Decrypt sensitive data."""
        try:
            decrypted = self.fernet.decrypt(encrypted_data.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise

    def hash_data(self, data: str, salt: Optional[str] = None) -> str:
        """Create SHA-256 hash of data with optional salt."""
        if salt:
            data = salt + data

        return hashlib.sha256(data.encode()).hexdigest()

    def generate_data_fingerprint(self, data: Dict[str, Any]) -> str:
        """Generate fingerprint for data integrity verification."""
        # Convert data to string representation for hashing
        data_str = str(sorted(data.items()))
        return self.hash_data(data_str)

    async def audit_log_event(
        self,
        event_type: str,
        user_id: Optional[int] = None,
        verification_id: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> None:
        """
        Log audit event for compliance.

        Args:
            event_type: Type of event (e.g., "user_login", "verification_created")
            user_id: ID of user performing action
            verification_id: Related verification ID
            details: Additional event details
            ip_address: Client IP address
            user_agent: Client user agent
        """
        from sqlalchemy.ext.asyncio import AsyncSession
        from app.database.session import get_db
        from app import models

        try:
            async with get_db() as session:
                audit_log = models.AuditLog(
                    user_id=user_id,
                    verification_id=verification_id,
                    action=event_type,
                    resource=self._get_resource_from_event(event_type),
                    details=details or {},
                    ip_address=ip_address,
                    user_agent=user_agent,
                    timestamp=datetime.utcnow()
                )

                session.add(audit_log)
                await session.commit()

                logger.info(f"Audit log: {event_type} by user {user_id}")

        except Exception as e:
            logger.error(f"Failed to create audit log: {e}")

    def _get_resource_from_event(self, event_type: str) -> str:
        """Extract resource type from event type."""
        if "user" in event_type:
            return "user"
        elif "verification" in event_type:
            return "verification"
        elif "system" in event_type:
            return "system"
        elif "api" in event_type:
            return "api"
        else:
            return "unknown"

    async def check_data_retention_policy(self) -> Dict[str, Any]:
        """
        Check for data that needs to be deleted based on retention policy.

        Returns:
            Dict with cleanup statistics
        """
        from sqlalchemy.ext.asyncio import AsyncSession
        from sqlalchemy.future import select
        from app.database.session import get_db
        from app import models

        cutoff_date = datetime.utcnow() - timedelta(days=self.compliance_retention_days)

        async with get_db() as session:
            try:
                # Find old verifications
                result = await session.execute(
                    select(models.Verification).where(
                        models.Verification.created_at < cutoff_date,
                        models.Verification.status.in_(["completed", "rejected"])
                    )
                )
                old_verifications = result.scalars().all()

                deleted_count = 0
                for verification in old_verifications:
                    # In a real implementation, you might want to:
                    # 1. Anonymize the data instead of deleting
                    # 2. Archive to long-term storage
                    # 3. Delete associated files

                    # For now, just mark as deleted (soft delete)
                    verification.status = "deleted"
                    verification.updated_at = datetime.utcnow()

                    deleted_count += 1

                    # Log deletion
                    await self.audit_log_event(
                        "data_retention_cleanup",
                        verification_id=verification.id,
                        details={"retention_days": self.compliance_retention_days}
                    )

                await session.commit()

                return {
                    "cleanup_completed": True,
                    "records_processed": len(old_verifications),
                    "records_deleted": deleted_count,
                    "retention_days": self.compliance_retention_days,
                    "cutoff_date": cutoff_date.isoformat()
                }

            except Exception as e:
                logger.error(f"Data retention cleanup failed: {e}")
                return {
                    "cleanup_completed": False,
                    "error": str(e)
                }

    async def mask_sensitive_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Mask sensitive data for logging and display purposes.
        Follows GDPR principles for data minimization.
        """
        masked_data = data.copy()

        # Fields to mask
        sensitive_fields = [
            'passport_number', 'id_number', 'social_security_number',
            'drivers_license_number', 'bank_account', 'credit_card'
        ]

        for field in sensitive_fields:
            if field in masked_data and isinstance(masked_data[field], str):
                value = masked_data[field]
                if len(value) > 4:
                    # Mask all but last 4 characters
                    masked_data[field] = '*' * (len(value) - 4) + value[-4:]
                else:
                    masked_data[field] = '*' * len(value)

        # Mask face embeddings (they are just numbers)
        if 'face_embedding' in masked_data:
            masked_data['face_embedding'] = '[REDACTED]'

        return masked_data

    async def validate_request_compliance(
        self,
        request_data: Dict[str, Any],
        ip_address: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Validate request for compliance requirements.

        Args:
            request_data: Request data to validate
            ip_address: Client IP address

        Returns:
            Dict with validation results
        """
        violations = []
        warnings = []

        # Check for suspicious patterns
        if self._has_suspicious_patterns(request_data):
            violations.append("Suspicious data patterns detected")

        # Check rate limiting (basic)
        if ip_address:
            rate_check = await self._check_rate_limit(ip_address)
            if not rate_check['allowed']:
                violations.append(f"Rate limit exceeded: {rate_check['reason']}")

        # Check data quality
        quality_check = self._check_data_quality(request_data)
        warnings.extend(quality_check['warnings'])

        return {
            'compliant': len(violations) == 0,
            'violations': violations,
            'warnings': warnings,
            'recommendations': self._generate_compliance_recommendations(violations, warnings)
        }

    def _has_suspicious_patterns(self, data: Dict[str, Any]) -> bool:
        """Check for potentially suspicious data patterns."""
        # This is a basic implementation - in production you'd have more sophisticated checks

        suspicious_indicators = [
            # Common test/placeholder data
            "test", "dummy", "sample", "example", "123456789",
            # Obviously fake data
            "999999999", "ABCDEFGHI",
        ]

        text_data = str(data).lower()

        for indicator in suspicious_indicators:
            if indicator in text_data:
                return True

        return False

    async def _check_rate_limit(self, ip_address: str) -> Dict[str, Any]:
        """Basic rate limiting check."""
        # In a production system, you'd use Redis or similar for rate limiting
        # This is a simplified version

        # For now, always allow (implement proper rate limiting)
        return {
            'allowed': True,
            'remaining': 100,
            'reset_time': datetime.utcnow() + timedelta(minutes=1)
        }

    def _check_data_quality(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Check data quality for compliance."""
        warnings = []

        # Check for missing required fields
        required_fields = ['id_document', 'selfie_video']  # Simplify for demo
        for field in required_fields:
            if field not in data:
                warnings.append(f"Missing required field: {field}")

        # Check file sizes (basic)
        if 'file_size' in data and data['file_size'] > 50 * 1024 * 1024:  # 50MB
            warnings.append("File size exceeds recommended limit")

        return {'warnings': warnings}

    def _generate_compliance_recommendations(
        self, violations: list, warnings: list
    ) -> list:
        """Generate compliance recommendations."""
        recommendations = []

        if violations:
            recommendations.append("Address security violations before proceeding")
            recommendations.append("Consider additional verification steps")

        if warnings:
            recommendations.append("Review data quality warnings")
            recommendations.append("Consider enhanced data validation")

        if not violations and not warnings:
            recommendations.append("Request appears compliant")

        return recommendations

    def generate_privacy_notice(self) -> Dict[str, Any]:
        """
        Generate privacy notice for GDPR compliance.
        """
        return {
            "title": "KYC Verification Privacy Notice",
            "data_collected": [
                "Identity document images",
                "Selfie videos",
                "IP addresses",
                "Device information"
            ],
            "data_usage": [
                "Identity verification",
                "Fraud prevention",
                "Service improvement"
            ],
            "retention_period": f"{self.compliance_retention_days} days",
            "data_rights": [
                "Right to access",
                "Right to rectification",
                "Right to erasure",
                "Right to data portability"
            ],
            "contact": "privacy@kycplatform.com"
        }


# Global security service instance
security_service = SecurityService()
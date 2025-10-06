"""
User model for authentication and authorization.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.orm import relationship

from app.database.session import Base


class User(Base):
    """
    User model for businesses/developers using the KYC platform.
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # Business information
    company_name = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)

    # API key for authentication
    api_key = Column(String(64), unique=True, index=True, nullable=True)

    # Audit fields
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    verifications = relationship("Verification", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
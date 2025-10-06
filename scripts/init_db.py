#!/usr/bin/env python3
"""
Database initialization script for KYC Verification Platform.
Creates database tables and optionally adds initial data.
"""

import asyncio
import logging

from app.core.config import settings
from app.database.session import Base, get_db
from app import models
from app.core.security import get_password_hash

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_tables():
    """Create all database tables."""
    logger.info("Creating database tables...")
    async with get_db() as session:
        async with session.begin():
            # Create tables using SQLAlchemy metadata
            await session.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully.")


async def create_superuser():
    """Create a default superuser for testing."""
    logger.info("Creating default superuser...")
    async with get_db() as session:
        # Check if superuser already exists
        from sqlalchemy.future import select
        result = await session.execute(
            select(models.User).where(models.User.email == "admin@kycplatform.com")
        )
        existing_user = result.scalars().first()

        if existing_user:
            logger.info("Superuser already exists.")
            return

        # Create default superuser
        superuser = models.User(
            email="admin@kycplatform.com",
            hashed_password=get_password_hash("admin123"),
            company_name="KYC Platform",
            full_name="Administrator",
            api_key="admin-key-123456789",
            is_active=True,
            is_superuser=True,
        )

        session.add(superuser)
        await session.commit()
        await session.refresh(superuser)

        logger.info("Superuser created with email: admin@kycplatform.com, password: admin123")


async def main():
    """Run database initialization."""
    logger.info("Starting database initialization...")

    try:
        await create_tables()
        await create_superuser()
        logger.info("Database initialization completed successfully.")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
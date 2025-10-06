#!/usr/bin/env python3
"""
Test script to verify database setup and connectivity.
"""

import asyncio
import logging

from app.core.config import settings
from app.database.session import get_db
from app import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database():
    """Test database connectivity and operations."""
    logger.info("Testing database connectivity...")

    try:
        async with get_db() as session:
            # Test basic connection
            result = await session.execute(
                "SELECT 1 as test"
            )
            test_result = result.scalar()
            logger.info(f"Database connection test: {test_result}")

            # Try to query users table
            from sqlalchemy.future import select
            result = await session.execute(
                select(models.User).limit(1)
            )
            user = result.scalars().first()
            logger.info(f"Sample user query successful: {user}")

    except Exception as e:
        logger.error(f"Database test failed: {e}")
        raise

    logger.info("Database tests completed successfully.")


if __name__ == "__main__":
    asyncio.run(test_database())
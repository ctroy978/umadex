#!/usr/bin/env python3
"""
Test the actual API endpoint with authentication
"""
import asyncio
import logging
import sys
import time
import json
from uuid import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.append('/app')

from app.core.database import get_db, set_rls_context
from app.models.user import User
from app.utils.deps import get_current_user
from app.api.v1.student import start_vocabulary_challenge, require_student_or_teacher
from fastapi import Depends

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = "postgresql+asyncpg://umadex_user:umadex_password@postgres:5432/umadex"
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def test_api_endpoint_directly():
    """Test the API endpoint logic directly"""
    
    vocabulary_list_id = UUID("b89cb43e-6c43-4051-91c4-88bc5d05ac42")  # "Bit of a big test"
    student_id = UUID("6cbf47a1-a88b-4c22-b3c2-fbe982abaf66")  # aggi coop
    
    logger.info(f"Testing API endpoint for vocabulary list {vocabulary_list_id} and student {student_id}")
    
    async with AsyncSessionLocal() as db:
        try:
            # Set RLS context for the student
            await set_rls_context(db, str(student_id), "acoop@csd8.info", False)
            
            # Get the student user object
            from sqlalchemy import select
            result = await db.execute(
                select(User).where(User.id == student_id)
            )
            current_user = result.scalar_one()
            
            logger.info("Starting API endpoint call...")
            start_time = time.time()
            
            # Call the actual API endpoint function
            response = await start_vocabulary_challenge(
                assignment_id=vocabulary_list_id,
                current_user=current_user,
                db=db
            )
            
            end_time = time.time()
            logger.info(f"API endpoint completed in {end_time - start_time:.2f} seconds")
            logger.info(f"Response: {response}")
            
        except Exception as e:
            logger.error(f"Error during API endpoint test: {str(e)}", exc_info=True)
            raise

if __name__ == "__main__":
    asyncio.run(test_api_endpoint_directly())
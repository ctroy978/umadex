#!/usr/bin/env python3
"""
Test script to debug vocabulary challenge hang
"""
import asyncio
import logging
import sys
import os
import time
from uuid import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.append('/app')

from app.core.config import settings
from app.services.vocabulary_practice import VocabularyPracticeService
from app.core.database import set_rls_context

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = "postgresql+asyncpg://umadex_user:umadex_password@postgres:5432/umadex"
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def test_vocabulary_challenge():
    """Test the vocabulary challenge to see where it hangs"""
    
    # Test data
    vocabulary_list_id = UUID("b89cb43e-6c43-4051-91c4-88bc5d05ac42")  # "Bit of a big test"
    student_id = UUID("6cbf47a1-a88b-4c22-b3c2-fbe982abaf66")  # aggi coop
    
    logger.info(f"Testing vocabulary challenge for list {vocabulary_list_id} and student {student_id}")
    
    async with AsyncSessionLocal() as db:
        try:
            # Set RLS context for the student
            await set_rls_context(db, str(student_id), "acoop@csd8.info", False)
            
            # First, find the classroom assignment ID
            from sqlalchemy import select, and_
            from app.models.classroom import ClassroomAssignment, ClassroomStudent
            
            # Find classroom assignment
            result = await db.execute(
                select(ClassroomAssignment.id)
                .join(ClassroomStudent, ClassroomStudent.classroom_id == ClassroomAssignment.classroom_id)
                .where(
                    and_(
                        ClassroomAssignment.vocabulary_list_id == vocabulary_list_id,
                        ClassroomAssignment.assignment_type == "vocabulary",
                        ClassroomStudent.student_id == student_id
                    )
                )
                .limit(1)
            )
            classroom_assignment_id = result.scalar_one_or_none()
            
            if not classroom_assignment_id:
                logger.error("No classroom assignment found for this student and vocabulary list")
                return
                
            logger.info(f"Found classroom assignment ID: {classroom_assignment_id}")
            
            # Create vocabulary practice service
            practice_service = VocabularyPracticeService(db)
            
            # Add timing to see where it hangs
            start_time = time.time()
            logger.info("Starting vocabulary challenge...")
            
            # This is where the hang likely occurs
            game_data = await practice_service.start_vocabulary_challenge(
                student_id=student_id,
                vocabulary_list_id=vocabulary_list_id,
                classroom_assignment_id=classroom_assignment_id
            )
            
            end_time = time.time()
            logger.info(f"Vocabulary challenge completed in {end_time - start_time:.2f} seconds")
            logger.info(f"Game data: {game_data}")
            
        except Exception as e:
            logger.error(f"Error during vocabulary challenge test: {str(e)}", exc_info=True)
            raise

if __name__ == "__main__":
    asyncio.run(test_vocabulary_challenge())
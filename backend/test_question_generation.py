#!/usr/bin/env python3
"""
Test question generation specifically to identify hang
"""
import asyncio
import logging
import sys
import time
from uuid import UUID
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Add app to path
sys.path.append('/app')

from app.services.vocabulary_game_generator import VocabularyGameGenerator

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database setup
DATABASE_URL = "postgresql+asyncpg://umadex_user:umadex_password@postgres:5432/umadex"
engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def test_question_generation():
    """Test question generation for the vocabulary list"""
    
    vocabulary_list_id = UUID("b89cb43e-6c43-4051-91c4-88bc5d05ac42")  # "Bit of a big test"
    
    logger.info(f"Testing question generation for vocabulary list {vocabulary_list_id}")
    
    async with AsyncSessionLocal() as db:
        try:
            generator = VocabularyGameGenerator(db)
            
            # Test checking if questions exist (should be fast)
            logger.info("Checking if questions already exist...")
            start_time = time.time()
            
            questions = await generator.generate_game_questions(vocabulary_list_id)
            
            end_time = time.time()
            logger.info(f"Question generation completed in {end_time - start_time:.2f} seconds")
            logger.info(f"Number of questions returned: {len(questions)}")
            
        except Exception as e:
            logger.error(f"Error during question generation test: {str(e)}", exc_info=True)
            raise

if __name__ == "__main__":
    asyncio.run(test_question_generation())
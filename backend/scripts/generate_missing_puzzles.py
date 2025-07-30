#!/usr/bin/env python3
"""
Script to generate missing puzzles for all vocabulary lists
"""
import asyncio
import os
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.models.vocabulary import VocabularyList
from app.models.vocabulary_practice import VocabularyPuzzleGame
from app.services.vocabulary_puzzle_generator import VocabularyPuzzleGenerator
from app.core.config import settings
import logging

# Import the database configuration  
from app.core.database import engine as db_engine, AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def generate_missing_puzzles():
    """Generate puzzles for all vocabulary lists that don't have them"""
    
    async with AsyncSessionLocal() as db:
        try:
            # Get all vocabulary lists
            vocab_lists_result = await db.execute(
                select(VocabularyList)
            )
            vocab_lists = vocab_lists_result.scalars().all()
            
            logger.info(f"Found {len(vocab_lists)} vocabulary lists")
            
            for vocab_list in vocab_lists:
                # Check if puzzles already exist
                puzzles_result = await db.execute(
                    select(VocabularyPuzzleGame)
                    .where(VocabularyPuzzleGame.vocabulary_list_id == vocab_list.id)
                )
                existing_puzzles = puzzles_result.scalars().all()
                
                if not existing_puzzles:
                    logger.info(f"Generating puzzles for vocabulary list: {vocab_list.title} (ID: {vocab_list.id})")
                    
                    try:
                        generator = VocabularyPuzzleGenerator(db)
                        puzzle_data = await generator.generate_puzzle_set(vocab_list.id)
                        
                        # Save puzzles to database
                        for p_data in puzzle_data:
                            puzzle = VocabularyPuzzleGame(**p_data)
                            db.add(puzzle)
                        
                        await db.commit()
                        logger.info(f"Generated {len(puzzle_data)} puzzles for {vocab_list.title}")
                        
                    except Exception as e:
                        logger.error(f"Failed to generate puzzles for {vocab_list.title}: {e}")
                        await db.rollback()
                else:
                    logger.info(f"Puzzles already exist for {vocab_list.title} ({len(existing_puzzles)} puzzles)")
            
            logger.info("Puzzle generation complete!")
            
        except Exception as e:
            logger.error(f"Error in puzzle generation script: {e}")
            raise
        finally:
            pass  # Session cleanup handled by context manager


if __name__ == "__main__":
    asyncio.run(generate_missing_puzzles())
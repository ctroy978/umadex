#!/usr/bin/env python3
"""
Script to regenerate puzzles for existing vocabulary lists that don't have puzzles
"""

import asyncio
import logging
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.core.database import AsyncSessionLocal
from app.models.vocabulary import VocabularyList
from app.models.vocabulary_practice import VocabularyPuzzleGame
from app.services.vocabulary_puzzle_generator import VocabularyPuzzleGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def regenerate_puzzles():
    """Find vocabulary lists without puzzles and generate them"""
    
    async with AsyncSessionLocal() as db:
        # Find vocabulary lists that don't have puzzles
        lists_query = select(VocabularyList).options(selectinload(VocabularyList.words))
        lists_result = await db.execute(lists_query)
        all_lists = lists_result.scalars().all()
        
        for vocab_list in all_lists:
            # Check if puzzles exist for this list
            puzzle_count_query = select(VocabularyPuzzleGame).where(
                VocabularyPuzzleGame.vocabulary_list_id == vocab_list.id
            )
            puzzle_result = await db.execute(puzzle_count_query)
            existing_puzzles = puzzle_result.scalars().all()
            
            if len(existing_puzzles) == 0 and len(vocab_list.words) > 0:
                logger.info(f"Generating puzzles for list '{vocab_list.title}' (ID: {vocab_list.id}) with {len(vocab_list.words)} words")
                
                try:
                    # Generate puzzles
                    puzzle_generator = VocabularyPuzzleGenerator(db)
                    puzzle_data = await puzzle_generator.generate_puzzle_set(vocab_list.id)
                    
                    # Save puzzles to database
                    for p_data in puzzle_data:
                        puzzle = VocabularyPuzzleGame(**p_data)
                        db.add(puzzle)
                    
                    await db.commit()
                    logger.info(f"Successfully generated {len(puzzle_data)} puzzles for list '{vocab_list.title}'")
                    
                except Exception as e:
                    await db.rollback()
                    logger.error(f"Failed to generate puzzles for list '{vocab_list.title}': {e}")
            else:
                if len(existing_puzzles) > 0:
                    logger.info(f"List '{vocab_list.title}' already has {len(existing_puzzles)} puzzles")
                else:
                    logger.info(f"List '{vocab_list.title}' has no words, skipping")


if __name__ == "__main__":
    asyncio.run(regenerate_puzzles())
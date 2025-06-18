#!/usr/bin/env python3
"""
Script to check existing vocabulary lists that may be affected by the new 4-8 word limits
"""
import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import selectinload, sessionmaker
from app.models.vocabulary import VocabularyList, VocabularyWord
from app.core.config import settings

async def check_vocabulary_word_counts():
    """Check all vocabulary lists and their word counts"""
    
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        # Query to get vocabulary lists with word counts
        result = await db.execute(
            select(
                VocabularyList.id,
                VocabularyList.title,
                VocabularyList.status,
                func.count(VocabularyWord.id).label('word_count')
            )
            .outerjoin(VocabularyWord)
            .group_by(VocabularyList.id)
            .order_by(func.count(VocabularyWord.id).desc())
        )
        
        lists = result.all()
        
        print("\n=== Vocabulary Lists Word Count Analysis ===\n")
        
        # Statistics
        total_lists = len(lists)
        lists_under_4 = sum(1 for l in lists if l.word_count < 4)
        lists_4_to_8 = sum(1 for l in lists if 4 <= l.word_count <= 8)
        lists_over_8 = sum(1 for l in lists if l.word_count > 8)
        
        print(f"Total vocabulary lists: {total_lists}")
        print(f"Lists with < 4 words: {lists_under_4}")
        print(f"Lists with 4-8 words: {lists_4_to_8}")
        print(f"Lists with > 8 words: {lists_over_8}")
        
        # Show problematic lists
        if lists_under_4 > 0 or lists_over_8 > 0:
            print("\n=== Lists Outside New Limits (4-8 words) ===\n")
            
            for vlist in lists:
                if vlist.word_count < 4 or vlist.word_count > 8:
                    print(f"ID: {vlist.id}")
                    print(f"Title: {vlist.title}")
                    print(f"Status: {vlist.status}")
                    print(f"Word Count: {vlist.word_count}")
                    print("-" * 50)
        
        # Get distribution
        print("\n=== Word Count Distribution ===\n")
        distribution = {}
        for vlist in lists:
            count = vlist.word_count
            distribution[count] = distribution.get(count, 0) + 1
        
        for word_count in sorted(distribution.keys()):
            print(f"{word_count} words: {distribution[word_count]} lists")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_vocabulary_word_counts())
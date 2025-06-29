#!/usr/bin/env python3
"""
Migration script to fix archived vocabulary lists.
Converts status='archived' to deleted_at timestamp.
"""
import asyncio
from datetime import datetime
from sqlalchemy import select, update, and_
from app.core.database import AsyncSessionLocal
from app.models.vocabulary import VocabularyList
from sqlalchemy.sql import text

async def fix_archived_vocabulary():
    """Convert archived status to deleted_at"""
    async with AsyncSessionLocal() as db:
        try:
            # First, let's check how many lists have status='archived'
            result = await db.execute(
                text("SELECT COUNT(*) FROM vocabulary_lists WHERE status = 'archived'")
            )
            count = result.scalar()
            print(f"Found {count} vocabulary lists with status='archived'")
            
            if count > 0:
                # Update all archived lists: set deleted_at if not already set, and change status to 'published'
                await db.execute(
                    text("""
                        UPDATE vocabulary_lists 
                        SET deleted_at = CASE 
                            WHEN deleted_at IS NULL THEN NOW() 
                            ELSE deleted_at 
                        END,
                        status = 'published'
                        WHERE status = 'archived'
                    """)
                )
                
                await db.commit()
                print(f"Successfully migrated {count} archived vocabulary lists")
            else:
                print("No archived vocabulary lists found")
                
        except Exception as e:
            print(f"Error during migration: {e}")
            await db.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(fix_archived_vocabulary())
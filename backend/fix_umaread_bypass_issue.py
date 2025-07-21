#!/usr/bin/env python3
"""
Script to fix the umaread assignment completion issue for a student who used bypass code
"""
import asyncio
import sys
from sqlalchemy import select, update, and_, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from datetime import datetime
import os

# Database connection
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/umadex")

async def fix_assignment_completion(student_id: str, assignment_id: str):
    """Fix the assignment completion status for a student"""
    engine = create_async_engine(DATABASE_URL)
    
    async with AsyncSession(engine) as session:
        # Import models after engine is created
        from app.models.umaread import UmareadAssignmentProgress, UmareadChunkProgress
        from app.models.reading import ReadingAssignment, ReadingChunk
        
        # Get total chunks for the assignment
        total_chunks_result = await session.execute(
            select(ReadingAssignment.total_chunks)
            .where(ReadingAssignment.id == assignment_id)
        )
        total_chunks = total_chunks_result.scalar_one()
        
        # Get completed chunks count
        completed_chunks_result = await session.execute(
            select(func.count(UmareadChunkProgress.id))
            .where(
                and_(
                    UmareadChunkProgress.student_id == student_id,
                    UmareadChunkProgress.assignment_id == assignment_id,
                    UmareadChunkProgress.summary_completed == True,
                    UmareadChunkProgress.comprehension_completed == True
                )
            )
        )
        completed_chunks = completed_chunks_result.scalar() or 0
        
        # Update assignment progress
        await session.execute(
            update(UmareadAssignmentProgress)
            .where(
                and_(
                    UmareadAssignmentProgress.student_id == student_id,
                    UmareadAssignmentProgress.assignment_id == assignment_id
                )
            )
            .values(
                total_chunks_completed=completed_chunks,
                current_chunk=min(completed_chunks + 1, total_chunks),
                completed_at=datetime.utcnow() if completed_chunks >= total_chunks else None
            )
        )
        
        await session.commit()
        print(f"Updated assignment progress: {completed_chunks}/{total_chunks} chunks completed")
        if completed_chunks >= total_chunks:
            print("Assignment marked as completed!")
        else:
            print(f"Assignment not yet complete. Student should continue from chunk {completed_chunks + 1}")
    
    await engine.dispose()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python fix_umaread_bypass_issue.py <student_id> <assignment_id>")
        sys.exit(1)
    
    student_id = sys.argv[1]
    assignment_id = sys.argv[2]
    
    asyncio.run(fix_assignment_completion(student_id, assignment_id))
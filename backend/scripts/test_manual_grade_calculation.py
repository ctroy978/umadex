#!/usr/bin/env python3
"""Test manual grade calculation for UMALecture"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from app.core.database import get_db
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from app.core.config import settings
from app.services.umalecture import UMALectureService


async def test_grade_calculation():
    """Test calculating grade for bcoop-csd8info"""
    # Create async engine
    engine = create_async_engine(settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))
    
    async with AsyncSession(engine) as db:
        service = UMALectureService()
        
        # Student and assignment info from database query
        student_id = UUID("6d3adf1e-d50d-4259-9cf1-685fcbe71207")
        assignment_id = 8
        lecture_id = UUID("4f9b8785-486c-4e1d-8b97-211c48bb48f5")
        
        print("Testing grade calculation for student bcoop-csd8info")
        print(f"Student ID: {student_id}")
        print(f"Assignment ID: {assignment_id}")
        print(f"Lecture ID: {lecture_id}")
        
        # Calculate grade
        grade = await service.calculate_lecture_grade(db, student_id, assignment_id)
        print(f"\nCalculated grade: {grade}%")
        
        if grade is not None:
            # Create gradebook entry
            print("\nCreating gradebook entry...")
            await service.create_or_update_gradebook_entry(
                db, student_id, assignment_id, lecture_id, grade
            )
            print("Gradebook entry created/updated successfully!")
        else:
            print("No grade calculated - student may not have completed any levels")


if __name__ == "__main__":
    asyncio.run(test_grade_calculation())
#!/usr/bin/env python3
"""Test script for UMALecture grading functionality"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import text
from app.core.database import SessionLocal
from app.services.umalecture import UMALectureService


async def test_lecture_grading():
    """Test the UMALecture grading system"""
    async with SessionLocal() as db:
        service = UMALectureService()
        
        print("Testing UMALecture Grading System")
        print("=" * 50)
        
        # Test data - you'll need to update these with real IDs from your database
        student_id = UUID("00000000-0000-0000-0000-000000000001")  # Replace with real student ID
        assignment_id = 1  # Replace with real assignment ID
        
        # Test 1: Calculate grade for a student with no progress
        print("\nTest 1: Calculate grade for student with no progress")
        grade = await service.calculate_lecture_grade(db, student_id, assignment_id)
        print(f"Grade: {grade}")
        assert grade is None, "Grade should be None for student with no progress"
        
        # Test 2: Simulate progress through difficulty levels
        print("\nTest 2: Simulating student progress...")
        
        # Create mock progress data
        progress_metadata = {
            "topic_completion": {
                "topic1": {
                    "completed_tabs": ["basic"],
                    "questions_correct": {
                        "basic": [True, True, True]
                    }
                }
            }
        }
        
        # Update student assignment with mock progress
        update_query = text("""
            UPDATE student_assignments
            SET progress_metadata = :metadata
            WHERE student_id = :student_id
            AND classroom_assignment_id = :assignment_id
        """)
        
        await db.execute(update_query, {
            "metadata": progress_metadata,
            "student_id": student_id,
            "assignment_id": assignment_id
        })
        await db.commit()
        
        # Calculate grade - should be 70% for basic
        grade = await service.calculate_lecture_grade(db, student_id, assignment_id)
        print(f"Grade after completing basic: {grade}%")
        assert grade == 70, "Grade should be 70% after completing basic level"
        
        # Test 3: Progress to intermediate
        progress_metadata["topic_completion"]["topic1"]["completed_tabs"].append("intermediate")
        progress_metadata["topic_completion"]["topic1"]["questions_correct"]["intermediate"] = [True, True, True]
        
        await db.execute(update_query, {
            "metadata": progress_metadata,
            "student_id": student_id,
            "assignment_id": assignment_id
        })
        await db.commit()
        
        grade = await service.calculate_lecture_grade(db, student_id, assignment_id)
        print(f"Grade after completing intermediate: {grade}%")
        assert grade == 80, "Grade should be 80% after completing intermediate level"
        
        # Test 4: Progress to advanced
        progress_metadata["topic_completion"]["topic1"]["completed_tabs"].append("advanced")
        progress_metadata["topic_completion"]["topic1"]["questions_correct"]["advanced"] = [True, True, True]
        
        await db.execute(update_query, {
            "metadata": progress_metadata,
            "student_id": student_id,
            "assignment_id": assignment_id
        })
        await db.commit()
        
        grade = await service.calculate_lecture_grade(db, student_id, assignment_id)
        print(f"Grade after completing advanced: {grade}%")
        assert grade == 90, "Grade should be 90% after completing advanced level"
        
        # Test 5: Complete expert level
        progress_metadata["topic_completion"]["topic1"]["completed_tabs"].append("expert")
        progress_metadata["topic_completion"]["topic1"]["questions_correct"]["expert"] = [True, True]
        
        await db.execute(update_query, {
            "metadata": progress_metadata,
            "student_id": student_id,
            "assignment_id": assignment_id
        })
        await db.commit()
        
        grade = await service.calculate_lecture_grade(db, student_id, assignment_id)
        print(f"Grade after completing expert: {grade}%")
        assert grade == 100, "Grade should be 100% after completing expert level"
        
        # Test 6: Test expert level with some wrong answers
        progress_metadata["topic_completion"]["topic1"]["questions_correct"]["expert"] = [True, False]
        
        await db.execute(update_query, {
            "metadata": progress_metadata,
            "student_id": student_id,
            "assignment_id": assignment_id
        })
        await db.commit()
        
        grade = await service.calculate_lecture_grade(db, student_id, assignment_id)
        print(f"Grade with expert level partially correct: {grade}%")
        assert grade == 90, "Grade should remain at 90% if expert questions aren't all correct"
        
        print("\n" + "=" * 50)
        print("All tests passed! ✅")
        
        # Clean up test data
        print("\nCleaning up test data...")
        cleanup_query = text("""
            UPDATE student_assignments
            SET progress_metadata = NULL
            WHERE student_id = :student_id
            AND classroom_assignment_id = :assignment_id
        """)
        
        await db.execute(cleanup_query, {
            "student_id": student_id,
            "assignment_id": assignment_id
        })
        await db.commit()


if __name__ == "__main__":
    print("Note: Before running this test, update the student_id and assignment_id with real values from your database.")
    print("You can find these by querying:")
    print("  - SELECT id FROM users WHERE role = 'student' LIMIT 1;")
    print("  - SELECT ca.id FROM classroom_assignments ca WHERE ca.assignment_type = 'UMALecture' LIMIT 1;")
    print()
    
    # Uncomment to run the test
    # asyncio.run(test_lecture_grading())
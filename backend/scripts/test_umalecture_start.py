#!/usr/bin/env python3
"""Test starting a UMALecture assignment"""
import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.services.umalecture import UMALectureService
from uuid import UUID


async def test_start_lecture():
    """Test starting lecture assignment 55"""
    service = UMALectureService()
    
    async with AsyncSessionLocal() as db:
        # Test student ID - you'll need to replace with a real student ID
        # For now, let's just check if the method works without error
        print("Testing get_or_create_student_progress for assignment 55...")
        
        try:
            # First, let's get a student ID from the database
            from sqlalchemy import text
            result = await db.execute(text("""
                SELECT u.id, u.username 
                FROM users u 
                WHERE u.role = 'student' 
                LIMIT 1
            """))
            student = result.first()
            
            if not student:
                print("❌ No student users found in database")
                return
                
            student_id = student.id
            print(f"✓ Using student: {student.username} (ID: {student_id})")
            
            # Test the method
            progress = await service.get_or_create_student_progress(
                db, student_id, 55
            )
            
            print("✅ Success! Student progress created/retrieved:")
            print(f"  - Assignment ID: {progress.assignment_id}")
            print(f"  - Lecture ID: {progress.lecture_id}")
            print(f"  - Current Topic: {progress.current_topic}")
            print(f"  - Total Points: {progress.total_points}")
            
        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_start_lecture())
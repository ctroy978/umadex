#!/usr/bin/env python3
"""Find the photosynthesis UMALecture and its assignments"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.classroom import ClassroomAssignment, StudentAssignment
from app.models.reading import ReadingAssignment
from app.models.user import User


async def find_photosynthesis_lecture():
    """Find the photosynthesis lecture by title and teacher"""
    async with AsyncSessionLocal() as db:
        # First find the teacher
        teacher_query = select(User).where(User.username == "tcooper-csd8")
        teacher_result = await db.execute(teacher_query)
        teacher = teacher_result.scalar_one_or_none()
        
        if not teacher:
            print("❌ Teacher 'tcooper-csd8' not found")
            return
        
        print(f"✓ Found teacher: {teacher.username} (ID: {teacher.id})")
        
        # Find UMALecture assignments with "photosynthesis" in title
        lecture_query = (
            select(ReadingAssignment)
            .where(
                and_(
                    ReadingAssignment.assignment_type == "UMALecture",
                    ReadingAssignment.teacher_id == teacher.id,
                    or_(
                        ReadingAssignment.title.ilike("%photosynthesis%"),
                        ReadingAssignment.title.ilike("%Introduction to photosynthesis%")
                    )
                )
            )
        )
        
        lecture_result = await db.execute(lecture_query)
        lectures = lecture_result.scalars().all()
        
        if not lectures:
            print("❌ No photosynthesis UMALecture found for this teacher")
            
            # Let's check all UMALectures by this teacher
            all_lectures_query = (
                select(ReadingAssignment)
                .where(
                    and_(
                        ReadingAssignment.assignment_type == "UMALecture",
                        ReadingAssignment.teacher_id == teacher.id
                    )
                )
            )
            all_result = await db.execute(all_lectures_query)
            all_lectures = all_result.scalars().all()
            
            print(f"\nAll UMALectures by {teacher.username}:")
            for lec in all_lectures:
                print(f"  - ID: {lec.id}, Title: {lec.title}, Status: {lec.status}")
            
            return
        
        print(f"\n✓ Found {len(lectures)} photosynthesis lecture(s):")
        
        for lecture in lectures:
            print(f"\n📚 Lecture: {lecture.title}")
            print(f"  - Reading Assignment ID: {lecture.id}")
            print(f"  - Status: {lecture.status}")
            print(f"  - Created: {lecture.created_at}")
            
            # Find classroom assignments for this lecture
            ca_query = (
                select(ClassroomAssignment)
                .where(
                    and_(
                        ClassroomAssignment.assignment_id == lecture.id,
                        ClassroomAssignment.assignment_type == "UMALecture"
                    )
                )
            )
            ca_result = await db.execute(ca_query)
            classroom_assignments = ca_result.scalars().all()
            
            print(f"  - Classroom Assignments: {len(classroom_assignments)}")
            
            for ca in classroom_assignments:
                print(f"    → Classroom Assignment ID: {ca.id}")
                print(f"      - Classroom ID: {ca.classroom_id}")
                print(f"      - Due Date: {ca.due_date}")
                
                # Check student assignments
                sa_query = (
                    select(StudentAssignment)
                    .where(StudentAssignment.classroom_assignment_id == ca.id)
                )
                sa_result = await db.execute(sa_query)
                student_count = len(sa_result.scalars().all())
                print(f"      - Students assigned: {student_count}")


if __name__ == "__main__":
    asyncio.run(find_photosynthesis_lecture())
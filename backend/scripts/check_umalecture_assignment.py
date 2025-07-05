#!/usr/bin/env python3
"""Check if UMALecture assignment exists"""
import asyncio
import sys
from pathlib import Path
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import AsyncSessionLocal
from app.models.classroom import ClassroomAssignment, StudentAssignment
from app.models.reading import ReadingAssignment


async def check_assignment(assignment_id: int):
    """Check if classroom assignment exists and its details"""
    async with AsyncSessionLocal() as db:
        # Check classroom assignment
        query = (
            select(ClassroomAssignment, ReadingAssignment)
            .join(ReadingAssignment, ClassroomAssignment.assignment_id == ReadingAssignment.id)
            .where(ClassroomAssignment.id == assignment_id)
        )
        
        result = await db.execute(query)
        row = result.first()
        
        if not row:
            print(f"❌ Classroom assignment {assignment_id} not found")
            
            # Check if it exists without the join
            ca_query = select(ClassroomAssignment).where(ClassroomAssignment.id == assignment_id)
            ca_result = await db.execute(ca_query)
            ca = ca_result.scalar_one_or_none()
            
            if ca:
                print(f"✓ Classroom assignment {assignment_id} exists:")
                print(f"  - Assignment ID: {ca.assignment_id}")
                print(f"  - Assignment Type: {ca.assignment_type}")
                print(f"  - Classroom ID: {ca.classroom_id}")
                
                # Check if reading assignment exists
                ra_query = select(ReadingAssignment).where(ReadingAssignment.id == ca.assignment_id)
                ra_result = await db.execute(ra_query)
                ra = ra_result.scalar_one_or_none()
                
                if ra:
                    print(f"✓ Reading assignment {ca.assignment_id} exists:")
                    print(f"  - Type: {ra.assignment_type}")
                    print(f"  - Title: {ra.title}")
                    print(f"  - Status: {ra.status}")
                else:
                    print(f"❌ Reading assignment {ca.assignment_id} not found")
            
            return
        
        classroom_assignment, reading_assignment = row
        
        print(f"✓ Found assignment {assignment_id}:")
        print(f"  - Classroom Assignment ID: {classroom_assignment.id}")
        print(f"  - Assignment Type: {classroom_assignment.assignment_type}")
        print(f"  - Reading Assignment ID: {reading_assignment.id}")
        print(f"  - Reading Type: {reading_assignment.assignment_type}")
        print(f"  - Title: {reading_assignment.title}")
        print(f"  - Status: {reading_assignment.status}")
        
        # Check for any student assignments
        sa_query = (
            select(StudentAssignment)
            .where(StudentAssignment.classroom_assignment_id == assignment_id)
        )
        sa_result = await db.execute(sa_query)
        student_assignments = sa_result.scalars().all()
        
        print(f"  - Student Assignments: {len(student_assignments)}")


if __name__ == "__main__":
    assignment_id = 55
    if len(sys.argv) > 1:
        assignment_id = int(sys.argv[1])
    
    asyncio.run(check_assignment(assignment_id))
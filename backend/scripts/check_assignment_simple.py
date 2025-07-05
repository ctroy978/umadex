#!/usr/bin/env python3
"""Simple check for UMALecture assignment"""
import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy import text

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://umadex:umadex123@localhost:5432/umadex_db")
DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")


async def check_assignment():
    """Check assignment 55 directly with SQL"""
    engine = create_async_engine(DATABASE_URL)
    
    async with AsyncSession(engine) as session:
        # Check classroom assignment 55
        query = text("""
            SELECT 
                ca.id as ca_id,
                ca.assignment_id,
                ca.assignment_type,
                ca.classroom_id,
                ra.id as ra_id,
                ra.assignment_title,
                ra.assignment_type as ra_type,
                ra.status
            FROM classroom_assignments ca
            LEFT JOIN reading_assignments ra ON ca.assignment_id = ra.id
            WHERE ca.id = :assignment_id
        """)
        
        result = await session.execute(query, {"assignment_id": 55})
        row = result.first()
        
        if not row:
            print(f"❌ Classroom assignment 55 not found")
            
            # Let's search for photosynthesis lectures
            search_query = text("""
                SELECT 
                    ra.id,
                    ra.assignment_title,
                    ra.status,
                    ra.teacher_id,
                    u.username,
                    COUNT(ca.id) as classroom_count
                FROM reading_assignments ra
                JOIN users u ON ra.teacher_id = u.id
                LEFT JOIN classroom_assignments ca ON ca.assignment_id = ra.id
                WHERE ra.assignment_type = 'UMALecture'
                AND (ra.assignment_title ILIKE '%photosynthesis%' OR u.username = 'tcooper-csd8')
                GROUP BY ra.id, ra.assignment_title, ra.status, ra.teacher_id, u.username
            """)
            
            search_result = await session.execute(search_query)
            lectures = search_result.all()
            
            print("\n🔍 Searching for photosynthesis lectures:")
            for lec in lectures:
                print(f"\n📚 {lec.assignment_title}")
                print(f"  - ID: {lec.id}")
                print(f"  - Status: {lec.status}")
                print(f"  - Teacher: {lec.username}")
                print(f"  - Classrooms: {lec.classroom_count}")
                
                # Get classroom assignments
                ca_query = text("""
                    SELECT id, classroom_id, due_date
                    FROM classroom_assignments
                    WHERE assignment_id = :lecture_id
                    AND assignment_type = 'UMALecture'
                """)
                ca_result = await session.execute(ca_query, {"lecture_id": lec.id})
                cas = ca_result.all()
                
                for ca in cas:
                    print(f"    → Classroom Assignment ID: {ca.id}")
                    print(f"      Classroom: {ca.classroom_id}, Due: {ca.due_date}")
                    
        else:
            print(f"✓ Found assignment 55:")
            print(f"  - Classroom Assignment ID: {row.ca_id}")
            print(f"  - Assignment Type: {row.assignment_type}")
            print(f"  - Reading Assignment ID: {row.assignment_id}")
            print(f"  - Title: {row.assignment_title}")
            print(f"  - Reading Type: {row.ra_type}")
            print(f"  - Status: {row.status}")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(check_assignment())
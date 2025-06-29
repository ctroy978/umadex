import asyncio
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
import sys
sys.path.append('/home/tcoop/projects/umadex/backend')
from app.models.classroom import ClassroomAssignment, StudentAssignment
from app.models.writing import WritingAssignment, StudentWritingSubmission

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://umadex_user:umadex_password@localhost/umadex_db")

async def check_writing_data():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Check WritingAssignment count
        wa_count = await session.execute(select(func.count(WritingAssignment.id)))
        print(f"WritingAssignment count: {wa_count.scalar()}")
        
        # Check ClassroomAssignment with assignment_type='writing' count
        ca_count = await session.execute(
            select(func.count(ClassroomAssignment.id)).where(
                ClassroomAssignment.assignment_type == 'writing'
            )
        )
        print(f"ClassroomAssignment (writing) count: {ca_count.scalar()}")
        
        # Check StudentAssignment with assignment_type='writing' count
        sa_count = await session.execute(
            select(func.count(StudentAssignment.id)).where(
                StudentAssignment.assignment_type == 'writing'
            )
        )
        print(f"StudentAssignment (writing) count: {sa_count.scalar()}")
        
        # Check StudentWritingSubmission count
        sws_count = await session.execute(select(func.count(StudentWritingSubmission.id)))
        print(f"StudentWritingSubmission count: {sws_count.scalar()}")
        
        # Check if there are any writing classroom assignments
        ca_writing = await session.execute(
            select(ClassroomAssignment).where(
                ClassroomAssignment.assignment_type == 'writing'
            ).limit(5)
        )
        writing_cas = ca_writing.scalars().all()
        print(f"\nSample ClassroomAssignments (writing):")
        for ca in writing_cas:
            print(f"  ID: {ca.id}, Assignment ID: {ca.assignment_id}, Classroom ID: {ca.classroom_id}")

if __name__ == "__main__":
    asyncio.run(check_writing_data())
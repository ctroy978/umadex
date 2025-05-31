"""
Simplified UMARead service for initial testing
"""
from typing import Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func, text
from sqlalchemy.orm import selectinload

from app.models.reading import ReadingAssignment, ReadingChunk
from app.models.classroom import StudentAssignment, ClassroomAssignment
from app.models.user import User
from app.schemas.umaread import (
    ChunkResponse,
    AssignmentStartResponse,
    StudentProgress,
    AssignmentMetadata,
    WorkType,
    LiteraryForm
)


class UMAReadService:
    """Simplified UMARead service for initial testing"""
    
    async def start_assignment(self, 
                             db: AsyncSession,
                             student_id: UUID,
                             assignment_id: UUID) -> AssignmentStartResponse:
        """Start or resume a reading assignment"""
        # Get the reading assignment
        result = await db.execute(
            select(ReadingAssignment).where(ReadingAssignment.id == assignment_id)
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            raise ValueError("Assignment not found")
        
        # Determine starting difficulty based on grade level
        grade_level = assignment.grade_level.lower()
        starting_difficulty = 3  # Default for grade 5+
        
        # Check if K-4 grade level (be more specific to avoid matching "14" in "9-14")
        k4_patterns = [
            'k', 'kindergarten',
            'grade 1', 'grade 2', 'grade 3', 'grade 4',
            '1st', '2nd', '3rd', '4th',
            'first', 'second', 'third', 'fourth'
        ]
        
        # Only set to Level 1 if it's explicitly K-4 and NOT a range that includes higher grades
        if any(pattern in grade_level for pattern in k4_patterns) and not any(str(i) in grade_level for i in range(5, 13)):
            starting_difficulty = 1
        
        # Get total chunks
        total_result = await db.execute(
            select(func.count(ReadingChunk.id))
            .where(ReadingChunk.assignment_id == assignment_id)
        )
        total_chunks = total_result.scalar()
        
        # Check if student assignment exists
        student_assignment_result = await db.execute(
            select(StudentAssignment).where(
                and_(
                    StudentAssignment.student_id == student_id,
                    StudentAssignment.assignment_id == assignment_id
                )
            )
        )
        student_assignment = student_assignment_result.scalar_one_or_none()
        
        if not student_assignment:
            # Find the classroom assignment for this reading assignment
            classroom_assignment_result = await db.execute(
                select(ClassroomAssignment).where(
                    ClassroomAssignment.assignment_id == assignment_id
                )
            )
            classroom_assignment = classroom_assignment_result.scalar_one_or_none()
            
            if not classroom_assignment:
                raise ValueError("Assignment not assigned to any classroom")
            
            # Create new student assignment
            student_assignment = StudentAssignment(
                student_id=student_id,
                assignment_id=assignment_id,
                classroom_assignment_id=classroom_assignment.id,
                assignment_type="reading",
                status="not_started",
                current_position=1,
                progress_metadata={}
            )
            db.add(student_assignment)
            await db.commit()
            await db.refresh(student_assignment)
        
        return AssignmentStartResponse(
            assignment_id=assignment_id,
            title=assignment.assignment_title,
            author=assignment.author,
            total_chunks=total_chunks,
            current_chunk=student_assignment.current_position,
            difficulty_level=starting_difficulty,
            status=student_assignment.status
        )
    
    async def get_chunk_content(self,
                              db: AsyncSession,
                              assignment_id: UUID,
                              chunk_number: int) -> ChunkResponse:
        """Get chunk content"""
        # Get the specific chunk
        chunk_result = await db.execute(
            select(ReadingChunk).where(
                and_(
                    ReadingChunk.assignment_id == assignment_id,
                    ReadingChunk.chunk_order == chunk_number
                )
            )
        )
        chunk = chunk_result.scalar_one_or_none()
        
        if not chunk:
            raise ValueError(f"Chunk {chunk_number} not found")
        
        # Get total chunks
        total_result = await db.execute(
            select(func.count(ReadingChunk.id))
            .where(ReadingChunk.assignment_id == assignment_id)
        )
        total_chunks = total_result.scalar()
        
        return ChunkResponse(
            chunk_number=chunk_number,
            total_chunks=total_chunks,
            content=chunk.content,
            images=[],  # Simplified for now
            has_next=chunk_number < total_chunks,
            has_previous=chunk_number > 1
        )
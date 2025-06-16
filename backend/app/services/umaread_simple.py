"""
Simplified UMARead service for initial testing
"""
from typing import Optional, Dict, Any, Tuple, List
from uuid import UUID
from datetime import datetime
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func, text
from sqlalchemy.orm import selectinload

from app.models.reading import ReadingAssignment, ReadingChunk, AssignmentImage
from app.models.classroom import StudentAssignment, ClassroomAssignment
from app.models.user import User
from app.schemas.umaread import (
    ChunkResponse,
    AssignmentStartResponse,
    StudentProgress,
    AssignmentMetadata,
    WorkType,
    LiteraryForm,
    ChunkImage
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
        
        # First, find the classroom assignment for this reading assignment
        classroom_assignment_result = await db.execute(
            select(ClassroomAssignment).where(
                ClassroomAssignment.assignment_id == assignment_id
            )
        )
        classroom_assignment = classroom_assignment_result.scalar_one_or_none()
        
        if not classroom_assignment:
            raise ValueError("This assignment hasn't been assigned to any classroom yet.")
        
        # Check if student assignment exists for this specific classroom assignment
        student_assignment_result = await db.execute(
            select(StudentAssignment).where(
                and_(
                    StudentAssignment.student_id == student_id,
                    StudentAssignment.assignment_id == assignment_id,
                    StudentAssignment.classroom_assignment_id == classroom_assignment.id
                )
            )
        )
        student_assignment = student_assignment_result.scalar_one_or_none()
        
        if not student_assignment:
            # Check if student is in the classroom
            from ..models.classroom import ClassroomStudent
            
            student_in_classroom = await db.execute(
                select(ClassroomStudent).where(
                    and_(
                        ClassroomStudent.student_id == student_id,
                        ClassroomStudent.classroom_id == classroom_assignment.classroom_id,
                        ClassroomStudent.removed_at.is_(None)
                    )
                )
            )
            
            if not student_in_classroom.scalar_one_or_none():
                raise ValueError("You need to join the classroom first to access this assignment.")
            
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
            try:
                await db.commit()
                await db.refresh(student_assignment)
            except Exception:
                # If there's a unique constraint violation, fetch the existing assignment
                await db.rollback()
                student_assignment_result = await db.execute(
                    select(StudentAssignment).where(
                        and_(
                            StudentAssignment.student_id == student_id,
                            StudentAssignment.assignment_id == assignment_id,
                            StudentAssignment.classroom_assignment_id == classroom_assignment.id
                        )
                    )
                )
                student_assignment = student_assignment_result.scalar_one()
        
        # Store assignment details before commit
        assignment_title = assignment.assignment_title
        assignment_author = assignment.author
        
        # Update status to in_progress if it's not_started
        if student_assignment.status == "not_started":
            student_assignment.status = "in_progress"
            student_assignment.started_at = datetime.utcnow()
            await db.commit()
        
        return AssignmentStartResponse(
            assignment_id=assignment_id,
            title=assignment_title,
            author=assignment_author,
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
        
        # Extract image tags from content
        image_pattern = re.compile(r'<image>(.*?)</image>')
        image_tags = image_pattern.findall(chunk.content)
        
        # Fetch images for these tags
        images: List[ChunkImage] = []
        if image_tags:
            images_result = await db.execute(
                select(AssignmentImage).where(
                    and_(
                        AssignmentImage.assignment_id == assignment_id,
                        AssignmentImage.image_tag.in_(image_tags)
                    )
                )
            )
            assignment_images = images_result.scalars().all()
            
            # Convert to ChunkImage schema
            for img in assignment_images:
                images.append(ChunkImage(
                    url=img.display_url or img.image_url or "",
                    thumbnail_url=img.thumbnail_url,
                    description=img.ai_description if isinstance(img.ai_description, str) else None,
                    image_tag=img.image_tag
                ))
        
        return ChunkResponse(
            chunk_number=chunk_number,
            total_chunks=total_chunks,
            content=chunk.content,
            images=images,
            has_next=chunk_number < total_chunks,
            has_previous=chunk_number > 1
        )
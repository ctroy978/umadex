import re
from typing import List, Tuple, Optional, Dict
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
import os
from datetime import datetime

from app.models.reading import ReadingAssignment, ReadingChunk, AssignmentImage
from app.schemas.reading import (
    ReadingAssignmentCreate, 
    ReadingAssignmentUpdate,
    MarkupValidationResult,
    PublishResult
)
from app.services.reading import MarkupParser


class ReadingAssignmentAsyncService:
    """Async service for handling reading assignment operations"""
    
    @staticmethod
    async def create_draft(
        db: AsyncSession,
        teacher_id: UUID,
        assignment_data: ReadingAssignmentCreate
    ) -> ReadingAssignment:
        """Create a new draft reading assignment"""
        
        # Convert work_type to lowercase for database
        assignment_dict = assignment_data.dict()
        assignment_dict['work_type'] = assignment_dict['work_type'].lower()
        
        assignment = ReadingAssignment(
            teacher_id=teacher_id,
            **assignment_dict
        )
        
        db.add(assignment)
        await db.commit()
        await db.refresh(assignment)
        
        return assignment
    
    @staticmethod
    async def update_assignment(
        db: AsyncSession,
        assignment_id: UUID,
        teacher_id: UUID,
        update_data: ReadingAssignmentUpdate
    ) -> ReadingAssignment:
        """Update an existing assignment"""
        
        # Add logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Updating assignment {assignment_id}")
        logger.info(f"Update data: {update_data.dict(exclude_unset=True)}")
        
        result = await db.execute(
            select(ReadingAssignment).where(
                ReadingAssignment.id == assignment_id,
                ReadingAssignment.teacher_id == teacher_id
            )
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Only update fields that were provided
        update_dict = update_data.dict(exclude_unset=True)
        if 'work_type' in update_dict:
            update_dict['work_type'] = update_dict['work_type'].lower()
        
        for field, value in update_dict.items():
            setattr(assignment, field, value)
        
        assignment.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(assignment)
        
        return assignment
    
    @staticmethod
    async def validate_assignment_markup(
        db: AsyncSession,
        assignment_id: UUID,
        teacher_id: UUID
    ) -> MarkupValidationResult:
        """Validate the markup of an assignment"""
        
        result = await db.execute(
            select(ReadingAssignment).where(
                ReadingAssignment.id == assignment_id,
                ReadingAssignment.teacher_id == teacher_id
            )
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Get available images for this assignment
        images_result = await db.execute(
            select(AssignmentImage).where(
                AssignmentImage.assignment_id == assignment_id
            )
        )
        images = images_result.scalars().all()
        available_images = [img.image_key for img in images]
        
        return MarkupParser.validate_markup(assignment.raw_content, available_images)
    
    @staticmethod
    async def publish_assignment(
        db: AsyncSession,
        assignment_id: UUID,
        teacher_id: UUID
    ) -> PublishResult:
        """Parse chunks and publish the assignment"""
        
        result = await db.execute(
            select(ReadingAssignment).where(
                ReadingAssignment.id == assignment_id,
                ReadingAssignment.teacher_id == teacher_id
            )
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Validate markup first
        images_result = await db.execute(
            select(AssignmentImage).where(
                AssignmentImage.assignment_id == assignment_id
            )
        )
        images = images_result.scalars().all()
        available_images = [img.image_key for img in images]
        
        validation_result = MarkupParser.validate_markup(
            assignment.raw_content, 
            available_images
        )
        
        if not validation_result.is_valid:
            return PublishResult(
                success=False,
                message=f"Validation failed: {'; '.join(validation_result.errors)}"
            )
        
        # Delete existing chunks if any
        chunks_result = await db.execute(
            select(ReadingChunk).where(
                ReadingChunk.assignment_id == assignment_id
            )
        )
        existing_chunks = chunks_result.scalars().all()
        for chunk in existing_chunks:
            await db.delete(chunk)
        
        # Parse and create chunks
        chunks_data = MarkupParser.parse_chunks(assignment.raw_content)
        
        for order, (content, has_important) in enumerate(chunks_data, 1):
            chunk = ReadingChunk(
                assignment_id=assignment_id,
                chunk_order=order,
                content=content,
                has_important_sections=has_important
            )
            db.add(chunk)
        
        # Update assignment
        assignment.total_chunks = len(chunks_data)
        assignment.status = 'published'
        assignment.updated_at = datetime.utcnow()
        
        await db.commit()
        
        return PublishResult(
            success=True,
            message="Assignment published successfully",
            chunk_count=len(chunks_data)
        )
    
    @staticmethod
    async def get_teacher_assignments(
        db: AsyncSession,
        teacher_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> List[ReadingAssignment]:
        """Get all assignments for a teacher"""
        
        result = await db.execute(
            select(ReadingAssignment).where(
                ReadingAssignment.teacher_id == teacher_id
            ).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    @staticmethod
    async def get_assignment_by_id(
        db: AsyncSession,
        assignment_id: UUID,
        teacher_id: UUID
    ) -> ReadingAssignment:
        """Get a specific assignment"""
        
        result = await db.execute(
            select(ReadingAssignment).where(
                ReadingAssignment.id == assignment_id,
                ReadingAssignment.teacher_id == teacher_id
            )
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        return assignment
    
    @staticmethod
    async def delete_assignment(
        db: AsyncSession,
        assignment_id: UUID,
        teacher_id: UUID
    ) -> bool:
        """Delete an assignment"""
        
        result = await db.execute(
            select(ReadingAssignment).where(
                ReadingAssignment.id == assignment_id,
                ReadingAssignment.teacher_id == teacher_id
            )
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        await db.delete(assignment)
        await db.commit()
        
        return True
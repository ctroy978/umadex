import re
from typing import List, Tuple, Optional, Dict
from uuid import UUID
from sqlalchemy.orm import Session
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


class MarkupParser:
    """Handles parsing and validation of reading assignment markup"""
    
    @staticmethod
    def validate_markup(content: str, available_images: List[str] = []) -> MarkupValidationResult:
        """Validate the markup content"""
        errors = []
        warnings = []
        image_references = []
        
        # Debug logging
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Validating content length: {len(content)}")
        logger.info(f"Content preview: {content[:200]}...")
        
        # Check for unclosed tags
        for tag in ['chunk', 'important', 'image']:
            open_count = len(re.findall(f'<{tag}>', content))
            close_count = len(re.findall(f'</{tag}>', content))
            if open_count != close_count:
                errors.append(f"Unclosed <{tag}> tag: {open_count} opening tags, {close_count} closing tags")
        
        # Check for at least one chunk
        chunk_matches = re.findall(r'<chunk>(.*?)</chunk>', content, re.DOTALL)
        chunk_count = len(chunk_matches)
        logger.info(f"Found {chunk_count} chunks")
        if chunk_count == 0:
            errors.append("At least one <chunk> tag is required")
        
        # Check that important tags are inside chunks
        important_pattern = r'<important>(.*?)</important>'
        for match in re.finditer(important_pattern, content, re.DOTALL):
            start_pos = match.start()
            # Find if this position is inside a chunk
            in_chunk = False
            for chunk_match in re.finditer(r'<chunk>(.*?)</chunk>', content, re.DOTALL):
                if chunk_match.start() < start_pos < chunk_match.end():
                    in_chunk = True
                    break
            if not in_chunk:
                errors.append(f"<important> tag at position {start_pos} must be inside a <chunk> tag")
        
        # Extract image references
        image_pattern = r'<image>(.*?)</image>'
        for match in re.finditer(image_pattern, content):
            image_key = match.group(1).strip()
            image_references.append(image_key)
            if available_images and image_key not in available_images:
                errors.append(f"Referenced image '{image_key}' not found in uploaded images")
        
        # Check for empty chunks
        for i, chunk_content in enumerate(chunk_matches):
            if not chunk_content.strip():
                warnings.append(f"Chunk {i+1} is empty")
        
        return MarkupValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            chunk_count=chunk_count,
            image_references=image_references
        )
    
    @staticmethod
    def parse_chunks(content: str) -> List[Tuple[str, bool]]:
        """Parse content into chunks with their content and whether they have important sections"""
        chunks = []
        chunk_pattern = r'<chunk>(.*?)</chunk>'
        
        for match in re.finditer(chunk_pattern, content, re.DOTALL):
            chunk_content = match.group(1).strip()
            has_important = '<important>' in chunk_content
            
            # Clean up the content but preserve important tags for later processing
            cleaned_content = chunk_content
            
            chunks.append((cleaned_content, has_important))
        
        return chunks


class ReadingAssignmentService:
    """Service for handling reading assignment operations"""
    
    @staticmethod
    def create_draft(
        db: Session,
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
        db.commit()
        db.refresh(assignment)
        
        return assignment
    
    @staticmethod
    def update_assignment(
        db: Session,
        assignment_id: UUID,
        teacher_id: UUID,
        update_data: ReadingAssignmentUpdate
    ) -> ReadingAssignment:
        """Update an existing assignment"""
        
        assignment = db.query(ReadingAssignment).filter(
            ReadingAssignment.id == assignment_id,
            ReadingAssignment.teacher_id == teacher_id
        ).first()
        
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
        db.commit()
        db.refresh(assignment)
        
        return assignment
    
    @staticmethod
    def validate_assignment_markup(
        db: Session,
        assignment_id: UUID,
        teacher_id: UUID
    ) -> MarkupValidationResult:
        """Validate the markup of an assignment"""
        
        assignment = db.query(ReadingAssignment).filter(
            ReadingAssignment.id == assignment_id,
            ReadingAssignment.teacher_id == teacher_id
        ).first()
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Get available images for this assignment
        images = db.query(AssignmentImage).filter(
            AssignmentImage.assignment_id == assignment_id
        ).all()
        available_images = [img.image_key for img in images]
        
        return MarkupParser.validate_markup(assignment.raw_content, available_images)
    
    @staticmethod
    def publish_assignment(
        db: Session,
        assignment_id: UUID,
        teacher_id: UUID
    ) -> PublishResult:
        """Parse chunks and publish the assignment"""
        
        assignment = db.query(ReadingAssignment).filter(
            ReadingAssignment.id == assignment_id,
            ReadingAssignment.teacher_id == teacher_id
        ).first()
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        # Validate markup first
        images = db.query(AssignmentImage).filter(
            AssignmentImage.assignment_id == assignment_id
        ).all()
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
        db.query(ReadingChunk).filter(
            ReadingChunk.assignment_id == assignment_id
        ).delete()
        
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
        
        db.commit()
        
        return PublishResult(
            success=True,
            message="Assignment published successfully",
            chunk_count=len(chunks_data)
        )
    
    @staticmethod
    def get_teacher_assignments(
        db: Session,
        teacher_id: UUID,
        skip: int = 0,
        limit: int = 20
    ) -> List[ReadingAssignment]:
        """Get all assignments for a teacher"""
        
        return db.query(ReadingAssignment).filter(
            ReadingAssignment.teacher_id == teacher_id
        ).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_assignment_by_id(
        db: Session,
        assignment_id: UUID,
        teacher_id: UUID
    ) -> ReadingAssignment:
        """Get a specific assignment"""
        
        assignment = db.query(ReadingAssignment).filter(
            ReadingAssignment.id == assignment_id,
            ReadingAssignment.teacher_id == teacher_id
        ).first()
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        return assignment
    
    @staticmethod
    def delete_assignment(
        db: Session,
        assignment_id: UUID,
        teacher_id: UUID
    ) -> bool:
        """Delete an assignment"""
        
        assignment = db.query(ReadingAssignment).filter(
            ReadingAssignment.id == assignment_id,
            ReadingAssignment.teacher_id == teacher_id
        ).first()
        
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment not found"
            )
        
        db.delete(assignment)
        db.commit()
        
        return True
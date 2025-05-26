from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.models import User, UserRole
from app.models.reading import ReadingAssignment as ReadingAssignmentModel
from app.schemas.reading import ReadingAssignment, ReadingAssignmentList
from app.utils.deps import get_current_user

router = APIRouter()


def require_student(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be a student"""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access this resource"
        )
    return current_user


@router.get("/assignments/reading", response_model=List[ReadingAssignmentList])
async def list_available_assignments(
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 20
):
    """List reading assignments available to the student based on date visibility"""
    current_time = datetime.utcnow()
    
    result = await db.execute(
        select(ReadingAssignmentModel)
        .where(
            and_(
                ReadingAssignmentModel.status == "published",
                ReadingAssignmentModel.deleted_at.is_(None),
                # Date-based visibility
                (ReadingAssignmentModel.start_date.is_(None) | (ReadingAssignmentModel.start_date <= current_time)),
                (ReadingAssignmentModel.end_date.is_(None) | (ReadingAssignmentModel.end_date >= current_time))
            )
        )
        .order_by(ReadingAssignmentModel.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    return result.scalars().all()


@router.get("/assignments/reading/{assignment_id}", response_model=ReadingAssignment)
async def get_assignment_details(
    assignment_id: UUID,
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific reading assignment with chunks and images"""
    current_time = datetime.utcnow()
    
    result = await db.execute(
        select(ReadingAssignmentModel)
        .options(
            selectinload(ReadingAssignmentModel.chunks),
            selectinload(ReadingAssignmentModel.images)
        )
        .where(
            and_(
                ReadingAssignmentModel.id == assignment_id,
                ReadingAssignmentModel.status == "published",
                ReadingAssignmentModel.deleted_at.is_(None),
                # Date-based visibility
                (ReadingAssignmentModel.start_date.is_(None) | (ReadingAssignmentModel.start_date <= current_time)),
                (ReadingAssignmentModel.end_date.is_(None) | (ReadingAssignmentModel.end_date >= current_time))
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found or not available"
        )
    
    return assignment


@router.get("/assignments/reading/{assignment_id}/availability")
async def check_assignment_availability(
    assignment_id: UUID,
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Check if an assignment is currently available and when it expires"""
    current_time = datetime.utcnow()
    
    result = await db.execute(
        select(ReadingAssignmentModel)
        .where(
            and_(
                ReadingAssignmentModel.id == assignment_id,
                ReadingAssignmentModel.status == "published",
                ReadingAssignmentModel.deleted_at.is_(None)
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Check availability
    is_available = True
    availability_message = "Assignment is currently available"
    expires_in_hours = None
    
    if assignment.start_date and assignment.start_date > current_time:
        is_available = False
        availability_message = f"Assignment will be available from {assignment.start_date.isoformat()}"
    elif assignment.end_date and assignment.end_date < current_time:
        is_available = False
        availability_message = "Assignment is no longer available"
    elif assignment.end_date:
        # Calculate hours until expiration
        time_until_expiry = assignment.end_date - current_time
        expires_in_hours = time_until_expiry.total_seconds() / 3600
        
        if expires_in_hours <= 24:
            availability_message = f"Assignment expires in {expires_in_hours:.1f} hours"
    
    return {
        "is_available": is_available,
        "message": availability_message,
        "start_date": assignment.start_date,
        "end_date": assignment.end_date,
        "expires_in_hours": expires_in_hours
    }
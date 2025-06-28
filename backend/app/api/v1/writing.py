from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, update, delete
from sqlalchemy.orm import selectinload
from typing import Optional, List
from uuid import UUID
from datetime import datetime

from app.core.database import get_db
from app.utils.deps import get_current_user
from app.models import WritingAssignment, StudentWritingSubmission, ClassroomAssignment
from app.models.user import User, UserRole
from app.schemas.writing import (
    WritingAssignmentCreate,
    WritingAssignmentUpdate,
    WritingAssignmentResponse,
    WritingAssignmentListResponse,
    StudentWritingSubmissionCreate,
    StudentWritingSubmissionUpdate,
    StudentWritingSubmissionResponse
)

router = APIRouter(prefix="/writing", tags=["writing"])


def require_teacher(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be a teacher"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this resource"
        )
    return current_user


@router.post("/assignments", response_model=WritingAssignmentResponse)
async def create_writing_assignment(
    assignment: WritingAssignmentCreate,
    current_user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Create a new writing assignment."""
    db_assignment = WritingAssignment(
        teacher_id=current_user.id,
        title=assignment.title,
        prompt_text=assignment.prompt_text,
        word_count_min=assignment.word_count_min,
        word_count_max=assignment.word_count_max,
        evaluation_criteria=assignment.evaluation_criteria.model_dump(),
        instructions=assignment.instructions,
        grade_level=assignment.grade_level,
        subject=assignment.subject
    )
    
    db.add(db_assignment)
    await db.commit()
    await db.refresh(db_assignment)
    
    # Get classroom count
    result = await db.execute(
        select(func.count(ClassroomAssignment.id))
        .where(
            and_(
                ClassroomAssignment.assignment_id == db_assignment.id,
                ClassroomAssignment.assignment_type == "writing"
            )
        )
    )
    classroom_count = result.scalar() or 0
    
    response = WritingAssignmentResponse.model_validate(db_assignment)
    response.classroom_count = classroom_count
    response.is_archived = db_assignment.deleted_at is not None
    
    return response


@router.get("/assignments", response_model=WritingAssignmentListResponse)
async def list_writing_assignments(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    grade_level: Optional[str] = None,
    subject: Optional[str] = None,
    archived: Optional[bool] = None,
    current_user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """List teacher's writing assignments with pagination and filters."""
    # Build base query
    stmt = select(WritingAssignment).where(
        WritingAssignment.teacher_id == current_user.id
    )
    
    # Apply filters
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            or_(
                WritingAssignment.title.ilike(search_term),
                WritingAssignment.prompt_text.ilike(search_term)
            )
        )
    
    if grade_level:
        stmt = stmt.where(WritingAssignment.grade_level == grade_level)
    
    if subject:
        stmt = stmt.where(WritingAssignment.subject == subject)
    
    if archived is not None:
        if archived:
            stmt = stmt.where(WritingAssignment.deleted_at.isnot(None))
        else:
            stmt = stmt.where(WritingAssignment.deleted_at.is_(None))
    
    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # Apply pagination
    stmt = stmt.order_by(WritingAssignment.created_at.desc())
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    
    result = await db.execute(stmt)
    assignments = result.scalars().all()
    
    # Get classroom counts for each assignment
    assignment_responses = []
    for assignment in assignments:
        count_result = await db.execute(
            select(func.count(ClassroomAssignment.id))
            .where(
                and_(
                    ClassroomAssignment.assignment_id == assignment.id,
                    ClassroomAssignment.assignment_type == "writing"
                )
            )
        )
        classroom_count = count_result.scalar() or 0
        
        response = WritingAssignmentResponse.model_validate(assignment)
        response.classroom_count = classroom_count
        response.is_archived = assignment.deleted_at is not None
        assignment_responses.append(response)
    
    total_pages = (total + per_page - 1) // per_page
    
    return WritingAssignmentListResponse(
        assignments=assignment_responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@router.get("/assignments/{assignment_id}", response_model=WritingAssignmentResponse)
async def get_writing_assignment(
    assignment_id: UUID,
    current_user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific writing assignment."""
    result = await db.execute(
        select(WritingAssignment).where(
            and_(
                WritingAssignment.id == assignment_id,
                WritingAssignment.teacher_id == current_user.id
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Writing assignment not found")
    
    # Get classroom count
    count_result = await db.execute(
        select(func.count(ClassroomAssignment.id))
        .where(
            and_(
                ClassroomAssignment.assignment_id == assignment.id,
                ClassroomAssignment.assignment_type == "writing"
            )
        )
    )
    classroom_count = count_result.scalar() or 0
    
    response = WritingAssignmentResponse.model_validate(assignment)
    response.classroom_count = classroom_count
    response.is_archived = assignment.deleted_at is not None
    
    return response


@router.put("/assignments/{assignment_id}", response_model=WritingAssignmentResponse)
async def update_writing_assignment(
    assignment_id: UUID,
    update_data: WritingAssignmentUpdate,
    current_user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Update a writing assignment."""
    result = await db.execute(
        select(WritingAssignment).where(
            and_(
                WritingAssignment.id == assignment_id,
                WritingAssignment.teacher_id == current_user.id
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Writing assignment not found")
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # Handle evaluation_criteria separately
    if 'evaluation_criteria' in update_dict and update_dict['evaluation_criteria'] is not None:
        update_dict['evaluation_criteria'] = update_data.evaluation_criteria.model_dump()
    
    for field, value in update_dict.items():
        setattr(assignment, field, value)
    
    assignment.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(assignment)
    
    # Get classroom count
    count_result = await db.execute(
        select(func.count(ClassroomAssignment.id))
        .where(
            and_(
                ClassroomAssignment.assignment_id == assignment.id,
                ClassroomAssignment.assignment_type == "writing"
            )
        )
    )
    classroom_count = count_result.scalar() or 0
    
    response = WritingAssignmentResponse.model_validate(assignment)
    response.classroom_count = classroom_count
    response.is_archived = assignment.deleted_at is not None
    
    return response


@router.delete("/assignments/{assignment_id}")
async def archive_writing_assignment(
    assignment_id: UUID,
    current_user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Archive (soft delete) a writing assignment."""
    result = await db.execute(
        select(WritingAssignment).where(
            and_(
                WritingAssignment.id == assignment_id,
                WritingAssignment.teacher_id == current_user.id
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Writing assignment not found")
    
    # Check if assignment is attached to any classrooms
    count_result = await db.execute(
        select(func.count(ClassroomAssignment.id))
        .where(
            and_(
                ClassroomAssignment.assignment_id == assignment.id,
                ClassroomAssignment.assignment_type == "writing"
            )
        )
    )
    classroom_count = count_result.scalar() or 0
    
    if classroom_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot archive assignment attached to {classroom_count} classroom(s). Remove from classrooms first."
        )
    
    assignment.deleted_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Writing assignment archived successfully"}


@router.post("/assignments/{assignment_id}/restore")
async def restore_writing_assignment(
    assignment_id: UUID,
    current_user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Restore an archived writing assignment."""
    result = await db.execute(
        select(WritingAssignment).where(
            and_(
                WritingAssignment.id == assignment_id,
                WritingAssignment.teacher_id == current_user.id,
                WritingAssignment.deleted_at.isnot(None)
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Archived writing assignment not found")
    
    assignment.deleted_at = None
    assignment.updated_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Writing assignment restored successfully"}
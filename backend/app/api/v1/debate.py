"""
API routes for UMADebate teacher interface
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.models.user import User
from app.models.debate import DebateAssignment, ContentFlag
from app.utils.supabase_deps import get_current_user_supabase as get_current_user
from app.models.user import UserRole
from app.schemas.debate import (
    DebateAssignmentCreate,
    DebateAssignmentUpdate,
    DebateAssignmentResponse,
    DebateAssignmentListResponse,
    DebateAssignmentSummary,
    ContentFlagResponse,
    ContentFlagUpdate,
    DebateAssignmentFilters
)

router = APIRouter(prefix="/debate", tags=["debate"])


def require_teacher(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be a teacher"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this resource"
        )
    return current_user


@router.post("/assignments", response_model=DebateAssignmentResponse)
async def create_debate_assignment(
    assignment: DebateAssignmentCreate,
    current_teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Create a new debate assignment"""
    # Create new assignment
    db_assignment = DebateAssignment(
        teacher_id=current_teacher.id,
        **assignment.model_dump()
    )
    
    db.add(db_assignment)
    await db.commit()
    await db.refresh(db_assignment)
    
    return db_assignment


@router.get("/assignments", response_model=DebateAssignmentListResponse)
async def list_debate_assignments(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    grade_level: Optional[str] = None,
    subject: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    include_archived: bool = False,
    current_teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """List teacher's debate assignments with filtering and pagination"""
    # Base query
    query = select(DebateAssignment).where(
        DebateAssignment.teacher_id == current_teacher.id
    )
    
    # Apply filters
    filters = []
    
    if not include_archived:
        filters.append(DebateAssignment.deleted_at.is_(None))
    
    if search:
        search_term = f"%{search}%"
        filters.append(
            or_(
                DebateAssignment.title.ilike(search_term),
                DebateAssignment.topic.ilike(search_term),
                DebateAssignment.description.ilike(search_term)
            )
        )
    
    if grade_level:
        filters.append(DebateAssignment.grade_level == grade_level)
    
    if subject:
        filters.append(DebateAssignment.subject == subject)
    
    if date_from:
        filters.append(DebateAssignment.created_at >= date_from)
    
    if date_to:
        filters.append(DebateAssignment.created_at <= date_to)
    
    if filters:
        query = query.where(and_(*filters))
    
    # Get total count
    total_query = select(func.count()).select_from(
        select(DebateAssignment).where(
            DebateAssignment.teacher_id == current_teacher.id
        ).subquery()
    )
    total_result = await db.execute(total_query)
    total_count = total_result.scalar()
    
    # Get filtered count
    filtered_query = select(func.count()).select_from(query.subquery())
    filtered_result = await db.execute(filtered_query)
    filtered_count = filtered_result.scalar()
    
    # Apply pagination
    query = query.order_by(DebateAssignment.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    # Execute query
    result = await db.execute(query)
    assignments = result.scalars().all()
    
    # Convert to summary format
    assignment_summaries = []
    for assignment in assignments:
        summary = DebateAssignmentSummary(
            id=assignment.id,
            title=assignment.title,
            topic=assignment.topic,
            grade_level=assignment.grade_level,
            subject=assignment.subject,
            rounds_per_debate=assignment.rounds_per_debate,
            debate_count=assignment.debate_count,
            time_limit_hours=assignment.time_limit_hours,
            created_at=assignment.created_at,
            deleted_at=assignment.deleted_at,
            student_count=0,  # Will be populated in Phase 2
            completion_rate=0.0  # Will be populated in Phase 2
        )
        assignment_summaries.append(summary)
    
    return DebateAssignmentListResponse(
        assignments=assignment_summaries,
        total=total_count,
        filtered=filtered_count,
        page=page,
        per_page=per_page
    )


@router.get("/assignments/{assignment_id}", response_model=DebateAssignmentResponse)
async def get_debate_assignment(
    assignment_id: UUID,
    current_teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific debate assignment"""
    query = select(DebateAssignment).where(
        and_(
            DebateAssignment.id == assignment_id,
            DebateAssignment.teacher_id == current_teacher.id
        )
    )
    
    result = await db.execute(query)
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    return assignment


@router.put("/assignments/{assignment_id}", response_model=DebateAssignmentResponse)
async def update_debate_assignment(
    assignment_id: UUID,
    update_data: DebateAssignmentUpdate,
    current_teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Update a debate assignment"""
    # Get assignment
    query = select(DebateAssignment).where(
        and_(
            DebateAssignment.id == assignment_id,
            DebateAssignment.teacher_id == current_teacher.id
        )
    )
    
    result = await db.execute(query)
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(assignment, field, value)
    
    assignment.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(assignment)
    
    return assignment


@router.delete("/assignments/{assignment_id}")
async def archive_debate_assignment(
    assignment_id: UUID,
    current_teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete (archive) a debate assignment"""
    # Get assignment
    query = select(DebateAssignment).where(
        and_(
            DebateAssignment.id == assignment_id,
            DebateAssignment.teacher_id == current_teacher.id,
            DebateAssignment.deleted_at.is_(None)
        )
    )
    
    result = await db.execute(query)
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Check if assignment is attached to any classrooms
    from app.models.classroom import ClassroomAssignment
    count_result = await db.execute(
        select(func.count(ClassroomAssignment.id))
        .where(
            and_(
                ClassroomAssignment.assignment_id == assignment.id,
                ClassroomAssignment.assignment_type == "debate"
            )
        )
    )
    classroom_count = count_result.scalar() or 0
    
    if classroom_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot archive assignment attached to {classroom_count} classroom(s). Remove from classrooms first."
        )
    
    # Soft delete
    assignment.deleted_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Assignment archived successfully"}


@router.post("/assignments/{assignment_id}/restore")
async def restore_debate_assignment(
    assignment_id: UUID,
    current_teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Restore a soft-deleted debate assignment"""
    # Get assignment
    query = select(DebateAssignment).where(
        and_(
            DebateAssignment.id == assignment_id,
            DebateAssignment.teacher_id == current_teacher.id,
            DebateAssignment.deleted_at.is_not(None)
        )
    )
    
    result = await db.execute(query)
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archived assignment not found"
        )
    
    # Restore
    assignment.deleted_at = None
    assignment.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "Assignment restored successfully"}


@router.get("/content-flags", response_model=List[ContentFlagResponse])
async def get_pending_content_flags(
    status: Optional[str] = Query("pending"),
    current_teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get content flags for teacher review"""
    query = select(ContentFlag).where(
        ContentFlag.teacher_id == current_teacher.id
    ).options(
        selectinload(ContentFlag.student),
        selectinload(ContentFlag.assignment)
    )
    
    if status:
        query = query.where(ContentFlag.status == status)
    
    query = query.order_by(ContentFlag.created_at.desc())
    
    result = await db.execute(query)
    flags = result.scalars().all()
    
    # Enhance response with additional info
    flag_responses = []
    for flag in flags:
        flag_response = ContentFlagResponse(
            **flag.__dict__,
            student_name=f"{flag.student.first_name} {flag.student.last_name}",
            assignment_title=flag.assignment.title
        )
        flag_responses.append(flag_response)
    
    return flag_responses


@router.put("/content-flags/{flag_id}", response_model=ContentFlagResponse)
async def update_content_flag(
    flag_id: UUID,
    update_data: ContentFlagUpdate,
    current_teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Update a content flag (resolve moderation)"""
    query = select(ContentFlag).where(
        and_(
            ContentFlag.id == flag_id,
            ContentFlag.teacher_id == current_teacher.id
        )
    ).options(
        selectinload(ContentFlag.student),
        selectinload(ContentFlag.assignment)
    )
    
    result = await db.execute(query)
    flag = result.scalar_one_or_none()
    
    if not flag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Content flag not found"
        )
    
    # Update flag
    flag.status = update_data.status
    flag.teacher_action = update_data.teacher_action
    flag.teacher_notes = update_data.teacher_notes
    flag.resolved_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(flag)
    
    return ContentFlagResponse(
        **flag.__dict__,
        student_name=f"{flag.student.first_name} {flag.student.last_name}",
        assignment_title=flag.assignment.title
    )
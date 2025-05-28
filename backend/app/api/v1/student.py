from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from typing import List
from uuid import UUID
from datetime import datetime, timezone

from app.core.database import get_db
from app.models import User, UserRole, Classroom, ClassroomStudent
from app.models.classroom import ClassroomAssignment
from app.models.reading import ReadingAssignment as ReadingAssignmentModel
from app.schemas.reading import ReadingAssignment, ReadingAssignmentList
from app.schemas.classroom import (
    ClassroomResponse, JoinClassroomRequest, JoinClassroomResponse,
    AssignmentInClassroom
)
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
    """List all published reading assignments available to the student"""
    result = await db.execute(
        select(ReadingAssignmentModel)
        .where(
            and_(
                ReadingAssignmentModel.status == "published",
                ReadingAssignmentModel.deleted_at.is_(None)
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
                ReadingAssignmentModel.deleted_at.is_(None)
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


# Classroom endpoints

@router.post("/join-classroom", response_model=JoinClassroomResponse)
async def join_classroom(
    request: JoinClassroomRequest,
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Join a classroom using a class code"""
    # Find classroom by code
    result = await db.execute(
        select(Classroom).where(Classroom.class_code == request.class_code)
    )
    classroom = result.scalar_one_or_none()
    
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid class code"
        )
    
    # Check if already enrolled
    enrollment_result = await db.execute(
        select(ClassroomStudent).where(
            and_(
                ClassroomStudent.classroom_id == classroom.id,
                ClassroomStudent.student_id == student.id,
                ClassroomStudent.removed_at.is_(None)
            )
        )
    )
    existing_enrollment = enrollment_result.scalar_one_or_none()
    
    if existing_enrollment:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already enrolled in this classroom"
        )
    
    # Create enrollment
    enrollment = ClassroomStudent(
        classroom_id=classroom.id,
        student_id=student.id,
        joined_at=datetime.utcnow()
    )
    db.add(enrollment)
    await db.commit()
    
    # Get counts for response
    student_count_result = await db.execute(
        select(func.count(ClassroomStudent.id)).where(
            and_(
                ClassroomStudent.classroom_id == classroom.id,
                ClassroomStudent.removed_at.is_(None)
            )
        )
    )
    student_count = student_count_result.scalar() or 0
    
    assignment_count_result = await db.execute(
        select(func.count(ClassroomAssignment.id)).where(
            ClassroomAssignment.classroom_id == classroom.id
        )
    )
    assignment_count = assignment_count_result.scalar() or 0
    
    classroom_response = ClassroomResponse(
        id=classroom.id,
        name=classroom.name,
        teacher_id=classroom.teacher_id,
        class_code=classroom.class_code,
        created_at=classroom.created_at,
        deleted_at=classroom.deleted_at,
        student_count=student_count,
        assignment_count=assignment_count
    )
    
    return JoinClassroomResponse(
        classroom=classroom_response,
        message="Successfully joined classroom"
    )


@router.get("/classrooms", response_model=List[ClassroomResponse])
async def list_my_classrooms(
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """List all classrooms the student is enrolled in"""
    # Get classrooms student is enrolled in
    result = await db.execute(
        select(Classroom)
        .join(ClassroomStudent)
        .where(
            and_(
                ClassroomStudent.student_id == student.id,
                ClassroomStudent.removed_at.is_(None)
            )
        )
        .order_by(Classroom.created_at.desc())
    )
    classrooms = result.scalars().all()
    
    classroom_responses = []
    for classroom in classrooms:
        # Get student count
        student_count_result = await db.execute(
            select(func.count(ClassroomStudent.id)).where(
                and_(
                    ClassroomStudent.classroom_id == classroom.id,
                    ClassroomStudent.removed_at.is_(None)
                )
            )
        )
        student_count = student_count_result.scalar() or 0
        
        # Get assignment count
        assignment_count_result = await db.execute(
            select(func.count(ClassroomAssignment.id)).where(
                ClassroomAssignment.classroom_id == classroom.id
            )
        )
        assignment_count = assignment_count_result.scalar() or 0
        
        response = ClassroomResponse(
            id=classroom.id,
            name=classroom.name,
            teacher_id=classroom.teacher_id,
            class_code=classroom.class_code,
            created_at=classroom.created_at,
            deleted_at=classroom.deleted_at,
            student_count=student_count,
            assignment_count=assignment_count
        )
        classroom_responses.append(response)
    
    return classroom_responses


@router.delete("/classrooms/{classroom_id}/leave")
async def leave_classroom(
    classroom_id: UUID,
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Leave a classroom"""
    # Find enrollment
    result = await db.execute(
        select(ClassroomStudent).where(
            and_(
                ClassroomStudent.classroom_id == classroom_id,
                ClassroomStudent.student_id == student.id,
                ClassroomStudent.removed_at.is_(None)
            )
        )
    )
    enrollment = result.scalar_one_or_none()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not enrolled in this classroom"
        )
    
    # Mark as removed
    enrollment.removed_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Successfully left classroom"}


@router.get("/classrooms/{classroom_id}/assignments", response_model=List[AssignmentInClassroom])
async def list_classroom_assignments(
    classroom_id: UUID,
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """List assignments in a classroom the student is enrolled in"""
    # Verify student is enrolled
    enrollment_result = await db.execute(
        select(ClassroomStudent).where(
            and_(
                ClassroomStudent.classroom_id == classroom_id,
                ClassroomStudent.student_id == student.id,
                ClassroomStudent.removed_at.is_(None)
            )
        )
    )
    enrollment = enrollment_result.scalar_one_or_none()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not enrolled in this classroom"
        )
    
    # Get current time for date filtering
    current_time = datetime.now(timezone.utc)
    
    # Get assignments with classroom assignment details
    result = await db.execute(
        select(
            ClassroomAssignment,
            ReadingAssignmentModel
        )
        .join(
            ReadingAssignmentModel,
            ClassroomAssignment.assignment_id == ReadingAssignmentModel.id
        )
        .where(
            and_(
                ClassroomAssignment.classroom_id == classroom_id,
                ReadingAssignmentModel.deleted_at.is_(None),
                # Filter by start date - either no start date or already started
                (ClassroomAssignment.start_date.is_(None) | (ClassroomAssignment.start_date <= current_time)),
                # Filter by end date - either no end date or not yet ended
                (ClassroomAssignment.end_date.is_(None) | (ClassroomAssignment.end_date > current_time))
            )
        )
        .order_by(ClassroomAssignment.display_order.asc(), ClassroomAssignment.assigned_at.desc())
    )
    
    assignment_list = []
    for ca, assignment in result:
        assignment_list.append(AssignmentInClassroom(
            assignment_id=assignment.id,
            title=assignment.assignment_title,
            assignment_type=assignment.assignment_type,
            assigned_at=ca.assigned_at,
            display_order=ca.display_order,
            start_date=ca.start_date,
            end_date=ca.end_date
        ))
    
    return assignment_list
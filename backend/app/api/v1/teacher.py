from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.schemas.classroom import (
    ClassroomCreate, ClassroomResponse, ClassroomUpdate,
    DashboardStats, ClassroomStudentResponse, EnrollStudentRequest
)
from app.models import User, Classroom, ClassroomStudent, Assignment, UserRole
from app.utils.deps import get_current_user

router = APIRouter()

def require_teacher(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be a teacher"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this resource"
        )
    return current_user

@router.get("/dashboard-stats", response_model=DashboardStats)
async def get_dashboard_stats(
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard statistics for teacher"""
    # Count classrooms
    classrooms_result = await db.execute(
        select(func.count(Classroom.id)).where(Classroom.teacher_id == teacher.id)
    )
    total_classrooms = classrooms_result.scalar() or 0
    
    # Count unique students across all classrooms
    students_result = await db.execute(
        select(func.count(func.distinct(ClassroomStudent.student_id)))
        .select_from(ClassroomStudent)
        .join(Classroom)
        .where(Classroom.teacher_id == teacher.id)
    )
    total_students = students_result.scalar() or 0
    
    # Count active (published) assignments
    assignments_result = await db.execute(
        select(func.count(Assignment.id))
        .where(and_(
            Assignment.teacher_id == teacher.id,
            Assignment.is_published == True
        ))
    )
    active_assignments = assignments_result.scalar() or 0
    
    # Get recent assignments
    recent_assignments_result = await db.execute(
        select(Assignment)
        .where(Assignment.teacher_id == teacher.id)
        .order_by(Assignment.created_at.desc())
        .limit(5)
    )
    recent_assignments = recent_assignments_result.scalars().all()
    
    return DashboardStats(
        total_classrooms=total_classrooms,
        total_students=total_students,
        active_assignments=active_assignments,
        recent_assignments=recent_assignments
    )

@router.get("/classrooms", response_model=List[ClassroomResponse])
async def list_classrooms(
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List all teacher's classrooms"""
    result = await db.execute(
        select(Classroom)
        .where(Classroom.teacher_id == teacher.id)
        .order_by(Classroom.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    classrooms = result.scalars().all()
    
    # Add student count to each classroom
    classroom_responses = []
    for classroom in classrooms:
        count_result = await db.execute(
            select(func.count(ClassroomStudent.id))
            .where(ClassroomStudent.classroom_id == classroom.id)
        )
        student_count = count_result.scalar() or 0
        
        response = ClassroomResponse.model_validate(classroom)
        response.student_count = student_count
        classroom_responses.append(response)
    
    return classroom_responses

@router.post("/classrooms", response_model=ClassroomResponse)
async def create_classroom(
    classroom_data: ClassroomCreate,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Create a new classroom"""
    classroom = Classroom(
        teacher_id=teacher.id,
        **classroom_data.model_dump()
    )
    db.add(classroom)
    await db.commit()
    await db.refresh(classroom)
    
    response = ClassroomResponse.model_validate(classroom)
    response.student_count = 0
    return response

@router.put("/classrooms/{classroom_id}", response_model=ClassroomResponse)
async def update_classroom(
    classroom_id: UUID,
    classroom_data: ClassroomUpdate,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Update classroom details"""
    result = await db.execute(
        select(Classroom).where(
            and_(
                Classroom.id == classroom_id,
                Classroom.teacher_id == teacher.id
            )
        )
    )
    classroom = result.scalar_one_or_none()
    
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )
    
    # Update fields
    update_data = classroom_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(classroom, field, value)
    
    await db.commit()
    await db.refresh(classroom)
    
    # Get student count
    count_result = await db.execute(
        select(func.count(ClassroomStudent.id))
        .where(ClassroomStudent.classroom_id == classroom.id)
    )
    student_count = count_result.scalar() or 0
    
    response = ClassroomResponse.model_validate(classroom)
    response.student_count = student_count
    return response

@router.get("/classrooms/{classroom_id}/students", response_model=List[ClassroomStudentResponse])
async def list_classroom_students(
    classroom_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """List students in a classroom"""
    # Verify classroom belongs to teacher
    classroom_result = await db.execute(
        select(Classroom).where(
            and_(
                Classroom.id == classroom_id,
                Classroom.teacher_id == teacher.id
            )
        )
    )
    classroom = classroom_result.scalar_one_or_none()
    
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )
    
    # Get students
    result = await db.execute(
        select(ClassroomStudent, User)
        .join(User, User.id == ClassroomStudent.student_id)
        .where(ClassroomStudent.classroom_id == classroom_id)
        .order_by(User.last_name, User.first_name)
    )
    
    students = []
    for enrollment, student in result:
        students.append(ClassroomStudentResponse(
            id=enrollment.id,
            student_id=student.id,
            first_name=student.first_name,
            last_name=student.last_name,
            email=student.email,
            enrolled_at=enrollment.enrolled_at,
            status=enrollment.status
        ))
    
    return students

@router.post("/classrooms/{classroom_id}/students")
async def enroll_student(
    classroom_id: UUID,
    request: EnrollStudentRequest,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Enroll a student in a classroom"""
    # Verify classroom belongs to teacher
    classroom_result = await db.execute(
        select(Classroom).where(
            and_(
                Classroom.id == classroom_id,
                Classroom.teacher_id == teacher.id
            )
        )
    )
    classroom = classroom_result.scalar_one_or_none()
    
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )
    
    # Find student by email
    student_result = await db.execute(
        select(User).where(
            and_(
                User.email == request.student_email,
                User.role == UserRole.STUDENT
            )
        )
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Check if already enrolled
    existing_result = await db.execute(
        select(ClassroomStudent).where(
            and_(
                ClassroomStudent.classroom_id == classroom_id,
                ClassroomStudent.student_id == student.id
            )
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student already enrolled"
        )
    
    # Create enrollment
    enrollment = ClassroomStudent(
        classroom_id=classroom_id,
        student_id=student.id
    )
    db.add(enrollment)
    await db.commit()
    
    return {"message": "Student enrolled successfully"}
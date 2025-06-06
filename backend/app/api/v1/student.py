from typing import List, Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, and_, or_, func, exists, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.classroom import Classroom, ClassroomStudent, ClassroomAssignment
from app.models.reading import ReadingAssignment
from app.models.vocabulary import VocabularyList
from app.models.umaread import UmareadAssignmentProgress
from app.models.tests import AssignmentTest
from app.utils.deps import get_current_user
from app.schemas.classroom import ClassroomResponse

router = APIRouter()


class JoinClassroomRequest(BaseModel):
    class_code: str = Field(..., min_length=6, max_length=8)


class JoinClassroomResponse(BaseModel):
    success: bool
    message: str
    classroom: Optional[ClassroomResponse] = None


class StudentClassroomResponse(BaseModel):
    id: UUID
    name: str
    teacher_name: str
    teacher_id: UUID
    class_code: str
    joined_at: datetime
    assignment_count: int
    available_assignment_count: int
    created_at: datetime


class AssignmentStatus(BaseModel):
    status: str  # "not_started", "active", "expired"
    
class StudentAssignmentResponse(BaseModel):
    id: str
    title: str
    work_title: Optional[str] = None
    author: Optional[str] = None
    grade_level: Optional[str] = None
    type: str
    item_type: str  # 'reading' or 'vocabulary'
    assigned_at: datetime
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    display_order: Optional[int] = None
    status: str  # "not_started", "active", "expired"
    is_completed: bool = False
    has_test: bool = False

class StudentClassroomDetailResponse(BaseModel):
    id: UUID
    name: str
    teacher_name: str
    teacher_id: UUID
    class_code: str
    joined_at: datetime
    created_at: datetime
    assignments: List[StudentAssignmentResponse]


def calculate_assignment_status(start_date: Optional[datetime], end_date: Optional[datetime]) -> str:
    """Calculate assignment status based on current time and start/end dates"""
    current_time = datetime.now(timezone.utc)
    
    if start_date and current_time < start_date:
        return "not_started"
    elif end_date and current_time > end_date:
        return "expired"
    else:
        return "active"


def require_student_or_teacher(current_user: User = Depends(get_current_user)) -> User:
    """Allow both students and teachers (teachers can view student experience)"""
    if current_user.role not in [UserRole.STUDENT, UserRole.TEACHER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    return current_user


@router.get("/classrooms", response_model=List[StudentClassroomResponse])
async def get_student_classrooms(
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get all classrooms the current user is enrolled in"""
    # Query classrooms with teacher info and assignment counts
    query = (
        select(
            Classroom,
            ClassroomStudent,
            User.first_name.label('teacher_first_name'),
            User.last_name.label('teacher_last_name'),
            func.count(ClassroomAssignment.id).label('total_assignments'),
            func.count(
                case(
                    (
                        and_(
                            or_(ClassroomAssignment.start_date.is_(None), 
                                ClassroomAssignment.start_date <= datetime.now(timezone.utc)),
                            or_(ClassroomAssignment.end_date.is_(None), 
                                ClassroomAssignment.end_date >= datetime.now(timezone.utc))
                        ),
                        ClassroomAssignment.id
                    ),
                    else_=None
                )
            ).label('available_assignments')
        )
        .join(ClassroomStudent, ClassroomStudent.classroom_id == Classroom.id)
        .join(User, User.id == Classroom.teacher_id)
        .outerjoin(ClassroomAssignment, ClassroomAssignment.classroom_id == Classroom.id)
        .where(
            and_(
                ClassroomStudent.student_id == current_user.id,
                ClassroomStudent.removed_at.is_(None),
                Classroom.deleted_at.is_(None)
            )
        )
        .group_by(Classroom.id, ClassroomStudent.classroom_id, ClassroomStudent.student_id, 
                  ClassroomStudent.joined_at, ClassroomStudent.removed_at, ClassroomStudent.removed_by,
                  User.first_name, User.last_name)
        .order_by(ClassroomStudent.joined_at.desc())
    )
    
    result = await db.execute(query)
    classrooms = []
    
    for row in result:
        classroom = row.Classroom
        student = row.ClassroomStudent
        classrooms.append(StudentClassroomResponse(
            id=classroom.id,
            name=classroom.name,
            teacher_name=f"{row.teacher_first_name} {row.teacher_last_name}",
            teacher_id=classroom.teacher_id,
            class_code=classroom.class_code,
            joined_at=student.joined_at,
            assignment_count=row.total_assignments,
            available_assignment_count=row.available_assignments,
            created_at=classroom.created_at
        ))
    
    return classrooms


@router.post("/join-classroom", response_model=JoinClassroomResponse)
async def join_classroom(
    request: JoinClassroomRequest,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Join a classroom using the class code"""
    # Clean up the class code
    class_code = request.class_code.strip().upper()
    
    # Find classroom by code
    result = await db.execute(
        select(Classroom)
        .where(
            and_(
                Classroom.class_code == class_code,
                Classroom.deleted_at.is_(None)
            )
        )
    )
    classroom = result.scalar_one_or_none()
    
    if not classroom:
        return JoinClassroomResponse(
            success=False,
            message="Invalid classroom code. Please check and try again."
        )
    
    # Check if already enrolled
    existing = await db.execute(
        select(ClassroomStudent)
        .where(
            and_(
                ClassroomStudent.classroom_id == classroom.id,
                ClassroomStudent.student_id == current_user.id
            )
        )
    )
    enrollment = existing.scalar_one_or_none()
    
    if enrollment:
        if enrollment.removed_at:
            # Re-enroll the student
            enrollment.removed_at = None
            enrollment.removed_by = None
            enrollment.joined_at = datetime.now(timezone.utc)
            await db.commit()
            
            # Get teacher info for response
            teacher_result = await db.execute(
                select(User).where(User.id == classroom.teacher_id)
            )
            teacher = teacher_result.scalar_one()
            
            return JoinClassroomResponse(
                success=True,
                message="Successfully re-enrolled in the classroom!",
                classroom=ClassroomResponse(
                    id=classroom.id,
                    name=classroom.name,
                    teacher_id=classroom.teacher_id,
                    teacher_name=f"{teacher.first_name} {teacher.last_name}",
                    class_code=classroom.class_code,
                    created_at=classroom.created_at,
                    student_count=0,  # Not calculated here
                    assignment_count=0  # Not calculated here
                )
            )
        else:
            return JoinClassroomResponse(
                success=False,
                message="You are already enrolled in this classroom."
            )
    
    # Create new enrollment
    new_enrollment = ClassroomStudent(
        classroom_id=classroom.id,
        student_id=current_user.id,
        joined_at=datetime.now(timezone.utc)
    )
    db.add(new_enrollment)
    await db.commit()
    
    # Get teacher info for response
    teacher_result = await db.execute(
        select(User).where(User.id == classroom.teacher_id)
    )
    teacher = teacher_result.scalar_one()
    
    return JoinClassroomResponse(
        success=True,
        message="Successfully joined the classroom!",
        classroom=ClassroomResponse(
            id=classroom.id,
            name=classroom.name,
            teacher_id=classroom.teacher_id,
            teacher_name=f"{teacher.first_name} {teacher.last_name}",
            class_code=classroom.class_code,
            created_at=classroom.created_at,
            student_count=0,  # Not calculated here
            assignment_count=0  # Not calculated here
        )
    )


@router.delete("/classrooms/{classroom_id}/leave")
async def leave_classroom(
    classroom_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Leave a classroom (soft delete)"""
    # Find enrollment
    result = await db.execute(
        select(ClassroomStudent)
        .where(
            and_(
                ClassroomStudent.classroom_id == classroom_id,
                ClassroomStudent.student_id == current_user.id,
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
    
    # Soft delete the enrollment
    enrollment.removed_at = datetime.now(timezone.utc)
    enrollment.removed_by = current_user.id
    await db.commit()
    
    return {"message": "Successfully left the classroom"}


@router.get("/classrooms/{classroom_id}", response_model=StudentClassroomDetailResponse)
async def get_classroom_detail(
    classroom_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed classroom information for an enrolled student"""
    # Verify enrollment
    enrollment_check = await db.execute(
        select(ClassroomStudent)
        .where(
            and_(
                ClassroomStudent.classroom_id == classroom_id,
                ClassroomStudent.student_id == current_user.id,
                ClassroomStudent.removed_at.is_(None)
            )
        )
    )
    enrollment = enrollment_check.scalar_one_or_none()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not enrolled in this classroom"
        )
    
    # Get classroom with teacher info
    classroom_result = await db.execute(
        select(Classroom, User)
        .join(User, User.id == Classroom.teacher_id)
        .where(
            and_(
                Classroom.id == classroom_id,
                Classroom.deleted_at.is_(None)
            )
        )
    )
    result = classroom_result.one_or_none()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )
    
    classroom, teacher = result
    
    # Get all assignments (not filtered by date)
    assignments = []
    
    # Get reading assignments with completion status and test availability
    reading_query = await db.execute(
        select(
            ReadingAssignment, 
            ClassroomAssignment,
            UmareadAssignmentProgress.completed_at,
            exists().where(
                and_(
                    AssignmentTest.assignment_id == ReadingAssignment.id,
                    AssignmentTest.status == "approved"
                )
            ).label("has_test")
        )
        .join(ClassroomAssignment, 
              and_(
                  ClassroomAssignment.assignment_id == ReadingAssignment.id,
                  ClassroomAssignment.assignment_type == "reading"
              ))
        .outerjoin(
            UmareadAssignmentProgress,
            and_(
                UmareadAssignmentProgress.assignment_id == ReadingAssignment.id,
                UmareadAssignmentProgress.student_id == current_user.id
            )
        )
        .where(
            and_(
                ClassroomAssignment.classroom_id == classroom_id,
                ReadingAssignment.deleted_at.is_(None),
                ReadingAssignment.status == "published"
            )
        )
        .order_by(ClassroomAssignment.start_date, ClassroomAssignment.display_order, ClassroomAssignment.assigned_at)
    )
    
    for row in reading_query:
        assignment = row.ReadingAssignment
        ca = row.ClassroomAssignment
        completed_at = row.completed_at
        has_test = row.has_test
        
        status = calculate_assignment_status(ca.start_date, ca.end_date)
        assignments.append(StudentAssignmentResponse(
            id=str(assignment.id),
            title=assignment.assignment_title,
            work_title=assignment.work_title,
            author=assignment.author,
            grade_level=assignment.grade_level,
            type=assignment.assignment_type,
            item_type="reading",
            assigned_at=ca.assigned_at,
            start_date=ca.start_date,
            end_date=ca.end_date,
            display_order=ca.display_order,
            status=status,
            is_completed=completed_at is not None,
            has_test=has_test
        ))
    
    # Get vocabulary assignments
    vocab_query = await db.execute(
        select(VocabularyList, ClassroomAssignment)
        .join(ClassroomAssignment,
              and_(
                  ClassroomAssignment.vocabulary_list_id == VocabularyList.id,
                  ClassroomAssignment.assignment_type == "vocabulary"
              ))
        .where(
            and_(
                ClassroomAssignment.classroom_id == classroom_id,
                VocabularyList.deleted_at.is_(None)
            )
        )
        .order_by(ClassroomAssignment.start_date, ClassroomAssignment.display_order, ClassroomAssignment.assigned_at)
    )
    
    for vocab_list, ca in vocab_query:
        status = calculate_assignment_status(ca.start_date, ca.end_date)
        assignments.append(StudentAssignmentResponse(
            id=str(vocab_list.id),
            title=vocab_list.title,
            work_title=None,
            author=None,
            grade_level=None,
            type="UMAVocab",
            item_type="vocabulary",
            assigned_at=ca.assigned_at,
            start_date=ca.start_date,
            end_date=ca.end_date,
            display_order=ca.display_order,
            status=status,
            is_completed=False,  # Vocabulary assignments don't have completion tracking yet
            has_test=False  # Vocabulary assignments don't have tests
        ))
    
    # Sort assignments by start date (earliest first), then display order
    assignments.sort(key=lambda x: (
        x.start_date or datetime.min.replace(tzinfo=timezone.utc),
        x.display_order or float('inf'),
        x.assigned_at
    ))
    
    return StudentClassroomDetailResponse(
        id=classroom.id,
        name=classroom.name,
        teacher_name=f"{teacher.first_name} {teacher.last_name}",
        teacher_id=classroom.teacher_id,
        class_code=classroom.class_code,
        joined_at=enrollment.joined_at,
        created_at=classroom.created_at,
        assignments=assignments
    )


@router.get("/assignment/{assignment_type}/{assignment_id}/validate")
async def validate_assignment_access(
    assignment_type: str,
    assignment_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Validate if a student can access a specific assignment"""
    # Check assignment type
    if assignment_type not in ["reading", "vocabulary"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid assignment type"
        )
    
    # Find the classroom assignment
    ca_query = select(ClassroomAssignment, Classroom)
    ca_query = ca_query.join(Classroom, Classroom.id == ClassroomAssignment.classroom_id)
    
    if assignment_type == "reading":
        ca_query = ca_query.where(
            and_(
                ClassroomAssignment.assignment_id == assignment_id,
                ClassroomAssignment.assignment_type == "reading"
            )
        )
    else:
        ca_query = ca_query.where(
            and_(
                ClassroomAssignment.vocabulary_list_id == assignment_id,
                ClassroomAssignment.assignment_type == "vocabulary"
            )
        )
    
    result = await db.execute(ca_query)
    ca_result = result.one_or_none()
    
    if not ca_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    classroom_assignment, classroom = ca_result
    
    # Check if student is enrolled
    enrollment = await db.execute(
        select(ClassroomStudent)
        .where(
            and_(
                ClassroomStudent.classroom_id == classroom.id,
                ClassroomStudent.student_id == current_user.id,
                ClassroomStudent.removed_at.is_(None)
            )
        )
    )
    
    if not enrollment.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not enrolled in this classroom"
        )
    
    # Check assignment status
    status = calculate_assignment_status(classroom_assignment.start_date, classroom_assignment.end_date)
    
    if status == "not_started":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Assignment not available yet. Starts on {classroom_assignment.start_date.strftime('%B %d, %Y')}"
        )
    elif status == "expired":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Assignment has ended. Ended on {classroom_assignment.end_date.strftime('%B %d, %Y')}"
        )
    
    # Check if assignment is archived
    if assignment_type == "reading":
        assignment_check = await db.execute(
            select(ReadingAssignment)
            .where(
                and_(
                    ReadingAssignment.id == assignment_id,
                    ReadingAssignment.deleted_at.is_(None),
                    ReadingAssignment.status == "published"
                )
            )
        )
        if not assignment_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Assignment is not available"
            )
    else:
        vocab_check = await db.execute(
            select(VocabularyList)
            .where(
                and_(
                    VocabularyList.id == assignment_id,
                    VocabularyList.deleted_at.is_(None)
                )
            )
        )
        if not vocab_check.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Assignment is not available"
            )
    
    return {
        "access_granted": True,
        "classroom_id": str(classroom.id),
        "classroom_name": classroom.name,
        "assignment_type": assignment_type,
        "assignment_id": str(assignment_id)
    }


class TestStatusResponse(BaseModel):
    has_test: bool
    test_id: Optional[str] = None


@router.get("/assignment/reading/{assignment_id}/test-status", response_model=TestStatusResponse)
async def get_assignment_test_status(
    assignment_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Check if a reading assignment has an associated test"""
    # First, verify that the student has access to this assignment through their classroom enrollment
    ca_query = select(ClassroomAssignment, Classroom)
    ca_query = ca_query.join(Classroom, Classroom.id == ClassroomAssignment.classroom_id)
    ca_query = ca_query.where(
        and_(
            ClassroomAssignment.assignment_id == assignment_id,
            ClassroomAssignment.assignment_type == "reading"
        )
    )
    
    result = await db.execute(ca_query)
    ca_result = result.one_or_none()
    
    if not ca_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    classroom_assignment, classroom = ca_result
    
    # Check if student is enrolled in the classroom
    enrollment = await db.execute(
        select(ClassroomStudent)
        .where(
            and_(
                ClassroomStudent.classroom_id == classroom.id,
                ClassroomStudent.student_id == current_user.id,
                ClassroomStudent.removed_at.is_(None)
            )
        )
    )
    
    if not enrollment.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not enrolled in this classroom"
        )
    
    # Check if assignment has an approved test
    test_query = await db.execute(
        select(AssignmentTest.id)
        .where(
            and_(
                AssignmentTest.assignment_id == assignment_id,
                AssignmentTest.status == "approved"
            )
        )
    )
    test = test_query.scalar_one_or_none()
    
    if test:
        return TestStatusResponse(has_test=True, test_id=str(test))
    else:
        return TestStatusResponse(has_test=False)
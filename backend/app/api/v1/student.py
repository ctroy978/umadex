from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy import select, and_, or_, func, exists, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.classroom import Classroom, ClassroomStudent, ClassroomAssignment, StudentAssignment
from app.models.reading import ReadingAssignment
from app.models.vocabulary import VocabularyList
from app.models.umaread import UmareadAssignmentProgress
from app.models.tests import AssignmentTest, StudentTestAttempt
from app.utils.deps import get_current_user
from app.schemas.classroom import ClassroomResponse
from app.services.vocabulary_practice import VocabularyPracticeService

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
    test_completed: bool = False
    test_attempt_id: Optional[str] = None

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


@router.get("/vocabulary/{assignment_id}")
async def get_vocabulary_assignment(
    assignment_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get vocabulary assignment details with words filtered by classroom settings"""
    # Get the vocabulary list and verify student access
    vocab_result = await db.execute(
        select(VocabularyList, ClassroomAssignment, Classroom, User)
        .join(ClassroomAssignment, ClassroomAssignment.vocabulary_list_id == VocabularyList.id)
        .join(Classroom, Classroom.id == ClassroomAssignment.classroom_id)
        .join(User, User.id == Classroom.teacher_id)  # Join teacher
        .join(ClassroomStudent, 
              and_(
                  ClassroomStudent.classroom_id == Classroom.id,
                  ClassroomStudent.student_id == current_user.id,
                  ClassroomStudent.removed_at.is_(None)
              ))
        .where(
            and_(
                VocabularyList.id == assignment_id,
                VocabularyList.deleted_at.is_(None),
                VocabularyList.status == "published"
            )
        )
    )
    
    result = vocab_result.one_or_none()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary assignment not found or you don't have access"
        )
    
    vocab_list, classroom_assignment, classroom, teacher = result
    
    # Check if assignment is active
    status = calculate_assignment_status(classroom_assignment.start_date, classroom_assignment.end_date)
    if status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This assignment is not currently active"
        )
    
    # Get all words for this vocabulary list
    from sqlalchemy.orm import selectinload
    words_result = await db.execute(
        select(VocabularyList)
        .where(VocabularyList.id == assignment_id)
        .options(selectinload(VocabularyList.words))
    )
    vocab_with_words = words_result.scalar_one()
    
    # Apply vocabulary settings to filter available words
    vocab_settings = classroom_assignment.vocab_settings or {}
    delivery_mode = vocab_settings.get('delivery_mode', 'all_at_once')
    group_size = vocab_settings.get('group_size', 5)
    released_groups = vocab_settings.get('released_groups', [])
    
    # Sort words by position
    all_words = sorted(vocab_with_words.words, key=lambda w: w.position)
    
    # Filter words based on settings
    available_words = []
    
    if delivery_mode == 'all_at_once':
        available_words = all_words
    elif delivery_mode == 'in_groups':
        # Show words from all groups (for now - this is Phase 1)
        # In Phase 2, we would track which groups are unlocked
        available_words = all_words
    elif delivery_mode == 'teacher_controlled':
        # Only show words from released groups
        if released_groups:
            for group_num in released_groups:
                start_idx = (group_num - 1) * group_size
                end_idx = start_idx + group_size
                available_words.extend(all_words[start_idx:end_idx])
        # If no groups released, show no words
    
    # Format words for response
    formatted_words = []
    for word in available_words:
        # Use teacher definition/examples first, fall back to AI
        definition = word.teacher_definition or word.ai_definition
        example_1 = word.teacher_example_1 or word.ai_example_1
        example_2 = word.teacher_example_2 or word.ai_example_2
        
        formatted_words.append({
            "id": str(word.id),
            "word": word.word,
            "definition": definition,
            "example_1": example_1,
            "example_2": example_2,
            "audio_url": word.audio_url,
            "phonetic_text": word.phonetic_text,
            "position": word.position
        })
    
    return {
        "id": str(vocab_list.id),
        "title": vocab_list.title,
        "context_description": vocab_list.context_description,
        "grade_level": vocab_list.grade_level,
        "subject_area": vocab_list.subject_area,
        "classroom_name": classroom.name,
        "teacher_name": f"{teacher.first_name} {teacher.last_name}",
        "start_date": classroom_assignment.start_date,
        "end_date": classroom_assignment.end_date,
        "total_words": len(all_words),
        "available_words": len(available_words),
        "words": formatted_words,
        "settings": {
            "delivery_mode": delivery_mode,
            "group_size": group_size,
            "groups_count": (len(all_words) + group_size - 1) // group_size if group_size > 0 else 1,
            "released_groups": released_groups
        }
    }


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
            AssignmentTest.id.label("test_id"),
            AssignmentTest.status.label("test_status"),
            StudentTestAttempt.id.label("test_attempt_id"),
            StudentTestAttempt.status.label("attempt_status")
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
        .outerjoin(
            AssignmentTest,
            and_(
                AssignmentTest.assignment_id == ReadingAssignment.id,
                AssignmentTest.status == "approved"
            )
        )
        .outerjoin(
            StudentTestAttempt,
            and_(
                StudentTestAttempt.assignment_test_id == AssignmentTest.id,
                StudentTestAttempt.student_id == current_user.id,
                StudentTestAttempt.status.in_(["submitted", "evaluated", "graded"])
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
        test_id = row.test_id
        test_status = row.test_status
        test_attempt_id = row.test_attempt_id
        attempt_status = row.attempt_status
        
        # Assignment has test if there's an approved test
        has_test = test_id is not None and test_status == "approved"
        
        # Test is completed if there's a submitted, evaluated, or graded attempt
        test_completed = test_attempt_id is not None and attempt_status in ["submitted", "evaluated", "graded"]
        
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
            has_test=has_test,
            test_completed=test_completed,
            test_attempt_id=str(test_attempt_id) if test_attempt_id else None
        ))
    
    # Get vocabulary assignments with completion status
    vocab_query = await db.execute(
        select(
            VocabularyList, 
            ClassroomAssignment,
            StudentAssignment.completed_at
        )
        .join(ClassroomAssignment,
              and_(
                  ClassroomAssignment.vocabulary_list_id == VocabularyList.id,
                  ClassroomAssignment.assignment_type == "vocabulary"
              ))
        .outerjoin(
            StudentAssignment,
            and_(
                StudentAssignment.student_id == current_user.id,
                StudentAssignment.assignment_id == VocabularyList.id,
                StudentAssignment.classroom_assignment_id == ClassroomAssignment.id,
                StudentAssignment.assignment_type == "vocabulary"
            )
        )
        .where(
            and_(
                ClassroomAssignment.classroom_id == classroom_id,
                VocabularyList.deleted_at.is_(None)
            )
        )
        .order_by(ClassroomAssignment.start_date, ClassroomAssignment.display_order, ClassroomAssignment.assigned_at)
    )
    
    for vocab_list, ca, completed_at in vocab_query:
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
            is_completed=completed_at is not None,  # Check actual completion from StudentAssignment
            has_test=False,  # Vocabulary assignments don't have tests
            test_completed=False,
            test_attempt_id=None
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


async def _validate_assignment_access_helper(
    assignment_type: str,
    assignment_id: UUID,
    current_user: User,
    db: AsyncSession
):
    """Helper function to validate if a student can access a specific assignment"""
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


@router.get("/assignment/{assignment_type}/{assignment_id}/validate")
async def validate_assignment_access(
    assignment_type: str,
    assignment_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Validate if a student can access a specific assignment"""
    return await _validate_assignment_access_helper(assignment_type, assignment_id, current_user, db)


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


# Vocabulary Practice Endpoints

class VocabularyPracticeStatusResponse(BaseModel):
    assignments: List[Dict[str, Any]]
    completed_count: int
    required_count: int
    test_unlocked: bool
    test_unlock_date: Optional[str] = None


class StartVocabularyChallengeResponse(BaseModel):
    game_attempt_id: str
    total_questions: int
    passing_score: int
    max_possible_score: int
    current_question: int
    question: Optional[Dict[str, Any]]


class SubmitAnswerRequest(BaseModel):
    question_id: str
    student_answer: str
    attempt_number: int = Field(..., ge=1, le=2)
    time_spent_seconds: int = Field(..., ge=0)


class SubmitAnswerResponse(BaseModel):
    correct: bool
    points_earned: int
    explanation: str
    correct_answer: Optional[str] = None
    current_score: int
    questions_remaining: int
    is_complete: bool
    passed: Optional[bool] = None
    next_question: Optional[Dict[str, Any]] = None
    can_retry: bool


@router.get("/vocabulary/{assignment_id}/practice/status", response_model=VocabularyPracticeStatusResponse)
async def get_vocabulary_practice_status(
    assignment_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get practice activity status for a vocabulary assignment"""
    # Verify student has access to this assignment
    access_check = await _validate_assignment_access_helper(
        assignment_type="vocabulary",
        assignment_id=assignment_id,
        current_user=current_user,
        db=db
    )
    
    # Get classroom assignment ID
    ca_result = await db.execute(
        select(ClassroomAssignment.id)
        .where(
            and_(
                ClassroomAssignment.vocabulary_list_id == assignment_id,
                ClassroomAssignment.classroom_id == UUID(access_check['classroom_id'])
            )
        )
    )
    classroom_assignment_id = ca_result.scalar_one()
    
    # Get practice status
    practice_service = VocabularyPracticeService(db)
    status = await practice_service.get_practice_status(
        student_id=current_user.id,
        vocabulary_list_id=assignment_id,
        classroom_assignment_id=classroom_assignment_id
    )
    
    return VocabularyPracticeStatusResponse(**status)


@router.post("/vocabulary/{assignment_id}/practice/start-challenge", response_model=StartVocabularyChallengeResponse)
async def start_vocabulary_challenge(
    assignment_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Start a new vocabulary challenge game"""
    # Verify student has access
    access_check = await _validate_assignment_access_helper(
        assignment_type="vocabulary",
        assignment_id=assignment_id,
        current_user=current_user,
        db=db
    )
    
    # Get classroom assignment ID
    ca_result = await db.execute(
        select(ClassroomAssignment.id)
        .where(
            and_(
                ClassroomAssignment.vocabulary_list_id == assignment_id,
                ClassroomAssignment.classroom_id == UUID(access_check['classroom_id'])
            )
        )
    )
    classroom_assignment_id = ca_result.scalar_one()
    
    # Start the game
    practice_service = VocabularyPracticeService(db)
    game_data = await practice_service.start_vocabulary_challenge(
        student_id=current_user.id,
        vocabulary_list_id=assignment_id,
        classroom_assignment_id=classroom_assignment_id
    )
    
    return StartVocabularyChallengeResponse(**game_data)


@router.post("/vocabulary/practice/submit-answer/{game_attempt_id}", response_model=SubmitAnswerResponse)
async def submit_vocabulary_answer(
    game_attempt_id: UUID,
    request: SubmitAnswerRequest,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Submit an answer for a vocabulary challenge question"""
    practice_service = VocabularyPracticeService(db)
    
    # Submit the answer
    result = await practice_service.submit_answer(
        game_attempt_id=game_attempt_id,
        question_id=UUID(request.question_id),
        student_answer=request.student_answer,
        attempt_number=request.attempt_number,
        time_spent_seconds=request.time_spent_seconds
    )
    
    return SubmitAnswerResponse(**result)


@router.get("/vocabulary/practice/next-question/{game_attempt_id}")
async def get_next_vocabulary_question(
    game_attempt_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get the next question in a vocabulary challenge game"""
    practice_service = VocabularyPracticeService(db)
    
    result = await practice_service.get_next_question(game_attempt_id)
    return result


# Story Builder Endpoints

class StartStoryBuilderResponse(BaseModel):
    story_attempt_id: str
    total_prompts: int
    passing_score: int
    max_possible_score: int
    current_prompt: int
    prompt: Optional[Dict[str, Any]]


class SubmitStoryRequest(BaseModel):
    prompt_id: str
    story_text: str
    attempt_number: int = Field(..., ge=1, le=2)


class SubmitStoryResponse(BaseModel):
    evaluation: Dict[str, Any]
    current_score: int
    prompts_remaining: int
    is_complete: bool
    passed: Optional[bool] = None
    percentage_score: Optional[float] = None
    needs_confirmation: bool = False
    next_prompt: Optional[Dict[str, Any]] = None
    can_revise: bool


# Concept Mapping Models

class StartConceptMappingResponse(BaseModel):
    concept_attempt_id: str
    total_words: int
    passing_score: float
    max_possible_score: float
    current_word_index: int
    word: Optional[Dict[str, Any]]
    grade_level: str


class SubmitConceptMapRequest(BaseModel):
    word_id: str
    definition: str = Field(..., min_length=10, max_length=500)
    synonyms: str = Field(..., min_length=3, max_length=200)
    antonyms: str = Field(..., min_length=3, max_length=200)
    context_theme: str = Field(..., min_length=10, max_length=300)
    connotation: str = Field(..., min_length=3, max_length=100)
    example_sentence: str = Field(..., min_length=15, max_length=300)
    time_spent_seconds: int = Field(..., ge=0)


class SubmitConceptMapResponse(BaseModel):
    valid: bool
    errors: Optional[Dict[str, str]] = None
    evaluation: Optional[Dict[str, Any]] = None
    current_score: Optional[float] = None
    average_score: Optional[float] = None
    words_remaining: Optional[int] = None
    is_complete: Optional[bool] = None
    passed: Optional[bool] = None
    next_word: Optional[Dict[str, Any]] = None
    progress_percentage: Optional[float] = None


class ConceptMapProgressResponse(BaseModel):
    concept_attempt_id: str
    status: str
    total_words: int
    words_completed: int
    current_word_index: int
    current_score: float
    average_score: float
    passing_score: float
    max_possible_score: float
    progress_percentage: float
    current_word: Optional[Dict[str, Any]]
    completed_words: List[Dict[str, Any]]


class FinishEarlyResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    status: Optional[str] = None
    final_score: Optional[float] = None
    average_score: Optional[float] = None
    words_completed: Optional[int] = None
    total_words: Optional[int] = None
    passed: Optional[bool] = None


@router.post("/vocabulary/{assignment_id}/practice/start-story-builder", response_model=StartStoryBuilderResponse)
async def start_story_builder(
    assignment_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Start a new story builder challenge"""
    # Verify student has access
    access_check = await _validate_assignment_access_helper(
        assignment_type="vocabulary",
        assignment_id=assignment_id,
        current_user=current_user,
        db=db
    )
    
    # Get classroom assignment ID
    ca_result = await db.execute(
        select(ClassroomAssignment.id)
        .where(
            and_(
                ClassroomAssignment.vocabulary_list_id == assignment_id,
                ClassroomAssignment.classroom_id == UUID(access_check['classroom_id'])
            )
        )
    )
    classroom_assignment_id = ca_result.scalar_one()
    
    # Start the challenge
    practice_service = VocabularyPracticeService(db)
    story_data = await practice_service.start_story_builder(
        student_id=current_user.id,
        vocabulary_list_id=assignment_id,
        classroom_assignment_id=classroom_assignment_id
    )
    
    return StartStoryBuilderResponse(**story_data)


@router.post("/vocabulary/practice/submit-story/{story_attempt_id}", response_model=SubmitStoryResponse)
async def submit_story(
    story_attempt_id: UUID,
    request: SubmitStoryRequest,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Submit a story for evaluation"""
    practice_service = VocabularyPracticeService(db)
    
    # Submit the story
    result = await practice_service.submit_story(
        story_attempt_id=story_attempt_id,
        prompt_id=UUID(request.prompt_id),
        story_text=request.story_text,
        attempt_number=request.attempt_number
    )
    
    return SubmitStoryResponse(**result)


@router.get("/vocabulary/practice/next-story-prompt/{story_attempt_id}")
async def get_next_story_prompt(
    story_attempt_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get the next story prompt in the challenge"""
    practice_service = VocabularyPracticeService(db)
    
    result = await practice_service.get_next_story_prompt(story_attempt_id)
    return result


class StoryCompletionResponse(BaseModel):
    success: bool
    message: str
    final_score: int
    percentage_score: float


@router.post("/vocabulary/practice/confirm-story-completion/{story_attempt_id}", response_model=StoryCompletionResponse)
async def confirm_story_completion(
    story_attempt_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Confirm story builder completion and mark assignment as complete"""
    practice_service = VocabularyPracticeService(db)
    
    result = await practice_service.confirm_story_completion(
        story_attempt_id=story_attempt_id,
        student_id=current_user.id
    )
    
    return StoryCompletionResponse(**result)


@router.post("/vocabulary/practice/decline-story-completion/{story_attempt_id}", response_model=StoryCompletionResponse)
async def decline_story_completion(
    story_attempt_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Decline story completion and prepare for retake"""
    practice_service = VocabularyPracticeService(db)
    
    result = await practice_service.decline_story_completion(
        story_attempt_id=story_attempt_id,
        student_id=current_user.id
    )
    
    return StoryCompletionResponse(**result)


# Concept Mapping Endpoints

@router.post("/vocabulary/{assignment_id}/practice/start-concept-mapping", response_model=StartConceptMappingResponse)
async def start_concept_mapping(
    assignment_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Start a new concept mapping activity"""
    # Verify student has access
    access_check = await _validate_assignment_access_helper(
        assignment_type="vocabulary",
        assignment_id=assignment_id,
        current_user=current_user,
        db=db
    )
    
    # Get classroom assignment ID
    ca_result = await db.execute(
        select(ClassroomAssignment.id)
        .where(
            and_(
                ClassroomAssignment.classroom_id == access_check['classroom_id'],
                ClassroomAssignment.vocabulary_list_id == assignment_id,
                ClassroomAssignment.assignment_type == "vocabulary"
            )
        )
    )
    classroom_assignment_id = ca_result.scalar()
    
    practice_service = VocabularyPracticeService(db)
    concept_data = await practice_service.start_concept_mapping(
        student_id=current_user.id,
        vocabulary_list_id=assignment_id,
        classroom_assignment_id=classroom_assignment_id
    )
    
    return StartConceptMappingResponse(**concept_data)


@router.post("/vocabulary/practice/submit-concept-map/{concept_attempt_id}", response_model=SubmitConceptMapResponse)
async def submit_concept_map(
    concept_attempt_id: UUID,
    request: SubmitConceptMapRequest,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Submit a concept map for evaluation"""
    practice_service = VocabularyPracticeService(db)
    
    result = await practice_service.submit_concept_map(
        concept_attempt_id=concept_attempt_id,
        word_id=UUID(request.word_id),
        definition=request.definition,
        synonyms=request.synonyms,
        antonyms=request.antonyms,
        context_theme=request.context_theme,
        connotation=request.connotation,
        example_sentence=request.example_sentence,
        time_spent_seconds=request.time_spent_seconds
    )
    
    return SubmitConceptMapResponse(**result)


@router.get("/vocabulary/practice/concept-map-progress/{concept_attempt_id}", response_model=ConceptMapProgressResponse)
async def get_concept_map_progress(
    concept_attempt_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get current progress in concept mapping"""
    practice_service = VocabularyPracticeService(db)
    
    result = await practice_service.get_concept_map_progress(concept_attempt_id)
    return ConceptMapProgressResponse(**result)


@router.post("/vocabulary/practice/finish-concept-mapping-early/{concept_attempt_id}", response_model=FinishEarlyResponse)
async def finish_concept_mapping_early(
    concept_attempt_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Finish concept mapping early with partial completion"""
    practice_service = VocabularyPracticeService(db)
    
    result = await practice_service.finish_concept_mapping_early(concept_attempt_id)
    return FinishEarlyResponse(**result)


# Puzzle Path Models

class StartPuzzlePathResponse(BaseModel):
    puzzle_attempt_id: str
    total_puzzles: int
    passing_score: int
    max_possible_score: int
    current_puzzle_index: int
    puzzle: Optional[Dict[str, Any]]


class SubmitPuzzleAnswerRequest(BaseModel):
    puzzle_id: str
    student_answer: str = Field(..., min_length=1, max_length=200)
    time_spent_seconds: int = Field(..., ge=0)


class SubmitPuzzleAnswerResponse(BaseModel):
    valid: bool
    errors: Optional[Dict[str, str]] = None
    evaluation: Optional[Dict[str, Any]] = None
    current_score: Optional[int] = None
    puzzles_remaining: Optional[int] = None
    is_complete: Optional[bool] = None
    passed: Optional[bool] = None
    next_puzzle: Optional[Dict[str, Any]] = None
    progress_percentage: Optional[float] = None


class PuzzlePathProgressResponse(BaseModel):
    puzzle_attempt_id: str
    status: str
    total_puzzles: int
    puzzles_completed: int
    current_puzzle_index: int
    current_score: int
    passing_score: int
    max_possible_score: int
    progress_percentage: float
    current_puzzle: Optional[Dict[str, Any]]
    completed_puzzles: List[Dict[str, Any]]


# Puzzle Path Endpoints

@router.post("/vocabulary/{assignment_id}/practice/start-puzzle-path", response_model=StartPuzzlePathResponse)
async def start_puzzle_path(
    assignment_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Start a new puzzle path activity"""
    # Verify student has access
    access_check = await _validate_assignment_access_helper(
        assignment_type="vocabulary",
        assignment_id=assignment_id,
        current_user=current_user,
        db=db
    )
    
    # Get classroom assignment ID
    ca_result = await db.execute(
        select(ClassroomAssignment.id)
        .where(
            and_(
                ClassroomAssignment.classroom_id == access_check['classroom_id'],
                ClassroomAssignment.vocabulary_list_id == assignment_id,
                ClassroomAssignment.assignment_type == "vocabulary"
            )
        )
    )
    classroom_assignment_id = ca_result.scalar()
    
    practice_service = VocabularyPracticeService(db)
    puzzle_data = await practice_service.start_puzzle_path(
        student_id=current_user.id,
        vocabulary_list_id=assignment_id,
        classroom_assignment_id=classroom_assignment_id
    )
    
    return StartPuzzlePathResponse(**puzzle_data)


@router.post("/vocabulary/practice/submit-puzzle-answer/{puzzle_attempt_id}", response_model=SubmitPuzzleAnswerResponse)
async def submit_puzzle_answer(
    puzzle_attempt_id: UUID,
    request: SubmitPuzzleAnswerRequest,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Submit a puzzle answer for evaluation"""
    practice_service = VocabularyPracticeService(db)
    
    result = await practice_service.submit_puzzle_answer(
        puzzle_attempt_id=puzzle_attempt_id,
        puzzle_id=UUID(request.puzzle_id),
        student_answer=request.student_answer,
        time_spent_seconds=request.time_spent_seconds
    )
    
    return SubmitPuzzleAnswerResponse(**result)


@router.get("/vocabulary/practice/puzzle-path-progress/{puzzle_attempt_id}", response_model=PuzzlePathProgressResponse)
async def get_puzzle_path_progress(
    puzzle_attempt_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get current progress in puzzle path"""
    practice_service = VocabularyPracticeService(db)
    
    result = await practice_service.get_puzzle_path_progress(puzzle_attempt_id)
    return PuzzlePathProgressResponse(**result)
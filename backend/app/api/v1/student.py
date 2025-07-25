from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
import logging
from sqlalchemy import select, and_, or_, func, exists, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.classroom import Classroom, ClassroomStudent, ClassroomAssignment, StudentAssignment
from app.models.reading import ReadingAssignment
from app.models.vocabulary import VocabularyList
from app.models.debate import DebateAssignment
from app.models.writing import WritingAssignment
from app.models.vocabulary_practice import VocabularyPuzzleAttempt, VocabularyFillInBlankAttempt, VocabularyPracticeProgress
from app.models.umaread import UmareadAssignmentProgress
from app.models.tests import AssignmentTest, StudentTestAttempt
from app.models.umatest import TestAssignment
from app.utils.deps import get_current_user
from app.schemas.classroom import ClassroomResponse
from app.services.vocabulary_practice import VocabularyPracticeService
from app.services.vocabulary_test import VocabularyTestService
from app.services.test_schedule import TestScheduleService
from app.schemas.vocabulary import (
    VocabularyTestEligibilityResponse, VocabularyTestAttemptRequest,
    VocabularyTestAttemptResponse, VocabularyProgressUpdate
)
from app.schemas.test_schedule import ValidateOverrideRequest

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
    classroom_assignment_id: Optional[str] = None  # Added for UMATest navigation
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
    has_started: bool = False  # New field to track if assignment has been started
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
            status_code=http_status.HTTP_403_FORBIDDEN,
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
            status_code=http_status.HTTP_404_NOT_FOUND,
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
                ClassroomAssignment.removed_from_classroom_at.is_(None),  # Filter out soft-deleted assignments
                VocabularyList.deleted_at.is_(None),
                VocabularyList.status == "published"
            )
        )
    )
    
    results = vocab_result.all()
    
    if not results:
        raise HTTPException(
            status_code=http_http_status.HTTP_404_NOT_FOUND,
            detail="Vocabulary assignment not found or you don't have access"
        )
    
    if len(results) > 1:
        # Student is enrolled in multiple classes with this assignment
        classrooms = [r[2].name for r in results]  # Get classroom names
        raise HTTPException(
            status_code=http_http_status.HTTP_403_FORBIDDEN,
            detail=f"Access denied: You are enrolled in multiple classes with this assignment ({', '.join(classrooms)}). Please access the assignment through your specific classroom."
        )
    
    result = results[0]
    
    vocab_list, classroom_assignment, classroom, teacher = result
    
    # Check if assignment is active
    status = calculate_assignment_status(classroom_assignment.start_date, classroom_assignment.end_date)
    if status != "active":
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
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
            status_code=http_status.HTTP_403_FORBIDDEN,
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
            status_code=http_status.HTTP_404_NOT_FOUND,
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
            UmareadAssignmentProgress.started_at,  # Add started_at field
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
                ClassroomAssignment.removed_from_classroom_at.is_(None),  # Filter out soft-deleted assignments
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
        started_at = row.started_at  # Get started_at
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
            has_started=started_at is not None,  # Add has_started
            has_test=has_test,
            test_completed=test_completed,
            test_attempt_id=str(test_attempt_id) if test_attempt_id else None
        ))
    
    # Get vocabulary assignments and check completion by counting subtypes
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
                ClassroomAssignment.removed_from_classroom_at.is_(None),  # Filter out soft-deleted assignments
                VocabularyList.deleted_at.is_(None)
            )
        )
        .order_by(ClassroomAssignment.start_date, ClassroomAssignment.display_order, ClassroomAssignment.assigned_at)
    )
    
    for vocab_list, ca in vocab_query:
        # Count completed vocabulary practice activities (need 3 out of 4)
        completed_subtypes_query = await db.execute(
            select(func.count(StudentAssignment.id))
            .where(
                and_(
                    StudentAssignment.student_id == current_user.id,
                    StudentAssignment.assignment_id == vocab_list.id,
                    StudentAssignment.classroom_assignment_id == ca.id,
                    StudentAssignment.assignment_type == "vocabulary",
                    StudentAssignment.completed_at.is_not(None)
                )
            )
        )
        completed_count = completed_subtypes_query.scalar() or 0
        
        # Check if vocabulary practice has started
        practice_progress_query = await db.execute(
            select(VocabularyPracticeProgress)
            .where(
                and_(
                    VocabularyPracticeProgress.student_id == current_user.id,
                    VocabularyPracticeProgress.vocabulary_list_id == vocab_list.id,
                    VocabularyPracticeProgress.classroom_assignment_id == ca.id
                )
            )
        )
        practice_progress = practice_progress_query.scalar_one_or_none()
        has_started_vocab = practice_progress is not None
        
        # Vocabulary assignment is complete when 3+ practice activities are done
        is_vocabulary_complete = completed_count >= 3
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
            is_completed=is_vocabulary_complete,  # Complete when 3+ practice activities done
            has_started=has_started_vocab,  # Add has_started
            has_test=False,  # Vocabulary assignments don't have tests
            test_completed=False,
            test_attempt_id=None
        ))
    
    # Get debate assignments
    debate_query = await db.execute(
        select(DebateAssignment, ClassroomAssignment)
        .join(ClassroomAssignment,
              and_(
                  ClassroomAssignment.assignment_id == DebateAssignment.id,
                  ClassroomAssignment.assignment_type == "debate"
              ))
        .where(
            and_(
                ClassroomAssignment.classroom_id == classroom_id,
                ClassroomAssignment.removed_from_classroom_at.is_(None),  # Filter out soft-deleted assignments
                DebateAssignment.deleted_at.is_(None)
            )
        )
        .order_by(ClassroomAssignment.start_date, ClassroomAssignment.display_order, ClassroomAssignment.assigned_at)
    )
    
    for debate, ca in debate_query:
        status = calculate_assignment_status(ca.start_date, ca.end_date)
        assignments.append(StudentAssignmentResponse(
            id=str(debate.id),
            title=debate.title,
            work_title=debate.topic,
            author=None,
            grade_level=debate.grade_level,
            type="UMADebate",
            item_type="debate",
            assigned_at=ca.assigned_at,
            start_date=ca.start_date,
            end_date=ca.end_date,
            display_order=ca.display_order,
            status=status,
            is_completed=False,  # Will be updated when student debate tracking is implemented
            has_started=False,  # Will be updated when debate tracking is implemented
            has_test=False,  # Debates don't have tests
            test_completed=False,
            test_attempt_id=None
        ))
    
    # Get writing assignments with student progress
    writing_query = await db.execute(
        select(WritingAssignment, ClassroomAssignment, StudentAssignment)
        .join(ClassroomAssignment,
              and_(
                  ClassroomAssignment.assignment_id == WritingAssignment.id,
                  ClassroomAssignment.assignment_type == "writing"
              ))
        .outerjoin(StudentAssignment,
                   and_(
                       StudentAssignment.classroom_assignment_id == ClassroomAssignment.id,
                       StudentAssignment.student_id == current_user.id
                   ))
        .where(
            and_(
                ClassroomAssignment.classroom_id == classroom_id,
                ClassroomAssignment.removed_from_classroom_at.is_(None),  # Filter out soft-deleted assignments
                WritingAssignment.deleted_at.is_(None)
            )
        )
        .order_by(ClassroomAssignment.start_date, ClassroomAssignment.display_order, ClassroomAssignment.assigned_at)
    )
    
    for writing, ca, student_assignment in writing_query:
        status = calculate_assignment_status(ca.start_date, ca.end_date)
        is_completed = student_assignment.status == "completed" if student_assignment else False
        
        assignments.append(StudentAssignmentResponse(
            id=str(writing.id),
            title=writing.title,
            work_title=writing.prompt_text[:100] + "..." if len(writing.prompt_text) > 100 else writing.prompt_text,
            author=None,
            grade_level=writing.grade_level,
            type="UMAWrite",
            item_type="writing",
            assigned_at=ca.assigned_at,
            start_date=ca.start_date,
            end_date=ca.end_date,
            display_order=ca.display_order,
            status=status,
            is_completed=is_completed,
            has_started=student_assignment is not None,  # Has started if StudentAssignment exists
            has_test=False,  # Writing assignments don't have tests
            test_completed=False,
            test_attempt_id=None
        ))
    
    # Get UMALecture assignments
    lecture_query = await db.execute(
        select(
            ReadingAssignment,
            ClassroomAssignment,
            StudentAssignment.id.label("student_assignment_id"),
            StudentAssignment.started_at,
            StudentAssignment.completed_at,
            StudentAssignment.progress_metadata
        )
        .join(ClassroomAssignment,
              and_(
                  ClassroomAssignment.assignment_id == ReadingAssignment.id,
                  ClassroomAssignment.assignment_type.in_(["UMALecture", "lecture"])
              ))
        .outerjoin(StudentAssignment,
              and_(
                  StudentAssignment.classroom_assignment_id == ClassroomAssignment.id,
                  StudentAssignment.student_id == current_user.id
              ))
        .where(
            and_(
                ClassroomAssignment.classroom_id == classroom_id,
                ClassroomAssignment.assignment_type.in_(["UMALecture", "lecture"]),
                ClassroomAssignment.removed_from_classroom_at.is_(None),
                ReadingAssignment.deleted_at.is_(None),
                ReadingAssignment.assignment_type == "UMALecture"
            )
        )
        .order_by(ClassroomAssignment.start_date, ClassroomAssignment.display_order, ClassroomAssignment.assigned_at)
    )
    
    for reading, ca, student_assignment_id, started_at, completed_at, progress_metadata in lecture_query:
        status = calculate_assignment_status(ca.start_date, ca.end_date)
        
        # For UMALecture, we use the classroom_assignment id as the ID
        # since student_assignment records may not exist yet
        assignment_id = str(ca.id)
        
        assignments.append(StudentAssignmentResponse(
            id=assignment_id,
            title=reading.assignment_title,  # Use the actual lecture title
            work_title=None,
            author=None,
            grade_level=reading.grade_level,
            type="UMALecture",
            item_type="lecture",
            assigned_at=ca.assigned_at,
            start_date=ca.start_date,
            end_date=ca.end_date,
            display_order=ca.display_order,
            status=status,
            is_completed=completed_at is not None,
            has_started=started_at is not None,
            has_test=False,
            test_completed=False,
            test_attempt_id=None
        ))
    
    # Get UMATest assignments with test attempt status
    test_query = await db.execute(
        select(
            TestAssignment,
            ClassroomAssignment,
            StudentTestAttempt.id.label("test_attempt_id"),
            StudentTestAttempt.status.label("attempt_status"),
            StudentTestAttempt.score
        )
        .join(ClassroomAssignment,
              and_(
                  ClassroomAssignment.assignment_id == TestAssignment.id,
                  ClassroomAssignment.assignment_type == "test"
              ))
        .outerjoin(StudentTestAttempt,
                   and_(
                       StudentTestAttempt.classroom_assignment_id == ClassroomAssignment.id,
                       StudentTestAttempt.student_id == current_user.id,
                       StudentTestAttempt.status.in_(["submitted", "graded"])
                   ))
        .where(
            and_(
                ClassroomAssignment.classroom_id == classroom_id,
                ClassroomAssignment.removed_from_classroom_at.is_(None),
                TestAssignment.deleted_at.is_(None),
                TestAssignment.status == "published"
            )
        )
        .order_by(ClassroomAssignment.start_date, ClassroomAssignment.display_order, ClassroomAssignment.assigned_at)
    )
    
    for test_assignment, ca, test_attempt_id, attempt_status, score in test_query:
        status = calculate_assignment_status(ca.start_date, ca.end_date)
        
        # Test is completed if there's a submitted or graded attempt
        test_completed = test_attempt_id is not None and attempt_status in ["submitted", "graded"]
        
        assignments.append(StudentAssignmentResponse(
            id=str(ca.id),
            title=test_assignment.test_title,
            work_title=test_assignment.test_description,
            author=None,
            grade_level=None,
            type="UMATest",
            item_type="test",
            assigned_at=ca.assigned_at,
            start_date=ca.start_date,
            end_date=ca.end_date,
            display_order=ca.display_order,
            status=status,
            is_completed=test_completed,
            has_started=test_attempt_id is not None,
            has_test=True,  # UMATest is a test itself
            test_completed=test_completed,
            test_attempt_id=str(test_attempt_id) if test_attempt_id else None
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
    if assignment_type not in ["reading", "vocabulary", "debate"]:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
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
    elif assignment_type == "vocabulary":
        ca_query = ca_query.where(
            and_(
                ClassroomAssignment.vocabulary_list_id == assignment_id,
                ClassroomAssignment.assignment_type == "vocabulary"
            )
        )
    else:  # debate
        ca_query = ca_query.where(
            and_(
                ClassroomAssignment.assignment_id == assignment_id,
                ClassroomAssignment.assignment_type == "debate"
            )
        )
    
    result = await db.execute(ca_query)
    ca_result = result.first()
    
    if not ca_result:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
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
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail="You are not enrolled in this classroom"
        )
    
    # Check assignment status
    status = calculate_assignment_status(classroom_assignment.start_date, classroom_assignment.end_date)
    
    if status == "not_started":
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=f"Assignment not available yet. Starts on {classroom_assignment.start_date.strftime('%B %d, %Y')}"
        )
    elif status == "expired":
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
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
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Assignment is not available"
            )
    elif assignment_type == "vocabulary":
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
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Assignment is not available"
            )
    else:  # debate
        debate_check = await db.execute(
            select(DebateAssignment)
            .where(
                and_(
                    DebateAssignment.id == assignment_id,
                    DebateAssignment.deleted_at.is_(None)
                )
            )
        )
        if not debate_check.scalar_one_or_none():
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
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
            ClassroomAssignment.assignment_type == "reading",
            ClassroomAssignment.removed_from_classroom_at.is_(None)
        )
    )
    
    result = await db.execute(ca_query)
    ca_result = result.first()
    
    if not ca_result:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
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
            status_code=http_status.HTTP_403_FORBIDDEN,
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
    test_completed: bool = False
    test_attempts_count: int = 0
    max_test_attempts: int
    best_test_score: Optional[float] = None
    last_test_completed_at: Optional[datetime] = None




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




# Story Builder Endpoints

class StartStoryBuilderResponse(BaseModel):
    story_attempt_id: str
    total_prompts: int
    passing_score: int
    max_possible_score: int
    current_prompt: int
    prompt: Optional[Dict[str, Any]]
    current_score: int = 0


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
    percentage_score: Optional[float] = None
    needs_confirmation: bool = False
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


class ConceptMappingCompletionResponse(BaseModel):
    success: bool
    message: str
    final_score: float
    percentage_score: float


@router.post("/vocabulary/practice/confirm-concept-completion/{concept_attempt_id}", response_model=ConceptMappingCompletionResponse)
async def confirm_concept_completion(
    concept_attempt_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Confirm concept mapping completion and mark assignment as complete"""
    practice_service = VocabularyPracticeService(db)
    
    result = await practice_service.confirm_concept_completion(
        concept_attempt_id=concept_attempt_id,
        student_id=current_user.id
    )
    
    return ConceptMappingCompletionResponse(**result)


@router.post("/vocabulary/practice/decline-concept-completion/{concept_attempt_id}", response_model=ConceptMappingCompletionResponse)
async def decline_concept_completion(
    concept_attempt_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Decline concept mapping completion and prepare for retake"""
    practice_service = VocabularyPracticeService(db)
    
    result = await practice_service.decline_concept_completion(
        concept_attempt_id=concept_attempt_id,
        student_id=current_user.id
    )
    
    return ConceptMappingCompletionResponse(**result)


# Puzzle Path Models

class StartPuzzlePathResponse(BaseModel):
    puzzle_attempt_id: str
    total_puzzles: int
    passing_score: int
    max_possible_score: int
    current_puzzle_index: int
    puzzle: Optional[Dict[str, Any]]
    is_complete: Optional[bool] = False
    needs_confirmation: Optional[bool] = False
    current_score: Optional[int] = None
    percentage_score: Optional[float] = None


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
    percentage_score: Optional[float] = None
    needs_confirmation: bool = False
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
    logger = logging.getLogger(__name__)
    
    try:
        # Validate puzzle_id
        try:
            puzzle_id = UUID(request.puzzle_id)
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid puzzle_id format: {request.puzzle_id}"
            )
        
        # Get puzzle attempt with basic validation
        result = await db.execute(
            select(VocabularyPuzzleAttempt)
            .where(VocabularyPuzzleAttempt.id == puzzle_attempt_id)
        )
        puzzle_attempt = result.scalar_one_or_none()
        
        if not puzzle_attempt:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Puzzle attempt not found"
            )
        
        if puzzle_attempt.status != 'in_progress':
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail="Puzzle attempt is not in progress"
            )
        
        # Use the proper vocabulary practice service for evaluation
        practice_service = VocabularyPracticeService(db)
        
        try:
            # Submit answer to the practice service which handles evaluation
            result = await practice_service.submit_puzzle_answer(
                puzzle_attempt_id=puzzle_attempt_id,
                puzzle_id=puzzle_id,
                student_answer=request.student_answer,
                time_spent_seconds=request.time_spent_seconds
            )
            
            # If the result doesn't have 'valid' key or it's False, return error
            if not result.get('valid', True):
                raise HTTPException(
                    status_code=http_status.HTTP_400_BAD_REQUEST,
                    detail=result.get('errors', {'answer': 'Invalid answer'})
                )
            
            # Get the evaluation from the result
            evaluation = result.get('evaluation', {
                'score': 1,
                'accuracy': 'incorrect',
                'feedback': 'Unable to evaluate answer',
                'areas_checked': []
            })
            
            # Refresh puzzle attempt to get updated values
            await db.refresh(puzzle_attempt)
            
            # Return the result from the service
            return SubmitPuzzleAnswerResponse(
                valid=True,
                evaluation=evaluation,
                current_score=result.get('current_score', puzzle_attempt.total_score),
                puzzles_remaining=result.get('puzzles_remaining', puzzle_attempt.total_puzzles - puzzle_attempt.puzzles_completed),
                is_complete=result.get('is_complete', False),
                passed=result.get('passed'),
                percentage_score=result.get('percentage_score'),
                needs_confirmation=result.get('needs_confirmation', False),
                next_puzzle=result.get('next_puzzle'),
                progress_percentage=result.get('progress_percentage', 0)
            )
            
        except ValueError as e:
            # Handle specific ValueError from service
            logger.error(f"ValueError in puzzle answer submission: {e}")
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error submitting puzzle answer: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            
            # If service call fails, handle it gracefully
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to evaluate answer: {str(e)}"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in submit_puzzle_answer: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit answer: {str(e)}"
        )


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


class PuzzleCompletionResponse(BaseModel):
    success: bool
    message: str
    final_score: int
    percentage_score: float


@router.post("/vocabulary/practice/confirm-puzzle-completion/{puzzle_attempt_id}", response_model=PuzzleCompletionResponse)
async def confirm_puzzle_completion(
    puzzle_attempt_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Confirm puzzle path completion and mark assignment as complete"""
    practice_service = VocabularyPracticeService(db)
    
    result = await practice_service.confirm_puzzle_completion(
        puzzle_attempt_id=puzzle_attempt_id,
        student_id=current_user.id
    )
    
    return PuzzleCompletionResponse(**result)


@router.post("/vocabulary/practice/decline-puzzle-completion/{puzzle_attempt_id}", response_model=PuzzleCompletionResponse)
async def decline_puzzle_completion(
    puzzle_attempt_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Decline puzzle completion and prepare for retake"""
    logger = logging.getLogger(__name__)
    
    try:
        # Get puzzle attempt 
        result = await db.execute(
            select(VocabularyPuzzleAttempt)
            .where(VocabularyPuzzleAttempt.id == puzzle_attempt_id)
        )
        puzzle_attempt = result.scalar_one_or_none()
        
        if puzzle_attempt and puzzle_attempt.student_id == current_user.id:
            # Mark as declined and reset for retake
            puzzle_attempt.status = 'declined'
            await db.commit()
            
            # Clear Redis session data to ensure clean slate for retake
            from app.services.vocabulary_session import VocabularySessionManager
            session_manager = VocabularySessionManager()
            await session_manager.clear_all_session_data(current_user.id, puzzle_attempt.vocabulary_list_id)
        
        return PuzzleCompletionResponse(
            success=True,
            message="Puzzle path completion declined. You can retake when ready.",
            final_score=puzzle_attempt.total_score if puzzle_attempt else 0,
            percentage_score=0.0
        )
        
    except Exception as e:
        logger.error(f"Error declining puzzle completion: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return PuzzleCompletionResponse(
            success=True,
            message="Declined successfully.",
            final_score=0,
            percentage_score=0.0
        )


@router.post("/vocabulary/{assignment_id}/practice/reset-puzzle-path")
async def reset_puzzle_path(
    assignment_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Reset puzzle path progress and clear Redis sessions"""
    logger = logging.getLogger(__name__)
    
    try:
        # Clear Redis sessions first
        from app.services.vocabulary_session import VocabularySessionManager
        session_manager = VocabularySessionManager()
        await session_manager.clear_all_session_data(current_user.id, assignment_id)
        
        # Delete any existing puzzle attempts for this user and assignment
        from sqlalchemy import delete
        await db.execute(
            delete(VocabularyPuzzleAttempt)
            .where(
                and_(
                    VocabularyPuzzleAttempt.student_id == current_user.id,
                    VocabularyPuzzleAttempt.vocabulary_list_id == assignment_id
                )
            )
        )
        
        # Also clear any StudentAssignment records for puzzle_path subtype
        await db.execute(
            delete(StudentAssignment)
            .where(
                and_(
                    StudentAssignment.student_id == current_user.id,
                    StudentAssignment.assignment_id == assignment_id,
                    StudentAssignment.assignment_type == "vocabulary",
                    StudentAssignment.progress_metadata.contains({"subtype": "puzzle_path"})
                )
            )
        )
        
        await db.commit()
        
        return {"success": True, "message": "Puzzle path progress and sessions reset successfully"}
        
    except Exception as e:
        logger.error(f"Error resetting puzzle path: {e}")
        return {"success": False, "message": f"Failed to reset: {str(e)}"}


@router.post("/vocabulary/clear-all-sessions")
async def clear_all_vocabulary_sessions(
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Clear all vocabulary practice sessions for the current user"""
    logger = logging.getLogger(__name__)
    
    try:
        from app.core.redis import get_redis_client
        
        redis = get_redis_client()
        
        # Pattern to match all vocabulary sessions for this user
        pattern = f"vocab:*:{current_user.id}:*"
        
        # Get all matching keys
        cursor = 0
        keys_to_delete = []
        while True:
            cursor, keys = await redis.scan(cursor, match=pattern, count=1000)
            keys_to_delete.extend(keys)
            if cursor == 0:
                break
        
        # Delete all found keys
        if keys_to_delete:
            await redis.delete(*keys_to_delete)
        
        return {
            "success": True,
            "message": f"Cleared {len(keys_to_delete)} vocabulary session keys",
            "keys_cleared": len(keys_to_delete)
        }
        
    except Exception as e:
        logger.error(f"Error clearing vocabulary sessions: {e}")
        return {"success": False, "message": f"Failed to clear sessions: {str(e)}"}


# Fill-in-the-Blank Models

class StartFillInBlankResponse(BaseModel):
    fill_in_blank_attempt_id: str
    total_sentences: int
    passing_score: int
    current_sentence_index: int
    sentence: Optional[Dict[str, Any]]
    is_complete: Optional[bool] = False
    needs_confirmation: Optional[bool] = False
    correct_answers: Optional[int] = None
    score_percentage: Optional[float] = None


class SubmitFillInBlankAnswerRequest(BaseModel):
    sentence_id: str
    student_answer: str = Field(..., min_length=1, max_length=100)
    time_spent_seconds: int = Field(..., ge=0)


class SubmitFillInBlankAnswerResponse(BaseModel):
    valid: bool
    errors: Optional[Dict[str, str]] = None
    is_correct: bool
    correct_answer: str
    correct_answers: int
    sentences_remaining: int
    is_complete: bool
    passed: Optional[bool] = None
    score_percentage: Optional[float] = None
    needs_confirmation: bool = False
    next_sentence: Optional[Dict[str, Any]] = None
    progress_percentage: float


class FillInBlankProgressResponse(BaseModel):
    fill_in_blank_attempt_id: str
    status: str
    total_sentences: int
    sentences_completed: int
    current_sentence_index: int
    correct_answers: int
    incorrect_answers: int
    passing_score: int
    progress_percentage: float
    current_sentence: Optional[Dict[str, Any]]
    vocabulary_words: List[str]


class FillInBlankCompletionResponse(BaseModel):
    success: bool
    message: str
    final_score: int
    score_percentage: float


# Fill-in-the-Blank Endpoints

@router.post("/vocabulary/{assignment_id}/practice/start-fill-in-blank", response_model=StartFillInBlankResponse)
async def start_fill_in_blank(
    assignment_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Start a new fill-in-the-blank activity"""
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
    fill_in_blank_data = await practice_service.start_fill_in_blank(
        student_id=current_user.id,
        vocabulary_list_id=assignment_id,
        classroom_assignment_id=classroom_assignment_id
    )
    
    return StartFillInBlankResponse(**fill_in_blank_data)


@router.post("/vocabulary/practice/submit-fill-in-blank-answer/{fill_in_blank_attempt_id}", response_model=SubmitFillInBlankAnswerResponse)
async def submit_fill_in_blank_answer(
    fill_in_blank_attempt_id: UUID,
    request: SubmitFillInBlankAnswerRequest,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Submit a fill-in-the-blank answer for evaluation"""
    logger = logging.getLogger(__name__)
    
    try:
        # Validate sentence_id
        try:
            sentence_id = UUID(request.sentence_id)
        except ValueError:
            raise HTTPException(
                status_code=http_status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid sentence_id format: {request.sentence_id}"
            )
        
        # Get fill-in-blank attempt with basic validation
        result = await db.execute(
            select(VocabularyFillInBlankAttempt)
            .where(VocabularyFillInBlankAttempt.id == fill_in_blank_attempt_id)
        )
        fill_in_blank_attempt = result.scalar_one_or_none()
        
        if not fill_in_blank_attempt:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Fill-in-blank attempt not found"
            )
        
        if fill_in_blank_attempt.student_id != current_user.id:
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail="Not authorized to submit answer for this attempt"
            )
        
        # Submit answer
        practice_service = VocabularyPracticeService(db)
        result = await practice_service.submit_fill_in_blank_answer(
            fill_in_blank_attempt_id=fill_in_blank_attempt_id,
            sentence_id=sentence_id,
            student_answer=request.student_answer,
            time_spent_seconds=request.time_spent_seconds
        )
        
        return SubmitFillInBlankAnswerResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in submit_fill_in_blank_answer: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit answer: {str(e)}"
        )


@router.get("/vocabulary/practice/fill-in-blank-progress/{fill_in_blank_attempt_id}", response_model=FillInBlankProgressResponse)
async def get_fill_in_blank_progress(
    fill_in_blank_attempt_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get current progress in fill-in-the-blank"""
    practice_service = VocabularyPracticeService(db)
    
    result = await practice_service.get_fill_in_blank_progress(fill_in_blank_attempt_id)
    return FillInBlankProgressResponse(**result)


@router.post("/vocabulary/practice/confirm-fill-in-blank-completion/{fill_in_blank_attempt_id}", response_model=FillInBlankCompletionResponse)
async def confirm_fill_in_blank_completion(
    fill_in_blank_attempt_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Confirm completion of fill-in-the-blank assignment"""
    practice_service = VocabularyPracticeService(db)
    
    result = await practice_service.confirm_fill_in_blank_completion(
        fill_in_blank_attempt_id=fill_in_blank_attempt_id,
        student_id=current_user.id
    )
    
    return FillInBlankCompletionResponse(**result)


@router.post("/vocabulary/practice/decline-fill-in-blank-completion/{fill_in_blank_attempt_id}", response_model=FillInBlankCompletionResponse)
async def decline_fill_in_blank_completion(
    fill_in_blank_attempt_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Decline fill-in-the-blank completion and prepare for retake"""
    practice_service = VocabularyPracticeService(db)
    
    result = await practice_service.decline_fill_in_blank_completion(
        fill_in_blank_attempt_id=fill_in_blank_attempt_id,
        student_id=current_user.id
    )
    
    return FillInBlankCompletionResponse(**result)


# ============================================================================
# VOCABULARY TEST ENDPOINTS
# ============================================================================

class StartVocabularyTestResponse(BaseModel):
    test_id: UUID
    test_attempt_id: UUID
    total_questions: int
    time_limit_minutes: int
    max_attempts: int
    attempt_number: int
    expires_at: datetime


class VocabularyTestQuestion(BaseModel):
    id: str
    word: str
    example_sentence: str
    question_type: str


class VocabularyTestStartResponse(BaseModel):
    test_attempt_id: UUID
    questions: List[VocabularyTestQuestion]
    total_questions: int
    time_limit_minutes: int
    started_at: datetime


@router.get("/vocabulary/{assignment_id}/test/eligibility", response_model=VocabularyTestEligibilityResponse)
async def check_vocabulary_test_eligibility(
    assignment_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Check if student is eligible to take vocabulary test"""
    
    # Validate assignment access using the correct helper function signature
    await _validate_assignment_access_helper(
        assignment_type="vocabulary",
        assignment_id=assignment_id,
        current_user=current_user,
        db=db
    )
    
    # Get classroom assignment details
    ca_result = await db.execute(
        select(ClassroomAssignment)
        .where(
            and_(
                ClassroomAssignment.vocabulary_list_id == assignment_id,
                ClassroomAssignment.assignment_type == "vocabulary"
            )
        )
    )
    classroom_assignment = ca_result.scalar_one_or_none()
    
    if not classroom_assignment:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Vocabulary assignment not found"
        )
    
    # Check test eligibility
    eligibility = await VocabularyTestService.check_test_eligibility(
        db, current_user.id, assignment_id, classroom_assignment.id
    )
    
    return VocabularyTestEligibilityResponse(**eligibility)


@router.post("/vocabulary/{assignment_id}/test/progress")
async def update_vocabulary_assignment_progress(
    assignment_id: UUID,
    progress_data: VocabularyProgressUpdate,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Update progress for vocabulary assignment completion"""
    
    # Validate assignment access
    await _validate_assignment_access_helper(
        assignment_type="vocabulary",
        assignment_id=assignment_id,
        current_user=current_user,
        db=db
    )
    
    # Get classroom assignment details
    ca_result = await db.execute(
        select(ClassroomAssignment)
        .where(
            and_(
                ClassroomAssignment.vocabulary_list_id == assignment_id,
                ClassroomAssignment.assignment_type == "vocabulary"
            )
        )
    )
    classroom_assignment = ca_result.scalar_one_or_none()
    
    if not classroom_assignment:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Vocabulary assignment not found"
        )
    
    # Update assignment progress
    result = await VocabularyTestService.update_assignment_progress(
        db, current_user.id, assignment_id, classroom_assignment.id,
        progress_data.assignment_type, progress_data.completed
    )
    
    return result


@router.post("/vocabulary/{assignment_id}/test/start", response_model=VocabularyTestStartResponse)
async def start_vocabulary_test(
    assignment_id: UUID,
    override_code: Optional[str] = None,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Start a new vocabulary test"""
    
    # Validate assignment access
    await _validate_assignment_access_helper(
        assignment_type="vocabulary",
        assignment_id=assignment_id,
        current_user=current_user,
        db=db
    )
    
    # Get classroom assignment details
    ca_result = await db.execute(
        select(ClassroomAssignment)
        .where(
            and_(
                ClassroomAssignment.vocabulary_list_id == assignment_id,
                ClassroomAssignment.assignment_type == "vocabulary"
            )
        )
    )
    classroom_assignment = ca_result.scalar_one_or_none()
    
    if not classroom_assignment:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Vocabulary assignment not found"
        )
    
    # Check classroom test schedule using TestScheduleService
    classroom_id = classroom_assignment.classroom_id
    
    # Use async TestScheduleService methods with error handling
    try:
        availability = await TestScheduleService.check_test_availability(db, classroom_id)
    except Exception as e:
        print(f"Error checking test availability: {e}")
        # If schedule check fails, allow testing (fallback)
        availability = type('obj', (object,), {
            'allowed': True,
            'schedule_active': False,
            'message': 'Testing is available (schedule check bypassed due to error)',
            'next_window': None,
            'current_window_end': None
        })()
    
    # Initialize variables for tracking
    override_id = None
    grace_period_end = None
    started_within_schedule = True
    
    if not availability.allowed:
        # Check if there's an override code
        if override_code:
            try:
                validation = await TestScheduleService.validate_and_use_override(
                    db,
                    ValidateOverrideRequest(
                        override_code=override_code,
                        student_id=current_user.id
                    )
                )
                
                if not validation["valid"]:
                    # IMPORTANT: Don't create test attempt if validation fails
                    raise HTTPException(
                        status_code=http_status.HTTP_403_FORBIDDEN,
                        detail=f"Testing not available: {availability.message}. Override code invalid: {validation['message']}",
                        headers={
                            "X-Next-Window": str(availability.next_window) if availability.next_window else "",
                            "X-Schedule-Active": str(availability.schedule_active)
                        }
                    )
                else:
                    # Override was valid
                    override_id = validation.get("override_id")
                    started_within_schedule = False
                    
            except HTTPException:
                # Re-raise HTTP exceptions as-is
                raise
            except Exception as validation_error:
                print(f"Error validating override code: {validation_error}")
                raise HTTPException(
                    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error validating override code: {str(validation_error)}"
                )
        else:
            # No override code provided - don't create test attempt
            raise HTTPException(
                status_code=http_status.HTTP_403_FORBIDDEN,
                detail=availability.message,
                headers={
                    "X-Next-Window": str(availability.next_window) if availability.next_window else "",
                    "X-Schedule-Active": str(availability.schedule_active),
                    "X-Override-Required": "true"
                }
            )
    
    # Calculate grace period if test is allowed during schedule
    if availability.allowed and availability.current_window_end:
        schedule = await TestScheduleService.get_schedule(db, classroom_id)
        if schedule and schedule.grace_period_minutes:
            from datetime import timedelta
            grace_period_end = availability.current_window_end + timedelta(minutes=schedule.grace_period_minutes)
    
    # Check test eligibility
    eligibility = await VocabularyTestService.check_test_eligibility(
        db, current_user.id, assignment_id, classroom_assignment.id
    )
    
    if not eligibility["eligible"]:
        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=eligibility["reason"]
        )
    
    # Check for existing locked test attempt
    from app.models.vocabulary_test import VocabularyTestAttempt
    locked_attempt_result = await db.execute(
        select(VocabularyTestAttempt)
        .where(
            and_(
                VocabularyTestAttempt.student_id == current_user.id,
                VocabularyTestAttempt.is_locked == True,
                VocabularyTestAttempt.status == "in_progress"
            )
        )
        .order_by(VocabularyTestAttempt.started_at.desc())
    )
    locked_attempt = locked_attempt_result.scalar_one_or_none()
    
    if locked_attempt:
        raise HTTPException(
            status_code=http_status.HTTP_423_LOCKED,
            detail="You have a locked test attempt. Please contact your teacher to unlock it.",
            headers={"X-Locked-Attempt-Id": str(locked_attempt.id)}
        )
    
    try:
        # Generate test
        test_data = await VocabularyTestService.generate_test(
            db, assignment_id, classroom_assignment.id, current_user.id
        )
        
        # Start test attempt
        test_attempt_id = await VocabularyTestService.start_test_attempt(
            db, test_data["test_id"], current_user.id
        )
        
        # Format questions for frontend
        formatted_questions = []
        for question in test_data["questions"]:
            formatted_questions.append(VocabularyTestQuestion(
                id=question["id"],
                word=question["word"],
                example_sentence=question["example_sentence"],
                question_type=question["question_type"]
            ))
        
        return VocabularyTestStartResponse(
            test_attempt_id=test_attempt_id,
            questions=formatted_questions,
            total_questions=test_data["total_questions"],
            time_limit_minutes=test_data["time_limit_minutes"],
            started_at=datetime.now(timezone.utc)
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/vocabulary/test/submit/{test_attempt_id}", response_model=VocabularyTestAttemptResponse)
async def submit_vocabulary_test(
    test_attempt_id: UUID,
    responses: VocabularyTestAttemptRequest,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Submit vocabulary test answers"""
    
    # Check if test is locked before allowing submission
    from app.models.vocabulary_test import VocabularyTestAttempt
    attempt_result = await db.execute(
        select(VocabularyTestAttempt)
        .where(
            and_(
                VocabularyTestAttempt.id == test_attempt_id,
                VocabularyTestAttempt.student_id == current_user.id
            )
        )
    )
    test_attempt = attempt_result.scalar_one_or_none()
    
    if not test_attempt:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Test attempt not found"
        )
    
    if test_attempt.is_locked:
        raise HTTPException(
            status_code=http_status.HTTP_423_LOCKED,
            detail="This test is locked due to security violations. Please contact your teacher."
        )
    
    try:
        # Evaluate test attempt
        result = await VocabularyTestService.evaluate_test_attempt(
            db, test_attempt_id, responses.responses
        )
        
        return VocabularyTestAttemptResponse(**result)
        
    except ValueError as e:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/vocabulary/test/results/{test_attempt_id}", response_model=VocabularyTestAttemptResponse)
async def get_vocabulary_test_results(
    test_attempt_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get vocabulary test results"""
    
    # Get test attempt results
    result = await db.execute(
        select().select_from(text("""
            SELECT vta.*, vt.vocabulary_list_id, vt.classroom_assignment_id
            FROM vocabulary_test_attempts vta
            JOIN vocabulary_tests vt ON vt.id = vta.test_id
            WHERE vta.id = :test_attempt_id
            AND vta.student_id = :student_id
            AND vta.status = 'completed'
        """)),
        {
            "test_attempt_id": str(test_attempt_id),
            "student_id": str(current_user.id)
        }
    )
    
    attempt = result.fetchone()
    
    if not attempt:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Test attempt not found or not completed"
        )
    
    import json
    detailed_results = json.loads(attempt.responses) if attempt.responses else []
    
    return VocabularyTestAttemptResponse(
        test_attempt_id=attempt.id,
        test_id=attempt.test_id,
        score_percentage=float(attempt.score_percentage),
        questions_correct=attempt.questions_correct,
        total_questions=attempt.total_questions,
        time_spent_seconds=attempt.time_spent_seconds,
        status=attempt.status,
        started_at=attempt.started_at,
        completed_at=attempt.completed_at,
        detailed_results=detailed_results
    )


# Vocabulary Test Security Endpoints
@router.post("/vocabulary/test/{test_attempt_id}/security-incident")
async def log_vocabulary_test_security_incident(
    test_attempt_id: UUID,
    incident_data: dict,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Log a security incident during vocabulary test"""
    from app.models.vocabulary_test import VocabularyTestAttempt, VocabularyTestSecurityIncident
    
    # Verify test attempt exists and belongs to user
    result = await db.execute(
        select(VocabularyTestAttempt)
        .where(
            and_(
                VocabularyTestAttempt.id == test_attempt_id,
                VocabularyTestAttempt.student_id == current_user.id,
                VocabularyTestAttempt.status == "in_progress"
            )
        )
    )
    test_attempt = result.scalar_one_or_none()
    
    if not test_attempt:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Test attempt not found or not in progress"
        )
    
    # Create security incident record
    incident = VocabularyTestSecurityIncident(
        test_attempt_id=test_attempt_id,
        incident_type=incident_data.get("incident_type"),
        incident_data=incident_data.get("incident_data")
    )
    db.add(incident)
    
    # Update violation count
    violations = test_attempt.security_violations or []
    violations.append({
        "type": incident_data.get("incident_type"),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": incident_data.get("incident_data")
    })
    test_attempt.security_violations = violations
    
    # Check if we need to lock the test (2 violations = lock)
    violation_count = len(violations)
    warning_issued = False
    test_locked = False
    
    if violation_count == 1:
        warning_issued = True
    elif violation_count >= 2:
        test_locked = True
        test_attempt.is_locked = True
        test_attempt.locked_at = datetime.now(timezone.utc)
        test_attempt.locked_reason = f"Security violation: {incident_data.get('incident_type')}"
        incident.resulted_in_lock = True
    
    await db.commit()
    
    return {
        "violation_count": violation_count,
        "warning_issued": warning_issued,
        "test_locked": test_locked
    }


@router.get("/vocabulary/test/{test_attempt_id}/security-status")
async def get_vocabulary_test_security_status(
    test_attempt_id: UUID,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get security status of vocabulary test"""
    from app.models.vocabulary_test import VocabularyTestAttempt
    
    result = await db.execute(
        select(VocabularyTestAttempt)
        .where(
            and_(
                VocabularyTestAttempt.id == test_attempt_id,
                VocabularyTestAttempt.student_id == current_user.id
            )
        )
    )
    test_attempt = result.scalar_one_or_none()
    
    if not test_attempt:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Test attempt not found"
        )
    
    return {
        "violation_count": len(test_attempt.security_violations or []),
        "is_locked": test_attempt.is_locked,
        "locked_at": test_attempt.locked_at.isoformat() if test_attempt.locked_at else None,
        "locked_reason": test_attempt.locked_reason
    }


@router.post("/vocabulary/test/{test_attempt_id}/unlock")
async def unlock_vocabulary_test_with_bypass_code(
    test_attempt_id: UUID,
    unlock_data: dict,
    current_user: User = Depends(require_student_or_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Unlock vocabulary test with teacher bypass code"""
    from app.models.vocabulary_test import VocabularyTestAttempt, VocabularyTest
    from app.models.vocabulary import VocabularyList
    from app.models.tests import TeacherBypassCode
    
    # Get the locked test attempt
    result = await db.execute(
        select(VocabularyTestAttempt)
        .where(
            and_(
                VocabularyTestAttempt.id == test_attempt_id,
                VocabularyTestAttempt.student_id == current_user.id,
                VocabularyTestAttempt.is_locked == True
            )
        )
    )
    test_attempt = result.scalar_one_or_none()
    
    if not test_attempt:
        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail="Locked test attempt not found"
        )
    
    # Verify bypass code using the unified bypass validation system
    from app.services.bypass_validation import validate_bypass_code
    
    unlock_code = unlock_data.get("unlock_code", "").strip()
    
    # For vocabulary tests, we pass the vocabulary_list_id as the assignment context
    # since bypass_validation will use it to find the teacher
    vocab_test_result = await db.execute(
        select(VocabularyTest)
        .join(VocabularyTestAttempt, VocabularyTestAttempt.test_id == VocabularyTest.id)
        .where(VocabularyTestAttempt.id == test_attempt_id)
    )
    vocab_test = vocab_test_result.scalar_one_or_none()
    
    # Validate bypass code
    bypass_valid, bypass_type, teacher_id = await validate_bypass_code(
        db=db,
        student_id=current_user.id,
        answer_text=unlock_code,
        context_type="vocabulary_test",
        context_id=str(test_attempt_id),
        assignment_id=str(vocab_test.vocabulary_list_id) if vocab_test else None
    )
    
    if not bypass_valid:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired bypass code"
        )
    
    # Reset test attempt
    test_attempt.is_locked = False
    test_attempt.locked_at = None
    test_attempt.locked_reason = None
    test_attempt.security_violations = []
    test_attempt.responses = {}
    test_attempt.started_at = datetime.now(timezone.utc)
    test_attempt.status = "in_progress"
    
    await db.commit()
    
    return {
        "success": True,
        "message": "Test unlocked successfully. You will restart from the beginning.",
        "test_attempt_id": str(test_attempt_id),
        "bypass_type": bypass_type or "general"
    }
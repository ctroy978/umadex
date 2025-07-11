"""
Unified classroom assignment endpoints for all assignment types
"""
from typing import Optional, List, Union
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, and_, or_, func, delete, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
import logging

from app.core.database import get_db
from app.utils.deps import get_current_user
from app.models.user import User, UserRole
from app.models.classroom import Classroom, ClassroomAssignment, StudentAssignment
from app.models.reading import ReadingAssignment as ReadingAssignmentModel
from app.models.vocabulary import VocabularyList
from app.models.debate import DebateAssignment
from app.models.writing import WritingAssignment
from app.models.reading import ReadingAssignment as UMALectureAssignment
from app.models.umatest import TestAssignment

router = APIRouter()
logger = logging.getLogger(__name__)

# Assignment type normalization mapping
# Maps any variation to the canonical backend type
ASSIGNMENT_TYPE_MAP = {
    "reading": "reading",
    "UMARead": "reading",
    "vocabulary": "vocabulary",
    "UMAVocab": "vocabulary",
    "debate": "debate",
    "UMADebate": "debate",
    "writing": "writing",
    "UMAWrite": "writing",
    "lecture": "UMALecture",
    "UMALecture": "UMALecture",
    "test": "test",
    "UMATest": "test"
}

def normalize_assignment_type(assignment_type: str) -> str:
    """Normalize assignment type to canonical backend form"""
    return ASSIGNMENT_TYPE_MAP.get(assignment_type, "reading")

def require_teacher(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be a teacher"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this resource"
        )
    return current_user


class AssignmentSchedule(BaseModel):
    assignment_id: UUID
    assignment_type: str = "reading"  # "reading", "vocabulary", "debate", "writing", "lecture", or "test"
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


class UpdateClassroomAssignmentsRequest(BaseModel):
    assignments: List[AssignmentSchedule]


class UpdateClassroomAssignmentsResponse(BaseModel):
    added: List[str]
    removed: List[str]
    total: int
    students_affected: Optional[int] = 0


class CheckAssignmentRemovalResponse(BaseModel):
    assignments_with_students: List[dict]
    total_students_affected: int


@router.post("/classrooms/{classroom_id}/assignments/check-removal", response_model=CheckAssignmentRemovalResponse)
async def check_assignment_removal(
    classroom_id: UUID,
    request: UpdateClassroomAssignmentsRequest,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Check how many students would be affected by removing assignments.
    Note: Removing assignments will prevent students from accessing them, but all student work is preserved."""
    # Verify classroom exists and belongs to teacher
    result = await db.execute(
        select(Classroom).where(
            and_(
                Classroom.id == classroom_id,
                Classroom.teacher_id == teacher.id,
                Classroom.deleted_at.is_(None)
            )
        )
    )
    classroom = result.scalar_one_or_none()
    
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )
    
    # Get current ACTIVE assignments (not soft-deleted)
    current_result = await db.execute(
        select(ClassroomAssignment)
        .where(
            and_(
                ClassroomAssignment.classroom_id == classroom_id,
                ClassroomAssignment.removed_from_classroom_at.is_(None)
            )
        )
    )
    current_assignments = list(current_result.scalars())
    
    # Build lookup maps
    current_reading = {}
    current_vocabulary = {}
    current_debate = {}
    current_writing = {}
    current_lecture = {}
    current_test = {}
    for ca in current_assignments:
        if ca.assignment_type == "reading" and ca.assignment_id:
            current_reading[ca.assignment_id] = ca
        elif ca.assignment_type == "vocabulary" and ca.vocabulary_list_id:
            current_vocabulary[ca.vocabulary_list_id] = ca
        elif ca.assignment_type == "debate" and ca.assignment_id:
            current_debate[ca.assignment_id] = ca
        elif ca.assignment_type == "writing" and ca.assignment_id:
            current_writing[ca.assignment_id] = ca
        elif ca.assignment_type in ["UMALecture", "lecture"] and ca.assignment_id:
            current_lecture[ca.assignment_id] = ca
        elif ca.assignment_type == "test" and ca.assignment_id:
            current_test[ca.assignment_id] = ca
    
    # Process requested assignments
    requested_reading = set()
    requested_vocabulary = set()
    requested_debate = set()
    requested_writing = set()
    requested_test = set()
    for sched in request.assignments:
        normalized_type = normalize_assignment_type(sched.assignment_type)
        if normalized_type == "vocabulary":
            requested_vocabulary.add(sched.assignment_id)
        elif normalized_type == "debate":
            requested_debate.add(sched.assignment_id)
        elif normalized_type == "writing":
            requested_writing.add(sched.assignment_id)
        elif normalized_type == "test":
            requested_test.add(sched.assignment_id)
        else:
            requested_reading.add(sched.assignment_id)
    
    # Calculate what will be removed
    reading_to_remove = set(current_reading.keys()) - requested_reading
    vocabulary_to_remove = set(current_vocabulary.keys()) - requested_vocabulary
    debate_to_remove = set(current_debate.keys()) - requested_debate
    writing_to_remove = set(current_writing.keys()) - requested_writing
    test_to_remove = set(current_test.keys()) - requested_test
    
    assignments_with_students = []
    total_students = 0
    
    # Check reading assignments
    for assignment_id in reading_to_remove:
        ca = current_reading[assignment_id]
        
        # Get assignment details
        assignment_result = await db.execute(
            select(ReadingAssignmentModel).where(ReadingAssignmentModel.id == assignment_id)
        )
        assignment = assignment_result.scalar_one_or_none()
        
        # Count students
        count_result = await db.execute(
            select(func.count(StudentAssignment.id)).where(
                StudentAssignment.classroom_assignment_id == ca.id
            )
        )
        student_count = count_result.scalar() or 0
        
        if student_count > 0:
            assignments_with_students.append({
                "assignment_id": str(assignment_id),
                "assignment_type": "reading",
                "assignment_title": assignment.assignment_title if assignment else "Unknown",
                "student_count": student_count
            })
            total_students += student_count
    
    # Check vocabulary assignments
    for list_id in vocabulary_to_remove:
        ca = current_vocabulary[list_id]
        
        # Get vocabulary list details
        vocab_result = await db.execute(
            select(VocabularyList).where(VocabularyList.id == list_id)
        )
        vocab_list = vocab_result.scalar_one_or_none()
        
        # Count students
        count_result = await db.execute(
            select(func.count(StudentAssignment.id)).where(
                StudentAssignment.classroom_assignment_id == ca.id
            )
        )
        student_count = count_result.scalar() or 0
        
        if student_count > 0:
            assignments_with_students.append({
                "assignment_id": str(list_id),
                "assignment_type": "vocabulary",
                "assignment_title": vocab_list.title if vocab_list else "Unknown",
                "student_count": student_count
            })
            total_students += student_count
    
    # Check debate assignments
    for assignment_id in debate_to_remove:
        ca = current_debate[assignment_id]
        
        # Get assignment details
        assignment_result = await db.execute(
            select(DebateAssignment).where(DebateAssignment.id == assignment_id)
        )
        assignment = assignment_result.scalar_one_or_none()
        
        # Count students
        count_result = await db.execute(
            select(func.count(StudentAssignment.id)).where(
                StudentAssignment.classroom_assignment_id == ca.id
            )
        )
        student_count = count_result.scalar() or 0
        
        if student_count > 0:
            assignments_with_students.append({
                "assignment_id": str(assignment_id),
                "assignment_type": "debate",
                "assignment_title": assignment.title if assignment else "Unknown",
                "student_count": student_count
            })
            total_students += student_count
    
    # Check writing assignments
    for assignment_id in writing_to_remove:
        ca = current_writing[assignment_id]
        
        # Get assignment details
        assignment_result = await db.execute(
            select(WritingAssignment).where(WritingAssignment.id == assignment_id)
        )
        assignment = assignment_result.scalar_one_or_none()
        
        # Count students
        count_result = await db.execute(
            select(func.count(StudentAssignment.id)).where(
                StudentAssignment.classroom_assignment_id == ca.id
            )
        )
        student_count = count_result.scalar() or 0
        
        if student_count > 0:
            assignments_with_students.append({
                "assignment_id": str(assignment_id),
                "assignment_type": "writing",
                "assignment_title": assignment.title if assignment else "Unknown",
                "student_count": student_count
            })
            total_students += student_count
    
    # Check test assignments
    for assignment_id in test_to_remove:
        ca = current_test[assignment_id]
        
        # Get assignment details
        assignment_result = await db.execute(
            select(TestAssignment).where(TestAssignment.id == assignment_id)
        )
        assignment = assignment_result.scalar_one_or_none()
        
        # Count students
        count_result = await db.execute(
            select(func.count(StudentAssignment.id)).where(
                StudentAssignment.classroom_assignment_id == ca.id
            )
        )
        student_count = count_result.scalar() or 0
        
        if student_count > 0:
            assignments_with_students.append({
                "assignment_id": str(assignment_id),
                "assignment_type": "test",
                "assignment_title": assignment.test_title if assignment else "Unknown",
                "student_count": student_count
            })
            total_students += student_count
    
    return CheckAssignmentRemovalResponse(
        assignments_with_students=assignments_with_students,
        total_students_affected=total_students
    )


@router.get("/classrooms/{classroom_id}/assignments/available/all")
async def get_all_available_assignments(
    classroom_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None),
    assignment_type: Optional[str] = Query(None),
    grade_level: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """Get all teacher's assignments (reading and vocabulary) with their assignment status for this classroom"""
    # Verify classroom ownership
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
    
    # Get currently ACTIVE assigned items with their schedules (not soft-deleted)
    assigned_result = await db.execute(
        select(ClassroomAssignment).where(
            and_(
                ClassroomAssignment.classroom_id == classroom_id,
                ClassroomAssignment.removed_from_classroom_at.is_(None)
            )
        )
    )
    assigned_items = assigned_result.scalars().all()
    
    # Separate by type
    assigned_reading = {}
    assigned_vocabulary = {}
    assigned_debate = {}
    assigned_writing = {}
    assigned_lecture = {}
    assigned_test = {}
    for ca in assigned_items:
        if ca.assignment_type == "reading" and ca.assignment_id:
            assigned_reading[ca.assignment_id] = ca
        elif ca.assignment_type == "vocabulary" and ca.vocabulary_list_id:
            assigned_vocabulary[ca.vocabulary_list_id] = ca
        elif ca.assignment_type == "debate" and ca.assignment_id:
            assigned_debate[ca.assignment_id] = ca
        elif ca.assignment_type == "writing" and ca.assignment_id:
            assigned_writing[ca.assignment_id] = ca
        elif ca.assignment_type in ["UMALecture", "lecture"] and ca.assignment_id:
            assigned_lecture[ca.assignment_id] = ca
        elif ca.assignment_type == "test" and ca.assignment_id:
            assigned_test[ca.assignment_id] = ca
    
    all_assignments = []
    
    # Handle reading assignments
    if not assignment_type or assignment_type in ["all", "UMARead", "UMADebate", "UMAWrite", "UMALecture"]:
        # Build query for reading assignments
        reading_query = select(ReadingAssignmentModel).where(
            and_(
                ReadingAssignmentModel.teacher_id == teacher.id,
                ReadingAssignmentModel.status == "published",
                ReadingAssignmentModel.deleted_at.is_(None)  # Filter out archived assignments
            )
        )
        
        # Apply filters
        if search:
            reading_query = reading_query.where(
                or_(
                    ReadingAssignmentModel.assignment_title.ilike(f"%{search}%"),
                    ReadingAssignmentModel.work_title.ilike(f"%{search}%"),
                    ReadingAssignmentModel.author.ilike(f"%{search}%")
                )
            )
        
        if assignment_type and assignment_type != "all":
            reading_query = reading_query.where(ReadingAssignmentModel.assignment_type == assignment_type)
        
        if grade_level and grade_level != "all":
            reading_query = reading_query.where(ReadingAssignmentModel.grade_level == grade_level)
        
        if status:
            if status == "assigned":
                reading_query = reading_query.where(ReadingAssignmentModel.id.in_(assigned_reading.keys()))
            elif status == "unassigned":
                reading_query = reading_query.where(ReadingAssignmentModel.id.notin_(assigned_reading.keys()))
        
        # Execute query
        reading_result = await db.execute(reading_query)
        reading_assignments = reading_result.scalars().all()
        
        # Format reading assignments
        for assignment in reading_assignments:
            assignment_dict = {
                "id": str(assignment.id),
                "assignment_title": assignment.assignment_title,
                "work_title": assignment.work_title,
                "author": assignment.author or "",
                "assignment_type": assignment.assignment_type,
                "grade_level": assignment.grade_level,
                "work_type": assignment.work_type,
                "status": assignment.status,
                "created_at": assignment.created_at,
                "is_assigned": assignment.id in assigned_reading or assignment.id in assigned_lecture,
                "is_archived": assignment.deleted_at is not None,
                "item_type": "lecture" if assignment.assignment_type == "UMALecture" else "reading"
            }
            
            # Add schedule info if assigned
            if assignment.id in assigned_reading:
                ca = assigned_reading[assignment.id]
                assignment_dict["current_schedule"] = {
                    "start_date": ca.start_date,
                    "end_date": ca.end_date
                }
            elif assignment.id in assigned_lecture:
                ca = assigned_lecture[assignment.id]
                assignment_dict["current_schedule"] = {
                    "start_date": ca.start_date,
                    "end_date": ca.end_date
                }
            
            all_assignments.append(assignment_dict)
    
    # Handle vocabulary assignments
    if not assignment_type or assignment_type in ["all", "UMAVocab"]:
        # Build query for vocabulary lists
        vocab_query = select(VocabularyList).where(
            and_(
                VocabularyList.teacher_id == teacher.id,
                VocabularyList.status == "published",
                VocabularyList.deleted_at.is_(None)  # Filter out archived vocabulary lists
            )
        )
        
        # Apply filters
        if search:
            vocab_query = vocab_query.where(
                or_(
                    VocabularyList.title.ilike(f"%{search}%"),
                    VocabularyList.context_description.ilike(f"%{search}%")
                )
            )
        
        if grade_level and grade_level != "all":
            vocab_query = vocab_query.where(VocabularyList.grade_level == grade_level)
        
        if status:
            if status == "assigned":
                vocab_query = vocab_query.where(VocabularyList.id.in_(assigned_vocabulary.keys()))
            elif status == "unassigned":
                vocab_query = vocab_query.where(VocabularyList.id.notin_(assigned_vocabulary.keys()))
        
        # Execute query
        vocab_result = await db.execute(vocab_query)
        vocab_lists = vocab_result.scalars().all()
        
        # Get word counts
        word_counts = {}
        if vocab_lists:
            list_ids = [vl.id for vl in vocab_lists]
            from sqlalchemy import text
            count_query = text("""
                SELECT list_id, COUNT(*) as word_count 
                FROM vocabulary_words 
                WHERE list_id = ANY(:list_ids)
                GROUP BY list_id
            """)
            count_result = await db.execute(count_query, {"list_ids": list_ids})
            word_counts = {row[0]: row[1] for row in count_result}
        
        # Format vocabulary assignments
        for vocab_list in vocab_lists:
            vocab_dict = {
                "id": str(vocab_list.id),
                "assignment_title": vocab_list.title,
                "work_title": vocab_list.context_description,
                "author": "",  # No author for vocabulary lists
                "assignment_type": "UMAVocab",
                "grade_level": vocab_list.grade_level,
                "work_type": vocab_list.subject_area,
                "status": vocab_list.status,
                "created_at": vocab_list.created_at,
                "is_assigned": vocab_list.id in assigned_vocabulary,
                "is_archived": vocab_list.deleted_at is not None,
                "word_count": word_counts.get(vocab_list.id, 0),
                "item_type": "vocabulary"
            }
            
            # Add schedule info if assigned
            if vocab_list.id in assigned_vocabulary:
                ca = assigned_vocabulary[vocab_list.id]
                vocab_dict["current_schedule"] = {
                    "start_date": ca.start_date,
                    "end_date": ca.end_date
                }
            
            all_assignments.append(vocab_dict)
    
    # Handle debate assignments
    if not assignment_type or assignment_type in ["all", "UMADebate"]:
        # Build query for debate assignments
        debate_query = select(DebateAssignment).where(
            and_(
                DebateAssignment.teacher_id == teacher.id,
                DebateAssignment.deleted_at.is_(None)  # Filter out archived assignments
            )
        )
        
        # Apply filters
        if search:
            debate_query = debate_query.where(
                or_(
                    DebateAssignment.title.ilike(f"%{search}%"),
                    DebateAssignment.topic.ilike(f"%{search}%"),
                    DebateAssignment.description.ilike(f"%{search}%")
                )
            )
        
        if grade_level and grade_level != "all":
            debate_query = debate_query.where(DebateAssignment.grade_level == grade_level)
        
        if status:
            if status == "assigned":
                debate_query = debate_query.where(DebateAssignment.id.in_(assigned_debate.keys()))
            elif status == "unassigned":
                debate_query = debate_query.where(DebateAssignment.id.notin_(assigned_debate.keys()))
        
        # Execute query
        debate_result = await db.execute(debate_query)
        debate_assignments = debate_result.scalars().all()
        
        # Format debate assignments
        for assignment in debate_assignments:
            debate_dict = {
                "id": str(assignment.id),
                "assignment_title": assignment.title,
                "work_title": assignment.topic,
                "author": "",  # No author for debates
                "assignment_type": "UMADebate",
                "grade_level": assignment.grade_level,
                "work_type": assignment.subject,
                "status": "published",  # Debates don't have draft status
                "created_at": assignment.created_at,
                "is_assigned": assignment.id in assigned_debate,
                "is_archived": assignment.deleted_at is not None,
                "debate_config": {
                    "rounds_per_debate": assignment.rounds_per_debate,
                    "debate_count": assignment.debate_count,
                    "time_limit_hours": assignment.time_limit_hours
                },
                "item_type": "debate"
            }
            
            # Add schedule info if assigned
            if assignment.id in assigned_debate:
                ca = assigned_debate[assignment.id]
                debate_dict["current_schedule"] = {
                    "start_date": ca.start_date,
                    "end_date": ca.end_date
                }
            
            all_assignments.append(debate_dict)
    
    # Handle writing assignments
    if not assignment_type or assignment_type in ["all", "UMAWrite"]:
        # Build query for writing assignments
        writing_query = select(WritingAssignment).where(
            and_(
                WritingAssignment.teacher_id == teacher.id,
                WritingAssignment.deleted_at.is_(None)  # Filter out archived assignments
            )
        )
        
        # Apply filters
        if search:
            writing_query = writing_query.where(
                or_(
                    WritingAssignment.title.ilike(f"%{search}%"),
                    WritingAssignment.prompt_text.ilike(f"%{search}%"),
                    WritingAssignment.subject.ilike(f"%{search}%")
                )
            )
        
        if grade_level and grade_level != "all":
            writing_query = writing_query.where(WritingAssignment.grade_level == grade_level)
        
        if status:
            if status == "assigned":
                writing_query = writing_query.where(WritingAssignment.id.in_(assigned_writing.keys()))
            elif status == "unassigned":
                writing_query = writing_query.where(WritingAssignment.id.notin_(assigned_writing.keys()))
        
        # Execute query
        writing_result = await db.execute(writing_query)
        writing_assignments = writing_result.scalars().all()
        
        # Format writing assignments
        for assignment in writing_assignments:
            writing_dict = {
                "id": str(assignment.id),
                "assignment_title": assignment.title,
                "work_title": assignment.prompt_text[:100] + "..." if len(assignment.prompt_text) > 100 else assignment.prompt_text,
                "author": "",  # No author for writing assignments
                "assignment_type": "UMAWrite",
                "grade_level": assignment.grade_level,
                "work_type": assignment.subject or "Writing",
                "status": "published",  # Writing assignments don't have draft status
                "created_at": assignment.created_at,
                "is_assigned": assignment.id in assigned_writing,
                "is_archived": assignment.deleted_at is not None,
                "writing_config": {
                    "word_count_min": assignment.word_count_min,
                    "word_count_max": assignment.word_count_max
                },
                "item_type": "writing"
            }
            
            # Add schedule info if assigned
            if assignment.id in assigned_writing:
                ca = assigned_writing[assignment.id]
                writing_dict["current_schedule"] = {
                    "start_date": ca.start_date,
                    "end_date": ca.end_date
                }
            
            all_assignments.append(writing_dict)
    
    # Handle test assignments
    if not assignment_type or assignment_type in ["all", "UMATest"]:
        # Build query for test assignments
        test_query = select(TestAssignment).where(
            and_(
                TestAssignment.teacher_id == teacher.id,
                TestAssignment.status == "published",
                TestAssignment.deleted_at.is_(None)  # Filter out archived assignments
            )
        )
        
        # Apply filters
        if search:
            test_query = test_query.where(
                or_(
                    TestAssignment.test_title.ilike(f"%{search}%"),
                    TestAssignment.test_description.ilike(f"%{search}%")
                )
            )
        
        if status:
            if status == "assigned":
                test_query = test_query.where(TestAssignment.id.in_(assigned_test.keys()))
            elif status == "unassigned":
                test_query = test_query.where(TestAssignment.id.notin_(assigned_test.keys()))
        
        # Execute query
        test_result = await db.execute(test_query)
        test_assignments = test_result.scalars().all()
        
        # Format test assignments
        for assignment in test_assignments:
            test_dict = {
                "id": str(assignment.id),
                "assignment_title": assignment.test_title,
                "work_title": assignment.test_description or "Comprehensive Test",
                "author": "",  # No author for tests
                "assignment_type": "UMATest",
                "grade_level": "Multiple",  # Tests can span multiple grade levels
                "work_type": "Test",
                "status": assignment.status,
                "created_at": assignment.created_at,
                "is_assigned": assignment.id in assigned_test,
                "is_archived": assignment.deleted_at is not None,
                "test_config": {
                    "time_limit_minutes": assignment.time_limit_minutes,
                    "attempt_limit": assignment.attempt_limit,
                    "randomize_questions": assignment.randomize_questions,
                    "total_questions": assignment.test_structure.get("total_questions", 0) if assignment.test_structure else 0
                },
                "item_type": "test"
            }
            
            # Add schedule info if assigned
            if assignment.id in assigned_test:
                ca = assigned_test[assignment.id]
                test_dict["current_schedule"] = {
                    "start_date": ca.start_date,
                    "end_date": ca.end_date
                }
            
            all_assignments.append(test_dict)
    
    # Sort all assignments by created_at desc
    # Handle both offset-naive and offset-aware datetimes
    all_assignments.sort(key=lambda x: x["created_at"].replace(tzinfo=None) if x["created_at"] else datetime.min, reverse=True)
    
    # Apply pagination
    total_count = len(all_assignments)
    start_idx = (page - 1) * per_page
    end_idx = start_idx + per_page
    paginated_assignments = all_assignments[start_idx:end_idx]
    
    return {
        "assignments": paginated_assignments,
        "total_count": total_count,
        "page": page,
        "per_page": per_page
    }


@router.put("/classrooms/{classroom_id}/assignments/all", response_model=UpdateClassroomAssignmentsResponse)
async def update_all_classroom_assignments(
    classroom_id: UUID,
    request: UpdateClassroomAssignmentsRequest,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Update assignments in a classroom (supports both reading and vocabulary)"""
    logger.info(f"Updating assignments for classroom {classroom_id}")
    logger.info(f"Request assignments count: {len(request.assignments)}")
    
    # IMPORTANT: The logic here works as follows:
    # 1. We get only ACTIVE assignments (not soft-deleted) as "current"
    # 2. When adding assignments, we check for ANY existing record (including soft-deleted)
    # 3. If a soft-deleted record exists, we reactivate it instead of creating a new one
    # 4. This allows previously removed assignments to be re-added to the classroom
    
    # Verify classroom exists and belongs to teacher
    result = await db.execute(
        select(Classroom).where(
            and_(
                Classroom.id == classroom_id,
                Classroom.teacher_id == teacher.id,
                Classroom.deleted_at.is_(None)
            )
        )
    )
    classroom = result.scalar_one_or_none()
    
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )
    
    # Get current ACTIVE assignments (not soft-deleted)
    current_result = await db.execute(
        select(ClassroomAssignment)
        .where(
            and_(
                ClassroomAssignment.classroom_id == classroom_id,
                ClassroomAssignment.removed_from_classroom_at.is_(None)
            )
        )
    )
    current_assignments = list(current_result.scalars())
    
    # Build lookup maps
    current_reading = {}
    current_vocabulary = {}
    current_debate = {}
    current_writing = {}
    current_lecture = {}
    current_test = {}
    for ca in current_assignments:
        if ca.assignment_type == "reading" and ca.assignment_id:
            current_reading[ca.assignment_id] = ca
        elif ca.assignment_type == "vocabulary" and ca.vocabulary_list_id:
            current_vocabulary[ca.vocabulary_list_id] = ca
        elif ca.assignment_type == "debate" and ca.assignment_id:
            current_debate[ca.assignment_id] = ca
        elif ca.assignment_type == "writing" and ca.assignment_id:
            current_writing[ca.assignment_id] = ca
        elif ca.assignment_type in ["UMALecture", "lecture"] and ca.assignment_id:
            current_lecture[ca.assignment_id] = ca
        elif ca.assignment_type == "test" and ca.assignment_id:
            current_test[ca.assignment_id] = ca
    
    # Process requested assignments
    requested_reading = {}
    requested_vocabulary = {}
    requested_debate = {}
    requested_writing = {}
    requested_lecture = {}
    requested_test = {}
    for sched in request.assignments:
        try:
            # Ensure assignment_id is a valid UUID
            assignment_id = sched.assignment_id
            # Normalize the assignment type
            normalized_type = normalize_assignment_type(sched.assignment_type)
            
            if normalized_type == "vocabulary":
                requested_vocabulary[assignment_id] = sched
            elif normalized_type == "debate":
                requested_debate[assignment_id] = sched
            elif normalized_type == "writing":
                requested_writing[assignment_id] = sched
            elif normalized_type == "UMALecture":
                requested_lecture[assignment_id] = sched
            elif normalized_type == "test":
                requested_test[assignment_id] = sched
            else:  # Default to reading
                requested_reading[assignment_id] = sched
        except Exception as e:
            logger.error(f"Error processing assignment schedule: {str(e)}, schedule: {sched}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid assignment data: {str(e)}"
            )
    
    # Calculate changes
    reading_to_add = set(requested_reading.keys()) - set(current_reading.keys())
    reading_to_remove = set(current_reading.keys()) - set(requested_reading.keys())
    reading_to_update = set(requested_reading.keys()) & set(current_reading.keys())
    
    vocabulary_to_add = set(requested_vocabulary.keys()) - set(current_vocabulary.keys())
    vocabulary_to_remove = set(current_vocabulary.keys()) - set(requested_vocabulary.keys())
    vocabulary_to_update = set(requested_vocabulary.keys()) & set(current_vocabulary.keys())
    
    debate_to_add = set(requested_debate.keys()) - set(current_debate.keys())
    debate_to_remove = set(current_debate.keys()) - set(requested_debate.keys())
    debate_to_update = set(requested_debate.keys()) & set(current_debate.keys())
    
    writing_to_add = set(requested_writing.keys()) - set(current_writing.keys())
    writing_to_remove = set(current_writing.keys()) - set(requested_writing.keys())
    writing_to_update = set(requested_writing.keys()) & set(current_writing.keys())
    
    lecture_to_add = set(requested_lecture.keys()) - set(current_lecture.keys())
    lecture_to_remove = set(current_lecture.keys()) - set(requested_lecture.keys())
    lecture_to_update = set(requested_lecture.keys()) & set(current_lecture.keys())
    
    test_to_add = set(requested_test.keys()) - set(current_test.keys())
    test_to_remove = set(current_test.keys()) - set(requested_test.keys())
    test_to_update = set(requested_test.keys()) & set(current_test.keys())
    
    # Count students affected by removals
    students_affected = 0
    
    # Handle all assignment removals using soft delete
    assignments_to_remove = (
        [(id, "reading") for id in reading_to_remove] +
        [(id, "vocabulary") for id in vocabulary_to_remove] +
        [(id, "debate") for id in debate_to_remove] +
        [(id, "writing") for id in writing_to_remove] +
        [(id, "lecture") for id in lecture_to_remove] +
        [(id, "test") for id in test_to_remove]
    )
    
    if assignments_to_remove:
        # Soft delete assignments by setting removed_from_classroom_at
        for assignment_id, assignment_type in assignments_to_remove:
            update_query = (
                update(ClassroomAssignment)
                .where(
                    and_(
                        ClassroomAssignment.classroom_id == classroom_id,
                        ClassroomAssignment.removed_from_classroom_at.is_(None)
                    )
                )
                .values(
                    removed_from_classroom_at=func.now(),
                    removed_by=teacher.id
                )
            )
            
            if assignment_type == "vocabulary":
                update_query = update_query.where(
                    ClassroomAssignment.vocabulary_list_id == assignment_id
                )
            elif assignment_type == "lecture":
                # Handle both "UMALecture" and "lecture" types
                update_query = update_query.where(
                    and_(
                        ClassroomAssignment.assignment_id == assignment_id,
                        ClassroomAssignment.assignment_type.in_(["UMALecture", "lecture"])
                    )
                )
            else:
                update_query = update_query.where(
                    and_(
                        ClassroomAssignment.assignment_id == assignment_id,
                        ClassroomAssignment.assignment_type == assignment_type
                    )
                )
            
            result = await db.execute(update_query)
            
            # Count affected students for reporting
            if result.rowcount > 0:
                count_query = (
                    select(func.count(StudentAssignment.id))
                    .select_from(StudentAssignment)
                    .join(ClassroomAssignment)
                    .where(
                        and_(
                            ClassroomAssignment.classroom_id == classroom_id,
                            ClassroomAssignment.removed_from_classroom_at.isnot(None),
                            StudentAssignment.completed_at.is_(None)  # Only count incomplete assignments
                        )
                    )
                )
                
                if assignment_type == "vocabulary":
                    count_query = count_query.where(
                        ClassroomAssignment.vocabulary_list_id == assignment_id
                    )
                elif assignment_type == "lecture":
                    count_query = count_query.where(
                        and_(
                            ClassroomAssignment.assignment_id == assignment_id,
                            ClassroomAssignment.assignment_type.in_(["UMALecture", "lecture"])
                        )
                    )
                else:
                    count_query = count_query.where(
                        and_(
                            ClassroomAssignment.assignment_id == assignment_id,
                            ClassroomAssignment.assignment_type == assignment_type
                        )
                    )
                
                count_result = await db.execute(count_query)
                students_affected += count_result.scalar() or 0
    
    # Note: Old hard delete code has been removed. Assignments are now soft-deleted to preserve student work.
    
    # Update existing assignments
    for assignment_id in reading_to_update:
        ca = current_reading[assignment_id]
        schedule = requested_reading[assignment_id]
        ca.start_date = schedule.start_date
        ca.end_date = schedule.end_date
        logger.debug(f"Updating reading assignment {assignment_id}: start_date={schedule.start_date}, end_date={schedule.end_date}")
    
    for list_id in vocabulary_to_update:
        ca = current_vocabulary[list_id]
        schedule = requested_vocabulary[list_id]
        ca.start_date = schedule.start_date
        ca.end_date = schedule.end_date
    
    for assignment_id in debate_to_update:
        ca = current_debate[assignment_id]
        schedule = requested_debate[assignment_id]
        ca.start_date = schedule.start_date
        ca.end_date = schedule.end_date
    
    for assignment_id in writing_to_update:
        ca = current_writing[assignment_id]
        schedule = requested_writing[assignment_id]
        ca.start_date = schedule.start_date
        ca.end_date = schedule.end_date
    
    for assignment_id in lecture_to_update:
        ca = current_lecture[assignment_id]
        schedule = requested_lecture[assignment_id]
        ca.start_date = schedule.start_date
        ca.end_date = schedule.end_date
    
    # Add new reading assignments
    display_order = len(current_assignments) - len(reading_to_remove) - len(vocabulary_to_remove) - len(debate_to_remove) - len(writing_to_remove) - len(lecture_to_remove)
    logger.info(f"Starting to add new assignments. Display order starting at: {display_order}")
    for assignment_id in reading_to_add:
        logger.info(f"Adding reading assignment {assignment_id} to classroom {classroom_id}")
        # Verify assignment exists and belongs to teacher
        assignment_result = await db.execute(
            select(ReadingAssignmentModel).where(
                and_(
                    ReadingAssignmentModel.id == assignment_id,
                    ReadingAssignmentModel.teacher_id == teacher.id,
                    ReadingAssignmentModel.deleted_at.is_(None)
                )
            )
        )
        assignment = assignment_result.scalar_one_or_none()
        if not assignment:
            logger.warning(f"Reading assignment {assignment_id} not found or archived, skipping")
            continue
        
        # Check if assignment already exists for this classroom (including soft-deleted)
        existing_result = await db.execute(
            select(ClassroomAssignment).where(
                and_(
                    ClassroomAssignment.classroom_id == classroom_id,
                    ClassroomAssignment.assignment_id == assignment_id
                )
            )
        )
        existing_assignment = existing_result.scalar_one_or_none()
        
        if existing_assignment:
            if existing_assignment.removed_from_classroom_at:
                # Reactivate the soft-deleted assignment
                logger.info(f"Reactivating soft-deleted assignment {assignment_id}")
                schedule = requested_reading[assignment_id]
                existing_assignment.removed_from_classroom_at = None
                existing_assignment.removed_by = None
                existing_assignment.start_date = schedule.start_date
                existing_assignment.end_date = schedule.end_date
                existing_assignment.display_order = display_order
                display_order += 1
            else:
                # Assignment is already active, just update dates if needed
                logger.info(f"Active assignment already exists for {assignment_id}, updating dates")
                schedule = requested_reading[assignment_id]
                existing_assignment.start_date = schedule.start_date
                existing_assignment.end_date = schedule.end_date
        else:
            # No existing assignment, create new one
            logger.info(f"No existing assignment found, creating new one for {assignment_id}")
            schedule = requested_reading[assignment_id]
            ca = ClassroomAssignment(
                classroom_id=classroom_id,
                assignment_id=assignment_id,
                assignment_type="reading",
                display_order=display_order,
                start_date=schedule.start_date,
                end_date=schedule.end_date
            )
            db.add(ca)
            display_order += 1
    
    # Add new vocabulary assignments
    for list_id in vocabulary_to_add:
        logger.info(f"Adding vocabulary assignment {list_id} to classroom {classroom_id}")
        # Verify vocabulary list exists and belongs to teacher
        vocab_result = await db.execute(
            select(VocabularyList).where(
                and_(
                    VocabularyList.id == list_id,
                    VocabularyList.teacher_id == teacher.id,
                    VocabularyList.deleted_at.is_(None)
                )
            )
        )
        vocab_list = vocab_result.scalar_one_or_none()
        if not vocab_list:
            logger.warning(f"Vocabulary list {list_id} not found or archived, skipping")
            continue
        
        # Check if vocabulary assignment already exists for this classroom (including soft-deleted)
        existing_result = await db.execute(
            select(ClassroomAssignment).where(
                and_(
                    ClassroomAssignment.classroom_id == classroom_id,
                    ClassroomAssignment.vocabulary_list_id == list_id,
                    ClassroomAssignment.assignment_type == "vocabulary"
                )
            )
        )
        existing_assignment = existing_result.scalar_one_or_none()
        
        if existing_assignment:
            if existing_assignment.removed_from_classroom_at:
                # Reactivate the soft-deleted assignment
                logger.info(f"Reactivating soft-deleted vocabulary assignment {list_id}")
                schedule = requested_vocabulary[list_id]
                existing_assignment.removed_from_classroom_at = None
                existing_assignment.removed_by = None
                existing_assignment.start_date = schedule.start_date
                existing_assignment.end_date = schedule.end_date
                existing_assignment.display_order = display_order
                display_order += 1
            else:
                # Assignment is already active, just update dates if needed
                logger.info(f"Active vocabulary assignment already exists for {list_id}, updating dates")
                schedule = requested_vocabulary[list_id]
                existing_assignment.start_date = schedule.start_date
                existing_assignment.end_date = schedule.end_date
        else:
            # No existing assignment, create new one
            logger.info(f"No existing vocabulary assignment found, creating new one for {list_id}")
            schedule = requested_vocabulary[list_id]
            ca = ClassroomAssignment(
                classroom_id=classroom_id,
                vocabulary_list_id=list_id,
                assignment_type="vocabulary",
                display_order=display_order,
                start_date=schedule.start_date,
                end_date=schedule.end_date
            )
            db.add(ca)
            display_order += 1
    
    # Add new debate assignments
    for assignment_id in debate_to_add:
        # Verify debate assignment exists and belongs to teacher
        debate_result = await db.execute(
            select(DebateAssignment).where(
                and_(
                    DebateAssignment.id == assignment_id,
                    DebateAssignment.teacher_id == teacher.id,
                    DebateAssignment.deleted_at.is_(None)
                )
            )
        )
        debate_assignment = debate_result.scalar_one_or_none()
        if not debate_assignment:
            logger.warning(f"Debate assignment {assignment_id} not found or archived, skipping")
            continue
        
        # Check if debate assignment already exists for this classroom (including soft-deleted)
        existing_result = await db.execute(
            select(ClassroomAssignment).where(
                and_(
                    ClassroomAssignment.classroom_id == classroom_id,
                    ClassroomAssignment.assignment_id == assignment_id,
                    ClassroomAssignment.assignment_type == "debate"
                )
            )
        )
        existing_assignment = existing_result.scalar_one_or_none()
        
        if existing_assignment:
            if existing_assignment.removed_from_classroom_at:
                # Reactivate the soft-deleted assignment
                logger.info(f"Reactivating soft-deleted debate assignment {assignment_id}")
                schedule = requested_debate[assignment_id]
                existing_assignment.removed_from_classroom_at = None
                existing_assignment.removed_by = None
                existing_assignment.start_date = schedule.start_date
                existing_assignment.end_date = schedule.end_date
                existing_assignment.display_order = display_order
                display_order += 1
            else:
                # Assignment is already active, just update dates if needed
                logger.info(f"Active debate assignment already exists for {assignment_id}, updating dates")
                schedule = requested_debate[assignment_id]
                existing_assignment.start_date = schedule.start_date
                existing_assignment.end_date = schedule.end_date
        else:
            # No existing assignment, create new one
            logger.info(f"No existing debate assignment found, creating new one for {assignment_id}")
            schedule = requested_debate[assignment_id]
            ca = ClassroomAssignment(
                classroom_id=classroom_id,
                assignment_id=assignment_id,
                assignment_type="debate",
                display_order=display_order,
                start_date=schedule.start_date,
                end_date=schedule.end_date
            )
            db.add(ca)
            display_order += 1
    
    # Add new writing assignments
    for assignment_id in writing_to_add:
        # Verify writing assignment exists and belongs to teacher
        writing_result = await db.execute(
            select(WritingAssignment).where(
                and_(
                    WritingAssignment.id == assignment_id,
                    WritingAssignment.teacher_id == teacher.id,
                    WritingAssignment.deleted_at.is_(None)
                )
            )
        )
        writing_assignment = writing_result.scalar_one_or_none()
        if not writing_assignment:
            logger.warning(f"Writing assignment {assignment_id} not found or archived, skipping")
            continue
        
        # Check if writing assignment already exists for this classroom (including soft-deleted)
        existing_result = await db.execute(
            select(ClassroomAssignment).where(
                and_(
                    ClassroomAssignment.classroom_id == classroom_id,
                    ClassroomAssignment.assignment_id == assignment_id,
                    ClassroomAssignment.assignment_type == "writing"
                )
            )
        )
        existing_assignment = existing_result.scalar_one_or_none()
        
        if existing_assignment:
            if existing_assignment.removed_from_classroom_at:
                # Reactivate the soft-deleted assignment
                logger.info(f"Reactivating soft-deleted writing assignment {assignment_id}")
                schedule = requested_writing[assignment_id]
                existing_assignment.removed_from_classroom_at = None
                existing_assignment.removed_by = None
                existing_assignment.start_date = schedule.start_date
                existing_assignment.end_date = schedule.end_date
                existing_assignment.display_order = display_order
                display_order += 1
            else:
                # Assignment is already active, just update dates if needed
                logger.info(f"Active writing assignment already exists for {assignment_id}, updating dates")
                schedule = requested_writing[assignment_id]
                existing_assignment.start_date = schedule.start_date
                existing_assignment.end_date = schedule.end_date
        else:
            # No existing assignment, create new one
            logger.info(f"No existing writing assignment found, creating new one for {assignment_id}")
            schedule = requested_writing[assignment_id]
            ca = ClassroomAssignment(
                classroom_id=classroom_id,
                assignment_id=assignment_id,
                assignment_type="writing",
                display_order=display_order,
                start_date=schedule.start_date,
                end_date=schedule.end_date
            )
            db.add(ca)
            display_order += 1
    
    # Add new UMALecture assignments
    for assignment_id in lecture_to_add:
        # Verify UMALecture assignment exists and belongs to teacher
        lecture_result = await db.execute(
            select(UMALectureAssignment).where(
                and_(
                    UMALectureAssignment.id == assignment_id,
                    UMALectureAssignment.teacher_id == teacher.id,
                    UMALectureAssignment.assignment_type == "UMALecture",
                    UMALectureAssignment.deleted_at.is_(None)
                )
            )
        )
        lecture_assignment = lecture_result.scalar_one_or_none()
        if not lecture_assignment:
            logger.warning(f"UMALecture assignment {assignment_id} not found or archived, skipping")
            continue
        
        # Check if UMALecture assignment already exists for this classroom (including soft-deleted)
        existing_result = await db.execute(
            select(ClassroomAssignment).where(
                and_(
                    ClassroomAssignment.classroom_id == classroom_id,
                    ClassroomAssignment.assignment_id == assignment_id,
                    ClassroomAssignment.assignment_type == "UMALecture"
                )
            )
        )
        existing_assignment = existing_result.scalar_one_or_none()
        
        if existing_assignment:
            if existing_assignment.removed_from_classroom_at:
                # Reactivate the soft-deleted assignment
                logger.info(f"Reactivating soft-deleted UMALecture assignment {assignment_id}")
                schedule = requested_lecture[assignment_id]
                existing_assignment.removed_from_classroom_at = None
                existing_assignment.removed_by = None
                existing_assignment.start_date = schedule.start_date
                existing_assignment.end_date = schedule.end_date
                existing_assignment.display_order = display_order
                display_order += 1
            else:
                # Assignment is already active, just update dates if needed
                logger.info(f"Active UMALecture assignment already exists for {assignment_id}, updating dates")
                schedule = requested_lecture[assignment_id]
                existing_assignment.start_date = schedule.start_date
                existing_assignment.end_date = schedule.end_date
        else:
            # No existing assignment, create new one
            logger.info(f"No existing UMALecture assignment found, creating new one for {assignment_id}")
            schedule = requested_lecture[assignment_id]
            ca = ClassroomAssignment(
                classroom_id=classroom_id,
                assignment_id=assignment_id,
                assignment_type="UMALecture",
                display_order=display_order,
                start_date=schedule.start_date,
                end_date=schedule.end_date
            )
            db.add(ca)
            display_order += 1
    
    # Add new test assignments
    for assignment_id in test_to_add:
        # Verify test assignment exists and belongs to teacher
        test_result = await db.execute(
            select(TestAssignment).where(
                and_(
                    TestAssignment.id == assignment_id,
                    TestAssignment.teacher_id == teacher.id,
                    TestAssignment.status == "published",
                    TestAssignment.deleted_at.is_(None)
                )
            )
        )
        test_assignment = test_result.scalar_one_or_none()
        if not test_assignment:
            logger.warning(f"Test assignment {assignment_id} not found or archived, skipping")
            continue
        
        # Check if test assignment already exists for this classroom (including soft-deleted)
        existing_result = await db.execute(
            select(ClassroomAssignment).where(
                and_(
                    ClassroomAssignment.classroom_id == classroom_id,
                    ClassroomAssignment.assignment_id == assignment_id,
                    ClassroomAssignment.assignment_type == "test"
                )
            )
        )
        existing_assignment = existing_result.scalar_one_or_none()
        
        if existing_assignment:
            if existing_assignment.removed_from_classroom_at:
                # Reactivate the soft-deleted assignment
                logger.info(f"Reactivating soft-deleted test assignment {assignment_id}")
                schedule = requested_test[assignment_id]
                existing_assignment.removed_from_classroom_at = None
                existing_assignment.removed_by = None
                existing_assignment.start_date = schedule.start_date
                existing_assignment.end_date = schedule.end_date
                existing_assignment.display_order = display_order
                display_order += 1
            else:
                # Assignment is already active, just update dates if needed
                logger.info(f"Active test assignment already exists for {assignment_id}, updating dates")
                schedule = requested_test[assignment_id]
                existing_assignment.start_date = schedule.start_date
                existing_assignment.end_date = schedule.end_date
        else:
            # No existing assignment, create new one
            logger.info(f"No existing test assignment found, creating new one for {assignment_id}")
            schedule = requested_test[assignment_id]
            ca = ClassroomAssignment(
                classroom_id=classroom_id,
                assignment_id=assignment_id,
                assignment_type="test",
                display_order=display_order,
                start_date=schedule.start_date,
                end_date=schedule.end_date
            )
            db.add(ca)
            display_order += 1
    
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        logger.error(f"IntegrityError in update_all_classroom_assignments: {str(e)}")
        if "_classroom_reading_assignment_uc" in str(e) or "_classroom_vocab_assignment_uc" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="One or more assignments are already assigned to this classroom"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Database constraint violation"
        )
    except Exception as e:
        await db.rollback()
        logger.error(f"Unexpected error in update_all_classroom_assignments: {str(e)}", exc_info=True)
        
        # Check for specific foreign key violations
        if "student_debates_classroom_assignment_id_fkey" in str(e):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot remove debate assignment: students have active debates. Please have students complete or abandon their debates first."
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update assignments: {str(e)}"
        )
    
    total_added = len(reading_to_add) + len(vocabulary_to_add) + len(debate_to_add) + len(writing_to_add) + len(lecture_to_add) + len(test_to_add)
    total_removed = len(reading_to_remove) + len(vocabulary_to_remove) + len(debate_to_remove) + len(writing_to_remove) + len(lecture_to_remove) + len(test_to_remove)
    
    logger.info(f"Assignment update completed for classroom {classroom_id}")
    logger.info(f"Added: {total_added} assignments - {list(reading_to_add)} reading, {list(vocabulary_to_add)} vocabulary")
    logger.info(f"Removed: {total_removed} assignments")
    logger.info(f"Total now assigned: {len(requested_reading) + len(requested_vocabulary) + len(requested_debate) + len(requested_writing) + len(requested_lecture) + len(requested_test)}")
    
    return UpdateClassroomAssignmentsResponse(
        added=[str(id) for id in list(reading_to_add) + list(vocabulary_to_add) + list(debate_to_add) + list(writing_to_add) + list(lecture_to_add) + list(test_to_add)],
        removed=[str(id) for id in list(reading_to_remove) + list(vocabulary_to_remove) + list(debate_to_remove) + list(writing_to_remove) + list(lecture_to_remove) + list(test_to_remove)],
        total=len(requested_reading) + len(requested_vocabulary) + len(requested_debate) + len(requested_writing) + len(requested_lecture) + len(requested_test),
        students_affected=students_affected
    )
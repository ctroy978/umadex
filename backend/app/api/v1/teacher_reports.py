"""
Teacher reports endpoints including bypass code usage
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
from decimal import Decimal
from sqlalchemy import select, and_, func, desc, or_, text, union_all
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from fastapi import APIRouter, Depends, HTTPException, status, Query, Response
from pydantic import BaseModel
import csv
import io
import json

from app.core.database import get_db
from app.utils.deps import get_current_user
from app.models.user import User, UserRole
from app.models.classroom import StudentEvent, Classroom, ClassroomStudent, ClassroomAssignment, StudentAssignment
from app.models.reading import ReadingAssignment
from app.models.tests import StudentTestAttempt
from app.models.vocabulary import VocabularyList
from app.models.debate import DebateAssignment, StudentDebate
from app.models.writing import WritingAssignment, StudentWritingSubmission
from app.models.umatest import TestAssignment
from app.models.vocabulary_test import VocabularyTestAttempt
from app.models.vocabulary_practice import VocabularyPracticeProgress, VocabularyStoryResponse, VocabularyConceptMap
from app.models.umaread import UmareadStudentResponse
from app.models.debate import DebatePost, DebateChallenge
from app.models.tests import TestQuestionEvaluation

router = APIRouter()


class BypassUsageItem(BaseModel):
    student_id: UUID
    student_name: str
    student_email: str
    classroom_id: UUID
    classroom_name: str
    assignment_id: Optional[UUID]
    assignment_title: str
    chunk_number: int
    question_type: str
    timestamp: datetime
    success: bool


class MostBypassedAssignment(BaseModel):
    assignment_id: UUID
    assignment_title: str
    count: int


class DailyUsage(BaseModel):
    date: str
    successful: int
    failed: int


class BypassUsageSummary(BaseModel):
    total_uses: int
    unique_students: int
    unique_assignments: int
    success_rate: float
    most_bypassed_assignments: List[MostBypassedAssignment]


class BypassCodeReport(BaseModel):
    summary: BypassUsageSummary
    recent_usage: List[BypassUsageItem]
    usage_by_day: List[DailyUsage]


class StudentGrade(BaseModel):
    id: str
    student_id: UUID
    student_name: str
    assignment_id: UUID
    assignment_title: str
    assignment_type: str  # 'UMARead' or 'UMAVocab' or 'UMADebate' or 'UMAWrite' or 'UMATest'
    work_title: str
    date_assigned: datetime
    date_completed: Optional[datetime]
    test_date: Optional[datetime]
    test_score: Optional[float]
    difficulty_reached: Optional[int]
    time_spent: Optional[int]
    status: str


class GradebookSummary(BaseModel):
    total_students: int
    average_score: float
    completion_rate: float
    average_time: float
    class_average_by_assignment: Dict[str, float]


class GradebookResponse(BaseModel):
    grades: List[StudentGrade]
    summary: GradebookSummary
    total_count: int
    page: int
    page_size: int


def require_teacher(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be a teacher"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this resource"
        )
    return current_user


@router.get("/reports/bypass-code-usage", response_model=BypassCodeReport)
async def get_bypass_code_usage_report(
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
    days: int = Query(30, ge=1, le=90, description="Number of days to include in report")
):
    """Get bypass code usage report for the teacher's classrooms (rolling window)"""
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get all teacher's classrooms
    classrooms_result = await db.execute(
        select(Classroom.id, Classroom.name).where(
            and_(
                Classroom.teacher_id == teacher.id,
                Classroom.deleted_at.is_(None)
            )
        )
    )
    teacher_classrooms = {row[0]: row[1] for row in classrooms_result.fetchall()}
    
    if not teacher_classrooms:
        return BypassCodeReport(
            summary=BypassUsageSummary(
                total_uses=0,
                unique_students=0,
                unique_assignments=0,
                success_rate=0.0,
                most_bypassed_assignments=[]
            ),
            recent_usage=[],
            usage_by_day=[]
        )
    
    # Get bypass events for teacher's classrooms
    events_query = select(StudentEvent).where(
        and_(
            StudentEvent.classroom_id.in_(list(teacher_classrooms.keys())),
            StudentEvent.event_type.in_(["bypass_code_used", "bypass_code_failed"]),
            StudentEvent.created_at >= start_date
        )
    ).order_by(desc(StudentEvent.created_at))
    
    events_result = await db.execute(events_query)
    events = events_result.scalars().all()
    
    # Process events
    usage_items = []
    assignment_counts = {}
    unique_students = set()
    unique_assignments = set()
    successful_uses = 0
    total_uses = 0
    daily_usage = {}
    
    for event in events:
        total_uses += 1
        is_success = event.event_type == "bypass_code_used"
        if is_success:
            successful_uses += 1
        
        # Get student info (exclude soft deleted students)
        student_result = await db.execute(
            select(User).where(
                and_(
                    User.id == event.student_id,
                    User.deleted_at.is_(None)
                )
            )
        )
        student = student_result.scalar_one_or_none()
        
        if student:
            unique_students.add(event.student_id)
            
            # Get assignment info
            assignment_title = "Unknown Assignment"
            if event.assignment_id:
                unique_assignments.add(event.assignment_id)
                assignment_result = await db.execute(
                    select(ReadingAssignment.assignment_title).where(
                        ReadingAssignment.id == event.assignment_id
                    )
                )
                title = assignment_result.scalar()
                if title:
                    assignment_title = title
                    
                    # Count for most bypassed
                    if is_success:
                        if event.assignment_id not in assignment_counts:
                            assignment_counts[event.assignment_id] = MostBypassedAssignment(
                                assignment_id=event.assignment_id,
                                assignment_title=assignment_title,
                                count=0
                            )
                        assignment_counts[event.assignment_id].count += 1
            
            # Track daily usage
            day_key = event.created_at.date().isoformat()
            if day_key not in daily_usage:
                daily_usage[day_key] = DailyUsage(date=day_key, successful=0, failed=0)
            
            if is_success:
                daily_usage[day_key].successful += 1
            else:
                daily_usage[day_key].failed += 1
            
            # Add to recent usage (limit to 50 most recent)
            if len(usage_items) < 50:
                usage_items.append(BypassUsageItem(
                    student_id=event.student_id,
                    student_name=f"{student.first_name} {student.last_name}",
                    student_email=student.email,
                    classroom_id=event.classroom_id,
                    classroom_name=teacher_classrooms.get(event.classroom_id, "Unknown"),
                    assignment_id=event.assignment_id,
                    assignment_title=assignment_title,
                    chunk_number=(event.event_data or {}).get("chunk_number", 0),
                    question_type=(event.event_data or {}).get("question_type", "unknown"),
                    timestamp=event.created_at,
                    success=is_success
                ))
    
    # Calculate summary
    success_rate = (successful_uses / total_uses * 100) if total_uses > 0 else 0.0
    
    # Get top 5 most bypassed assignments
    most_bypassed = sorted(
        assignment_counts.values(), 
        key=lambda x: x.count, 
        reverse=True
    )[:5]
    
    # Prepare daily usage data
    daily_usage_list = sorted(daily_usage.values(), key=lambda x: x.date)
    
    return BypassCodeReport(
        summary=BypassUsageSummary(
            total_uses=total_uses,
            unique_students=len(unique_students),
            unique_assignments=len(unique_assignments),
            success_rate=round(success_rate, 1),
            most_bypassed_assignments=most_bypassed
        ),
        recent_usage=usage_items,
        usage_by_day=daily_usage_list
    )


@router.get("/reports/gradebook", response_model=GradebookResponse)
async def get_gradebook(
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
    classrooms: Optional[str] = Query(None, description="Comma-separated classroom IDs"),
    assignments: Optional[str] = Query(None, description="Comma-separated assignment IDs"),
    assignment_types: Optional[str] = Query(None, description="Comma-separated assignment types (UMARead,UMAVocab,UMADebate,UMAWrite,UMATest,UMALecture)"),
    assigned_after: Optional[datetime] = Query(None),
    assigned_before: Optional[datetime] = Query(None),
    completed_after: Optional[datetime] = Query(None),
    completed_before: Optional[datetime] = Query(None),
    student_search: Optional[str] = Query(None),
    completion_status: Optional[str] = Query("all", regex="^(all|completed|incomplete)$"),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    max_score: Optional[float] = Query(None, ge=0, le=100),
    difficulty_level: Optional[int] = Query(None, ge=1, le=8),
    sort_by: Optional[str] = Query("student_name"),
    sort_direction: Optional[str] = Query("asc", regex="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100)
):
    """Get gradebook data for teacher's classrooms (UMARead, UMAVocab, UMADebate, UMAWrite, and UMATest)"""
    
    # Parse filters
    classroom_ids = [UUID(cid) for cid in classrooms.split(',')] if classrooms else None
    assignment_ids = [UUID(aid) for aid in assignments.split(',')] if assignments else None
    type_filter = assignment_types.split(',') if assignment_types else ['UMARead', 'UMAVocab', 'UMADebate', 'UMAWrite', 'UMATest', 'UMALecture']
    
    # Get all teacher's classrooms if not specified
    if not classroom_ids:
        classrooms_query = select(Classroom.id).where(
            and_(
                Classroom.teacher_id == teacher.id,
                Classroom.deleted_at.is_(None)
            )
        )
        classrooms_result = await db.execute(classrooms_query)
        classroom_ids = [row[0] for row in classrooms_result.fetchall()]
    
    if not classroom_ids:
        # No classrooms found
        return GradebookResponse(
            grades=[],
            summary=GradebookSummary(
                total_students=0,
                average_score=0.0,
                completion_rate=0.0,
                average_time=0.0,
                class_average_by_assignment={}
            ),
            total_count=0,
            page=page,
            page_size=page_size
        )
    
    all_grades = []
    
    # Query 1: Get UMARead scores (existing logic)
    if 'UMARead' in type_filter:
        umaread_query = select(
            StudentAssignment,
            User,
            ClassroomAssignment,
            ReadingAssignment,
            Classroom,
            StudentTestAttempt
        ).join(
            User, StudentAssignment.student_id == User.id
        ).join(
            ClassroomAssignment, StudentAssignment.classroom_assignment_id == ClassroomAssignment.id
        ).join(
            ReadingAssignment, ClassroomAssignment.assignment_id == ReadingAssignment.id
        ).join(
            Classroom, ClassroomAssignment.classroom_id == Classroom.id
        ).outerjoin(
            StudentTestAttempt, 
            and_(
                StudentTestAttempt.student_id == StudentAssignment.student_id,
                StudentTestAttempt.assignment_id == StudentAssignment.assignment_id,
                StudentTestAttempt.status == 'graded'
            )
        ).where(
            and_(
                Classroom.id.in_(classroom_ids),
                Classroom.teacher_id == teacher.id,
                Classroom.deleted_at.is_(None),
                StudentAssignment.assignment_type == 'reading',
                ReadingAssignment.assignment_type == 'UMARead',
                User.deleted_at.is_(None)
            )
        )
        
        # Apply filters to UMARead query
        if assignment_ids:
            umaread_query = umaread_query.where(ReadingAssignment.id.in_(assignment_ids))
        if assigned_after:
            umaread_query = umaread_query.where(ClassroomAssignment.assigned_at >= assigned_after)
        if assigned_before:
            umaread_query = umaread_query.where(ClassroomAssignment.assigned_at <= assigned_before)
        if completed_after:
            umaread_query = umaread_query.where(StudentAssignment.completed_at >= completed_after)
        if completed_before:
            umaread_query = umaread_query.where(StudentAssignment.completed_at <= completed_before)
        if student_search:
            search_term = f"%{student_search}%"
            umaread_query = umaread_query.where(
                or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    func.concat(User.first_name, ' ', User.last_name).ilike(search_term)
                )
            )
        if completion_status == "completed":
            umaread_query = umaread_query.where(StudentTestAttempt.id.isnot(None))
        elif completion_status == "incomplete":
            umaread_query = umaread_query.where(StudentTestAttempt.id.is_(None))
        if min_score is not None:
            umaread_query = umaread_query.where(StudentTestAttempt.score >= min_score)
        if max_score is not None:
            umaread_query = umaread_query.where(StudentTestAttempt.score <= max_score)
        
        # Execute UMARead query
        result = await db.execute(umaread_query)
        umaread_rows = result.all()
        
        # Process UMARead results
        for row in umaread_rows:
            student_assignment = row.StudentAssignment
            student = row.User
            classroom_assignment = row.ClassroomAssignment
            assignment = row.ReadingAssignment
            test_attempt = row.StudentTestAttempt
            
            # Determine status
            if test_attempt and test_attempt.status == 'graded':
                status = 'completed'
            elif student_assignment.completed_at:
                status = 'test_available'
            elif student_assignment.started_at:
                status = 'in_progress'
            else:
                status = 'not_started'
            
            all_grades.append(StudentGrade(
                id=str(student_assignment.id),
                student_id=student.id,
                student_name=f"{student.last_name}, {student.first_name}",
                assignment_id=assignment.id,
                assignment_title=assignment.assignment_title,
                assignment_type='UMARead',
                work_title=assignment.work_title,
                date_assigned=classroom_assignment.assigned_at,
                date_completed=student_assignment.completed_at,
                test_date=test_attempt.submitted_at if test_attempt else None,
                test_score=float(test_attempt.score) if test_attempt and test_attempt.score else None,
                difficulty_reached=student_assignment.progress_metadata.get('highest_difficulty') if student_assignment.progress_metadata else None,
                time_spent=test_attempt.time_spent_seconds // 60 if test_attempt and test_attempt.time_spent_seconds else None,
                status=status
            ))
    
    # Query 2: Get UMAVocab scores from gradebook_entries
    if 'UMAVocab' in type_filter:
        # Build filters for SQL query
        # Build classroom IDs list
        classroom_id_list = ','.join([f"'{str(cid)}'" for cid in classroom_ids])
        
        filters = [
            f"rs.classroom_id IN ({classroom_id_list})",
            "u.deleted_at IS NULL"
        ]
        
        if assignment_ids:
            assignment_id_list = ','.join([f"'{str(aid)}'" for aid in assignment_ids])
            filters.append(f"rs.assignment_id IN ({assignment_id_list})")
        if completed_after:
            filters.append(f"rs.completed_at >= '{completed_after.isoformat()}'")
        if completed_before:
            filters.append(f"rs.completed_at <= '{completed_before.isoformat()}'")
        if student_search:
            search_term = student_search.replace("'", "''")  # Escape single quotes
            filters.append(
                f"(u.first_name ILIKE '%{search_term}%' OR "
                f"u.last_name ILIKE '%{search_term}%' OR "
                f"CONCAT(u.first_name, ' ', u.last_name) ILIKE '%{search_term}%')"
            )
        if completion_status == "completed":
            filters.append("rs.score_percentage IS NOT NULL")
        elif completion_status == "incomplete":
            filters.append("rs.score_percentage IS NULL")
        if min_score is not None:
            filters.append(f"rs.score_percentage >= {min_score}")
        if max_score is not None:
            filters.append(f"rs.score_percentage <= {max_score}")
        
        # Query gradebook_entries for vocabulary test scores - only highest score per student/assignment
        vocab_sql = f"""
            WITH ranked_scores AS (
                SELECT 
                    ge.id,
                    ge.student_id,
                    ge.assignment_id,
                    ge.classroom_id,
                    ge.score_percentage,
                    ge.completed_at,
                    ge.metadata,
                    ROW_NUMBER() OVER (
                        PARTITION BY ge.student_id, ge.assignment_id 
                        ORDER BY ge.score_percentage DESC, ge.completed_at DESC
                    ) as rn
                FROM gradebook_entries ge
                WHERE ge.assignment_type = 'umavocab_test'
            )
            SELECT 
                rs.id,
                rs.student_id,
                u.first_name,
                u.last_name,
                rs.assignment_id,
                vl.title as assignment_title,
                vl.context_description,
                ca.assigned_at,
                rs.completed_at,
                rs.score_percentage,
                rs.metadata,
                c.name as classroom_name
            FROM ranked_scores rs
            JOIN users u ON rs.student_id = u.id
            JOIN vocabulary_lists vl ON rs.assignment_id = vl.id
            JOIN classrooms c ON rs.classroom_id = c.id
            LEFT JOIN classroom_assignments ca ON ca.classroom_id = rs.classroom_id 
                AND ca.assignment_id = rs.assignment_id
                AND ca.assignment_type = 'vocabulary'
            WHERE rs.rn = 1 AND {' AND '.join(filters)}
        """
        
        vocab_result = await db.execute(text(vocab_sql))
        vocab_rows = vocab_result.fetchall()
        
        # Process UMAVocab results
        for row in vocab_rows:
            metadata = row.metadata or {}
            time_spent = metadata.get('time_spent_seconds', 0) // 60 if metadata.get('time_spent_seconds') else None
            
            all_grades.append(StudentGrade(
                id=str(row.id),
                student_id=row.student_id,
                student_name=f"{row.last_name}, {row.first_name}",
                assignment_id=row.assignment_id,
                assignment_title=row.assignment_title,
                assignment_type='UMAVocab',
                work_title=row.context_description[:50] + '...' if len(row.context_description) > 50 else row.context_description,
                date_assigned=row.assigned_at or row.completed_at,  # Use completed_at if assigned_at is null
                date_completed=row.completed_at,
                test_date=row.completed_at,
                test_score=float(row.score_percentage) if row.score_percentage else None,
                difficulty_reached=None,  # Not applicable for vocabulary
                time_spent=time_spent,
                status='completed' if row.score_percentage is not None else 'in_progress'
            ))
    
    # Query 3: Get UMADebate scores
    if 'UMADebate' in type_filter:
        debate_query = select(
            StudentDebate,
            User,
            ClassroomAssignment,
            DebateAssignment,
            Classroom
        ).join(
            User, StudentDebate.student_id == User.id
        ).join(
            ClassroomAssignment, StudentDebate.classroom_assignment_id == ClassroomAssignment.id
        ).join(
            DebateAssignment, StudentDebate.assignment_id == DebateAssignment.id
        ).join(
            Classroom, ClassroomAssignment.classroom_id == Classroom.id
        ).where(
            and_(
                Classroom.id.in_(classroom_ids),
                Classroom.teacher_id == teacher.id,
                Classroom.deleted_at.is_(None),
                ClassroomAssignment.assignment_type == 'debate',
                User.deleted_at.is_(None)
            )
        )
        
        # Apply filters to UMADebate query
        if assignment_ids:
            debate_query = debate_query.where(DebateAssignment.id.in_(assignment_ids))
        if assigned_after:
            debate_query = debate_query.where(ClassroomAssignment.assigned_at >= assigned_after)
        if assigned_before:
            debate_query = debate_query.where(ClassroomAssignment.assigned_at <= assigned_before)
        if completed_after:
            debate_query = debate_query.where(StudentDebate.updated_at >= completed_after)
        if completed_before:
            debate_query = debate_query.where(StudentDebate.updated_at <= completed_before)
        if student_search:
            search_term = f"%{student_search}%"
            debate_query = debate_query.where(
                or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    func.concat(User.first_name, ' ', User.last_name).ilike(search_term)
                )
            )
        if completion_status == "completed":
            debate_query = debate_query.where(StudentDebate.final_percentage.isnot(None))
        elif completion_status == "incomplete":
            debate_query = debate_query.where(StudentDebate.final_percentage.is_(None))
        if min_score is not None:
            debate_query = debate_query.where(StudentDebate.final_percentage >= min_score)
        if max_score is not None:
            debate_query = debate_query.where(StudentDebate.final_percentage <= max_score)
        
        # Execute UMADebate query
        debate_result = await db.execute(debate_query)
        debate_rows = debate_result.all()
        
        # Process UMADebate results
        for row in debate_rows:
            student_debate = row.StudentDebate
            student = row.User
            classroom_assignment = row.ClassroomAssignment
            assignment = row.DebateAssignment
            
            # Determine status based on student debate progress
            if student_debate.final_percentage is not None:
                status = 'completed'
                test_date = student_debate.updated_at
            elif student_debate.status == 'in_progress':
                status = 'in_progress'
                test_date = None
            else:
                status = 'not_started'
                test_date = None
            
            # Calculate time spent (approximate based on assignment started time)
            time_spent_minutes = None
            if student_debate.assignment_started_at and student_debate.final_percentage is not None:
                time_diff = student_debate.updated_at - student_debate.assignment_started_at
                time_spent_minutes = int(time_diff.total_seconds() / 60)
            
            all_grades.append(StudentGrade(
                id=str(student_debate.id),
                student_id=student.id,
                student_name=f"{student.last_name}, {student.first_name}",
                assignment_id=assignment.id,
                assignment_title=assignment.title,
                assignment_type='UMADebate',
                work_title=f"{assignment.grade_level} - {assignment.subject}",
                date_assigned=classroom_assignment.assigned_at,
                date_completed=student_debate.updated_at if student_debate.final_percentage is not None else None,
                test_date=test_date,
                test_score=float(student_debate.final_percentage) if student_debate.final_percentage else None,
                difficulty_reached=None,  # Not applicable for debates
                time_spent=time_spent_minutes,
                status=status
            ))
    
    # Query 4: Get UMAWrite scores
    if 'UMAWrite' in type_filter:
        write_query = select(
            StudentAssignment,
            User,
            ClassroomAssignment,
            WritingAssignment,
            Classroom,
            StudentWritingSubmission
        ).join(
            User, StudentAssignment.student_id == User.id
        ).join(
            ClassroomAssignment, StudentAssignment.classroom_assignment_id == ClassroomAssignment.id
        ).join(
            WritingAssignment, ClassroomAssignment.assignment_id == WritingAssignment.id
        ).join(
            Classroom, ClassroomAssignment.classroom_id == Classroom.id
        ).outerjoin(
            StudentWritingSubmission,
            and_(
                StudentWritingSubmission.student_assignment_id == StudentAssignment.id,
                StudentWritingSubmission.is_final_submission == True  # Only consider final submissions for scores
            )
        ).where(
            and_(
                Classroom.id.in_(classroom_ids),
                Classroom.teacher_id == teacher.id,
                Classroom.deleted_at.is_(None),
                StudentAssignment.assignment_type == 'writing',
                User.deleted_at.is_(None)
            )
        )
        
        # Apply filters to UMAWrite query
        if assignment_ids:
            write_query = write_query.where(WritingAssignment.id.in_(assignment_ids))
        if assigned_after:
            write_query = write_query.where(ClassroomAssignment.assigned_at >= assigned_after)
        if assigned_before:
            write_query = write_query.where(ClassroomAssignment.assigned_at <= assigned_before)
        if completed_after:
            write_query = write_query.where(StudentAssignment.completed_at >= completed_after)
        if completed_before:
            write_query = write_query.where(StudentAssignment.completed_at <= completed_before)
        if student_search:
            search_term = f"%{student_search}%"
            write_query = write_query.where(
                or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    func.concat(User.first_name, ' ', User.last_name).ilike(search_term)
                )
            )
        if completion_status == "completed":
            write_query = write_query.where(StudentWritingSubmission.id.isnot(None))
        elif completion_status == "incomplete":
            write_query = write_query.where(StudentWritingSubmission.id.is_(None))
        if min_score is not None:
            write_query = write_query.where(StudentWritingSubmission.score >= min_score)
        if max_score is not None:
            write_query = write_query.where(StudentWritingSubmission.score <= max_score)
        
        # Execute UMAWrite query
        write_result = await db.execute(write_query)
        write_rows = write_result.all()
        
        # Process UMAWrite results
        for row in write_rows:
            student_assignment = row.StudentAssignment
            student = row.User
            classroom_assignment = row.ClassroomAssignment
            assignment = row.WritingAssignment
            submission = row.StudentWritingSubmission
            
            # Determine status
            if submission and submission.score is not None:
                status = 'completed'
                test_date = submission.submitted_at
            elif submission:
                status = 'in_progress'  # Submitted but not yet evaluated
                test_date = None
            elif student_assignment.completed_at:
                status = 'test_available'  # Ready to submit final
            elif student_assignment.started_at:
                status = 'in_progress'
            else:
                status = 'not_started'
            
            # Calculate time spent (not available for writing assignments)
            time_spent_minutes = None
            
            all_grades.append(StudentGrade(
                id=str(submission.id) if submission else str(student_assignment.id),
                student_id=student.id,
                student_name=f"{student.last_name}, {student.first_name}",
                assignment_id=assignment.id,
                assignment_title=assignment.title,
                assignment_type='UMAWrite',
                work_title=f"{assignment.grade_level or 'All Grades'} - {assignment.subject or 'Writing'}",
                date_assigned=classroom_assignment.assigned_at,
                date_completed=submission.submitted_at if submission and submission.score is not None else None,
                test_date=submission.submitted_at if submission else None,
                test_score=float(submission.score) if submission and submission.score else None,
                difficulty_reached=None,  # Not applicable for writing
                time_spent=time_spent_minutes,
                status=status
            ))
    
    # Query 5: Get UMATest scores
    if 'UMATest' in type_filter:
        umatest_query = select(
            StudentTestAttempt,
            User,
            ClassroomAssignment,
            TestAssignment,
            Classroom
        ).join(
            User, StudentTestAttempt.student_id == User.id
        ).join(
            TestAssignment, StudentTestAttempt.test_id == TestAssignment.id
        ).join(
            ClassroomAssignment, StudentTestAttempt.classroom_assignment_id == ClassroomAssignment.id
        ).join(
            Classroom, ClassroomAssignment.classroom_id == Classroom.id
        ).where(
            and_(
                Classroom.id.in_(classroom_ids),
                Classroom.teacher_id == teacher.id,
                Classroom.deleted_at.is_(None),
                ClassroomAssignment.assignment_type == 'test',
                StudentTestAttempt.test_id.isnot(None),  # Only UMATest attempts (not UMARead)
                User.deleted_at.is_(None)
            )
        )
        
        # Apply filters to UMATest query
        if assignment_ids:
            umatest_query = umatest_query.where(TestAssignment.id.in_(assignment_ids))
        if assigned_after:
            umatest_query = umatest_query.where(ClassroomAssignment.assigned_at >= assigned_after)
        if assigned_before:
            umatest_query = umatest_query.where(ClassroomAssignment.assigned_at <= assigned_before)
        if completed_after:
            umatest_query = umatest_query.where(StudentTestAttempt.submitted_at >= completed_after)
        if completed_before:
            umatest_query = umatest_query.where(StudentTestAttempt.submitted_at <= completed_before)
        if student_search:
            search_term = f"%{student_search}%"
            umatest_query = umatest_query.where(
                or_(
                    User.first_name.ilike(search_term),
                    User.last_name.ilike(search_term),
                    func.concat(User.first_name, ' ', User.last_name).ilike(search_term)
                )
            )
        if completion_status == "completed":
            umatest_query = umatest_query.where(StudentTestAttempt.status == 'graded')
        elif completion_status == "incomplete":
            umatest_query = umatest_query.where(StudentTestAttempt.status != 'graded')
        if min_score is not None:
            umatest_query = umatest_query.where(StudentTestAttempt.score >= min_score)
        if max_score is not None:
            umatest_query = umatest_query.where(StudentTestAttempt.score <= max_score)
        
        # Execute UMATest query
        umatest_result = await db.execute(umatest_query)
        umatest_rows = umatest_result.all()
        
        # Process UMATest results - deduplicate by keeping only the best attempt per student/test
        umatest_attempts = {}  # Key: (student_id, test_id), Value: StudentGrade
        
        for row in umatest_rows:
            test_attempt = row.StudentTestAttempt
            student = row.User
            classroom_assignment = row.ClassroomAssignment
            assignment = row.TestAssignment
            
            # Determine status
            if test_attempt.status == 'graded' and test_attempt.score is not None:
                status = 'completed'
            elif test_attempt.status in ['submitted', 'completed']:
                status = 'in_progress'  # Awaiting grading
            elif test_attempt.status == 'in_progress':
                status = 'in_progress'
            else:
                status = 'not_started'
            
            grade = StudentGrade(
                id=str(test_attempt.id),
                student_id=student.id,
                student_name=f"{student.last_name}, {student.first_name}",
                assignment_id=assignment.id,
                assignment_title=assignment.test_title,
                assignment_type='UMATest',
                work_title=assignment.test_description or 'Comprehensive Test',
                date_assigned=classroom_assignment.assigned_at,
                date_completed=test_attempt.submitted_at if test_attempt.status == 'graded' else None,
                test_date=test_attempt.submitted_at,
                test_score=float(test_attempt.score) if test_attempt.score is not None else None,
                difficulty_reached=None,  # Not applicable for UMATest
                time_spent=test_attempt.time_spent_seconds // 60 if test_attempt.time_spent_seconds else None,
                status=status
            )
            
            # Key for deduplication
            key = (student.id, assignment.id)
            
            # Keep only the best attempt (highest score if graded, otherwise most recent)
            if key not in umatest_attempts:
                umatest_attempts[key] = grade
            else:
                existing = umatest_attempts[key]
                # Replace if: new score is higher, or both ungraded but new is more recent
                if (grade.test_score is not None and 
                    (existing.test_score is None or grade.test_score > existing.test_score)):
                    umatest_attempts[key] = grade
                elif (grade.test_score is None and existing.test_score is None and
                      grade.test_date and existing.test_date and 
                      grade.test_date > existing.test_date):
                    umatest_attempts[key] = grade
        
        # Add deduplicated UMATest grades to all_grades
        all_grades.extend(umatest_attempts.values())
    
    # Query 6: Get UMALecture scores from gradebook_entries
    if 'UMALecture' in type_filter:
        # Build filters for SQL query
        quoted_classroom_ids = ','.join([f"'{str(cid)}'" for cid in classroom_ids])
        lecture_filters = [f"ge.classroom_id IN ({quoted_classroom_ids})"]
        lecture_filters.append("ge.assignment_type = 'umalecture'")
        
        if assignment_ids:
            quoted_assignment_ids = ','.join([f"'{str(aid)}'" for aid in assignment_ids])
            lecture_filters.append(f"ge.assignment_id IN ({quoted_assignment_ids})")
        if assigned_after:
            lecture_filters.append(f"ca.assigned_at >= '{assigned_after.isoformat()}'")
        if assigned_before:
            lecture_filters.append(f"ca.assigned_at <= '{assigned_before.isoformat()}'")
        if completed_after:
            lecture_filters.append(f"ge.completed_at >= '{completed_after.isoformat()}'")
        if completed_before:
            lecture_filters.append(f"ge.completed_at <= '{completed_before.isoformat()}'")
        if student_search:
            lecture_filters.append(f"(LOWER(u.first_name) LIKE LOWER('%{student_search}%') OR LOWER(u.last_name) LIKE LOWER('%{student_search}%'))")
        if completion_status == 'completed':
            lecture_filters.append("ge.score_percentage IS NOT NULL")
        elif completion_status == 'incomplete':
            lecture_filters.append("ge.score_percentage IS NULL")
        if min_score is not None:
            lecture_filters.append(f"ge.score_percentage >= {min_score}")
        if max_score is not None:
            lecture_filters.append(f"ge.score_percentage <= {max_score}")
        
        # Query gradebook_entries for UMALecture scores
        lecture_sql = f"""
            SELECT 
                ge.id,
                ge.student_id,
                ge.assignment_id as lecture_id,
                ge.classroom_id,
                ge.score_percentage,
                ge.completed_at,
                ge.metadata,
                u.first_name,
                u.last_name,
                la.assignment_title,
                la.subject,
                la.grade_level,
                ca.assigned_at,
                c.name as classroom_name
            FROM gradebook_entries ge
            JOIN users u ON u.id = ge.student_id
            JOIN reading_assignments la ON la.id = ge.assignment_id
            JOIN classroom_assignments ca ON ca.assignment_id = ge.assignment_id 
                AND ca.classroom_id = ge.classroom_id 
                AND ca.assignment_type = 'UMALecture'
            JOIN classrooms c ON c.id = ge.classroom_id
            WHERE {' AND '.join(lecture_filters)}
            AND c.teacher_id = :teacher_id
            AND c.deleted_at IS NULL
            AND u.deleted_at IS NULL
        """
        
        lecture_result = await db.execute(text(lecture_sql), {"teacher_id": teacher.id})
        lecture_rows = lecture_result.fetchall()
        
        # Process UMALecture results
        for row in lecture_rows:
            metadata = row.metadata or {}
            
            all_grades.append(StudentGrade(
                id=str(row.id),
                student_id=row.student_id,
                student_name=f"{row.last_name}, {row.first_name}",
                assignment_id=row.lecture_id,
                assignment_title=row.assignment_title,
                assignment_type='UMALecture',
                work_title=f"{row.grade_level} - {row.subject}",
                date_assigned=row.assigned_at,
                date_completed=row.completed_at,
                test_date=row.completed_at,
                test_score=float(row.score_percentage) if row.score_percentage else None,
                difficulty_reached=None,  # Could extract from metadata if needed
                time_spent=metadata.get('time_spent_minutes'),
                status='completed' if row.score_percentage else 'in_progress'
            ))
    
    # Calculate summary statistics
    total_students = len(set(grade.student_id for grade in all_grades))
    scores = [grade.test_score for grade in all_grades if grade.test_score is not None]
    average_score = sum(scores) / len(scores) if scores else 0.0
    completion_rate = (len(scores) / len(all_grades) * 100) if all_grades else 0.0
    
    times = [grade.time_spent for grade in all_grades if grade.time_spent is not None]
    average_time = sum(times) / len(times) if times else 0.0
    
    # Calculate class averages by assignment
    assignment_scores: Dict[str, List[float]] = {}
    for grade in all_grades:
        if grade.test_score is not None:
            assignment_key = str(grade.assignment_id)
            if assignment_key not in assignment_scores:
                assignment_scores[assignment_key] = []
            assignment_scores[assignment_key].append(grade.test_score)
    
    class_average_by_assignment = {
        aid: sum(scores) / len(scores) 
        for aid, scores in assignment_scores.items()
    }
    
    # Apply sorting
    if sort_by == "student_name":
        all_grades.sort(key=lambda x: x.student_name, reverse=(sort_direction == "desc"))
    elif sort_by == "assignment_title":
        all_grades.sort(key=lambda x: x.assignment_title, reverse=(sort_direction == "desc"))
    elif sort_by == "assignment_type":
        all_grades.sort(key=lambda x: x.assignment_type, reverse=(sort_direction == "desc"))
    elif sort_by == "date_assigned":
        all_grades.sort(key=lambda x: x.date_assigned or datetime.min, reverse=(sort_direction == "desc"))
    elif sort_by == "test_date":
        all_grades.sort(key=lambda x: x.test_date or datetime.min, reverse=(sort_direction == "desc"))
    elif sort_by == "test_score":
        all_grades.sort(key=lambda x: x.test_score or -1, reverse=(sort_direction == "desc"))
    
    # Apply pagination
    start = (page - 1) * page_size
    end = start + page_size
    paginated_grades = all_grades[start:end]
    
    return GradebookResponse(
        grades=paginated_grades,
        summary=GradebookSummary(
            total_students=total_students,
            average_score=round(average_score, 1),
            completion_rate=round(completion_rate, 1),
            average_time=round(average_time, 1),
            class_average_by_assignment=class_average_by_assignment
        ),
        total_count=len(all_grades),
        page=page,
        page_size=page_size
    )


@router.get("/reports/gradebook/export")
async def export_gradebook(
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
    classrooms: Optional[str] = Query(None, description="Comma-separated classroom IDs"),
    assignments: Optional[str] = Query(None, description="Comma-separated assignment IDs"),
    assignment_types: Optional[str] = Query(None, description="Comma-separated assignment types (UMARead,UMAVocab,UMADebate,UMAWrite,UMATest,UMALecture)"),
    assigned_after: Optional[datetime] = Query(None),
    assigned_before: Optional[datetime] = Query(None),
    completed_after: Optional[datetime] = Query(None),
    completed_before: Optional[datetime] = Query(None),
    student_search: Optional[str] = Query(None),
    completion_status: Optional[str] = Query("all", regex="^(all|completed|incomplete)$"),
    min_score: Optional[float] = Query(None, ge=0, le=100),
    max_score: Optional[float] = Query(None, ge=0, le=100),
    difficulty_level: Optional[int] = Query(None, ge=1, le=8),
    format: str = Query("csv", regex="^(csv|pdf)$")
):
    """Export gradebook data as CSV or PDF"""
    
    if format == "pdf":
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="PDF export not yet implemented"
        )
    
    # Get all gradebook data (no pagination for export)
    gradebook_data = await get_gradebook(
        teacher=teacher,
        db=db,
        classrooms=classrooms,
        assignments=assignments,
        assignment_types=assignment_types,
        assigned_after=assigned_after,
        assigned_before=assigned_before,
        completed_after=completed_after,
        completed_before=completed_before,
        student_search=student_search,
        completion_status=completion_status,
        min_score=min_score,
        max_score=max_score,
        difficulty_level=difficulty_level,
        page=1,
        page_size=10000  # Get all records
    )
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write headers
    writer.writerow([
        'Student Name',
        'Assignment Title',
        'Assignment Type',
        'Work Title',
        'Date Assigned',
        'Date Completed',
        'Test Date',
        'Test Score (%)',
        'Time Spent (min)',
        'Status'
    ])
    
    # Write data
    for grade in gradebook_data.grades:
        writer.writerow([
            grade.student_name,
            grade.assignment_title,
            grade.assignment_type,
            grade.work_title,
            grade.date_assigned.strftime('%Y-%m-%d') if grade.date_assigned else '',
            grade.date_completed.strftime('%Y-%m-%d') if grade.date_completed else '',
            grade.test_date.strftime('%Y-%m-%d') if grade.test_date else '',
            f"{grade.test_score:.1f}" if grade.test_score is not None else '',
            str(grade.time_spent) if grade.time_spent is not None else '',
            grade.status
        ])
    
    # Add summary row
    writer.writerow([])
    writer.writerow(['Summary Statistics'])
    writer.writerow(['Total Students:', gradebook_data.summary.total_students])
    writer.writerow(['Average Score:', f"{gradebook_data.summary.average_score:.1f}%"])
    writer.writerow(['Completion Rate:', f"{gradebook_data.summary.completion_rate:.1f}%"])
    writer.writerow(['Average Time:', f"{gradebook_data.summary.average_time:.1f} min"])
    
    # Return CSV response
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type='text/csv',
        headers={
            'Content-Disposition': f'attachment; filename=gradebook_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
        }
    )


@router.get("/reports/gradebook/student/{student_id}/details")
async def get_student_gradebook_details(
    student_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
    assignment_id: Optional[UUID] = Query(None)
):
    """Get detailed breakdown for an individual student's assignment"""
    
    # Verify the student is in one of the teacher's classrooms and is active
    student_in_classroom = await db.execute(
        select(ClassroomStudent).join(
            Classroom, ClassroomStudent.classroom_id == Classroom.id
        ).join(
            User, ClassroomStudent.student_id == User.id
        ).where(
            and_(
                ClassroomStudent.student_id == student_id,
                Classroom.teacher_id == teacher.id,
                Classroom.deleted_at.is_(None),
                User.deleted_at.is_(None)  # Exclude soft deleted students
            )
        )
    )
    
    if not student_in_classroom.scalar():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Student not found in your classrooms"
        )
    
    # Build query for detailed information
    query = select(
        StudentAssignment,
        StudentTestAttempt,
        ReadingAssignment
    ).join(
        ReadingAssignment, StudentAssignment.assignment_id == ReadingAssignment.id
    ).outerjoin(
        StudentTestAttempt,
        and_(
            StudentTestAttempt.student_id == student_id,
            StudentTestAttempt.assignment_id == StudentAssignment.assignment_id
        )
    ).where(
        StudentAssignment.student_id == student_id
    )
    
    if assignment_id:
        query = query.where(StudentAssignment.assignment_id == assignment_id)
    
    result = await db.execute(query)
    rows = result.all()
    
    details = []
    for row in rows:
        student_assignment = row.StudentAssignment
        test_attempt = row.StudentTestAttempt
        assignment = row.ReadingAssignment
        
        # Get chunk-by-chunk breakdown if test was completed
        chunk_scores = []
        if test_attempt and test_attempt.feedback:
            for question_id, feedback in test_attempt.feedback.items():
                if isinstance(feedback, dict):
                    chunk_scores.append({
                        "chunk_number": feedback.get("chunk_number", 0),
                        "question_type": feedback.get("question_type", "unknown"),
                        "score": feedback.get("score", 0),
                        "feedback": feedback.get("feedback", "")
                    })
        
        details.append({
            "assignment_id": assignment.id,
            "assignment_title": assignment.assignment_title,
            "work_title": assignment.work_title,
            "status": student_assignment.status,
            "started_at": student_assignment.started_at,
            "completed_at": student_assignment.completed_at,
            "test_score": float(test_attempt.score) if test_attempt and test_attempt.score else None,
            "test_date": test_attempt.submitted_at if test_attempt else None,
            "time_spent_minutes": test_attempt.time_spent_seconds // 60 if test_attempt and test_attempt.time_spent_seconds else None,
            "chunk_scores": chunk_scores,
            "progress_metadata": student_assignment.progress_metadata
        })
    
    return {"student_id": student_id, "details": details}


@router.get("/students")
async def get_teacher_students(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all students in teacher's classrooms"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this endpoint"
        )
    
    # Get all students in teacher's classrooms
    query = select(
        User.id,
        User.first_name,
        User.last_name,
        User.email
    ).distinct().join(
        ClassroomStudent, User.id == ClassroomStudent.student_id
    ).join(
        Classroom, ClassroomStudent.classroom_id == Classroom.id
    ).where(
        and_(
            Classroom.teacher_id == current_user.id,
            ClassroomStudent.removed_at.is_(None),
            User.deleted_at.is_(None)
        )
    ).order_by(User.last_name, User.first_name)
    
    result = await db.execute(query)
    students = result.all()
    
    return [
        {
            "id": student.id,
            "first_name": student.first_name,
            "last_name": student.last_name,
            "email": student.email
        }
        for student in students
    ]


@router.get("/student-analytics/{student_id}")
async def get_student_analytics(
    student_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get comprehensive analytics data for a specific student"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this endpoint"
        )
    
    # Verify teacher has access to this student
    student_access = await db.execute(
        select(ClassroomStudent).join(
            Classroom, ClassroomStudent.classroom_id == Classroom.id
        ).where(
            and_(
                Classroom.teacher_id == current_user.id,
                ClassroomStudent.student_id == student_id,
                ClassroomStudent.removed_at.is_(None)
            )
        )
    )
    
    if not student_access.scalar():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this student's data"
        )
    
    # Get student info
    student = await db.get(User, student_id)
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    try:
        # Fetch UMARead analytics
        umaread_data = await get_umaread_analytics(db, student_id)
        
        # Fetch UMAVocab analytics
        umavocab_data = await get_umavocab_analytics(db, student_id)
        
        # Fetch UMADebate analytics
        umadebate_data = await get_umadebate_analytics(db, student_id)
        
        # Fetch UMAWrite analytics
        umawrite_data = await get_umawrite_analytics(db, student_id)
        
        # Fetch UMATest analytics
        umatest_data = await get_umatest_analytics(db, student_id)
        
        # Check if student has any meaningful data
        has_data = (
            (umaread_data.get("assignmentsCompleted", 0) > 0) or
            (umavocab_data.get("listsCompleted", 0) > 0) or
            (umadebate_data.get("debatesCompleted", 0) > 0) or
            (umawrite_data.get("assignmentsCompleted", 0) > 0) or
            (umatest_data.get("testsCompleted", 0) > 0)
        )
        
        if not has_data:
            return {
                "student": {
                    "id": student.id,
                    "first_name": student.first_name,
                    "last_name": student.last_name,
                    "email": student.email
                },
                "insufficient_data": True,
                "message": "This student does not have enough activity data to generate a meaningful analysis report. The student needs to complete at least one assignment or assessment."
            }
        
        return {
            "student": {
                "id": student.id,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "email": student.email
            },
            "umaread": umaread_data,
            "umavocab": umavocab_data,
            "umadebate": umadebate_data,
            "umawrite": umawrite_data,
            "umatest": umatest_data
        }
    except (ZeroDivisionError, ValueError, AttributeError) as e:
        # Handle cases where calculations fail due to insufficient data
        return {
            "student": {
                "id": student.id,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "email": student.email
            },
            "insufficient_data": True,
            "message": "Unable to generate analytics due to insufficient or incomplete data for this student."
        }


async def get_umaread_analytics(db: AsyncSession, student_id: UUID) -> Dict[Any, Any]:
    """Get UMARead analytics for a student"""
    # Get assignments completed
    assignments_result = await db.execute(
        select(StudentAssignment).where(
            and_(
                StudentAssignment.student_id == student_id,
                StudentAssignment.assignment_type == 'reading',
                StudentAssignment.status.in_(['completed', 'test_completed'])
            )
        )
    )
    assignments = assignments_result.scalars().all()
    
    # Get detailed responses
    responses_result = await db.execute(
        select(UmareadStudentResponse).where(
            UmareadStudentResponse.student_id == student_id
        ).order_by(UmareadStudentResponse.created_at.desc())
    )
    responses = responses_result.scalars().all()
    
    # Get test attempts
    test_attempts_result = await db.execute(
        select(
            StudentTestAttempt,
            TestQuestionEvaluation
        ).outerjoin(
            TestQuestionEvaluation,
            TestQuestionEvaluation.test_attempt_id == StudentTestAttempt.id
        ).where(
            and_(
                StudentTestAttempt.student_id == student_id,
                StudentTestAttempt.assignment_id.is_not(None)
            )
        )
    )
    test_data = test_attempts_result.all()
    
    # Calculate aggregated metrics
    total_responses = len(responses)
    correct_responses = sum(1 for r in responses if r.is_correct)
    average_comprehension = round((correct_responses / total_responses * 100) if total_responses > 0 else 0)
    total_time_spent = round(sum(r.time_spent_seconds or 0 for r in responses) / 60)
    current_difficulty = max((r.difficulty_level or 3 for r in responses), default=3)
    
    # Analyze error patterns
    error_patterns = {}
    for response in responses:
        if not response.is_correct:
            key = f"{response.question_type}_level_{response.difficulty_level}"
            error_patterns[key] = error_patterns.get(key, 0) + 1
    
    # Analyze progression
    progression_data = []
    date_stats = {}
    for response in responses:
        date = response.created_at.date().isoformat()
        if date not in date_stats:
            date_stats[date] = {'total': 0, 'correct': 0}
        date_stats[date]['total'] += 1
        if response.is_correct:
            date_stats[date]['correct'] += 1
    
    for date, stats in date_stats.items():
        progression_data.append({
            'date': date,
            'accuracy': round((stats['correct'] / stats['total']) * 100)
        })
    
    return {
        "assignmentsCompleted": len(assignments),
        "averageComprehension": average_comprehension,
        "totalTimeSpent": total_time_spent,
        "currentDifficulty": current_difficulty,
        "responses": [
            {
                "assignment_id": r.assignment_id,
                "chunk_number": r.chunk_number,
                "question_type": r.question_type,
                "difficulty_level": r.difficulty_level,
                "is_correct": r.is_correct,
                "attempt_number": r.attempt_number,
                "time_spent_seconds": r.time_spent_seconds,
                "ai_feedback": r.ai_feedback,
                "occurred_at": r.created_at.isoformat()
            }
            for r in responses[:100]  # Limit to most recent 100
        ],
        "testAttempts": [
            {
                "assignment_id": ta.StudentTestAttempt.assignment_id,
                "score": float(ta.StudentTestAttempt.score) if ta.StudentTestAttempt.score else None,
                "time_spent_seconds": ta.StudentTestAttempt.time_spent_seconds,
                "completed_at": ta.StudentTestAttempt.submitted_at.isoformat() if ta.StudentTestAttempt.submitted_at else None,
                "question_number": ta.TestQuestionEvaluation.question_number if ta.TestQuestionEvaluation else None,
                "rubric_score": ta.TestQuestionEvaluation.rubric_score if ta.TestQuestionEvaluation else None,
                "scoring_rationale": ta.TestQuestionEvaluation.scoring_rationale if ta.TestQuestionEvaluation else None,
                "key_concepts_identified": ta.TestQuestionEvaluation.key_concepts_identified if ta.TestQuestionEvaluation else None,
                "misconceptions_detected": ta.TestQuestionEvaluation.misconceptions_detected if ta.TestQuestionEvaluation else None
            }
            for ta in test_data
        ],
        "errorPatterns": error_patterns,
        "progressionData": progression_data
    }


async def get_umavocab_analytics(db: AsyncSession, student_id: UUID) -> Dict[Any, Any]:
    """Get UMAVocab analytics for a student"""
    # Get vocabulary test attempts
    test_attempts_result = await db.execute(
        select(VocabularyTestAttempt).where(
            VocabularyTestAttempt.student_id == student_id
        )
    )
    test_attempts = test_attempts_result.scalars().all()
    
    # Get practice progress
    practice_result = await db.execute(
        select(VocabularyPracticeProgress).where(
            VocabularyPracticeProgress.student_id == student_id
        )
    )
    practice_progress = practice_result.scalars().all()
    
    # Get story responses
    story_result = await db.execute(
        select(VocabularyStoryResponse).where(
            VocabularyStoryResponse.student_id == student_id
        )
    )
    story_responses = story_result.scalars().all()
    
    # Get concept maps
    concept_result = await db.execute(
        select(VocabularyConceptMap).where(
            VocabularyConceptMap.student_id == student_id
        )
    )
    concept_maps = concept_result.scalars().all()
    
    # Calculate metrics
    lists_completed = len(set(t.test_id for t in test_attempts))
    average_test_score = round(sum(t.score_percentage for t in test_attempts) / len(test_attempts)) if test_attempts else 0
    
    # Count practice activities completed
    practice_activities_completed = 0
    for progress in practice_progress:
        if progress.practice_status:
            # Handle both dict and string types
            if isinstance(progress.practice_status, str):
                try:
                    practice_data = json.loads(progress.practice_status)
                except:
                    continue
            else:
                practice_data = progress.practice_status
            
            assignments = practice_data.get('assignments', {})
            practice_activities_completed += sum(
                1 for a in assignments.values() 
                if isinstance(a, dict) and a.get('status') == 'completed'
            )
    
    words_mastered = sum(1 for c in concept_maps if c.word_score >= 3.5)
    
    # Identify problem words
    problem_words = {}
    for attempt in test_attempts:
        if attempt.responses:
            # Handle both dict and string types
            if isinstance(attempt.responses, str):
                try:
                    responses_data = json.loads(attempt.responses)
                except:
                    continue
            else:
                responses_data = attempt.responses
                
            for word_id, response in responses_data.items():
                if isinstance(response, dict) and not response.get('correct'):
                    problem_words[word_id] = problem_words.get(word_id, 0) + 1
    
    problem_words_list = sorted(
        [{'wordId': k, 'errorCount': v} for k, v in problem_words.items()],
        key=lambda x: x['errorCount'],
        reverse=True
    )[:10]
    
    return {
        "listsCompleted": lists_completed,
        "averageTestScore": average_test_score,
        "practiceActivitiesCompleted": practice_activities_completed,
        "wordsMastered": words_mastered,
        "testAttempts": [
            {
                "test_id": t.test_id,
                "score_percentage": float(t.score_percentage),
                "questions_correct": t.questions_correct,
                "total_questions": t.total_questions,
                "time_spent_seconds": t.time_spent_seconds,
                "completed_at": t.completed_at.isoformat() if t.completed_at else None,
                "responses": t.responses
            }
            for t in test_attempts[:50]
        ],
        "practiceProgress": [
            {
                "vocabulary_list_id": p.vocabulary_list_id,
                "practice_status": p.practice_status,
                "updated_at": p.updated_at.isoformat()
            }
            for p in practice_progress
        ],
        "storyResponses": [
            {
                "vocabulary_list_id": s.vocabulary_list_id,
                "total_score": s.total_score,
                "ai_evaluation": s.ai_evaluation,
                "submitted_at": s.submitted_at.isoformat()
            }
            for s in story_responses
        ],
        "conceptMaps": [
            {
                "word_id": c.word_id,
                "word_score": float(c.word_score),
                "ai_evaluation": c.ai_evaluation,
                "completed_at": c.completed_at.isoformat()
            }
            for c in concept_maps
        ],
        "problemWords": problem_words_list
    }


async def get_umadebate_analytics(db: AsyncSession, student_id: UUID) -> Dict[Any, Any]:
    """Get UMADebate analytics for a student"""
    # Get debate participation
    debates_result = await db.execute(
        select(StudentDebate).where(
            StudentDebate.student_id == student_id
        )
    )
    debates = debates_result.scalars().all()
    
    # Get debate posts
    posts_result = await db.execute(
        select(DebatePost).join(
            StudentDebate, DebatePost.student_debate_id == StudentDebate.id
        ).where(
            and_(
                StudentDebate.student_id == student_id,
                DebatePost.post_type == 'student'
            )
        )
    )
    posts = posts_result.scalars().all()
    
    # Get challenges
    challenges_result = await db.execute(
        select(DebateChallenge).where(
            DebateChallenge.student_id == student_id
        )
    )
    challenges = challenges_result.scalars().all()
    
    # Calculate metrics
    debates_completed = sum(1 for d in debates if d.status == 'completed')
    average_score = round(
        sum(d.final_percentage or 0 for d in debates if d.final_percentage) / 
        sum(1 for d in debates if d.final_percentage)
    ) if any(d.final_percentage for d in debates) else 0
    
    techniques_used = len(set(p.selected_technique for p in posts if p.selected_technique))
    fallacies_identified = sum(1 for c in challenges if c.challenge_type == 'fallacy' and c.is_correct)
    
    # Analyze score breakdown
    score_dimensions = ['clarity', 'evidence', 'logic', 'persuasiveness', 'rebuttal']
    score_breakdown = []
    for dimension in score_dimensions:
        scores = [getattr(p, f"{dimension}_score") for p in posts if getattr(p, f"{dimension}_score") is not None]
        if scores:
            score_breakdown.append({
                'dimension': dimension,
                'average': round(sum(scores) / len(scores), 1)
            })
    
    return {
        "debatesCompleted": debates_completed,
        "averageScore": average_score,
        "techniquesUsed": techniques_used,
        "fallaciesIdentified": fallacies_identified,
        "debates": [
            {
                "assignment_id": d.assignment_id,
                "status": d.status,
                "debate_1_percentage": float(d.debate_1_percentage) if d.debate_1_percentage else None,
                "debate_2_percentage": float(d.debate_2_percentage) if d.debate_2_percentage else None,
                "debate_3_percentage": float(d.debate_3_percentage) if d.debate_3_percentage else None,
                "final_percentage": float(d.final_percentage) if d.final_percentage else None,
                "fallacy_counter": d.fallacy_counter,
                "created_at": d.created_at.isoformat(),
                "updated_at": d.updated_at.isoformat()
            }
            for d in debates
        ],
        "posts": [
            {
                "debate_number": p.debate_number,
                "round_number": p.round_number,
                "clarity_score": float(p.clarity_score) if p.clarity_score else None,
                "evidence_score": float(p.evidence_score) if p.evidence_score else None,
                "logic_score": float(p.logic_score) if p.logic_score else None,
                "persuasiveness_score": float(p.persuasiveness_score) if p.persuasiveness_score else None,
                "rebuttal_score": float(p.rebuttal_score) if p.rebuttal_score else None,
                "final_percentage": float(p.final_percentage) if p.final_percentage else None,
                "selected_technique": p.selected_technique,
                "technique_bonus_awarded": float(p.technique_bonus_awarded) if p.technique_bonus_awarded else None,
                "ai_feedback": p.ai_feedback
            }
            for p in posts[:100]
        ],
        "challenges": [
            {
                "challenge_type": c.challenge_type,
                "is_correct": c.is_correct,
                "points_awarded": float(c.points_awarded)
            }
            for c in challenges
        ],
        "scoreBreakdown": score_breakdown
    }


async def get_umawrite_analytics(db: AsyncSession, student_id: UUID) -> Dict[Any, Any]:
    """Get UMAWrite analytics for a student"""
    # Get writing submissions
    submissions_result = await db.execute(
        select(StudentWritingSubmission).where(
            StudentWritingSubmission.student_id == student_id
        ).order_by(StudentWritingSubmission.submitted_at.desc())
    )
    submissions = submissions_result.scalars().all()
    
    # Calculate metrics
    assignments_completed = len(set(s.writing_assignment_id for s in submissions))
    scored_submissions = [s for s in submissions if s.score is not None]
    average_score = sum(s.score for s in scored_submissions) / len(scored_submissions) if scored_submissions else 0
    average_word_count = round(sum(s.word_count for s in submissions) / len(submissions)) if submissions else 0
    
    # Calculate improvement rate
    improvement_rate = 0
    assignments_by_id = {}
    for submission in submissions:
        if submission.writing_assignment_id not in assignments_by_id:
            assignments_by_id[submission.writing_assignment_id] = []
        assignments_by_id[submission.writing_assignment_id].append(submission)
    
    improvements = []
    for assignment_id, attempts in assignments_by_id.items():
        if len(attempts) >= 2:
            sorted_attempts = sorted(attempts, key=lambda x: x.submission_attempt)
            first_score = sorted_attempts[0].score or 0
            last_score = sorted_attempts[-1].score or 0
            if first_score > 0:
                improvement = ((last_score - first_score) / first_score) * 100
                improvements.append(improvement)
    
    if improvements:
        improvement_rate = round(sum(improvements) / len(improvements))
    
    # Analyze technique usage
    technique_usage = {}
    for submission in submissions:
        for technique in (submission.selected_techniques or []):
            technique_usage[technique] = technique_usage.get(technique, 0) + 1
    
    # Analyze feedback patterns
    feedback_patterns = []
    for submission in submissions:
        if submission.ai_feedback:
            if isinstance(submission.ai_feedback, dict):
                areas = submission.ai_feedback.get('areas_for_improvement', [])
                feedback_patterns.extend(areas)
    
    return {
        "assignmentsCompleted": assignments_completed,
        "averageScore": round(average_score, 1),
        "averageWordCount": average_word_count,
        "improvementRate": improvement_rate,
        "submissions": [
            {
                "writing_assignment_id": s.writing_assignment_id,
                "response_text": s.response_text,
                "selected_techniques": s.selected_techniques,
                "word_count": s.word_count,
                "submission_attempt": s.submission_attempt,
                "score": float(s.score) if s.score else None,
                "ai_feedback": s.ai_feedback,
                "submitted_at": s.submitted_at.isoformat()
            }
            for s in submissions[:50]
        ],
        "techniqueAnalysis": technique_usage,
        "feedbackPatterns": feedback_patterns[:20]  # Limit to 20 most recent
    }


async def get_umatest_analytics(db: AsyncSession, student_id: UUID) -> Dict[Any, Any]:
    """Get UMATest analytics for a student"""
    # Get test attempts
    test_attempts_result = await db.execute(
        select(
            StudentTestAttempt,
            TestQuestionEvaluation
        ).outerjoin(
            TestQuestionEvaluation,
            TestQuestionEvaluation.test_attempt_id == StudentTestAttempt.id
        ).where(
            and_(
                StudentTestAttempt.student_id == student_id,
                StudentTestAttempt.test_id.is_not(None)
            )
        )
    )
    test_data = test_attempts_result.all()
    
    # Group by test attempt
    attempts_dict = {}
    for row in test_data:
        attempt = row.StudentTestAttempt
        evaluation = row.TestQuestionEvaluation
        
        if attempt.id not in attempts_dict:
            attempts_dict[attempt.id] = {
                'attempt': attempt,
                'evaluations': []
            }
        
        if evaluation:
            attempts_dict[attempt.id]['evaluations'].append(evaluation)
    
    # Calculate metrics
    tests_completed = len(set(a['attempt'].test_id for a in attempts_dict.values()))
    scored_attempts = [a['attempt'] for a in attempts_dict.values() if a['attempt'].score is not None]
    average_score = round(sum(a.score for a in scored_attempts) / len(scored_attempts)) if scored_attempts else 0
    pass_rate = round((sum(1 for a in scored_attempts if a.score >= 70) / len(scored_attempts)) * 100) if scored_attempts else 0
    
    # Calculate average time per question
    total_time = 0
    total_questions = 0
    for data in attempts_dict.values():
        if data['attempt'].time_spent_seconds and data['evaluations']:
            total_time += data['attempt'].time_spent_seconds
            total_questions += len(data['evaluations'])
    
    avg_time_per_question = round(total_time / total_questions) if total_questions > 0 else 0
    
    # Analyze concept mastery
    concept_stats = {}
    all_misconceptions = []
    
    for data in attempts_dict.values():
        for evaluation in data['evaluations']:
            if evaluation.key_concepts_identified:
                for concept in evaluation.key_concepts_identified:
                    if concept not in concept_stats:
                        concept_stats[concept] = {'correct': 0, 'total': 0}
                    concept_stats[concept]['total'] += 1
                    if evaluation.rubric_score >= 3:
                        concept_stats[concept]['correct'] += 1
            
            if evaluation.misconceptions_detected:
                all_misconceptions.extend(evaluation.misconceptions_detected)
    
    concept_mastery = [
        {
            'concept': concept,
            'mastery': round((stats['correct'] / stats['total']) * 100)
        }
        for concept, stats in concept_stats.items()
    ]
    
    return {
        "testsCompleted": tests_completed,
        "averageScore": average_score,
        "passRate": pass_rate,
        "avgTimePerQuestion": avg_time_per_question,
        "testAttempts": [
            {
                "test_id": data['attempt'].test_id,
                "score": float(data['attempt'].score) if data['attempt'].score else None,
                "time_spent_seconds": data['attempt'].time_spent_seconds,
                "completed_at": data['attempt'].submitted_at.isoformat() if data['attempt'].submitted_at else None,
                "evaluations": [
                    {
                        "question_number": e.question_number,
                        "rubric_score": e.rubric_score,
                        "points_earned": float(e.points_earned),
                        "max_points": float(e.max_points),
                        "key_concepts_identified": e.key_concepts_identified,
                        "misconceptions_detected": e.misconceptions_detected,
                        "scoring_rationale": e.scoring_rationale
                    }
                    for e in data['evaluations']
                ]
            }
            for data in list(attempts_dict.values())[:20]  # Limit to 20 most recent
        ],
        "conceptMastery": concept_mastery,
        "misconceptions": list(set(all_misconceptions))[:50]  # Unique misconceptions, limited to 50
    }
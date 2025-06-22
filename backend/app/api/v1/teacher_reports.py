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

from app.core.database import get_db
from app.utils.deps import get_current_user
from app.models.user import User, UserRole
from app.models.classroom import StudentEvent, Classroom, ClassroomStudent, ClassroomAssignment, StudentAssignment
from app.models.reading import ReadingAssignment
from app.models.tests import StudentTestAttempt
from app.models.vocabulary import VocabularyList

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
    assignment_type: str  # 'UMARead' or 'UMAVocab'
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
    assignment_types: Optional[str] = Query(None, description="Comma-separated assignment types (UMARead,UMAVocab)"),
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
    """Get gradebook data for teacher's classrooms (UMARead and UMAVocab)"""
    
    # Parse filters
    classroom_ids = [UUID(cid) for cid in classrooms.split(',')] if classrooms else None
    assignment_ids = [UUID(aid) for aid in assignments.split(',')] if assignments else None
    type_filter = assignment_types.split(',') if assignment_types else ['UMARead', 'UMAVocab']
    
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
    assignment_types: Optional[str] = Query(None, description="Comma-separated assignment types (UMARead,UMAVocab)"),
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
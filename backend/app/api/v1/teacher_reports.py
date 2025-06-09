"""
Teacher reports endpoints including bypass code usage
"""
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
from decimal import Decimal
from sqlalchemy import select, and_, func, desc, or_
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

router = APIRouter()


class BypassUsageItem(BaseModel):
    student_id: UUID
    student_name: str
    student_email: str
    classroom_id: UUID
    classroom_name: str
    assignment_id: UUID
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
                    chunk_number=event.event_data.get("chunk_number", 0),
                    question_type=event.event_data.get("question_type", "unknown"),
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
    """Get gradebook data for teacher's classrooms"""
    
    # Base query to get all student assignments for teacher's classrooms
    query = select(
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
            Classroom.teacher_id == teacher.id,
            Classroom.deleted_at.is_(None),
            StudentAssignment.assignment_type == 'reading',
            ReadingAssignment.assignment_type == 'UMARead',
            User.deleted_at.is_(None)  # Exclude soft deleted students
        )
    )
    
    # Apply filters
    if classrooms:
        classroom_ids = [UUID(cid) for cid in classrooms.split(',')]
        query = query.where(Classroom.id.in_(classroom_ids))
    
    if assignments:
        assignment_ids = [UUID(aid) for aid in assignments.split(',')]
        query = query.where(ReadingAssignment.id.in_(assignment_ids))
    
    if assigned_after:
        query = query.where(ClassroomAssignment.assigned_at >= assigned_after)
    
    if assigned_before:
        query = query.where(ClassroomAssignment.assigned_at <= assigned_before)
    
    if completed_after:
        query = query.where(StudentAssignment.completed_at >= completed_after)
    
    if completed_before:
        query = query.where(StudentAssignment.completed_at <= completed_before)
    
    if student_search:
        search_term = f"%{student_search}%"
        query = query.where(
            or_(
                User.first_name.ilike(search_term),
                User.last_name.ilike(search_term),
                func.concat(User.first_name, ' ', User.last_name).ilike(search_term)
            )
        )
    
    if completion_status == "completed":
        query = query.where(StudentTestAttempt.id.isnot(None))
    elif completion_status == "incomplete":
        query = query.where(StudentTestAttempt.id.is_(None))
    
    if min_score is not None:
        query = query.where(StudentTestAttempt.score >= min_score)
    
    if max_score is not None:
        query = query.where(StudentTestAttempt.score <= max_score)
    
    # Execute query to get all results for summary statistics
    result = await db.execute(query)
    all_rows = result.all()
    
    # Calculate summary statistics
    total_students = len(set(row.User.id for row in all_rows))
    scores = [float(row.StudentTestAttempt.score) for row in all_rows if row.StudentTestAttempt and row.StudentTestAttempt.score]
    average_score = sum(scores) / len(scores) if scores else 0.0
    completion_rate = (len(scores) / len(all_rows) * 100) if all_rows else 0.0
    
    times = [row.StudentTestAttempt.time_spent_seconds / 60 for row in all_rows 
             if row.StudentTestAttempt and row.StudentTestAttempt.time_spent_seconds]
    average_time = sum(times) / len(times) if times else 0.0
    
    # Calculate class averages by assignment
    assignment_scores: Dict[str, List[float]] = {}
    for row in all_rows:
        if row.StudentTestAttempt and row.StudentTestAttempt.score:
            assignment_key = str(row.ReadingAssignment.id)
            if assignment_key not in assignment_scores:
                assignment_scores[assignment_key] = []
            assignment_scores[assignment_key].append(float(row.StudentTestAttempt.score))
    
    class_average_by_assignment = {
        aid: sum(scores) / len(scores) 
        for aid, scores in assignment_scores.items()
    }
    
    # Apply sorting
    if sort_by == "student_name":
        all_rows.sort(key=lambda x: f"{x.User.last_name} {x.User.first_name}", 
                     reverse=(sort_direction == "desc"))
    elif sort_by == "assignment_title":
        all_rows.sort(key=lambda x: x.ReadingAssignment.assignment_title, 
                     reverse=(sort_direction == "desc"))
    elif sort_by == "date_assigned":
        all_rows.sort(key=lambda x: x.ClassroomAssignment.assigned_at, 
                     reverse=(sort_direction == "desc"))
    elif sort_by == "test_date":
        all_rows.sort(key=lambda x: x.StudentTestAttempt.submitted_at if x.StudentTestAttempt else datetime.min, 
                     reverse=(sort_direction == "desc"))
    elif sort_by == "test_score":
        all_rows.sort(key=lambda x: float(x.StudentTestAttempt.score) if x.StudentTestAttempt and x.StudentTestAttempt.score else -1, 
                     reverse=(sort_direction == "desc"))
    
    # Apply pagination
    start = (page - 1) * page_size
    end = start + page_size
    paginated_rows = all_rows[start:end]
    
    # Format response
    grades = []
    for row in paginated_rows:
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
        
        grades.append(StudentGrade(
            id=str(student_assignment.id),
            student_id=student.id,
            student_name=f"{student.last_name}, {student.first_name}",
            assignment_id=assignment.id,
            assignment_title=assignment.assignment_title,
            work_title=assignment.work_title,
            date_assigned=classroom_assignment.assigned_at,
            date_completed=student_assignment.completed_at,
            test_date=test_attempt.submitted_at if test_attempt else None,
            test_score=float(test_attempt.score) if test_attempt and test_attempt.score else None,
            difficulty_reached=student_assignment.progress_metadata.get('highest_difficulty') if student_assignment.progress_metadata else None,
            time_spent=test_attempt.time_spent_seconds // 60 if test_attempt and test_attempt.time_spent_seconds else None,
            status=status
        ))
    
    return GradebookResponse(
        grades=grades,
        summary=GradebookSummary(
            total_students=total_students,
            average_score=round(average_score, 1),
            completion_rate=round(completion_rate, 1),
            average_time=round(average_time, 1),
            class_average_by_assignment=class_average_by_assignment
        ),
        total_count=len(all_rows),
        page=page,
        page_size=page_size
    )


@router.get("/reports/gradebook/export")
async def export_gradebook(
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
    classrooms: Optional[str] = Query(None, description="Comma-separated classroom IDs"),
    assignments: Optional[str] = Query(None, description="Comma-separated assignment IDs"),
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
"""
Teacher reports endpoints including bypass code usage
"""
from typing import List, Optional, Dict
from datetime import datetime, timedelta
from uuid import UUID
from sqlalchemy import select, and_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from app.core.database import get_db
from app.utils.deps import get_current_user
from app.models.user import User, UserRole
from app.models.classroom import StudentEvent, Classroom, ClassroomStudent
from app.models.reading import ReadingAssignment

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
        
        # Get student info
        student_result = await db.execute(
            select(User).where(User.id == event.student_id)
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
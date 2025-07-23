"""
Unified bypass code validation service for all UMA applications
"""
from typing import Optional, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
import bcrypt
import re

from app.models.user import User, UserRole
from app.models.tests import TeacherBypassCode
from app.models.classroom import Classroom, ClassroomStudent, ClassroomAssignment, StudentAssignment, StudentEvent


async def validate_bypass_code(
    db: AsyncSession,
    student_id: str,
    answer_text: str,
    context_type: str = "general",
    context_id: Optional[str] = None,
    assignment_id: Optional[str] = None
) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate bypass code from student answer.
    Returns: (is_bypass_valid, bypass_type, teacher_id)
    - bypass_type: "permanent" or "one-time"
    """
    
    # Check for permanent bypass code pattern (!BYPASS-XXXX)
    bypass_pattern = r'^!BYPASS-(\d{4})$'
    bypass_match = re.match(bypass_pattern, answer_text.upper())
    
    if bypass_match:
        # Extract the 4-digit code
        provided_code = bypass_match.group(1)
        
        # Check rate limiting - max 5 attempts per hour
        one_hour_ago = datetime.utcnow() - timedelta(hours=1)
        bypass_attempts_result = await db.execute(
            select(func.count(StudentEvent.id))
            .where(
                and_(
                    StudentEvent.student_id == student_id,
                    StudentEvent.event_type.in_(["bypass_code_used", "bypass_code_failed"]),
                    StudentEvent.created_at >= one_hour_ago
                )
            )
        )
        bypass_attempts = bypass_attempts_result.scalar() or 0
        
        if bypass_attempts >= 5:
            print(f"Rate limit exceeded for bypass attempts by student {student_id}")
            return False, "rate_limited", None
        
        # Find the teacher through assignment or classroom context
        teacher_id = await _find_teacher_for_context(db, student_id, assignment_id, context_id)
        
        print(f"DEBUG: Bypass validation - Student: {student_id}, Assignment: {assignment_id}, Found teacher: {teacher_id}")
        
        if teacher_id:
            # Get the teacher's bypass code
            teacher_result = await db.execute(
                select(User).where(User.id == teacher_id)
            )
            teacher = teacher_result.scalar_one_or_none()
            
            if teacher and teacher.bypass_code:
                # Verify the bypass code
                try:
                    bypass_valid = bcrypt.checkpw(
                        provided_code.encode('utf-8'),
                        teacher.bypass_code.encode('utf-8')
                    )
                    if bypass_valid:
                        await _log_bypass_usage(
                            db, student_id, teacher_id, "permanent", 
                            context_type, context_id, True
                        )
                        return True, "permanent", str(teacher_id)
                except Exception as e:
                    print(f"Error checking bypass code: {e}")
        
        # Log failed attempt
        await _log_bypass_usage(
            db, student_id, teacher_id, "permanent", 
            context_type, context_id, False
        )
        return False, None, None
    
    # Check for one-time bypass code (12 alphanumeric characters)
    one_time_pattern = r'^([A-Z0-9]{12})$'
    one_time_match = re.match(one_time_pattern, answer_text.upper())
    
    if one_time_match:
        provided_code = one_time_match.group(1)
        
        # Look for valid one-time code
        now = datetime.utcnow()
        code_result = await db.execute(
            select(TeacherBypassCode)
            .where(
                and_(
                    TeacherBypassCode.bypass_code == provided_code,
                    TeacherBypassCode.expires_at > now,
                    TeacherBypassCode.used_at.is_(None),
                    or_(
                        TeacherBypassCode.student_id == student_id,
                        TeacherBypassCode.student_id.is_(None)  # Code not tied to specific student
                    )
                )
            )
        )
        bypass_record = code_result.scalar_one_or_none()
        
        if bypass_record:
            # Mark as used
            bypass_record.used_at = now
            
            # Log usage
            await _log_bypass_usage(
                db, student_id, bypass_record.teacher_id, "one-time",
                context_type, context_id or bypass_record.context_id, True
            )
            
            await db.commit()
            return True, "one-time", str(bypass_record.teacher_id)
    
    return False, None, None


async def _find_teacher_for_context(
    db: AsyncSession,
    student_id: str,
    assignment_id: Optional[str],
    context_id: Optional[str]
) -> Optional[str]:
    """Find the relevant teacher for the given context"""
    
    print(f"DEBUG: Finding teacher - Student: {student_id}, Assignment: {assignment_id}, Context: {context_id}")
    
    if assignment_id:
        # Try to find teacher through student assignment
        student_assignment_result = await db.execute(
            select(StudentAssignment)
            .where(
                and_(
                    StudentAssignment.student_id == student_id,
                    StudentAssignment.assignment_id == assignment_id
                )
            )
        )
        student_assignment = student_assignment_result.scalar_one_or_none()
        
        print(f"DEBUG: Found student_assignment: {student_assignment is not None}, classroom_assignment_id: {student_assignment.classroom_assignment_id if student_assignment else 'N/A'}")
        
        if student_assignment and student_assignment.classroom_assignment_id:
            # Get classroom through classroom assignment
            classroom_assignment_result = await db.execute(
                select(ClassroomAssignment)
                .where(ClassroomAssignment.id == student_assignment.classroom_assignment_id)
            )
            classroom_assignment = classroom_assignment_result.scalar_one_or_none()
            
            if classroom_assignment:
                # Get teacher from classroom
                classroom_result = await db.execute(
                    select(Classroom).where(Classroom.id == classroom_assignment.classroom_id)
                )
                classroom = classroom_result.scalar_one_or_none()
                if classroom:
                    return classroom.teacher_id
        
        # Fallback: Try to find teacher directly from the assignment
        # This handles cases where students access assignments directly without classroom context
        from app.models.reading import ReadingAssignment
        from app.models.vocabulary import VocabularyList
        
        # Check if this is a reading assignment
        reading_assignment_result = await db.execute(
            select(ReadingAssignment).where(ReadingAssignment.id == assignment_id)
        )
        reading_assignment = reading_assignment_result.scalar_one_or_none()
        
        if reading_assignment:
            print(f"DEBUG: Found reading assignment with teacher_id: {reading_assignment.teacher_id}")
            return str(reading_assignment.teacher_id)
        
        # Check if this is a vocabulary list (for vocabulary tests)
        vocab_list_result = await db.execute(
            select(VocabularyList).where(VocabularyList.id == assignment_id)
        )
        vocab_list = vocab_list_result.scalar_one_or_none()
        
        if vocab_list:
            print(f"DEBUG: Found vocabulary list with teacher_id: {vocab_list.teacher_id}")
            return str(vocab_list.teacher_id)
    
    # If no assignment context, try to find through student's classrooms
    # This might need to be more specific based on context
    return None


async def _log_bypass_usage(
    db: AsyncSession,
    student_id: str,
    teacher_id: Optional[str],
    bypass_type: str,
    context_type: str,
    context_id: Optional[str],
    success: bool
):
    """Log bypass code usage attempt"""
    event_type = "bypass_code_used" if success else "bypass_code_failed"
    
    # Find classroom context if possible
    classroom_id = None
    if context_id and context_type == "test":
        # Try to find classroom through test attempt
        from app.models.tests import StudentTestAttempt
        attempt_result = await db.execute(
            select(StudentTestAttempt).where(StudentTestAttempt.id == context_id)
        )
        attempt = attempt_result.scalar_one_or_none()
        if attempt and attempt.assignment_id:
            # Find classroom through assignment
            sa_result = await db.execute(
                select(StudentAssignment).where(
                    and_(
                        StudentAssignment.student_id == student_id,
                        StudentAssignment.assignment_id == attempt.assignment_id
                    )
                )
            )
            sa = sa_result.scalar_one_or_none()
            if sa and sa.classroom_assignment_id:
                ca_result = await db.execute(
                    select(ClassroomAssignment).where(
                        ClassroomAssignment.id == sa.classroom_assignment_id
                    )
                )
                ca = ca_result.scalar_one_or_none()
                if ca:
                    classroom_id = ca.classroom_id
    
    event = StudentEvent(
        student_id=student_id,
        classroom_id=classroom_id,
        assignment_id=context_id if context_type == "assignment" else None,
        event_type=event_type,
        event_data={
            "bypass_type": bypass_type,
            "context_type": context_type,
            "context_id": str(context_id) if context_id else None,
            "teacher_id": str(teacher_id) if teacher_id else None
        }
    )
    db.add(event)
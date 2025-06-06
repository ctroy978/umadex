"""
Student test-taking API endpoints
"""
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.user import User
from app.models.tests import AssignmentTest, StudentTestAttempt, TestSecurityIncident
from app.models.reading import ReadingAssignment, ReadingChunk
from app.models.classroom import ClassroomAssignment, ClassroomStudent
from app.utils.deps import get_current_user
from app.services.bypass_validation import validate_bypass_code


router = APIRouter(prefix="/tests", tags=["student-tests"])


class TestStartResponse(BaseModel):
    test_id: UUID
    test_attempt_id: UUID
    assignment_id: UUID
    assignment_title: str
    total_questions: int
    time_limit_minutes: Optional[int]
    current_question: int
    status: str
    attempt_number: int
    saved_answers: Dict[str, str]


class SaveAnswerRequest(BaseModel):
    question_index: int
    answer: str
    time_spent_seconds: int = 0


class TestProgressResponse(BaseModel):
    current_question: int
    total_questions: int
    answered_questions: List[int]
    time_spent_seconds: int
    status: str
    saved_answers: Dict[str, str]


class ReadingContentResponse(BaseModel):
    chunks: List[Dict[str, Any]]
    total_chunks: int
    assignment_title: str


class TestQuestionsResponse(BaseModel):
    questions: List[Dict[str, Any]]
    total_questions: int


class SecurityIncidentRequest(BaseModel):
    incident_type: str = Field(..., pattern="^(focus_loss|tab_switch|navigation_attempt|window_blur|app_switch|orientation_cheat)$")
    incident_data: Optional[Dict[str, Any]] = None


class TestLockRequest(BaseModel):
    reason: str = Field(..., max_length=255)


class SecurityStatusResponse(BaseModel):
    violation_count: int
    is_locked: bool
    locked_at: Optional[datetime]
    locked_reason: Optional[str]
    warnings_given: int


@router.get("/{assignment_id}/start", response_model=TestStartResponse)
async def start_test(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Initialize or resume a test attempt for a reading assignment"""
    
    # Verify student has access to this assignment
    access_query = await db.execute(
        select(ClassroomAssignment, ReadingAssignment, AssignmentTest)
        .join(ReadingAssignment, 
              and_(
                  ClassroomAssignment.assignment_id == ReadingAssignment.id,
                  ClassroomAssignment.assignment_type == "reading"
              ))
        .join(AssignmentTest, AssignmentTest.assignment_id == ReadingAssignment.id)
        .join(ClassroomStudent,
              and_(
                  ClassroomStudent.classroom_id == ClassroomAssignment.classroom_id,
                  ClassroomStudent.student_id == current_user.id,
                  ClassroomStudent.removed_at.is_(None)
              ))
        .where(
            and_(
                ReadingAssignment.id == assignment_id,
                ReadingAssignment.deleted_at.is_(None),
                AssignmentTest.status == "approved"
            )
        )
    )
    
    result = access_query.first()
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found or you don't have access"
        )
    
    classroom_assignment, reading_assignment, assignment_test = result
    
    # Check if student has completed the reading assignment
    from app.models.umaread import UmareadAssignmentProgress
    progress_query = await db.execute(
        select(UmareadAssignmentProgress)
        .where(
            and_(
                UmareadAssignmentProgress.student_id == current_user.id,
                UmareadAssignmentProgress.assignment_id == assignment_id,
                UmareadAssignmentProgress.completed_at.isnot(None)
            )
        )
    )
    
    if not progress_query.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You must complete the reading assignment before taking the test"
        )
    
    # Get the latest attempt number
    attempt_query = await db.execute(
        select(func.coalesce(func.max(StudentTestAttempt.attempt_number), 0))
        .where(
            and_(
                StudentTestAttempt.student_id == current_user.id,
                StudentTestAttempt.assignment_test_id == assignment_test.id
            )
        )
    )
    last_attempt_number = attempt_query.scalar() or 0
    
    # Check for existing in-progress attempt
    existing_attempt = await db.execute(
        select(StudentTestAttempt)
        .where(
            and_(
                StudentTestAttempt.student_id == current_user.id,
                StudentTestAttempt.assignment_test_id == assignment_test.id,
                StudentTestAttempt.status == "in_progress"
            )
        )
        .order_by(StudentTestAttempt.created_at.desc())
    )
    test_attempt = existing_attempt.scalar_one_or_none()
    
    if not test_attempt:
        # Check if max attempts reached
        if assignment_test.max_attempts and last_attempt_number >= assignment_test.max_attempts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum attempts ({assignment_test.max_attempts}) reached for this test"
            )
        
        # Create new test attempt
        test_attempt = StudentTestAttempt(
            student_id=current_user.id,
            assignment_test_id=assignment_test.id,
            assignment_id=assignment_id,
            attempt_number=last_attempt_number + 1,
            current_question=1,
            answers_data={},
            status="in_progress"
        )
        db.add(test_attempt)
        await db.commit()
        await db.refresh(test_attempt)
    
    # Parse test questions
    test_questions = assignment_test.test_questions or []
    if isinstance(test_questions, list):
        total_questions = len(test_questions)
    elif isinstance(test_questions, dict) and 'questions' in test_questions:
        total_questions = len(test_questions['questions'])
    else:
        total_questions = 0
    
    return TestStartResponse(
        test_id=assignment_test.id,
        test_attempt_id=test_attempt.id,
        assignment_id=assignment_id,
        assignment_title=reading_assignment.assignment_title,
        total_questions=total_questions,
        time_limit_minutes=assignment_test.time_limit_minutes,
        current_question=test_attempt.current_question,
        status=test_attempt.status,
        attempt_number=test_attempt.attempt_number,
        saved_answers=test_attempt.answers_data or {}
    )


@router.post("/{test_id}/save-answer")
async def save_answer(
    test_id: UUID,
    request: SaveAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Auto-save answer as student types"""
    
    # Get the test attempt
    attempt_query = await db.execute(
        select(StudentTestAttempt)
        .join(AssignmentTest, AssignmentTest.id == StudentTestAttempt.assignment_test_id)
        .where(
            and_(
                StudentTestAttempt.student_id == current_user.id,
                StudentTestAttempt.assignment_test_id == test_id,
                StudentTestAttempt.status == "in_progress"
            )
        )
    )
    test_attempt = attempt_query.scalar_one_or_none()
    
    if not test_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active test attempt not found"
        )
    
    # Update the answer
    answers = test_attempt.answers_data or {}
    answers[str(request.question_index)] = request.answer
    
    # Update current question and time spent
    test_attempt.answers_data = answers
    test_attempt.current_question = request.question_index + 1  # Next question
    test_attempt.time_spent_seconds = (test_attempt.time_spent_seconds or 0) + request.time_spent_seconds
    
    await db.commit()
    
    return {"success": True, "message": "Answer saved"}


@router.get("/{test_id}/progress", response_model=TestProgressResponse)
async def get_test_progress(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current progress and saved answers"""
    
    # Get the test attempt
    attempt_query = await db.execute(
        select(StudentTestAttempt, AssignmentTest)
        .join(AssignmentTest, AssignmentTest.id == StudentTestAttempt.assignment_test_id)
        .where(
            and_(
                StudentTestAttempt.student_id == current_user.id,
                StudentTestAttempt.assignment_test_id == test_id
            )
        )
        .order_by(StudentTestAttempt.created_at.desc())
    )
    result = attempt_query.first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attempt not found"
        )
    
    test_attempt, assignment_test = result
    
    # Get answered questions
    answers = test_attempt.answers_data or {}
    answered_questions = [int(k) for k in answers.keys() if answers[k].strip()]
    
    # Calculate total questions
    test_questions = assignment_test.test_questions or []
    total_questions = len(test_questions)
    
    return TestProgressResponse(
        current_question=test_attempt.current_question,
        total_questions=total_questions,
        answered_questions=answered_questions,
        time_spent_seconds=test_attempt.time_spent_seconds or 0,
        status=test_attempt.status,
        saved_answers=answers
    )


@router.post("/{test_id}/submit")
async def submit_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit test for evaluation"""
    
    # Get the test attempt
    attempt_query = await db.execute(
        select(StudentTestAttempt)
        .where(
            and_(
                StudentTestAttempt.student_id == current_user.id,
                StudentTestAttempt.assignment_test_id == test_id,
                StudentTestAttempt.status == "in_progress"
            )
        )
    )
    test_attempt = attempt_query.scalar_one_or_none()
    
    if not test_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active test attempt not found"
        )
    
    # Mark as submitted
    test_attempt.status = "submitted"
    test_attempt.submitted_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    # TODO: Trigger AI evaluation in Phase 4
    
    return {
        "success": True,
        "message": "Test submitted successfully",
        "attempt_id": test_attempt.id
    }


@router.get("/{assignment_id}/reading-content", response_model=ReadingContentResponse)
async def get_reading_content_for_test(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get chunked reading content for tabbed reference"""
    
    # Verify access (similar to start_test)
    access_query = await db.execute(
        select(ReadingAssignment)
        .join(ClassroomAssignment,
              and_(
                  ClassroomAssignment.assignment_id == ReadingAssignment.id,
                  ClassroomAssignment.assignment_type == "reading"
              ))
        .join(ClassroomStudent,
              and_(
                  ClassroomStudent.classroom_id == ClassroomAssignment.classroom_id,
                  ClassroomStudent.student_id == current_user.id,
                  ClassroomStudent.removed_at.is_(None)
              ))
        .where(
            and_(
                ReadingAssignment.id == assignment_id,
                ReadingAssignment.deleted_at.is_(None)
            )
        )
    )
    
    reading_assignment = access_query.scalar_one_or_none()
    if not reading_assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reading assignment not found or access denied"
        )
    
    # Get all chunks
    chunks_query = await db.execute(
        select(ReadingChunk)
        .where(ReadingChunk.assignment_id == assignment_id)
        .order_by(ReadingChunk.chunk_order)
    )
    chunks = chunks_query.scalars().all()
    
    # Get all images for this assignment
    from app.models.reading import AssignmentImage
    import re
    
    images_query = await db.execute(
        select(AssignmentImage)
        .where(AssignmentImage.assignment_id == assignment_id)
    )
    images_by_tag = {img.image_tag: img for img in images_query.scalars().all()}
    
    # Format chunks
    chunk_data = []
    image_pattern = re.compile(r'<image>(.*?)</image>')
    
    for chunk in chunks:
        # Extract image tags from content
        image_tags = image_pattern.findall(chunk.content)
        
        chunk_dict = {
            "chunk_number": chunk.chunk_order,
            "content": chunk.content,
            "has_image": len(image_tags) > 0
        }
        
        # Add images if present
        if image_tags:
            chunk_images = []
            for tag in image_tags:
                if tag in images_by_tag:
                    img = images_by_tag[tag]
                    chunk_images.append({
                        "url": img.display_url or img.image_url or "",
                        "thumbnail_url": img.thumbnail_url,
                        "description": img.ai_description,
                        "image_tag": img.image_tag
                    })
            if chunk_images:
                chunk_dict["images"] = chunk_images
        
        chunk_data.append(chunk_dict)
    
    return ReadingContentResponse(
        chunks=chunk_data,
        total_chunks=len(chunks),
        assignment_title=reading_assignment.assignment_title
    )


@router.get("/{test_id}/questions", response_model=TestQuestionsResponse)
async def get_test_questions(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get test questions for display"""
    
    # Verify the student has an active test attempt
    attempt_query = await db.execute(
        select(StudentTestAttempt, AssignmentTest)
        .join(AssignmentTest, AssignmentTest.id == StudentTestAttempt.assignment_test_id)
        .where(
            and_(
                StudentTestAttempt.student_id == current_user.id,
                StudentTestAttempt.assignment_test_id == test_id,
                StudentTestAttempt.status.in_(["in_progress", "submitted"])
            )
        )
    )
    result = attempt_query.first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active test attempt not found"
        )
    
    test_attempt, assignment_test = result
    
    # Parse questions without revealing answers
    test_questions = assignment_test.test_questions or []
    questions_list = []
    
    if isinstance(test_questions, list):
        questions_list = test_questions
    elif isinstance(test_questions, dict) and 'questions' in test_questions:
        questions_list = test_questions['questions']
    
    # Remove answer keys from questions before sending to frontend
    sanitized_questions = []
    for q in questions_list:
        sanitized_q = {
            "question": q.get("question", ""),
            "difficulty": q.get("difficulty", 5),
            "question_number": len(sanitized_questions) + 1
        }
        sanitized_questions.append(sanitized_q)
    
    return TestQuestionsResponse(
        questions=sanitized_questions,
        total_questions=len(sanitized_questions)
    )


@router.post("/{test_id}/security-incident")
async def log_security_incident(
    test_id: UUID,
    incident_data: SecurityIncidentRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Log a security violation (focus loss, tab switch, etc.)"""
    
    # Get the active test attempt
    attempt_query = await db.execute(
        select(StudentTestAttempt)
        .where(
            and_(
                StudentTestAttempt.student_id == current_user.id,
                StudentTestAttempt.assignment_test_id == test_id,
                StudentTestAttempt.status == "in_progress",
                StudentTestAttempt.is_locked == False
            )
        )
    )
    test_attempt = attempt_query.scalar_one_or_none()
    
    if not test_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active test attempt not found"
        )
    
    # Create security incident record
    incident = TestSecurityIncident(
        test_attempt_id=test_attempt.id,
        student_id=current_user.id,
        incident_type=incident_data.incident_type,
        incident_data=incident_data.incident_data or {}
    )
    db.add(incident)
    
    # Update violation count
    violations = test_attempt.security_violations or []
    violations.append({
        "type": incident_data.incident_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": incident_data.incident_data
    })
    test_attempt.security_violations = violations
    
    # Check if this should result in a lock (2+ violations)
    violation_count = len(violations)
    should_lock = violation_count >= 2
    
    if should_lock:
        test_attempt.is_locked = True
        test_attempt.locked_at = datetime.now(timezone.utc)
        test_attempt.locked_reason = f"Security violation: {incident_data.incident_type}"
        incident.resulted_in_lock = True
    
    await db.commit()
    
    return {
        "violation_count": violation_count,
        "warning_issued": violation_count == 1,
        "test_locked": should_lock
    }


@router.post("/{test_id}/lock")
async def lock_test(
    test_id: UUID,
    lock_data: TestLockRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Lock test due to security violations"""
    
    # Get the active test attempt
    attempt_query = await db.execute(
        select(StudentTestAttempt)
        .where(
            and_(
                StudentTestAttempt.student_id == current_user.id,
                StudentTestAttempt.assignment_test_id == test_id,
                StudentTestAttempt.status == "in_progress"
            )
        )
    )
    test_attempt = attempt_query.scalar_one_or_none()
    
    if not test_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active test attempt not found"
        )
    
    # Lock the test
    test_attempt.is_locked = True
    test_attempt.locked_at = datetime.now(timezone.utc)
    test_attempt.locked_reason = lock_data.reason
    
    await db.commit()
    
    return {
        "success": True,
        "message": "Test has been locked",
        "locked_at": test_attempt.locked_at
    }


@router.get("/{test_id}/security-status", response_model=SecurityStatusResponse)
async def get_security_status(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current security violation count and lock status"""
    
    # Get the test attempt
    attempt_query = await db.execute(
        select(StudentTestAttempt)
        .where(
            and_(
                StudentTestAttempt.student_id == current_user.id,
                StudentTestAttempt.assignment_test_id == test_id
            )
        )
        .order_by(StudentTestAttempt.created_at.desc())
    )
    test_attempt = attempt_query.scalar_one_or_none()
    
    if not test_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attempt not found"
        )
    
    violations = test_attempt.security_violations or []
    
    return SecurityStatusResponse(
        violation_count=len(violations),
        is_locked=test_attempt.is_locked,
        locked_at=test_attempt.locked_at,
        locked_reason=test_attempt.locked_reason,
        warnings_given=1 if len(violations) >= 1 else 0
    )


class UnlockRequest(BaseModel):
    unlock_code: str = Field(..., description="Bypass code (either !BYPASS-XXXX or 8-char code)")

@router.post("/tests/{test_attempt_id}/unlock")
async def unlock_test_with_code(
    test_attempt_id: UUID,
    request: UnlockRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Unlock a locked test using any bypass code"""
    
    # Get the test attempt
    attempt_query = await db.execute(
        select(StudentTestAttempt)
        .where(
            and_(
                StudentTestAttempt.id == test_attempt_id,
                StudentTestAttempt.student_id == current_user.id
            )
        )
    )
    test_attempt = attempt_query.scalar_one_or_none()
    
    if not test_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attempt not found"
        )
    
    if not test_attempt.is_locked:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test is not locked"
        )
    
    # Validate bypass code using unified system
    bypass_valid, bypass_type, teacher_id = await validate_bypass_code(
        db=db,
        student_id=current_user.id,
        answer_text=request.unlock_code,
        context_type="test",
        context_id=str(test_attempt_id),
        assignment_id=test_attempt.assignment_id
    )
    
    if not bypass_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired bypass code"
        )
    
    # Reset the test attempt completely
    test_attempt.is_locked = False
    test_attempt.locked_at = None
    test_attempt.locked_reason = None
    test_attempt.security_violations = []
    test_attempt.current_question = 1
    test_attempt.answers_data = {}
    test_attempt.time_spent_seconds = 0
    test_attempt.started_at = datetime.utcnow()
    test_attempt.last_activity_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "success": True,
        "message": "Test unlocked and reset successfully",
        "test_attempt_id": str(test_attempt_id),
        "bypass_type": bypass_type
    }
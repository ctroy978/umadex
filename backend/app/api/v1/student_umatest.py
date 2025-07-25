"""
Student API endpoints for UMATest
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
import logging
import re
from sqlalchemy import select, and_, or_, func, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.classroom import Classroom, ClassroomAssignment, StudentAssignment, ClassroomStudent
from app.models.umatest import TestAssignment
from app.models.tests import StudentTestAttempt, TestQuestionEvaluation, TestSecurityIncident
from app.utils.deps import get_current_user
from app.services.test_schedule import TestScheduleService
from app.services.umatest_evaluation import UMATestEvaluationService
from app.services.bypass_validation import validate_bypass_code

router = APIRouter()
logger = logging.getLogger(__name__)


class UMATestStartResponse(BaseModel):
    """Response when starting a UMATest"""
    test_attempt_id: UUID
    test_id: UUID
    assignment_id: int  # ClassroomAssignment.id is an integer
    assignment_title: str
    test_title: str
    test_description: Optional[str]
    status: str
    current_question: int
    total_questions: int
    time_limit_minutes: Optional[int]
    attempt_number: int
    max_attempts: int
    saved_answers: Dict[str, str]
    questions: List[Dict[str, Any]]  # Will contain question text, difficulty, etc.


class UMATestQuestionResponse(BaseModel):
    """Individual test question data"""
    id: str
    question_text: str
    difficulty_level: str
    source_lecture_title: str
    topic_title: str


class UMATestResultsResponse(BaseModel):
    """Test results with detailed evaluation"""
    test_attempt_id: UUID
    score: float
    status: str
    submitted_at: datetime
    evaluated_at: Optional[datetime]
    question_evaluations: List[Dict[str, Any]]
    feedback: Optional[str]


class SecurityIncidentRequest(BaseModel):
    """Request to log a security incident"""
    incident_type: str = Field(..., pattern="^(focus_loss|tab_switch|navigation_attempt|window_blur|app_switch|orientation_cheat)$")
    incident_data: Optional[Dict[str, Any]] = None


class SecurityStatusResponse(BaseModel):
    """Security status for a test attempt"""
    violation_count: int
    is_locked: bool
    locked_at: Optional[datetime]
    locked_reason: Optional[str]
    warnings_given: int


class UnlockRequest(BaseModel):
    """Request to unlock a test"""
    unlock_code: str = Field(..., description="Bypass code (either !BYPASS-XXXX or 8-char code)")


@router.post("/test/{assignment_id}/start", response_model=UMATestStartResponse)
async def start_umatest(
    assignment_id: int,
    override_code: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start or resume a UMATest"""
    logger.info(f"Starting UMATest for assignment {assignment_id}, user {current_user.id}, override_code: {override_code}")
    
    # Get classroom assignment and verify student has access
    # For UMATest, assignment_id is the ClassroomAssignment.id
    classroom_assignment = await db.execute(
        select(ClassroomAssignment)
        .join(Classroom, Classroom.id == ClassroomAssignment.classroom_id)
        .join(ClassroomStudent, ClassroomStudent.classroom_id == Classroom.id)
        .where(
            and_(
                ClassroomAssignment.id == assignment_id,
                ClassroomStudent.student_id == current_user.id,
                ClassroomStudent.removed_at.is_(None),
                ClassroomAssignment.removed_from_classroom_at.is_(None)
            )
        )
    )
    classroom_assignment = classroom_assignment.scalar_one_or_none()
    
    if not classroom_assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found or you don't have access"
        )
    
    if classroom_assignment.assignment_type != 'test':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not a test assignment"
        )
    
    # Check if assignment is active
    now = datetime.now(timezone.utc)
    if classroom_assignment.start_date and now < classroom_assignment.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test has not started yet"
        )
    
    if classroom_assignment.end_date and now > classroom_assignment.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test has ended"
        )
    
    # Check test availability schedule
    if classroom_assignment.classroom_id:
        availability = await TestScheduleService.check_test_availability(
            db,
            classroom_assignment.classroom_id,
            override_code
        )
        
        if not availability.allowed:
            response = HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=availability.message
            )
            response.headers["X-Override-Required"] = "true"
            raise response
    
    # Get the test assignment
    test_assignment = await db.execute(
        select(TestAssignment)
        .where(TestAssignment.id == classroom_assignment.assignment_id)
    )
    test_assignment = test_assignment.scalar_one_or_none()
    
    if not test_assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test configuration not found"
        )
    
    # Check for existing attempts
    existing_attempts = await db.execute(
        select(StudentTestAttempt)
        .where(
            and_(
                StudentTestAttempt.student_id == current_user.id,
                StudentTestAttempt.classroom_assignment_id == classroom_assignment.id,
                StudentTestAttempt.test_id == test_assignment.id
            )
        )
        .order_by(StudentTestAttempt.created_at.desc())
    )
    existing_attempts = existing_attempts.scalars().all()
    
    # Check if we can start a new attempt or need to resume
    current_attempt = None
    for attempt in existing_attempts:
        if attempt.status == 'in_progress':
            current_attempt = attempt
            break
    
    # If no in-progress attempt, check if we can create a new one
    if not current_attempt:
        completed_attempts = [a for a in existing_attempts if a.status in ['submitted', 'graded']]
        
        if len(completed_attempts) >= test_assignment.attempt_limit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum attempts ({test_assignment.attempt_limit}) reached"
            )
        
        # Create new attempt
        current_attempt = StudentTestAttempt(
            student_id=current_user.id,
            assignment_id=None,  # Not used for UMATest
            classroom_assignment_id=classroom_assignment.id,
            test_id=test_assignment.id,
            attempt_number=len(existing_attempts) + 1,
            status='in_progress',
            started_at=datetime.now(timezone.utc),
            answers_data={}
        )
        db.add(current_attempt)
        await db.commit()
        await db.refresh(current_attempt)
    
    # Extract questions from test structure
    questions = []
    if test_assignment.test_structure and 'topics' in test_assignment.test_structure:
        for topic_id, topic_data in test_assignment.test_structure['topics'].items():
            for question in topic_data.get('questions', []):
                questions.append({
                    'id': question['id'],
                    'question_text': question['question_text'],
                    'difficulty_level': question['difficulty_level'],
                    'source_lecture_title': topic_data.get('source_lecture_title', ''),
                    'topic_title': topic_data.get('topic_title', '')
                })
    
    # Randomize questions if configured
    if test_assignment.randomize_questions:
        import random
        random.shuffle(questions)
    
    return UMATestStartResponse(
        test_attempt_id=current_attempt.id,
        test_id=test_assignment.id,
        assignment_id=assignment_id,
        assignment_title=test_assignment.test_title,  # For UMATest, use the test title
        test_title=test_assignment.test_title,
        test_description=test_assignment.test_description,
        status=current_attempt.status,
        current_question=len(current_attempt.answers_data) + 1 if current_attempt.answers_data else 1,
        total_questions=len(questions),
        time_limit_minutes=test_assignment.time_limit_minutes,
        attempt_number=current_attempt.attempt_number,
        max_attempts=test_assignment.attempt_limit,
        saved_answers=current_attempt.answers_data or {},
        questions=questions
    )


class SaveAnswerRequest(BaseModel):
    """Request body for saving an answer"""
    question_index: int = Field(..., ge=0)
    answer: str = Field(..., min_length=1)
    time_spent_seconds: Optional[int] = None


@router.post("/test/{test_attempt_id}/save-answer")
async def save_umatest_answer(
    test_attempt_id: UUID,
    request: SaveAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Save an answer for a specific question in UMATest"""
    # Get the test attempt
    test_attempt = await db.execute(
        select(StudentTestAttempt)
        .where(
            and_(
                StudentTestAttempt.id == test_attempt_id,
                StudentTestAttempt.student_id == current_user.id
            )
        )
    )
    test_attempt = test_attempt.scalar_one_or_none()
    
    if not test_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attempt not found"
        )
    
    if test_attempt.status != 'in_progress':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test is not in progress"
        )
    
    # Update answers
    if not test_attempt.answers_data:
        test_attempt.answers_data = {}
    
    # Log the save operation
    logger.info(f"Saving answer for question {request.question_index}: '{request.answer[:50]}...' (length: {len(request.answer)})")
    logger.info(f"Current answers before save: {list(test_attempt.answers_data.keys())}")
    
    test_attempt.answers_data[str(request.question_index)] = request.answer
    test_attempt.last_activity_at = datetime.now(timezone.utc)
    
    # Force the ORM to recognize the change
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(test_attempt, "answers_data")
    
    # Update total time spent if provided
    if request.time_spent_seconds:
        current_time = test_attempt.time_spent_seconds or 0
        test_attempt.time_spent_seconds = current_time + request.time_spent_seconds
    
    await db.commit()
    await db.refresh(test_attempt)
    
    logger.info(f"After save - Total answers: {len(test_attempt.answers_data)}, Keys: {list(test_attempt.answers_data.keys())}")
    
    return {"success": True, "message": "Answer saved"}


@router.post("/test/{test_attempt_id}/submit")
async def submit_umatest(
    test_attempt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit UMATest for evaluation"""
    # Get the test attempt
    test_attempt = await db.execute(
        select(StudentTestAttempt)
        .where(
            and_(
                StudentTestAttempt.id == test_attempt_id,
                StudentTestAttempt.student_id == current_user.id
            )
        )
    )
    test_attempt = test_attempt.scalar_one_or_none()
    
    if not test_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test attempt not found"
        )
    
    if test_attempt.status != 'in_progress':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test has already been submitted"
        )
    
    # Update status to submitted
    test_attempt.status = 'submitted'
    test_attempt.submitted_at = datetime.now(timezone.utc)
    
    await db.commit()
    await db.refresh(test_attempt)
    
    # Log submission details
    logger.info(f"Test submitted - ID: {test_attempt_id}, Answers: {len(test_attempt.answers_data or {})}")
    
    # Trigger AI evaluation service
    try:
        evaluation_service = UMATestEvaluationService(db)
        evaluation_result = await evaluation_service.evaluate_test_submission(
            test_attempt_id=test_attempt_id,
            trigger_source="student_submission"
        )
        
        return {
            "success": True,
            "message": "Test submitted and evaluated successfully",
            "test_attempt_id": str(test_attempt_id),
            "evaluation_status": "completed",
            "score": evaluation_result.get("score", 0)
        }
    except Exception as e:
        logger.error(f"Error evaluating test {test_attempt_id}: {str(e)}")
        # Even if evaluation fails, the submission was successful
        return {
            "success": True,
            "message": "Test submitted successfully. Evaluation pending.",
            "test_attempt_id": str(test_attempt_id),
            "evaluation_status": "pending"
        }


@router.get("/test/debug/{test_attempt_id}")
async def debug_test_evaluation(
    test_attempt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Debug endpoint to check evaluation status"""
    # Get test attempt
    test_attempt = await db.execute(
        select(StudentTestAttempt)
        .where(
            and_(
                StudentTestAttempt.id == test_attempt_id,
                StudentTestAttempt.student_id == current_user.id
            )
        )
    )
    test_attempt = test_attempt.scalar_one_or_none()
    
    if not test_attempt:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Get evaluations
    evaluations_result = await db.execute(
        select(TestQuestionEvaluation)
        .where(TestQuestionEvaluation.test_attempt_id == test_attempt_id)
        .order_by(TestQuestionEvaluation.question_index)
    )
    evaluations = evaluations_result.scalars().all()
    
    return {
        "test_attempt_id": str(test_attempt_id),
        "status": test_attempt.status,
        "submitted_at": test_attempt.submitted_at,
        "evaluated_at": test_attempt.evaluated_at,
        "score": float(test_attempt.score) if test_attempt.score else None,
        "answers_count": len(test_attempt.answers_data) if test_attempt.answers_data else 0,
        "answer_indices": sorted(test_attempt.answers_data.keys()) if test_attempt.answers_data else [],
        "evaluations_count": len(evaluations),
        "evaluation_indices": [e.question_index for e in evaluations],
        "evaluation_scores": {e.question_index: e.rubric_score for e in evaluations}
    }


@router.get("/test/results/{test_attempt_id}", response_model=UMATestResultsResponse)
async def get_umatest_results(
    test_attempt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed results for a completed UMATest"""
    # Get the test attempt with evaluations
    test_attempt = await db.execute(
        select(StudentTestAttempt)
        .where(
            and_(
                StudentTestAttempt.id == test_attempt_id,
                StudentTestAttempt.student_id == current_user.id
            )
        )
        # UMATest doesn't use question_evaluations relationship
    )
    test_attempt = test_attempt.scalar_one_or_none()
    
    if not test_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test results not found"
        )
    
    if test_attempt.status not in ['submitted', 'graded']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test has not been submitted yet"
        )
    
    # Fetch question evaluations from TestQuestionEvaluation table
    evaluations_result = await db.execute(
        select(TestQuestionEvaluation)
        .where(TestQuestionEvaluation.test_attempt_id == test_attempt_id)
        .order_by(TestQuestionEvaluation.question_index)
    )
    evaluations = evaluations_result.scalars().all()
    
    logger.info(f"Found {len(evaluations)} evaluations for test attempt {test_attempt_id}")
    for eval in evaluations:
        logger.info(f"Evaluation {eval.question_index}: Score={eval.rubric_score}, Points={eval.points_earned}/{eval.max_points}")
    
    # Format question evaluations
    question_evaluations = []
    for eval in evaluations:
        question_evaluations.append({
            'question_index': eval.question_index,
            'rubric_score': eval.rubric_score,
            'points_earned': float(eval.points_earned),
            'max_points': float(eval.max_points),
            'scoring_rationale': eval.scoring_rationale,
            'feedback': eval.feedback or '',
            'key_concepts_identified': eval.key_concepts_identified or [],
            'misconceptions_detected': eval.misconceptions_detected or []
        })
    
    # Get overall feedback from test_attempt.feedback if it's a string
    overall_feedback = test_attempt.feedback if isinstance(test_attempt.feedback, str) else None
    
    return UMATestResultsResponse(
        test_attempt_id=test_attempt.id,
        score=float(test_attempt.score) if test_attempt.score else 0.0,
        status=test_attempt.status,
        submitted_at=test_attempt.submitted_at,
        evaluated_at=test_attempt.evaluated_at,
        question_evaluations=question_evaluations,
        feedback=overall_feedback
    )


@router.post("/test/{test_attempt_id}/security-incident")
async def log_security_incident(
    test_attempt_id: UUID,
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
                StudentTestAttempt.id == test_attempt_id,
                StudentTestAttempt.student_id == current_user.id,
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


@router.get("/test/{test_attempt_id}/security-status", response_model=SecurityStatusResponse)
async def get_security_status(
    test_attempt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current security violation count and lock status"""
    
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
    
    violations = test_attempt.security_violations or []
    
    return SecurityStatusResponse(
        violation_count=len(violations),
        is_locked=test_attempt.is_locked,
        locked_at=test_attempt.locked_at,
        locked_reason=test_attempt.locked_reason,
        warnings_given=1 if len(violations) >= 1 else 0
    )


@router.post("/test/{test_attempt_id}/unlock")
async def unlock_test(
    test_attempt_id: UUID,
    unlock_data: UnlockRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Unlock a test with override code"""
    
    # Get the test attempt
    attempt_query = await db.execute(
        select(StudentTestAttempt)
        .where(
            and_(
                StudentTestAttempt.id == test_attempt_id,
                StudentTestAttempt.student_id == current_user.id,
                StudentTestAttempt.is_locked == True
            )
        )
    )
    test_attempt = attempt_query.scalar_one_or_none()
    
    if not test_attempt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Locked test attempt not found"
        )
    
    # For UMATest, we need to get the test assignment to pass as context
    if not test_attempt.classroom_assignment_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find classroom assignment for this test"
        )
    
    # Get the classroom assignment to find the classroom
    classroom_assignment_result = await db.execute(
        select(ClassroomAssignment)
        .where(ClassroomAssignment.id == test_attempt.classroom_assignment_id)
    )
    classroom_assignment = classroom_assignment_result.scalar_one_or_none()
    
    if not classroom_assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find classroom assignment"
        )
    
    # Get the classroom to find the teacher
    classroom_result = await db.execute(
        select(Classroom)
        .where(Classroom.id == classroom_assignment.classroom_id)
    )
    classroom = classroom_result.scalar_one_or_none()
    
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Could not find classroom"
        )
    
    # Check if it's a permanent bypass code first
    unlock_code = unlock_data.unlock_code.strip()
    bypass_pattern = r'^!BYPASS-(\d{4})$'
    bypass_match = re.match(bypass_pattern, unlock_code.upper())
    
    bypass_valid = False
    bypass_type = None
    teacher_id = str(classroom.teacher_id)
    
    if bypass_match:
        # Permanent bypass code - check against teacher's code
        provided_code = bypass_match.group(1)
        teacher_result = await db.execute(
            select(User).where(User.id == classroom.teacher_id)
        )
        teacher = teacher_result.scalar_one_or_none()
        
        if teacher and teacher.bypass_code:
            # Bypass codes are hashed with bcrypt
            import bcrypt
            try:
                if bcrypt.checkpw(provided_code.encode('utf-8'), teacher.bypass_code.encode('utf-8')):
                    bypass_valid = True
                    bypass_type = "permanent"
            except Exception:
                # If bcrypt check fails, bypass is invalid
                pass
    else:
        # Try as a one-time code through the unified system
        bypass_valid, bypass_type, _ = await validate_bypass_code(
            db=db,
            student_id=str(current_user.id),
            answer_text=unlock_code,
            context_type="test",
            context_id=str(test_attempt_id),
            assignment_id=None
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
    test_attempt.started_at = datetime.now(timezone.utc)
    test_attempt.last_activity_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    return {
        "success": True,
        "message": "Test unlocked and reset successfully",
        "test_attempt_id": str(test_attempt_id),
        "bypass_type": bypass_type
    }
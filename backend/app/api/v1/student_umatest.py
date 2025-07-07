"""
Student API endpoints for UMATest
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, timezone
import logging
from sqlalchemy import select, and_, or_, func, exists
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.classroom import ClassroomAssignment, StudentAssignment
from app.models.umatest import TestAssignment
from app.models.tests import StudentTestAttempt
from app.utils.deps import get_current_user
from app.services.test_schedule import TestScheduleService

router = APIRouter()
logger = logging.getLogger(__name__)


class UMATestStartResponse(BaseModel):
    """Response when starting a UMATest"""
    test_attempt_id: UUID
    test_id: UUID
    assignment_id: UUID
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


@router.post("/test/{assignment_id}/start", response_model=UMATestStartResponse)
async def start_umatest(
    assignment_id: UUID,
    override_code: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start or resume a UMATest"""
    # Verify student has access to this assignment
    student_assignment = await db.execute(
        select(StudentAssignment)
        .where(
            and_(
                StudentAssignment.assignment_id == assignment_id,
                StudentAssignment.student_id == current_user.id
            )
        )
    )
    student_assignment = student_assignment.scalar_one_or_none()
    
    if not student_assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Get classroom assignment details
    classroom_assignment = await db.execute(
        select(ClassroomAssignment)
        .where(ClassroomAssignment.id == assignment_id)
        .options(selectinload(ClassroomAssignment.assignment))
    )
    classroom_assignment = classroom_assignment.scalar_one_or_none()
    
    if not classroom_assignment or classroom_assignment.assignment_type != 'test':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not a test assignment"
        )
    
    # Check if assignment is active
    now = datetime.now(timezone.utc)
    if now < classroom_assignment.start_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test has not started yet"
        )
    
    if now > classroom_assignment.end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test has ended"
        )
    
    # Check test availability schedule
    schedule_service = TestScheduleService(db)
    if classroom_assignment.classroom_id:
        availability = await schedule_service.check_test_availability(
            classroom_assignment.classroom_id,
            override_code
        )
        
        if not availability['allowed']:
            response = HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=availability['message']
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
        assignment_title=classroom_assignment.title,
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
    
    test_attempt.answers_data[str(request.question_index)] = request.answer
    test_attempt.last_activity_at = datetime.now(timezone.utc)
    
    # Update total time spent if provided
    if request.time_spent_seconds:
        current_time = test_attempt.time_spent_seconds or 0
        test_attempt.time_spent_seconds = current_time + request.time_spent_seconds
    
    await db.commit()
    
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
    
    # Trigger evaluation (this will be handled by the evaluation service)
    # For now, we'll import and call the evaluation service directly
    from app.services.umatest_evaluation import UMATestEvaluationService
    
    evaluation_service = UMATestEvaluationService(db)
    try:
        result = await evaluation_service.evaluate_test_submission(test_attempt_id)
        return {
            "success": True,
            "message": "Test submitted successfully",
            "test_attempt_id": str(test_attempt_id),
            "evaluation_status": "completed" if result['success'] else "pending"
        }
    except Exception as e:
        logger.error(f"Error evaluating test {test_attempt_id}: {str(e)}")
        # Don't fail the submission if evaluation fails
        return {
            "success": True,
            "message": "Test submitted. Evaluation will be processed.",
            "test_attempt_id": str(test_attempt_id),
            "evaluation_status": "pending"
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
        .options(selectinload(StudentTestAttempt.question_evaluations))
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
    
    # Format question evaluations
    question_evaluations = []
    for eval in test_attempt.question_evaluations:
        question_evaluations.append({
            'question_index': eval.question_index,
            'rubric_score': eval.rubric_score,
            'points_earned': eval.points_earned,
            'max_points': eval.max_points,
            'scoring_rationale': eval.scoring_rationale,
            'feedback': eval.feedback,
            'key_concepts_identified': eval.key_concepts_identified,
            'misconceptions_detected': eval.misconceptions_detected
        })
    
    return UMATestResultsResponse(
        test_attempt_id=test_attempt.id,
        score=float(test_attempt.score) if test_attempt.score else 0.0,
        status=test_attempt.status,
        submitted_at=test_attempt.submitted_at,
        evaluated_at=test_attempt.evaluated_at,
        question_evaluations=question_evaluations,
        feedback=test_attempt.feedback
    )
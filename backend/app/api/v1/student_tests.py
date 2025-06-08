"""
Student test-taking API endpoints
"""
import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_, text
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.user import User
from app.models.tests import AssignmentTest, StudentTestAttempt, TestSecurityIncident
from app.models.reading import ReadingAssignment, ReadingChunk
from app.models.classroom import ClassroomAssignment, ClassroomStudent
from app.utils.deps import get_current_user
from app.services.bypass_validation import validate_bypass_code
from app.services.test_schedule import TestScheduleService
from app.schemas.test_schedule import ValidateOverrideRequest

logger = logging.getLogger(__name__)
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
    override_code: Optional[str] = None,
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
    
    # Check for existing in-progress attempt first
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
    
    # Get the latest attempt number only if we need to create a new attempt
    last_attempt_number = 0
    if not test_attempt:
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
    
    # Clean up any "zombie" test attempts that were created outside valid windows
    # and have no answers (indicating they were never properly started)
    if not test_attempt:
        zombie_attempts = await db.execute(
            select(StudentTestAttempt)
            .where(
                and_(
                    StudentTestAttempt.student_id == current_user.id,
                    StudentTestAttempt.assignment_test_id == assignment_test.id,
                    StudentTestAttempt.status == "in_progress",
                    StudentTestAttempt.answers_data == {},
                    StudentTestAttempt.time_spent_seconds == 0
                )
            )
        )
        for zombie in zombie_attempts.scalars():
            await db.delete(zombie)
        await db.commit()
    
    # If resuming an existing attempt, check if it's still allowed
    if test_attempt:
        # Check if the test was started within a valid schedule window
        if test_attempt.started_within_schedule:
            # Check if we're still within the grace period
            if test_attempt.grace_period_end:
                current_time = datetime.now(timezone.utc)
                if current_time > test_attempt.grace_period_end:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Test grace period has expired. Please wait for the next testing window.",
                        headers={"X-Grace-Period-Expired": "true"}
                    )
        # If test was started with override, allow continuation
        # (Override codes are typically for emergency access)
    
    if not test_attempt:
        # Check if max attempts reached
        if assignment_test.max_attempts and last_attempt_number >= assignment_test.max_attempts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Maximum attempts ({assignment_test.max_attempts}) reached for this test"
            )
        
        # IMPORTANT: Check classroom test schedule BEFORE creating new attempt
        # This prevents creating database records for invalid attempts
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
                            status_code=status.HTTP_403_FORBIDDEN,
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
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Error validating override code: {str(validation_error)}"
                    )
            else:
                # No override code provided - don't create test attempt
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
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
        
        # Create test attempt with race condition handling
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Re-check for existing attempt in case one was created during race condition
                if retry_count > 0:
                    existing_check = await db.execute(
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
                    existing_test_attempt = existing_check.scalar_one_or_none()
                    if existing_test_attempt:
                        test_attempt = existing_test_attempt
                        break
                    
                    # Refresh attempt number in case it changed
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
                
                test_attempt = StudentTestAttempt(
                    student_id=current_user.id,
                    assignment_test_id=assignment_test.id,
                    assignment_id=assignment_id,
                    attempt_number=last_attempt_number + 1,
                    current_question=1,
                    answers_data={},
                    status="in_progress",
                    started_within_schedule=started_within_schedule,
                    override_code_used=override_id,
                    grace_period_end=grace_period_end
                )
                db.add(test_attempt)
                await db.commit()
                await db.refresh(test_attempt)
                break  # Success, exit retry loop
                
            except Exception as e:
                await db.rollback()
                retry_count += 1
                
                # Check if it's a unique constraint violation
                error_str = str(e).lower()
                if "unique_student_test_attempt" in error_str or "duplicate key" in error_str:
                    if retry_count < max_retries:
                        # Wait a small amount before retrying
                        import asyncio
                        await asyncio.sleep(0.1 * retry_count)
                        continue
                    else:
                        # Final retry failed, check if another attempt was created
                        final_check = await db.execute(
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
                        existing_attempt_final = final_check.scalar_one_or_none()
                        if existing_attempt_final:
                            test_attempt = existing_attempt_final
                            break
                
                # If it's not a constraint violation or we've exhausted retries, raise the error
                print(f"Error creating test attempt (retry {retry_count}): {e}")
                if retry_count >= max_retries:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Failed to create test attempt: {str(e)}"
                    )
        
        # If override was used, record the usage now that we have the test_attempt_id
        if override_id and override_code:
            try:
                # Record the override usage and increment count
                from app.models.test_schedule import TestOverrideUsage, ClassroomTestOverride
                
                # Create usage record
                usage = TestOverrideUsage(
                    override_id=override_id,
                    student_id=current_user.id,
                    test_attempt_id=test_attempt.id
                )
                db.add(usage)
                
                # Increment usage count on the override
                override_result = await db.execute(
                    select(ClassroomTestOverride).where(
                        ClassroomTestOverride.id == override_id
                    )
                )
                override_record = override_result.scalar_one_or_none()
                if override_record:
                    override_record.current_uses += 1
                    override_record.used_at = datetime.now(timezone.utc)
                
                await db.commit()
            except Exception as usage_error:
                # Log the error but don't fail the test start
                print(f"Warning: Failed to record override usage: {usage_error}")
    
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
    
    # Log the save operation for debugging
    logger.info(f"Saving answer - Test ID: {test_id}, Question: {request.question_index}, Answer length: {len(request.answer)}")
    logger.debug(f"All answers so far: {answers}")
    
    # Update current question and time spent
    test_attempt.answers_data = answers
    test_attempt.current_question = request.question_index + 1  # Next question
    test_attempt.time_spent_seconds = (test_attempt.time_spent_seconds or 0) + request.time_spent_seconds
    test_attempt.last_activity_at = datetime.now(timezone.utc)
    
    # Explicitly mark the answers_data as modified to ensure SQLAlchemy updates the JSONB field
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(test_attempt, "answers_data")
    
    await db.commit()
    
    return {"success": True, "message": "Answer saved", "saved_count": len(answers)}


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
    
    # Log submission details for debugging
    logger.info(f"Test submission - Attempt ID: {test_attempt.id}, Answers: {test_attempt.answers_data}")
    
    # Trigger AI evaluation using the new V2 service
    try:
        from app.services.test_evaluation_v2 import TestEvaluationServiceV2
        
        # Create evaluation service instance with database session
        evaluation_service = TestEvaluationServiceV2(db)
        
        # Perform evaluation asynchronously
        evaluation_result = await evaluation_service.evaluate_test_submission(
            test_attempt_id=test_attempt.id,
            trigger_source="student_submission"
        )
        
        logger.info(f"Test evaluation completed - Score: {evaluation_result.get('score')}")
        
        return {
            "success": True,
            "message": "Test submitted and evaluated successfully",
            "attempt_id": test_attempt.id,
            "score": evaluation_result.get("score"),
            "needs_review": evaluation_result.get("needs_review", False)
        }
    except Exception as e:
        logger.error(f"Error evaluating test: {str(e)}")
        # Don't fail the submission if evaluation fails
        test_attempt.evaluation_status = "failed"
        await db.commit()
        
        return {
            "success": True,
            "message": "Test submitted successfully. Evaluation will be completed shortly.",
            "attempt_id": test_attempt.id,
            "evaluation_error": str(e)
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
    test_attempt.started_at = datetime.now(timezone.utc)
    test_attempt.last_activity_at = datetime.now(timezone.utc)
    
    await db.commit()
    
    return {
        "success": True,
        "message": "Test unlocked and reset successfully",
        "test_attempt_id": str(test_attempt_id),
        "bypass_type": bypass_type
    }


class TestResultDetailResponse(BaseModel):
    attempt_id: UUID
    assignment_id: UUID
    assignment_title: str
    student_name: str
    overall_score: float
    total_points: int
    passed: bool
    status: str
    submitted_at: Optional[datetime]
    evaluated_at: Optional[datetime]
    question_evaluations: List[Dict[str, Any]]
    feedback_summary: Optional[str]
    needs_review: bool


@router.get("/results/{test_attempt_id}", response_model=TestResultDetailResponse)
async def get_test_result_details(
    test_attempt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed test results with evaluation breakdown"""
    
    # Get test attempt with related data
    attempt_query = await db.execute(
        select(StudentTestAttempt, ReadingAssignment, User)
        .join(ReadingAssignment, ReadingAssignment.id == StudentTestAttempt.assignment_id)
        .join(User, User.id == StudentTestAttempt.student_id)
        .where(StudentTestAttempt.id == test_attempt_id)
    )
    result = attempt_query.first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test result not found"
        )
    
    test_attempt, assignment, student = result
    
    # Check authorization
    if current_user.role.value == "student":
        if test_attempt.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own test results"
            )
    elif current_user.role.value == "teacher":
        # Verify teacher owns the assignment
        if assignment.teacher_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view results for your assignments"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
    
    # Get question evaluations if available, otherwise show submitted answers
    eval_query = await db.execute(
        text("""
        SELECT 
            qe.question_number,
            qe.question_text,
            qe.student_answer,
            qe.rubric_score,
            qe.points_earned,
            qe.scoring_rationale,
            qe.feedback_text,
            qe.key_concepts_identified,
            qe.misconceptions_detected,
            qe.evaluation_confidence
        FROM test_question_evaluations qe
        WHERE qe.test_attempt_id = :attempt_id
        ORDER BY qe.question_number
        """),
        {"attempt_id": test_attempt_id}
    )
    
    question_evaluations = []
    eval_rows = eval_query.fetchall()
    
    if eval_rows:
        # We have AI evaluation results
        for row in eval_rows:
            eval_data = {
                "question_number": row[0],
                "question_text": row[1],
                "student_answer": row[2],
                "rubric_score": row[3],
                "points_earned": row[4],
                "scoring_rationale": row[5],
                "feedback": row[6],
                "confidence": row[9] if row[9] is not None else 0.0
            }
            
            # Handle JSON fields (they're already parsed as dict/list in PostgreSQL JSONB)
            eval_data["key_concepts"] = row[7] if row[7] else []
            eval_data["misconceptions"] = row[8] if row[8] else []
            
            question_evaluations.append(eval_data)
    else:
        # No AI evaluation yet, show basic submitted answers
        # Get the test questions and student answers from the test attempt
        test_query = await db.execute(
            select(AssignmentTest)
            .where(AssignmentTest.id == test_attempt.assignment_test_id)
        )
        assignment_test = test_query.scalar_one()
        
        # Parse answers from the test attempt
        student_answers = test_attempt.answers_data or {}
        
        for i, question in enumerate(assignment_test.test_questions):
            question_key = str(i)
            student_answer = student_answers.get(question_key, "No answer provided")
            
            eval_data = {
                "question_number": i + 1,
                "question_text": question.get("question", "Question text not available"),
                "student_answer": student_answer,
                "rubric_score": 0,  # No score yet
                "points_earned": 0,
                "scoring_rationale": "Evaluation pending - your teacher will review your responses.",
                "feedback": None,
                "confidence": 0.0,
                "key_concepts": [],
                "misconceptions": []
            }
            
            question_evaluations.append(eval_data)
    
    # For now, we'll set needs_review based on evaluation status
    # TODO: Implement proper audit system later
    needs_review = test_attempt.evaluation_status in ["failed", "error"] if hasattr(test_attempt, 'evaluation_status') else False
    
    # Get feedback summary
    feedback_summary = None
    if test_attempt.feedback and isinstance(test_attempt.feedback, dict):
        feedback_summary = test_attempt.feedback.get("summary")
    elif not eval_rows:
        # No evaluation yet
        feedback_summary = "Your test has been submitted successfully. Your teacher will review and provide feedback soon."
    
    return TestResultDetailResponse(
        attempt_id=test_attempt.id,
        assignment_id=test_attempt.assignment_id,
        assignment_title=assignment.assignment_title,
        student_name=f"{student.first_name} {student.last_name}",
        overall_score=float(test_attempt.score or 0),
        total_points=100,  # Standard total
        passed=test_attempt.passed or False,
        status=test_attempt.status,
        submitted_at=test_attempt.submitted_at,
        evaluated_at=test_attempt.evaluated_at if hasattr(test_attempt, 'evaluated_at') else None,
        question_evaluations=question_evaluations,
        feedback_summary=feedback_summary,
        needs_review=needs_review
    )
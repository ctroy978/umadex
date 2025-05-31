"""
UMARead API endpoints for student interface
"""
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.utils.deps import get_current_user
from app.schemas.umaread import (
    ChunkResponse,
    QuestionResponse,
    SubmitAnswerRequest,
    SubmitAnswerResponse,
    AssignmentStartResponse,
    StudentProgress,
    QuestionType,
    StudentAnswer
)
from app.services.umaread_simple import UMAReadService


router = APIRouter(prefix="/umaread", tags=["umaread"])
umaread_service = UMAReadService()


@router.get("/assignments/{assignment_id}/start", response_model=AssignmentStartResponse)
async def start_assignment(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start or resume a reading assignment"""
    student_assignment = await umaread_service.get_student_assignment(
        db, current_user.id, assignment_id
    )
    
    if not student_assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found or not assigned to student"
        )
    
    # Get assignment details
    assignment = student_assignment.assignment
    progress_metadata = student_assignment.progress_metadata or {}
    
    # Get total chunks
    from sqlalchemy import select, func
    from app.models.reading import ReadingChunk
    
    total_result = await db.execute(
        select(func.count(ReadingChunk.id))
        .where(ReadingChunk.assignment_id == assignment_id)
    )
    total_chunks = total_result.scalar()
    
    # Start assignment if not started
    if student_assignment.status == "not_started":
        from datetime import datetime
        from sqlalchemy import update
        from app.models.classroom import StudentAssignment
        
        await db.execute(
            update(StudentAssignment)
            .where(StudentAssignment.id == student_assignment.id)
            .values(
                status="in_progress",
                started_at=datetime.utcnow(),
                progress_metadata={
                    "difficulty_level": 5,  # Start at middle difficulty
                    "chunks_completed": [],
                    "current_chunk": 1
                }
            )
        )
        await db.commit()
        
        # Refresh data
        await db.refresh(student_assignment)
        progress_metadata = student_assignment.progress_metadata
    
    return AssignmentStartResponse(
        assignment_id=assignment_id,
        title=assignment.title,
        author=assignment.author,
        total_chunks=total_chunks,
        current_chunk=student_assignment.current_position,
        difficulty_level=progress_metadata.get("difficulty_level", 5),
        status=student_assignment.status
    )


@router.get("/assignments/{assignment_id}/chunks/{chunk_number}", response_model=ChunkResponse)
async def get_chunk(
    assignment_id: UUID,
    chunk_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific chunk's content with images"""
    # Verify student has access
    student_assignment = await umaread_service.get_student_assignment(
        db, current_user.id, assignment_id
    )
    
    if not student_assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found or not assigned to student"
        )
    
    if student_assignment.status not in ["in_progress", "completed", "test_available"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignment not started"
        )
    
    try:
        return await umaread_service.get_chunk_content(db, assignment_id, chunk_number)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/assignments/{assignment_id}/chunks/{chunk_number}/question", response_model=QuestionResponse)
async def get_current_question(
    assignment_id: UUID,
    chunk_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the current question for a chunk"""
    # Get student assignment
    student_assignment = await umaread_service.get_student_assignment(
        db, current_user.id, assignment_id
    )
    
    if not student_assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Check what question type student should answer
    from app.core.database import execute_query
    
    # Get last responses for this chunk
    query = """
    SELECT 
        question_type,
        is_correct,
        ai_feedback,
        COUNT(*) as attempts
    FROM reading_student_responses
    WHERE student_id = :student_id
    AND assignment_id = :assignment_id
    AND chunk_number = :chunk_number
    GROUP BY question_type, is_correct, ai_feedback
    ORDER BY question_type
    """
    
    result = await execute_query(
        query,
        {
            "student_id": current_user.id,
            "assignment_id": assignment_id,
            "chunk_number": chunk_number
        }
    )
    
    responses = result.all()
    
    # Determine which question to show
    summary_correct = any(r.question_type == "summary" and r.is_correct for r in responses)
    comp_correct = any(r.question_type == "comprehension" and r.is_correct for r in responses)
    
    if not responses or not summary_correct:
        # Show summary question
        question_type = QuestionType.SUMMARY
        attempt_number = sum(r.attempts for r in responses if r.question_type == "summary") + 1
        previous_feedback = next(
            (r.ai_feedback for r in responses if r.question_type == "summary" and not r.is_correct),
            None
        )
    elif summary_correct and not comp_correct:
        # Show comprehension question
        question_type = QuestionType.COMPREHENSION
        attempt_number = sum(r.attempts for r in responses if r.question_type == "comprehension") + 1
        previous_feedback = next(
            (r.ai_feedback for r in responses if r.question_type == "comprehension" and not r.is_correct),
            None
        )
    else:
        # Both answered correctly
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Chunk already completed. Move to next chunk."
        )
    
    # Get or generate question
    progress_metadata = student_assignment.progress_metadata or {}
    difficulty_level = progress_metadata.get("difficulty_level", 5) if question_type == QuestionType.COMPREHENSION else None
    
    try:
        question = await umaread_service.get_or_generate_question(
            db, current_user.id, assignment_id, chunk_number,
            question_type, difficulty_level
        )
        
        return QuestionResponse(
            question_id=None,  # We don't expose internal IDs
            question_text=question.question_text,
            question_type=question_type,
            difficulty_level=question.difficulty_level,
            attempt_number=attempt_number,
            previous_feedback=previous_feedback
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generating question: {str(e)}"
        )


@router.post("/assignments/{assignment_id}/chunks/{chunk_number}/answer", response_model=SubmitAnswerResponse)
async def submit_answer(
    assignment_id: UUID,
    chunk_number: int,
    request: SubmitAnswerRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit an answer for evaluation"""
    # Determine question type from current state
    from app.core.database import execute_query
    
    query = """
    SELECT 
        MAX(CASE WHEN question_type = 'summary' AND is_correct THEN 1 ELSE 0 END) as summary_correct
    FROM reading_student_responses
    WHERE student_id = :student_id
    AND assignment_id = :assignment_id
    AND chunk_number = :chunk_number
    """
    
    result = await execute_query(
        query,
        {
            "student_id": current_user.id,
            "assignment_id": assignment_id,
            "chunk_number": chunk_number
        }
    )
    
    row = result.first()
    question_type = QuestionType.COMPREHENSION if row.summary_correct else QuestionType.SUMMARY
    
    # Get attempt number
    attempt_query = """
    SELECT COUNT(*) + 1 as attempt_number
    FROM reading_student_responses
    WHERE student_id = :student_id
    AND assignment_id = :assignment_id
    AND chunk_number = :chunk_number
    AND question_type = :question_type
    """
    
    attempt_result = await execute_query(
        attempt_query,
        {
            "student_id": current_user.id,
            "assignment_id": assignment_id,
            "chunk_number": chunk_number,
            "question_type": question_type.value
        }
    )
    
    attempt_number = attempt_result.scalar()
    
    # Create answer object
    answer = StudentAnswer(
        assignment_id=assignment_id,
        chunk_number=chunk_number,
        question_type=question_type,
        answer_text=request.answer_text,
        time_spent_seconds=request.time_spent_seconds,
        attempt_number=attempt_number
    )
    
    try:
        # Evaluate answer
        evaluation, can_proceed = await umaread_service.evaluate_answer(
            db, current_user.id, answer
        )
        
        # Determine next action
        if evaluation.is_correct:
            if question_type == QuestionType.SUMMARY:
                next_question = QuestionType.COMPREHENSION
            else:
                next_question = None  # Chunk complete
        else:
            next_question = question_type  # Retry same question
        
        # Check if difficulty changed
        student_assignment = await umaread_service.get_student_assignment(
            db, current_user.id, assignment_id
        )
        progress_metadata = student_assignment.progress_metadata or {}
        new_difficulty = progress_metadata.get("difficulty_level", 5)
        
        return SubmitAnswerResponse(
            is_correct=evaluation.is_correct,
            feedback=evaluation.feedback_text + "\n\n" + evaluation.content_specific_feedback,
            can_proceed=can_proceed,
            next_question_type=next_question,
            difficulty_changed=evaluation.suggested_difficulty_change.value != 0,
            new_difficulty_level=new_difficulty if evaluation.suggested_difficulty_change.value != 0 else None
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error evaluating answer: {str(e)}"
        )


@router.get("/assignments/{assignment_id}/progress", response_model=StudentProgress)
async def get_progress(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed progress for an assignment"""
    try:
        return await umaread_service.get_student_progress(
            db, current_user.id, assignment_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.post("/assignments/{assignment_id}/cache/flush")
async def flush_cache(
    assignment_id: UUID,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Flush question cache for an assignment (teachers only)"""
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can flush question cache"
        )
    
    try:
        count = await umaread_service.flush_question_cache(
            db, current_user.id, assignment_id, reason
        )
        
        return {
            "message": f"Successfully flushed {count} cached questions",
            "assignment_id": assignment_id,
            "questions_flushed": count
        }
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
"""
UMARead API with hybrid Redis + PostgreSQL storage
"""
from typing import Optional, Dict, Any, List
from uuid import UUID
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, and_, func, or_, update
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.user import User
from app.models.reading import ReadingAssignment, ReadingChunk, AssignmentImage
from app.models.umaread import UmareadStudentResponse, UmareadChunkProgress, UmareadAssignmentProgress
from app.models.classroom import StudentAssignment, ClassroomAssignment, Classroom, StudentEvent
from app.utils.supabase_deps import get_current_user_supabase as get_current_user
from app.schemas.umaread import ChunkResponse, AssignmentStartResponse
from app.services.umaread_simple import UMAReadService
from app.services.question_generation import generate_questions_for_chunk, Question
from app.services.answer_evaluation import evaluate_answer, should_increase_difficulty
from app.services.text_simplification import simplify_chunk_text
import bcrypt
import re


router = APIRouter(prefix="/umaread/v2", tags=["umaread-v2"])
umaread_service = UMAReadService()


@router.get("/assignments/{assignment_id}/start", response_model=AssignmentStartResponse)
async def start_assignment(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start or resume a reading assignment with hybrid storage"""
    
    # Get or create assignment progress
    progress_result = await db.execute(
        select(UmareadAssignmentProgress)
        .where(
            and_(
                UmareadAssignmentProgress.student_id == current_user.id,
                UmareadAssignmentProgress.assignment_id == assignment_id
            )
        )
    )
    progress = progress_result.scalar_one_or_none()
    
    if not progress:
        # Create new progress record
        assignment_info = await umaread_service.start_assignment(
            db, current_user.id, assignment_id
        )
        
        # Get the student assignment ID
        student_assignment_result = await db.execute(
            select(StudentAssignment.id)
            .where(
                and_(
                    StudentAssignment.student_id == current_user.id,
                    StudentAssignment.assignment_id == assignment_id
                )
            )
        )
        student_assignment_id = student_assignment_result.scalar()
        
        progress = UmareadAssignmentProgress(
            student_id=current_user.id,
            assignment_id=assignment_id,
            student_assignment_id=student_assignment_id,
            current_chunk=1,
            total_chunks_completed=0,
            current_difficulty_level=assignment_info.difficulty_level
        )
        db.add(progress)
        await db.commit()
        await db.refresh(progress)
        
        # Redis session initialization removed - using DB only
    else:
        # Update last activity
        progress.last_activity_at = datetime.utcnow()
        await db.commit()
    
    # Redis activity update removed - using DB only
    
    # Get assignment details
    assignment = await db.get(ReadingAssignment, assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    # Get total chunks
    chunk_count = await db.execute(
        select(func.count(ReadingChunk.id))
        .where(ReadingChunk.assignment_id == assignment_id)
    )
    total_chunks = chunk_count.scalar() or 0
    
    return AssignmentStartResponse(
        assignment_id=assignment_id,
        title=assignment.assignment_title,
        author=assignment.author,
        total_chunks=total_chunks,
        current_chunk=progress.current_chunk,
        difficulty_level=progress.current_difficulty_level,
        status="completed" if progress.completed_at else "in_progress"
    )


@router.get("/assignments/{assignment_id}/chunks/{chunk_number}", response_model=ChunkResponse)
async def get_chunk(
    assignment_id: UUID,
    chunk_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get chunk content"""
    return await umaread_service.get_chunk_content(
        db, assignment_id, chunk_number
    )


@router.get("/assignments/{assignment_id}/chunks/{chunk_number}/question")
async def get_current_question(
    assignment_id: UUID,
    chunk_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current question for a chunk using hybrid storage"""
    
    # Check chunk progress in database
    chunk_progress_result = await db.execute(
        select(UmareadChunkProgress)
        .where(
            and_(
                UmareadChunkProgress.student_id == current_user.id,
                UmareadChunkProgress.assignment_id == assignment_id,
                UmareadChunkProgress.chunk_number == chunk_number
            )
        )
    )
    chunk_progress = chunk_progress_result.scalar_one_or_none()
    
    # Check if chunk is already complete (both questions must be complete)
    if chunk_progress and chunk_progress.summary_completed and chunk_progress.comprehension_completed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This chunk has already been completed. Please move to the next section."
        )
    
    # Get state from DB progress
    state = None
    if chunk_progress and chunk_progress.summary_completed:
        state = "summary_complete"
    
    # Get difficulty from Redis or DB
    difficulty = None  # Redis lookup removed
    if not difficulty:
        # Get from DB
        progress = await db.execute(
            select(UmareadAssignmentProgress)
            .where(
                and_(
                    UmareadAssignmentProgress.student_id == current_user.id,
                    UmareadAssignmentProgress.assignment_id == assignment_id
                )
            )
        )
        progress_record = progress.scalar_one_or_none()
        difficulty = progress_record.current_difficulty_level if progress_record else 3
        # Redis difficulty update removed
    
    # Get assignment and chunk
    assignment = await db.get(ReadingAssignment, assignment_id)
    chunk_result = await db.execute(
        select(ReadingChunk).where(
            and_(
                ReadingChunk.assignment_id == assignment_id,
                ReadingChunk.chunk_order == chunk_number
            )
        )
    )
    chunk = chunk_result.scalar_one_or_none()
    
    if not chunk:
        raise HTTPException(status_code=404, detail=f"Chunk {chunk_number} not found")
    
    # Generate or get cached questions
    cached_questions = None  # Redis cache removed
    
    # Always generate questions since we don't have Redis cache
    questions = await generate_questions_for_chunk(
        chunk, assignment, difficulty, db
    )
    cached_questions = {
        "summary": questions.summary_question.dict(),
        "comprehension": questions.comprehension_question.dict()
    }
    
    # Return appropriate question based on state
    if state == "summary_complete":
        question = cached_questions["comprehension"]
        return {
            "question_id": None,
            "question_text": question["question"],
            "question_type": "comprehension",
            "difficulty_level": difficulty,
            "attempt_number": 1,
            "previous_feedback": None
        }
    else:
        question = cached_questions["summary"]
        return {
            "question_id": None,
            "question_text": question["question"],
            "question_type": "summary",
            "difficulty_level": None,
            "attempt_number": 1,
            "previous_feedback": None
        }


@router.post("/assignments/{assignment_id}/chunks/{chunk_number}/answer")
async def submit_answer(
    assignment_id: UUID,
    chunk_number: int,
    answer_data: dict,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit answer with hybrid storage"""
    
    # Rate limiting check removed - consider implementing DB-based rate limiting
    if False:  # Rate limiting disabled
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many submissions. Please wait before trying again."
        )
    
    # Extract and validate answer
    student_answer = answer_data.get("answer_text", "").strip()
    time_spent = answer_data.get("time_spent_seconds", 0)
    
    if len(student_answer) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Answer must be at least 10 characters long"
        )
    
    if len(student_answer) > 500:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Answer must not exceed 500 characters"
        )
    
    # Get current state and difficulty from database
    chunk_progress_result = await db.execute(
        select(UmareadChunkProgress)
        .where(
            and_(
                UmareadChunkProgress.student_id == current_user.id,
                UmareadChunkProgress.assignment_id == assignment_id,
                UmareadChunkProgress.chunk_number == chunk_number
            )
        )
    )
    chunk_progress = chunk_progress_result.scalar_one_or_none()
    
    # Determine state based on chunk progress
    state = None
    if chunk_progress and chunk_progress.summary_completed:
        state = "summary_complete"
    
    # Get difficulty from assignment progress
    progress_result = await db.execute(
        select(UmareadAssignmentProgress)
        .where(
            and_(
                UmareadAssignmentProgress.student_id == current_user.id,
                UmareadAssignmentProgress.assignment_id == assignment_id
            )
        )
    )
    progress = progress_result.scalar_one_or_none()
    difficulty = progress.current_difficulty_level if progress else 3
    
    # Get cached questions for evaluation
    cached_questions = None  # Redis cache removed
    
    # Generate questions for evaluation since we don't have Redis cache
    if not cached_questions:
        # Get assignment and chunk
        assignment = await db.get(ReadingAssignment, assignment_id)
        chunk_result = await db.execute(
            select(ReadingChunk).where(
                and_(
                    ReadingChunk.assignment_id == assignment_id,
                    ReadingChunk.chunk_order == chunk_number
                )
            )
        )
        chunk = chunk_result.scalar_one_or_none()
        
        # Generate questions
        questions = await generate_questions_for_chunk(
            chunk, assignment, difficulty, db
        )
        cached_questions = {
            "summary": questions.summary_question.dict(),
            "comprehension": questions.comprehension_question.dict()
        }
    
    # Determine question type
    is_summary = state != "summary_complete"
    question_type = "summary" if is_summary else "comprehension"
    current_question = cached_questions[question_type]
    
    # Get assignment and chunk for evaluation
    assignment = await db.get(ReadingAssignment, assignment_id)
    chunk_result = await db.execute(
        select(ReadingChunk).where(
            and_(
                ReadingChunk.assignment_id == assignment_id,
                ReadingChunk.chunk_order == chunk_number
            )
        )
    )
    chunk = chunk_result.scalar_one_or_none()
    
    # Check for bypass code using unified validation
    from app.services.bypass_validation import validate_bypass_code
    
    print(f"DEBUG: Checking bypass for answer: {student_answer}, assignment: {assignment_id}")
    bypass_valid, bypass_type, teacher_id = await validate_bypass_code(
        db=db,
        student_id=current_user.id,
        answer_text=student_answer,
        context_type="umaread",
        context_id=str(assignment_id),
        assignment_id=assignment_id
    )
    print(f"DEBUG: Bypass result - valid: {bypass_valid}, type: {bypass_type}, teacher: {teacher_id}")
    
    # Check if rate limited
    if bypass_type == "rate_limited":
        return {
            "is_correct": False,
            "feedback": "Too many bypass attempts. Please wait an hour before trying again or answer the question normally.",
            "can_proceed": False,
            "next_question_type": None,
            "difficulty_changed": False,
            "new_difficulty_level": difficulty
        }
    
    if bypass_valid:
        # Bypass successful - mark answer as correct and continue
        # Count previous attempts to get the correct attempt number
        attempt_count_result = await db.execute(
            select(func.count(UmareadStudentResponse.id))
            .where(
                and_(
                    UmareadStudentResponse.student_id == current_user.id,
                    UmareadStudentResponse.assignment_id == assignment_id,
                    UmareadStudentResponse.chunk_number == chunk_number,
                    UmareadStudentResponse.question_type == question_type
                )
            )
        )
        attempt_count = attempt_count_result.scalar() or 0
        
        # Store successful response
        response = UmareadStudentResponse(
            student_id=current_user.id,
            assignment_id=assignment_id,
            chunk_number=chunk_number,
            question_type=question_type,
            question_text=current_question["question"],
            student_answer=student_answer,
            is_correct=True,
            ai_feedback="Instructor override accepted. Moving to next question.",
            attempt_number=attempt_count + 1,
            difficulty_level=difficulty
        )
        db.add(response)
        
        # Get or create chunk progress
        chunk_progress_result = await db.execute(
            select(UmareadChunkProgress).where(
                and_(
                    UmareadChunkProgress.student_id == current_user.id,
                    UmareadChunkProgress.assignment_id == assignment_id,
                    UmareadChunkProgress.chunk_number == chunk_number
                )
            )
        )
        chunk_progress = chunk_progress_result.scalar_one_or_none()
        
        if not chunk_progress:
            chunk_progress = UmareadChunkProgress(
                student_id=current_user.id,
                assignment_id=assignment_id,
                chunk_number=chunk_number,
                current_difficulty_level=difficulty
            )
            db.add(chunk_progress)
        
        # Update progress based on question type
        if question_type == "summary":
            chunk_progress.summary_completed = True
            # Redis state update removed
        else:  # comprehension
            chunk_progress.comprehension_completed = True
            chunk_progress.completed_at = datetime.utcnow()
            # Redis state clear removed
        
        await db.commit()
        
        # Determine next action
        if question_type == "summary":
            # Just completed summary, move to comprehension
            return {
                "is_correct": True,
                "feedback": "Instructor override accepted. Moving to next question.",
                "can_proceed": False,
                "next_question_type": "comprehension",
                "difficulty_changed": False,
                "new_difficulty_level": difficulty
            }
        else:
            # Check if there are more chunks
            total_chunks_result = await db.execute(
                select(func.count(ReadingChunk.id))
                .where(ReadingChunk.assignment_id == assignment_id)
            )
            total_chunks = total_chunks_result.scalar()
            
            # Check if assignment is complete
            assignment_complete = chunk_number >= total_chunks
            
            # Update assignment progress for bypass completion
            update_values = {
                "total_chunks_completed": UmareadAssignmentProgress.total_chunks_completed + 1,
                "current_chunk": chunk_number + 1
            }
            
            if assignment_complete:
                update_values["completed_at"] = datetime.utcnow()
            
            await db.execute(
                update(UmareadAssignmentProgress)
                .where(
                    and_(
                        UmareadAssignmentProgress.student_id == current_user.id,
                        UmareadAssignmentProgress.assignment_id == assignment_id
                    )
                )
                .values(**update_values)
            )
            await db.commit()
            
            return {
                "is_correct": True,
                "feedback": "Instructor override accepted. Assignment completed!" if assignment_complete else "Instructor override accepted. Moving to next question.",
                "can_proceed": True,
                "next_question_type": None,
                "difficulty_changed": False,
                "new_difficulty_level": difficulty,
                "assignment_complete": assignment_complete
            }
    
    # If not a bypass, continue with normal evaluation
    
    # Evaluate answer
    # Create a Question object from the cached question data
    question_obj = Question(
        question=current_question["question"],
        answer=current_question.get("expected_answer_elements", [""])[0] if current_question.get("expected_answer_elements") else "",
        question_type=question_type
    )
    
    evaluation = await evaluate_answer(
        question=question_obj,
        student_answer=student_answer,
        difficulty_level=difficulty,
        chunk=chunk,
        assignment=assignment,
        db=db
    )
    
    # Count previous attempts for this question type
    attempt_count_result = await db.execute(
        select(func.count(UmareadStudentResponse.id))
        .where(
            and_(
                UmareadStudentResponse.student_id == current_user.id,
                UmareadStudentResponse.assignment_id == assignment_id,
                UmareadStudentResponse.chunk_number == chunk_number,
                UmareadStudentResponse.question_type == question_type
            )
        )
    )
    previous_attempts = attempt_count_result.scalar() or 0
    current_attempt = previous_attempts + 1
    
    # Save response to database
    response = UmareadStudentResponse(
        student_id=current_user.id,
        assignment_id=assignment_id,
        chunk_number=chunk_number,
        question_type=question_type,
        question_text=current_question["question"],
        student_answer=student_answer,
        is_correct=evaluation.is_correct,
        ai_feedback=evaluation.feedback,
        difficulty_level=difficulty if question_type == "comprehension" else None,
        time_spent_seconds=time_spent,
        attempt_number=current_attempt
    )
    db.add(response)
    
    # Update progress based on result (reuse chunk_progress from earlier query)
    chunk_progress_record = chunk_progress
    
    if not chunk_progress_record:
        chunk_progress_record = UmareadChunkProgress(
            student_id=current_user.id,
            assignment_id=assignment_id,
            chunk_number=chunk_number,
            current_difficulty_level=difficulty
        )
        db.add(chunk_progress_record)
    
    # Handle correct answer
    if evaluation.is_correct:
        if is_summary:
            # Summary complete, move to comprehension
            chunk_progress_record.summary_completed = True
            # Redis state update removed
            
            await db.commit()
            
            return {
                "is_correct": True,
                "feedback": evaluation.feedback,
                "can_proceed": False,
                "next_question_type": "comprehension",
                "difficulty_changed": False,
                "new_difficulty_level": None
            }
        else:
            # Comprehension complete, chunk done
            chunk_progress_record.comprehension_completed = True
            chunk_progress_record.completed_at = datetime.utcnow()
            
            # Check if should increase difficulty
            should_increase = await should_increase_difficulty(
                current_difficulty=difficulty,
                question_type="comprehension",
                evaluation_result=evaluation
            )
            
            new_difficulty = difficulty
            if should_increase and difficulty < 8:
                new_difficulty = difficulty + 1
                chunk_progress_record.current_difficulty_level = new_difficulty
                
                # Redis difficulty update removed
                
                # Update assignment progress
                await db.execute(
                    update(UmareadAssignmentProgress)
                    .where(
                        and_(
                            UmareadAssignmentProgress.student_id == current_user.id,
                            UmareadAssignmentProgress.assignment_id == assignment_id
                        )
                    )
                    .values(current_difficulty_level=new_difficulty)
                )
            
            # Get total chunks to check if assignment is complete
            total_chunks_result = await db.execute(
                select(func.count(ReadingChunk.id))
                .where(ReadingChunk.assignment_id == assignment_id)
            )
            total_chunks = total_chunks_result.scalar() or 0
            
            # Check if this was the last chunk
            is_last_chunk = chunk_number >= total_chunks
            
            # Update assignment progress
            update_values = {
                "total_chunks_completed": UmareadAssignmentProgress.total_chunks_completed + 1,
                "current_chunk": chunk_number + 1
            }
            
            # If this was the last chunk, mark assignment as complete
            if is_last_chunk:
                update_values["completed_at"] = datetime.utcnow()
            
            await db.execute(
                update(UmareadAssignmentProgress)
                .where(
                    and_(
                        UmareadAssignmentProgress.student_id == current_user.id,
                        UmareadAssignmentProgress.assignment_id == assignment_id
                    )
                )
                .values(**update_values)
            )
            
            await db.commit()
            
            # Redis state clear removed
            
            return {
                "is_correct": True,
                "feedback": evaluation.feedback,
                "can_proceed": True,
                "next_question_type": None,
                "difficulty_changed": new_difficulty != difficulty,
                "new_difficulty_level": new_difficulty if new_difficulty != difficulty else None
            }
    else:
        # Incorrect answer
        await db.commit()
        
        return {
            "is_correct": False,
            "feedback": evaluation.feedback,
            "can_proceed": False,
            "next_question_type": question_type,
            "difficulty_changed": False,
            "new_difficulty_level": None
        }


@router.get("/assignments/{assignment_id}/progress")
async def get_progress(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get student progress for an assignment"""
    
    # Get assignment progress
    progress_result = await db.execute(
        select(UmareadAssignmentProgress)
        .where(
            and_(
                UmareadAssignmentProgress.student_id == current_user.id,
                UmareadAssignmentProgress.assignment_id == assignment_id
            )
        )
    )
    progress = progress_result.scalar_one_or_none()
    
    if not progress:
        return {
            "assignment_id": str(assignment_id),
            "student_id": str(current_user.id),
            "current_chunk": 1,
            "total_chunks": 0,
            "difficulty_level": 3,
            "chunks_completed": [],
            "chunk_scores": {},
            "status": "not_started",
            "last_activity": datetime.utcnow().isoformat()
        }
    
    # Get total chunks
    chunk_count = await db.execute(
        select(func.count(ReadingChunk.id))
        .where(ReadingChunk.assignment_id == assignment_id)
    )
    total_chunks = chunk_count.scalar() or 0
    
    # Get completed chunks list
    completed_chunks_result = await db.execute(
        select(UmareadChunkProgress.chunk_number)
        .where(
            and_(
                UmareadChunkProgress.student_id == current_user.id,
                UmareadChunkProgress.assignment_id == assignment_id,
                UmareadChunkProgress.comprehension_completed == True
            )
        )
        .order_by(UmareadChunkProgress.chunk_number)
    )
    completed_chunk_numbers = [row[0] for row in completed_chunks_result.fetchall()]
    
    # Get chunk scores
    chunk_scores_result = await db.execute(
        select(UmareadChunkProgress)
        .where(
            and_(
                UmareadChunkProgress.student_id == current_user.id,
                UmareadChunkProgress.assignment_id == assignment_id
            )
        )
    )
    chunk_scores = {}
    for chunk_progress in chunk_scores_result.scalars():
        chunk_scores[str(chunk_progress.chunk_number)] = {
            "chunk_number": chunk_progress.chunk_number,
            "summary_completed": chunk_progress.summary_completed,
            "comprehension_completed": chunk_progress.comprehension_completed,
            "summary_attempts": 0,  # Would need to count from responses table
            "comprehension_attempts": 0,  # Would need to count from responses table
            "time_spent_seconds": 0  # Would need to sum from responses table
        }
    
    return {
        "assignment_id": str(assignment_id),
        "student_id": str(current_user.id),
        "current_chunk": progress.current_chunk,
        "total_chunks": total_chunks,
        "difficulty_level": progress.current_difficulty_level,
        "chunks_completed": completed_chunk_numbers,
        "chunk_scores": chunk_scores,
        "status": "completed" if progress.completed_at else "in_progress",
        "last_activity": progress.last_activity_at.isoformat()
    }


@router.get("/assignments/{assignment_id}/progress/detailed")
async def get_detailed_progress(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed student progress including which chunks are completed"""
    
    # Get assignment progress
    progress_result = await db.execute(
        select(UmareadAssignmentProgress)
        .where(
            and_(
                UmareadAssignmentProgress.student_id == current_user.id,
                UmareadAssignmentProgress.assignment_id == assignment_id
            )
        )
    )
    progress = progress_result.scalar_one_or_none()
    
    if not progress:
        return {
            "chunks_completed": 0,
            "current_chunk": 1,
            "difficulty_level": 3,
            "is_complete": False,
            "completed_chunks": []
        }
    
    # Get list of completed chunks
    completed_chunks_result = await db.execute(
        select(UmareadChunkProgress.chunk_number)
        .where(
            and_(
                UmareadChunkProgress.student_id == current_user.id,
                UmareadChunkProgress.assignment_id == assignment_id,
                UmareadChunkProgress.comprehension_completed == True
            )
        )
        .order_by(UmareadChunkProgress.chunk_number)
    )
    completed_chunk_numbers = [row[0] for row in completed_chunks_result.fetchall()]
    
    # Get total chunks
    chunk_count = await db.execute(
        select(func.count(ReadingChunk.id))
        .where(ReadingChunk.assignment_id == assignment_id)
    )
    total_chunks = chunk_count.scalar() or 0
    
    return {
        "chunks_completed": progress.total_chunks_completed,
        "current_chunk": progress.current_chunk,
        "difficulty_level": progress.current_difficulty_level,
        "is_complete": progress.completed_at is not None,
        "total_chunks": total_chunks,
        "completed_chunks": completed_chunk_numbers
    }


@router.post("/assignments/{assignment_id}/chunks/{chunk_number}/simpler")
async def request_simpler_question(
    assignment_id: UUID,
    chunk_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Request a simpler question by reducing difficulty level"""
    
    # Get current difficulty level from DB
    current_difficulty = 3  # Default difficulty - TODO: get from DB
    
    # Can't go below level 1
    if current_difficulty <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already at the simplest difficulty level"
        )
    
    # Reduce difficulty by 1
    new_difficulty = current_difficulty - 1
    
    # Redis difficulty update removed
    
    # Redis cache clear removed
    
    # Get assignment and chunk for new question generation
    assignment = await db.get(ReadingAssignment, assignment_id)
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    chunk_result = await db.execute(
        select(ReadingChunk).where(
            and_(
                ReadingChunk.assignment_id == assignment_id,
                ReadingChunk.chunk_number == chunk_number
            )
        )
    )
    chunk = chunk_result.scalar_one_or_none()
    
    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Chunk not found"
        )
    
    # Generate new questions at lower difficulty
    questions = await generate_questions_for_chunk(
        chunk, assignment, new_difficulty, db
    )
    
    # Redis caching removed
    
    # Return the comprehension question (since this is only for comprehension questions)
    return {
        "question_id": None,
        "question_text": questions.comprehension_question.question,
        "question_type": "comprehension",
        "difficulty_level": new_difficulty,
        "attempt_number": 1,
        "previous_feedback": "Let's try a simpler question at difficulty level " + str(new_difficulty)
    }


@router.post("/assignments/{assignment_id}/chunks/{chunk_number}/crunch")
async def crunch_text(
    assignment_id: UUID,
    chunk_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get simplified version of chunk text for easier reading"""
    try:
        # Verify user has access to this assignment
        assignment_info = await umaread_service.start_assignment(
            db, current_user.id, assignment_id
        )
        
        # Get simplified text
        simplified_text = await simplify_chunk_text(
            db, str(assignment_id), chunk_number
        )
        
        # Log usage for analytics (optional)
        try:
            student_event = StudentEvent(
                id=str(uuid.uuid4()),
                student_id=current_user.id,
                assignment_id=assignment_id,
                event_type="crunch_text_used",
                event_data={
                    "chunk_number": chunk_number,
                    "timestamp": datetime.utcnow().isoformat()
                }
            )
            db.add(student_event)
            await db.commit()
        except Exception as e:
            print(f"Warning: Could not log crunch text usage: {e}")
            # Don't fail the request if logging fails
            pass
        
        return {
            "simplified_text": simplified_text,
            "chunk_number": chunk_number,
            "message": "This is a simplified version to help with reading comprehension."
        }
        
    except ValueError as e:
        error_message = str(e)
        if "join the classroom" in error_message or "Assignment not found" in error_message:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_message
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_message
            )
    except Exception as e:
        print(f"Error in crunch text: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to generate simplified text. Please try again."
        )

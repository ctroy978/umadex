"""
Simplified UMARead API endpoints for initial testing
"""
from typing import Optional
from uuid import UUID
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, and_, func
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.user import User
from app.models.reading import ReadingAssignment, ReadingChunk, AssignmentImage
from app.utils.deps import get_current_user
from app.schemas.umaread import (
    ChunkResponse,
    AssignmentStartResponse
)
from app.services.umaread_simple import UMAReadService
from app.services.question_generation import generate_questions_for_chunk, Question
from app.services.answer_evaluation import evaluate_answer, should_increase_difficulty
from app.services.bypass_validation import validate_bypass_code
from app.models.reading import AnswerEvaluation
from app.models.classroom import StudentAssignment, ClassroomAssignment, Classroom, StudentEvent
import bcrypt
import re


router = APIRouter(prefix="/umaread", tags=["umaread"])
umaread_service = UMAReadService()

# Simple in-memory state for tracking question progress (for testing)
question_state = {}
# Track difficulty levels per student
difficulty_state = {}
# Track completed assignments
completed_assignments = {}
# Track current questions for evaluation
current_questions = {}


@router.get("/assignments/{assignment_id}/start", response_model=AssignmentStartResponse)
async def start_assignment(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start or resume a reading assignment"""
    # Check if assignment is completed
    completion_key = f"{current_user.id}:{assignment_id}"
    
    try:
        response = await umaread_service.start_assignment(
            db, current_user.id, assignment_id
        )
        
        # Override status if completed
        if completed_assignments.get(completion_key):
            response.status = "completed"
            
        return response
    except ValueError as e:
        error_message = str(e)
        if "join the classroom" in error_message:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=error_message
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=error_message
            )


@router.get("/assignments/{assignment_id}/chunks/{chunk_number}", response_model=ChunkResponse)
async def get_chunk(
    assignment_id: UUID,
    chunk_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific chunk's content"""
    try:
        return await umaread_service.get_chunk_content(db, assignment_id, chunk_number)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )


@router.get("/assignments/{assignment_id}/chunks/{chunk_number}/question")
async def get_current_question(
    assignment_id: UUID,
    chunk_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current question for a chunk - AI-powered implementation"""
    # Get assignment info to determine starting difficulty
    try:
        assignment_info = await umaread_service.start_assignment(
            db, current_user.id, assignment_id
        )
        starting_difficulty = assignment_info.difficulty_level
    except:
        starting_difficulty = 3  # Fallback
    
    # Create keys for tracking state
    state_key = f"{current_user.id}:{assignment_id}:{chunk_number}"
    difficulty_key = f"{current_user.id}:{assignment_id}"
    
    # Get current difficulty (may have been adjusted from correct answers)
    difficulty = difficulty_state.get(difficulty_key, starting_difficulty)
    
    # Debug logging
    print(f"DEBUG: Getting question for user {current_user.id}, assignment {assignment_id}")
    print(f"DEBUG: Starting difficulty: {starting_difficulty}, Current difficulty: {difficulty}")
    print(f"DEBUG: Difficulty state: {difficulty_state}")
    
    # Get the assignment and chunk
    assignment_result = await db.execute(
        select(ReadingAssignment).where(ReadingAssignment.id == assignment_id)
    )
    assignment = assignment_result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chunk {chunk_number} not found"
        )
    
    # Generate questions using AI
    try:
        questions = await generate_questions_for_chunk(
            chunk, assignment, difficulty, db
        )
    except Exception as e:
        print(f"Error generating AI questions: {e}")
        # Fall back to mock questions
        if question_state.get(state_key) == "summary_complete":
            return {
                "question_id": None,
                "question_text": "What was the most important information in this passage?",
                "question_type": "comprehension",
                "difficulty_level": difficulty,
                "attempt_number": 1,
                "previous_feedback": None
            }
        else:
            return {
                "question_id": None,
                "question_text": "In 2-3 sentences, summarize what happened in this section.",
                "question_type": "summary",
                "difficulty_level": None,
                "attempt_number": 1,
                "previous_feedback": None
            }
    
    # Store the questions for evaluation
    question_key = f"{current_user.id}:{assignment_id}:{chunk_number}"
    current_questions[question_key] = questions
    
    # Debug: Log the current state
    print(f"DEBUG: Current question state for {state_key}: {question_state.get(state_key)}")
    print(f"DEBUG: All question states: {question_state}")
    
    # Check if summary has been completed
    if question_state.get(state_key) == "summary_complete":
        print(f"DEBUG: Returning comprehension question for {state_key}")
        # Return comprehension question
        return {
            "question_id": None,
            "question_text": questions.comprehension_question.question,
            "question_type": "comprehension",
            "difficulty_level": difficulty,
            "attempt_number": 1,
            "previous_feedback": None
        }
    else:
        print(f"DEBUG: Returning summary question for {state_key}")
        # Return summary question
        return {
            "question_id": None,
            "question_text": questions.summary_question.question,
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
    """Submit answer with AI evaluation"""
    # Create keys for tracking state
    state_key = f"{current_user.id}:{assignment_id}:{chunk_number}"
    difficulty_key = f"{current_user.id}:{assignment_id}"
    question_key = f"{current_user.id}:{assignment_id}:{chunk_number}"
    
    # Get student answer (frontend sends 'answer_text')
    student_answer = answer_data.get("answer_text", answer_data.get("answer", "")).strip()
    
    # Validate answer length
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
    
    # Debug logging
    print(f"DEBUG: Received answer data: {answer_data}")
    print(f"DEBUG: Extracted answer: '{student_answer}' (length: {len(student_answer)})")
    
    # Get current difficulty
    try:
        assignment_info = await umaread_service.start_assignment(
            db, current_user.id, assignment_id
        )
        starting_difficulty = assignment_info.difficulty_level
    except:
        starting_difficulty = 3
    
    current_difficulty = difficulty_state.get(difficulty_key, starting_difficulty)
    
    # Get the assignment and chunk for evaluation
    assignment_result = await db.execute(
        select(ReadingAssignment).where(ReadingAssignment.id == assignment_id)
    )
    assignment = assignment_result.scalar_one_or_none()
    
    chunk_result = await db.execute(
        select(ReadingChunk).where(
            and_(
                ReadingChunk.assignment_id == assignment_id,
                ReadingChunk.chunk_order == chunk_number
            )
        )
    )
    chunk = chunk_result.scalar_one_or_none()
    
    if not assignment or not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment or chunk not found"
        )
    
    # Get the current questions
    questions = current_questions.get(question_key)
    if not questions:
        # Fallback if questions weren't stored
        return {
            "is_correct": True,
            "feedback": "Let's continue to the next section.",
            "can_proceed": True,
            "next_question_type": None,
            "difficulty_changed": False,
            "new_difficulty_level": None
        }
    
    # Check if this is a bypass code attempt using unified validation
    bypass_valid, bypass_type, teacher_id = await validate_bypass_code(
        db=db,
        student_id=current_user.id,
        answer_text=student_answer,
        context_type="umaread",
        context_id=str(assignment_id),
        assignment_id=assignment_id
    )
    
    if bypass_valid:
        # Bypass successful - mark answer as correct and continue
        # Update state for this chunk
        current_state = question_state.get(state_key, "answering_summary")
        
        if current_state == "answering_summary" or current_state != "summary_complete":
            # Just completed summary, move to comprehension
            question_state[state_key] = "summary_complete"
            next_question_type = "comprehension"
        else:
            # Completed comprehension, ready to proceed
            question_state[state_key] = "complete"
            next_question_type = None
        
        await db.commit()
        
        return {
            "is_correct": True,
            "feedback": "Instructor override accepted. Moving to next question.",
            "can_proceed": next_question_type is None,
            "next_question_type": next_question_type,
            "difficulty_changed": False,
            "new_difficulty_level": current_difficulty
        }
    
    # Determine which question we're evaluating
    is_summary = question_state.get(state_key) != "summary_complete"
    current_question = questions.summary_question if is_summary else questions.comprehension_question
    
    # Evaluate the answer using AI
    try:
        evaluation = await evaluate_answer(
            question=current_question,
            student_answer=student_answer,
            difficulty_level=current_difficulty,
            chunk=chunk,
            assignment=assignment,
            db=db
        )
        
        # Store evaluation result
        eval_record = AnswerEvaluation(
            id=str(uuid.uuid4()),
            student_id=current_user.id,
            assignment_id=assignment_id,
            chunk_number=chunk_number,
            question_type="summary" if is_summary else "comprehension",
            question_text=current_question.question,
            student_answer=student_answer,
            is_correct=evaluation.is_correct,
            confidence=evaluation.confidence,
            feedback=evaluation.feedback,
            difficulty_level=current_difficulty,
            attempt_number=1
        )
        db.add(eval_record)
        await db.commit()
        
    except Exception as e:
        print(f"Error in AI evaluation: {e}")
        # Fallback evaluation
        evaluation = type('obj', (object,), {
            'is_correct': True,
            'feedback': "Good effort! Let's continue.",
            'confidence': 0.5
        })()
    
    # Process result based on question type
    if is_summary:
        # Summary question
        if evaluation.is_correct:
            question_state[state_key] = "summary_complete"
            print(f"DEBUG: Setting state to summary_complete for {state_key}")
            return {
                "is_correct": True,
                "feedback": evaluation.feedback,
                "can_proceed": False,
                "next_question_type": "comprehension",
                "difficulty_changed": False,
                "new_difficulty_level": None
            }
        else:
            return {
                "is_correct": False,
                "feedback": evaluation.feedback,
                "can_proceed": False,
                "next_question_type": "summary",
                "difficulty_changed": False,
                "new_difficulty_level": None
            }
    else:
        # Comprehension question
        if evaluation.is_correct:
            question_state[state_key] = "chunk_complete"
            
            # Check if we should increase difficulty
            should_increase = await should_increase_difficulty(
                current_difficulty=current_difficulty,
                question_type="comprehension",
                evaluation_result=evaluation
            )
            
            new_difficulty = current_difficulty
            if should_increase:
                new_difficulty = min(current_difficulty + 1, 8)
                difficulty_state[difficulty_key] = new_difficulty
            
            difficulty_changed = new_difficulty != current_difficulty
            
            # Check if this was the last chunk
            try:
                chunk_info = await umaread_service.get_chunk_content(db, assignment_id, chunk_number)
                if not chunk_info.has_next:
                    completion_key = f"{current_user.id}:{assignment_id}"
                    completed_assignments[completion_key] = True
            except:
                pass
            
            return {
                "is_correct": True,
                "feedback": evaluation.feedback,
                "can_proceed": True,
                "next_question_type": None,
                "difficulty_changed": difficulty_changed,
                "new_difficulty_level": new_difficulty if difficulty_changed else None
            }
        else:
            return {
                "is_correct": False,
                "feedback": evaluation.feedback,
                "can_proceed": False,
                "next_question_type": "comprehension",
                "difficulty_changed": False,
                "new_difficulty_level": None
            }


@router.get("/assignments/{assignment_id}/progress")
async def get_progress(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get student progress - mock implementation"""
    # Get assignment info to determine starting difficulty
    try:
        assignment_info = await umaread_service.start_assignment(
            db, current_user.id, assignment_id
        )
        starting_difficulty = assignment_info.difficulty_level
    except:
        starting_difficulty = 3  # Fallback
    
    # Get current tracked difficulty
    difficulty_key = f"{current_user.id}:{assignment_id}"
    current_difficulty = difficulty_state.get(difficulty_key, starting_difficulty)
    
    return {
        "assignment_id": str(assignment_id),
        "student_id": str(current_user.id),
        "current_chunk": 1,
        "total_chunks": 5,
        "difficulty_level": current_difficulty,
        "chunks_completed": [],
        "chunk_scores": {},
        "status": "in_progress",
        "last_activity": "2025-05-31T18:00:00Z"
    }


@router.post("/assignments/{assignment_id}/chunks/{chunk_number}/simpler")
async def request_simpler_question(
    assignment_id: UUID,
    chunk_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Request a simpler question by reducing difficulty level"""
    
    # Get current difficulty level
    difficulty_key = f"{current_user.id}:{assignment_id}"
    current_difficulty = difficulty_state.get(difficulty_key, 3)
    
    # Can't go below level 1
    if current_difficulty <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already at the simplest difficulty level"
        )
    
    # Reduce difficulty by 1
    new_difficulty = current_difficulty - 1
    difficulty_state[difficulty_key] = new_difficulty
    
    # Clear cached questions to force regeneration
    question_key = f"{current_user.id}:{assignment_id}:{chunk_number}"
    if question_key in question_cache:
        del question_cache[question_key]
    
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
    
    # Get current question state
    state_key = f"{current_user.id}:{assignment_id}:{chunk_number}"
    current_state = question_state.get(state_key, "summary_pending")
    
    # Generate new question at lower difficulty (only for comprehension)
    if current_state == "summary_complete":
        try:
            questions = await generate_questions_for_chunk(
                chunk, assignment, new_difficulty, db
            )
            
            # Cache the new questions
            question_cache[question_key] = questions
            
            # Return the comprehension question
            return {
                "question_id": None,
                "question_text": questions.comprehension_question.question,
                "question_type": "comprehension",
                "difficulty_level": new_difficulty,
                "attempt_number": 1,
                "previous_feedback": f"Let's try a simpler question at difficulty level {new_difficulty}"
            }
        except Exception as e:
            print(f"Error generating simpler question: {e}")
            # If AI generation fails, return a generic simpler question
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to generate simpler question. Please try again."
            )
    else:
        # Can't reduce difficulty for summary questions
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reduce difficulty for summary questions"
        )


@router.get("/test")
async def test_endpoint():
    """Test endpoint to verify UMARead API is working"""
    return {
        "message": "UMARead API is working",
        "endpoints": [
            "/umaread/assignments/{id}/start",
            "/umaread/assignments/{id}/chunks/{n}",
            "/umaread/test"
        ]
    }
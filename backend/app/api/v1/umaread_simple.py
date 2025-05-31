"""
Simplified UMARead API endpoints for initial testing
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
    AssignmentStartResponse
)
from app.services.umaread_simple import UMAReadService


router = APIRouter(prefix="/umaread", tags=["umaread"])
umaread_service = UMAReadService()

# Simple in-memory state for tracking question progress (for testing)
question_state = {}
# Track difficulty levels per student
difficulty_state = {}
# Track completed assignments
completed_assignments = {}


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
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
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
    """Get current question for a chunk - mock implementation"""
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
    
    # Check if summary has been completed
    if question_state.get(state_key) == "summary_complete":
        # Return comprehension question based on difficulty level
        question_text = "What was the main character's motivation in this section?"  # Default
        
        if difficulty == 1:
            question_text = "What did the main character do in this section?"
        elif difficulty == 2:
            question_text = "Where did the events in this section take place?"
        elif difficulty == 3:
            question_text = "Why did the character go to that location?"
        elif difficulty == 4:
            question_text = "What is the main idea of this section?"
        elif difficulty == 5:
            question_text = "Based on their actions, how do you think the character feels?"
        elif difficulty == 6:
            question_text = "What does the author imply but not directly state?"
        elif difficulty == 7:
            question_text = "Why is this event significant to the story?"
        elif difficulty == 8:
            question_text = "How does the author's use of imagery contribute to the theme?"
        
        return {
            "question_id": None,
            "question_text": question_text,
            "question_type": "comprehension",
            "difficulty_level": difficulty,
            "attempt_number": 1,
            "previous_feedback": None
        }
    else:
        # Return summary question
        return {
            "question_id": None,
            "question_text": "In 2-3 sentences, summarize what happened in this section.",
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
    """Submit answer - mock implementation"""
    # Create keys for tracking state
    state_key = f"{current_user.id}:{assignment_id}:{chunk_number}"
    difficulty_key = f"{current_user.id}:{assignment_id}"
    
    # Get current difficulty
    try:
        assignment_info = await umaread_service.start_assignment(
            db, current_user.id, assignment_id
        )
        starting_difficulty = assignment_info.difficulty_level
    except:
        starting_difficulty = 3
    
    current_difficulty = difficulty_state.get(difficulty_key, starting_difficulty)
    
    # Check current state to determine question type
    if question_state.get(state_key) == "summary_complete":
        # This is a comprehension answer
        question_state[state_key] = "chunk_complete"
        
        # Increase difficulty for next chunk (max 8)
        new_difficulty = min(current_difficulty + 1, 8)
        difficulty_changed = new_difficulty != current_difficulty
        if difficulty_changed:
            difficulty_state[difficulty_key] = new_difficulty
            
        # Debug logging
        print(f"DEBUG: Answer submitted - Comprehension question completed")
        print(f"DEBUG: Current difficulty: {current_difficulty}, New difficulty: {new_difficulty}")
        print(f"DEBUG: Updated difficulty state: {difficulty_state}")
        
        # Check if this was the last chunk
        try:
            chunk_info = await umaread_service.get_chunk_content(db, assignment_id, chunk_number)
            if not chunk_info.has_next:
                # Mark assignment as complete
                completion_key = f"{current_user.id}:{assignment_id}"
                completed_assignments[completion_key] = True
        except:
            pass
        
        return {
            "is_correct": True,
            "feedback": "Excellent analysis! You correctly answered the comprehension question.",
            "can_proceed": True,
            "next_question_type": None,
            "difficulty_changed": difficulty_changed,
            "new_difficulty_level": new_difficulty if difficulty_changed else None
        }
    else:
        # This is a summary answer
        question_state[state_key] = "summary_complete"
        return {
            "is_correct": True,
            "feedback": "Good summary! You captured the main points of this section.",
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
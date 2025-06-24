from datetime import datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID
import random
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.utils.deps import get_current_user
from app.models.user import User
from app.models.debate import (
    DebateAssignment, 
    StudentDebate as StudentDebateModel, 
    DebatePost as DebatePostModel, 
    DebateChallenge as DebateChallengeModel
)
from app.models.classroom import ClassroomAssignment, ClassroomStudent
from app.schemas.student_debate import (
    StudentDebate, StudentDebateCreate, StudentDebateUpdate,
    DebatePost, StudentPostCreate, DebateProgress, AssignmentOverview,
    ChallengeCreate, ChallengeResult, PostScore, AssignmentScore,
    PositionSelection, RoundFeedback
)
from app.services.student_debate_service import StudentDebateService
from app.services.debate_ai import DebateAIService
from app.services.content_moderation import ContentModerationService
from app.services.debate_scoring import DebateScoringService

router = APIRouter()
logger = logging.getLogger(__name__)

debate_service = StudentDebateService()
ai_service = DebateAIService()
moderation_service = ContentModerationService()
scoring_service = DebateScoringService()


@router.get("/assignments", response_model=List[AssignmentOverview])
async def get_student_debate_assignments(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all available debate assignments for the current student."""
    
    # Get all classroom assignments the student has access to
    query = (
        select(ClassroomAssignment)
        .join(ClassroomStudent, ClassroomStudent.classroom_id == ClassroomAssignment.classroom_id)
        .where(
            and_(
                ClassroomStudent.student_id == current_user.id,
                ClassroomStudent.is_active == True,
                ClassroomAssignment.assignment_type == 'debate',
                ClassroomAssignment.is_active == True,
                ClassroomAssignment.access_date <= datetime.now(timezone.utc)
            )
        )
        .options(selectinload(ClassroomAssignment.debate_assignment))
    )
    
    result = await db.execute(query)
    classroom_assignments = result.scalars().all()
    
    overviews = []
    for ca in classroom_assignments:
        # Get student's progress if exists
        student_debate = await debate_service.get_student_debate(
            db, current_user.id, ca.assignment_id, ca.id
        )
        
        debate_assignment = ca.debate_assignment
        
        overview = AssignmentOverview(
            assignment_id=debate_assignment.id,
            title=debate_assignment.title,
            topic=debate_assignment.topic[:100] + "..." if len(debate_assignment.topic) > 100 else debate_assignment.topic,
            difficulty_level=debate_assignment.difficulty_level,
            debate_format={
                "rounds_per_debate": debate_assignment.rounds_per_debate,
                "debate_count": debate_assignment.debate_count,
                "time_limit_hours": debate_assignment.time_limit_hours
            },
            status=student_debate.status if student_debate else 'not_started',
            debates_completed=student_debate.current_debate - 1 if student_debate and student_debate.status != 'not_started' else 0,
            current_debate_position=getattr(student_debate, f'debate_{student_debate.current_debate}_position', None) if student_debate else None,
            time_remaining=debate_service.calculate_time_remaining(student_debate) if student_debate else None,
            can_start=ca.access_date <= datetime.now(timezone.utc) < ca.due_date,
            access_date=ca.access_date,
            due_date=ca.due_date
        )
        overviews.append(overview)
    
    return overviews


@router.get("/{assignment_id}", response_model=AssignmentOverview)
async def get_debate_assignment_details(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a specific debate assignment."""
    
    # Verify student has access
    classroom_assignment = await debate_service.verify_student_access(
        db, current_user.id, assignment_id
    )
    
    if not classroom_assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found or access denied"
        )
    
    # Get the debate assignment
    result = await db.execute(
        select(DebateAssignment).where(DebateAssignment.id == assignment_id)
    )
    debate_assignment = result.scalar_one_or_none()
    
    if not debate_assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debate assignment not found"
        )
    student_debate = await debate_service.get_student_debate(
        db, current_user.id, assignment_id, classroom_assignment.id
    )
    
    # Use current time as default if dates are not set
    now = datetime.now(timezone.utc)
    access_date = classroom_assignment.start_date or now
    due_date = classroom_assignment.end_date or (now + timedelta(days=30))  # Default to 30 days from now
    
    return AssignmentOverview(
        assignment_id=debate_assignment.id,
        title=debate_assignment.title,
        topic=debate_assignment.topic,
        difficulty_level=debate_assignment.difficulty_level,
        debate_format={
            "rounds_per_debate": debate_assignment.rounds_per_debate,
            "debate_count": debate_assignment.debate_count,
            "time_limit_hours": debate_assignment.time_limit_hours
        },
        status=student_debate.status if student_debate else 'not_started',
        debates_completed=student_debate.current_debate - 1 if student_debate and student_debate.status != 'not_started' else 0,
        current_debate_position=getattr(student_debate, f'debate_{student_debate.current_debate}_position', None) if student_debate else None,
        time_remaining=debate_service.calculate_time_remaining(student_debate) if student_debate else None,
        can_start=access_date <= now < due_date,
        access_date=access_date,
        due_date=due_date
    )


@router.post("/{assignment_id}/start", response_model=StudentDebate)
async def start_debate_assignment(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start a debate assignment, creating initial student debate record."""
    
    # Verify access and get classroom assignment
    classroom_assignment = await debate_service.verify_student_access(
        db, current_user.id, assignment_id
    )
    
    if not classroom_assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found or access denied"
        )
    
    # Check if already started
    existing = await debate_service.get_student_debate(
        db, current_user.id, assignment_id, classroom_assignment.id
    )
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignment already started"
        )
    
    # Check if within access dates
    now = datetime.now(timezone.utc)
    if classroom_assignment.start_date and classroom_assignment.end_date:
        if now < classroom_assignment.start_date or now > classroom_assignment.end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Assignment is not currently accessible"
            )
    
    # Create student debate record
    student_debate = await debate_service.create_student_debate(
        db,
        student_id=current_user.id,
        assignment_id=assignment_id,
        classroom_assignment_id=classroom_assignment.id
    )
    
    return student_debate


@router.get("/{assignment_id}/current", response_model=DebateProgress)
async def get_current_debate_state(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the current state of the student's debate."""
    
    # Get student debate
    classroom_assignment = await debate_service.verify_student_access(
        db, current_user.id, assignment_id
    )
    
    student_debate = await debate_service.get_student_debate(
        db, current_user.id, assignment_id, classroom_assignment.id
    )
    
    if not student_debate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debate not started"
        )
    
    # Get current posts for the active debate
    current_posts = await debate_service.get_debate_posts(
        db, student_debate.id, student_debate.current_debate
    )
    
    # Determine next action
    next_action = await debate_service.determine_next_action(
        db, student_debate, current_posts
    )
    
    # Get available challenges if AI just posted
    available_challenges = []
    if current_posts and current_posts[-1].post_type == 'ai':
        available_challenges = debate_service.get_available_challenges()
    
    # Calculate time remaining
    time_remaining = None
    if student_debate.current_debate_deadline:
        time_remaining = int((student_debate.current_debate_deadline - datetime.now(timezone.utc)).total_seconds())
        time_remaining = max(0, time_remaining)
    
    return DebateProgress(
        student_debate=student_debate,
        current_posts=current_posts,
        available_challenges=available_challenges,
        time_remaining=time_remaining,
        can_submit_post=next_action == 'submit_post',
        next_action=next_action
    )


@router.post("/{assignment_id}/post", response_model=DebatePost)
async def submit_student_post(
    assignment_id: UUID,
    post: StudentPostCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit a student post in the current debate."""
    
    # Get student debate
    classroom_assignment = await debate_service.verify_student_access(
        db, current_user.id, assignment_id
    )
    
    student_debate = await debate_service.get_student_debate(
        db, current_user.id, assignment_id, classroom_assignment.id
    )
    
    if not student_debate or student_debate.status == 'not_started':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Debate not started"
        )
    
    if student_debate.status == 'completed':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Assignment already completed"
        )
    
    # Check time limit
    if student_debate.current_debate_deadline and datetime.now(timezone.utc) > student_debate.current_debate_deadline:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Time limit exceeded for current debate"
        )
    
    # Verify it's student's turn
    current_posts = await debate_service.get_debate_posts(
        db, student_debate.id, student_debate.current_debate
    )
    
    if current_posts and current_posts[-1].post_type == 'student':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Waiting for AI response"
        )
    
    # Content moderation
    moderation_result = await moderation_service.check_student_post(
        post.content, assignment_id
    )
    
    if moderation_result["flagged"] and moderation_result["requires_review"]:
        # Create post but mark as pending moderation
        student_post = await debate_service.create_student_post(
            db,
            student_debate_id=student_debate.id,
            debate_number=student_debate.current_debate,
            round_number=student_debate.current_round,
            content=post.content,
            word_count=post.word_count,
            moderation_status='pending'
        )
        
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail="Post submitted for review",
            headers={"X-Moderation-Status": "pending"}
        )
    
    # Create the student post
    student_post = await debate_service.create_student_post(
        db,
        student_debate_id=student_debate.id,
        debate_number=student_debate.current_debate,
        round_number=student_debate.current_round,
        content=post.content,
        word_count=post.word_count
    )
    
    # Get debate assignment for scoring
    result = await db.execute(
        select(DebateAssignment).where(DebateAssignment.id == assignment_id)
    )
    debate_assignment = result.scalar_one_or_none()
    
    if not debate_assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debate assignment not found"
        )
    
    # Score the post
    student_position = getattr(student_debate, f'debate_{student_debate.current_debate}_position', 'pro')
    post_score = await scoring_service.score_student_post(
        post.content,
        student_debate.current_round,
        debate_assignment.topic,
        debate_assignment.difficulty_level,
        debate_assignment.grade_level,
        student_position
    )
    
    # Update post with scores
    student_post = await debate_service.update_post_scores(
        db, student_post.id, post_score
    )
    
    # Get current statement count for this debate
    posts_in_debate = await db.execute(
        select(func.count(DebatePost.id))
        .where(
            and_(
                DebatePost.student_debate_id == student_debate.id,
                DebatePost.debate_number == student_debate.current_debate
            )
        )
    )
    statement_count = posts_in_debate.scalar() or 0
    
    # Check if AI should respond (only after statements 1 and 3)
    if statement_count in [1, 3]:  # Just posted statement 1 or 3
        # AI responds with statement 2 or 4
        
        # Load AI personalities and fallacy templates
        await ai_service.load_personalities(db)
        await ai_service.load_fallacy_templates(db)
        
        # Generate AI response
        logger.info(f"Generating AI response for debate {student_debate.current_debate}, statement {statement_count + 1}")
        try:
            should_include_fallacy = await debate_service.should_inject_fallacy(db, student_debate)
            logger.info(f"Should include fallacy: {should_include_fallacy}")
            
            # Get or create the debate point for this round
            if student_debate.current_debate == 1:
                debate_point = student_debate.debate_1_point or await debate_service.get_or_create_debate_point(
                    db, assignment_id, 1, 'pro'
                )
            elif student_debate.current_debate == 2:
                debate_point = student_debate.debate_2_point or await debate_service.get_or_create_debate_point(
                    db, assignment_id, 2, 'con'
                )
            else:
                debate_point = student_debate.debate_3_point or "The main point being debated in this round"
            
            ai_response = await ai_service.generate_ai_response(
                student_post=post.content,
                debate_context={
                    'topic': debate_assignment.topic,
                    'debate_point': debate_point,
                    'position': getattr(student_debate, f'debate_{student_debate.current_debate}_position'),
                    'round_number': student_debate.current_debate,
                    'statement_number': statement_count + 1,
                    'difficulty': debate_assignment.difficulty_level,
                    'grade_level': debate_assignment.grade_level,
                    'previous_posts': current_posts
                },
                should_include_fallacy=should_include_fallacy
            )
            logger.info(f"AI response generated successfully: {len(ai_response.get('content', ''))} chars")
        except Exception as e:
            logger.error(f"Error generating AI response: {str(e)}", exc_info=True)
            raise
        
        # Create AI post
        ai_post = await debate_service.create_ai_post(
            db,
            student_debate_id=student_debate.id,
            debate_number=student_debate.current_debate,
            round_number=student_debate.current_round,
            content=ai_response['content'],
            word_count=ai_response['word_count'],
            ai_personality=ai_response['personality'],
            is_fallacy=ai_response['is_fallacy'],
            fallacy_type=ai_response['fallacy_type']
        )
    elif statement_count == 5:  # Just posted statement 5 (final)
        # Round complete - generate coaching feedback and advance
        await debate_service.advance_debate_progress(db, student_debate)
    
    # For statements 2 and 4, no AI response needed
    
    return student_post


@router.post("/{assignment_id}/challenge", response_model=ChallengeResult)
async def submit_challenge(
    assignment_id: UUID,
    challenge: ChallengeCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit a challenge for the most recent AI post."""
    
    # Verify access and get post
    post = await debate_service.get_debate_post(db, challenge.post_id)
    
    if not post or post.post_type != 'ai':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid post for challenge"
        )
    
    # Check if already challenged
    existing_challenge = await debate_service.get_post_challenges(
        db, challenge.post_id, current_user.id
    )
    
    if existing_challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Post already challenged"
        )
    
    # Evaluate challenge
    result = await ai_service.evaluate_challenge(
        post,
        challenge.challenge_type,
        challenge.challenge_value,
        challenge.explanation
    )
    
    # Save challenge
    await debate_service.create_challenge(
        db,
        post_id=challenge.post_id,
        student_id=current_user.id,
        challenge_type=challenge.challenge_type,
        challenge_value=challenge.challenge_value,
        explanation=challenge.explanation,
        is_correct=result.is_correct,
        points_awarded=result.points_awarded,
        ai_feedback=result.ai_feedback
    )
    
    # Update post bonus points
    await debate_service.add_bonus_points(
        db, post.student_debate_id, result.points_awarded
    )
    
    return result


@router.post("/{assignment_id}/position", response_model=StudentDebate)
async def select_final_debate_position(
    assignment_id: UUID,
    position: PositionSelection,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Select position for the final debate."""
    
    # Get student debate
    classroom_assignment = await debate_service.verify_student_access(
        db, current_user.id, assignment_id
    )
    
    student_debate = await debate_service.get_student_debate(
        db, current_user.id, assignment_id, classroom_assignment.id
    )
    
    if not student_debate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debate not started"
        )
    
    # Verify we're at debate 3 and haven't chosen yet
    if student_debate.current_debate != 3 or student_debate.debate_3_position:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Position selection not available"
        )
    
    # Update position
    student_debate = await debate_service.update_student_debate(
        db,
        student_debate.id,
        StudentDebateUpdate(debate_3_position=position.position)
    )
    
    return student_debate


@router.get("/{assignment_id}/scores", response_model=AssignmentScore)
async def get_assignment_scores(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get current scores for the assignment."""
    
    # Get student debate
    classroom_assignment = await debate_service.verify_student_access(
        db, current_user.id, assignment_id
    )
    
    student_debate = await debate_service.get_student_debate(
        db, current_user.id, assignment_id, classroom_assignment.id
    )
    
    if not student_debate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debate not started"
        )
    
    # Calculate scores
    assignment_score = await scoring_service.calculate_assignment_scores(
        db, student_debate
    )
    
    return assignment_score


@router.get("/{assignment_id}/feedback/{debate_number}", response_model=RoundFeedback)
async def get_round_feedback(
    assignment_id: UUID,
    debate_number: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get AI coaching feedback for a completed round."""
    
    # Get student debate
    classroom_assignment = await debate_service.verify_student_access(
        db, current_user.id, assignment_id
    )
    
    student_debate = await debate_service.get_student_debate(
        db, current_user.id, assignment_id, classroom_assignment.id
    )
    
    if not student_debate:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Debate not started"
        )
    
    # Get feedback for the specified debate round
    from app.models.debate import DebateRoundFeedback
    result = await db.execute(
        select(DebateRoundFeedback)
        .where(
            and_(
                DebateRoundFeedback.student_debate_id == student_debate.id,
                DebateRoundFeedback.debate_number == debate_number
            )
        )
    )
    
    feedback = result.scalar_one_or_none()
    
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found for this round"
        )
    
    return feedback
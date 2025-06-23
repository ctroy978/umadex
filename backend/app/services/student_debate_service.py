from datetime import datetime, timedelta, timezone
from typing import List, Optional, Dict, Literal, Tuple
from uuid import UUID
import random
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.debate import (
    DebateAssignment, StudentDebate, DebatePost, DebateChallenge,
    AIPersonality, FallacyTemplate
)
from app.models.classroom import ClassroomAssignment, ClassroomStudent
from app.models.user import User
from app.core.config import settings
from app.schemas.student_debate import (
    StudentDebateCreate, StudentDebateUpdate, PostScore
)


class StudentDebateService:
    def __init__(self):
        self._challenge_options = [
            {'type': 'fallacy', 'value': 'ad_hominem', 'displayName': 'Ad Hominem', 'description': 'Attacks person, not argument'},
            {'type': 'fallacy', 'value': 'strawman', 'displayName': 'Strawman', 'description': 'Misrepresents your position'},
            {'type': 'fallacy', 'value': 'red_herring', 'displayName': 'Red Herring', 'description': 'Introduces irrelevant information'},
            {'type': 'fallacy', 'value': 'false_dichotomy', 'displayName': 'False Dichotomy', 'description': 'Only two options presented'},
            {'type': 'fallacy', 'value': 'slippery_slope', 'displayName': 'Slippery Slope', 'description': 'Extreme consequences assumed'},
            {'type': 'appeal', 'value': 'ethos', 'displayName': 'Ethos (Credibility)', 'description': 'Uses authority/credibility'},
            {'type': 'appeal', 'value': 'pathos', 'displayName': 'Pathos (Emotion)', 'description': 'Appeals to emotions'},
            {'type': 'appeal', 'value': 'logos', 'displayName': 'Logos (Logic)', 'description': 'Uses logical reasoning'}
        ]
    
    async def verify_student_access(
        self,
        db: AsyncSession,
        student_id: UUID,
        assignment_id: UUID
    ) -> Optional[ClassroomAssignment]:
        """Verify student has access to a debate assignment."""
        
        result = await db.execute(
            select(ClassroomAssignment)
            .join(ClassroomStudent, ClassroomStudent.classroom_id == ClassroomAssignment.classroom_id)
            .where(
                and_(
                    ClassroomStudent.student_id == student_id,
                    ClassroomStudent.removed_at.is_(None),
                    ClassroomAssignment.assignment_id == assignment_id,
                    ClassroomAssignment.assignment_type == 'debate'
                )
            )
        )
        
        return result.scalar_one_or_none()
    
    async def get_student_debate(
        self,
        db: AsyncSession,
        student_id: UUID,
        assignment_id: UUID,
        classroom_assignment_id: UUID
    ) -> Optional[StudentDebate]:
        """Get student's debate progress record."""
        
        result = await db.execute(
            select(StudentDebate)
            .where(
                and_(
                    StudentDebate.student_id == student_id,
                    StudentDebate.assignment_id == assignment_id,
                    StudentDebate.classroom_assignment_id == classroom_assignment_id
                )
            )
        )
        
        return result.scalar_one_or_none()
    
    async def create_student_debate(
        self,
        db: AsyncSession,
        student_id: UUID,
        assignment_id: UUID,
        classroom_assignment_id: UUID
    ) -> StudentDebate:
        """Create initial student debate record."""
        
        # Randomly assign positions for debates 1 and 2
        debate_1_position = random.choice(['pro', 'con'])
        debate_2_position = 'con' if debate_1_position == 'pro' else 'pro'
        
        # Initialize fallacy scheduling (will appear in one of the 3 debates)
        fallacy_debate = random.randint(1, 3)
        
        student_debate = StudentDebate(
            student_id=student_id,
            assignment_id=assignment_id,
            classroom_assignment_id=classroom_assignment_id,
            status='debate_1',
            current_debate=1,
            current_round=1,
            debate_1_position=debate_1_position,
            debate_2_position=debate_2_position,
            fallacy_counter=0,
            fallacy_scheduled_debate=fallacy_debate,
            assignment_started_at=datetime.now(timezone.utc),
            current_debate_started_at=datetime.now(timezone.utc),
            current_debate_deadline=datetime.now(timezone.utc) + timedelta(hours=8)
        )
        
        db.add(student_debate)
        await db.commit()
        await db.refresh(student_debate)
        
        return student_debate
    
    async def update_student_debate(
        self,
        db: AsyncSession,
        student_debate_id: UUID,
        updates: StudentDebateUpdate
    ) -> StudentDebate:
        """Update student debate record."""
        
        student_debate = await db.get(StudentDebate, student_debate_id)
        if not student_debate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student debate not found"
            )
        
        update_data = updates.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(student_debate, key, value)
        
        student_debate.updated_at = datetime.now(timezone.utc)
        
        await db.commit()
        await db.refresh(student_debate)
        
        return student_debate
    
    async def get_debate_posts(
        self,
        db: AsyncSession,
        student_debate_id: UUID,
        debate_number: Optional[int] = None
    ) -> List[DebatePost]:
        """Get posts for a specific debate."""
        
        query = select(DebatePost).where(DebatePost.student_debate_id == student_debate_id)
        
        if debate_number:
            query = query.where(DebatePost.debate_number == debate_number)
        
        query = query.order_by(DebatePost.debate_number, DebatePost.round_number, DebatePost.created_at)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_debate_post(
        self,
        db: AsyncSession,
        post_id: UUID
    ) -> Optional[DebatePost]:
        """Get a specific debate post."""
        
        return await db.get(DebatePost, post_id)
    
    async def create_student_post(
        self,
        db: AsyncSession,
        student_debate_id: UUID,
        debate_number: int,
        round_number: int,
        content: str,
        word_count: int,
        moderation_status: str = 'approved'
    ) -> DebatePost:
        """Create a student post."""
        
        post = DebatePost(
            student_debate_id=student_debate_id,
            debate_number=debate_number,
            round_number=round_number,
            post_type='student',
            content=content,
            word_count=word_count,
            moderation_status=moderation_status
        )
        
        db.add(post)
        await db.commit()
        await db.refresh(post)
        
        return post
    
    async def create_ai_post(
        self,
        db: AsyncSession,
        student_debate_id: UUID,
        debate_number: int,
        round_number: int,
        content: str,
        word_count: int,
        ai_personality: str,
        is_fallacy: bool = False,
        fallacy_type: Optional[str] = None
    ) -> DebatePost:
        """Create an AI post."""
        
        post = DebatePost(
            student_debate_id=student_debate_id,
            debate_number=debate_number,
            round_number=round_number,
            post_type='ai',
            content=content,
            word_count=word_count,
            ai_personality=ai_personality,
            is_fallacy=is_fallacy,
            fallacy_type=fallacy_type
        )
        
        db.add(post)
        await db.commit()
        await db.refresh(post)
        
        return post
    
    async def update_post_scores(
        self,
        db: AsyncSession,
        post_id: UUID,
        scores: PostScore
    ) -> DebatePost:
        """Update post with AI-generated scores."""
        
        post = await db.get(DebatePost, post_id)
        if not post:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post not found"
            )
        
        post.clarity_score = scores.clarity
        post.evidence_score = scores.evidence
        post.logic_score = scores.logic
        post.persuasiveness_score = scores.persuasiveness
        post.rebuttal_score = scores.rebuttal
        post.base_percentage = scores.base_percentage
        post.final_percentage = scores.final_percentage
        post.ai_feedback = scores.feedback
        
        await db.commit()
        await db.refresh(post)
        
        return post
    
    async def should_inject_fallacy(
        self,
        db: AsyncSession,
        student_debate: StudentDebate
    ) -> bool:
        """Determine if current AI response should include a fallacy."""
        
        # Check if fallacy is scheduled for this debate
        if student_debate.fallacy_scheduled_debate != student_debate.current_debate:
            return False
        
        # Check if we haven't already injected a fallacy in this debate
        result = await db.execute(
            select(func.count(DebatePost.id))
            .where(
                and_(
                    DebatePost.student_debate_id == student_debate.id,
                    DebatePost.debate_number == student_debate.current_debate,
                    DebatePost.is_fallacy == True
                )
            )
        )
        
        fallacy_count = result.scalar()
        
        # Only inject once per debate
        if fallacy_count > 0:
            return False
        
        # Random chance for which round (weighted towards middle rounds)
        if not student_debate.fallacy_scheduled_round:
            # Schedule it now
            total_rounds = 4  # Default, should get from assignment
            if student_debate.current_round == 1:
                # 20% chance in round 1
                return random.random() < 0.2
            elif student_debate.current_round == total_rounds:
                # 20% chance in last round
                return random.random() < 0.2
            else:
                # 60% chance in middle rounds
                return random.random() < 0.6
        else:
            return student_debate.current_round == student_debate.fallacy_scheduled_round
    
    async def advance_debate_progress(
        self,
        db: AsyncSession,
        student_debate: StudentDebate
    ):
        """Advance to next round or debate."""
        
        # Get debate format to know total rounds
        classroom_assignment = await db.get(ClassroomAssignment, student_debate.classroom_assignment_id)
        debate_assignment = await db.get(DebateAssignment, student_debate.assignment_id)
        
        total_rounds = debate_assignment.rounds_per_debate
        
        # Check if we need to advance round or debate
        posts_in_round = await db.execute(
            select(func.count(DebatePost.id))
            .where(
                and_(
                    DebatePost.student_debate_id == student_debate.id,
                    DebatePost.debate_number == student_debate.current_debate,
                    DebatePost.round_number == student_debate.current_round
                )
            )
        )
        
        # Check if round is complete (2 posts) OR if it's the final round and student posted
        posts_count = posts_in_round.scalar()
        is_final_round = student_debate.current_round >= total_rounds
        
        if posts_count >= 2 or (is_final_round and posts_count >= 1):  
            if student_debate.current_round < total_rounds:
                # Advance to next round
                student_debate.current_round += 1
            else:
                # Debate complete, move to next debate
                if student_debate.current_debate < 3:
                    student_debate.current_debate += 1
                    student_debate.current_round = 1
                    student_debate.status = f'debate_{student_debate.current_debate}'
                    student_debate.current_debate_started_at = datetime.now(timezone.utc)
                    student_debate.current_debate_deadline = datetime.now(timezone.utc) + timedelta(hours=8)
                    
                    # Update debate percentage
                    from app.services.debate_scoring import DebateScoringService
                    scoring_service = DebateScoringService()
                    await scoring_service.update_debate_percentage(
                        db, student_debate.id, student_debate.current_debate - 1
                    )
                else:
                    # All debates complete
                    student_debate.status = 'completed'
                    
                    # Calculate final grade
                    from app.services.debate_scoring import DebateScoringService
                    scoring_service = DebateScoringService()
                    await scoring_service.update_debate_percentage(
                        db, student_debate.id, 3
                    )
                    await scoring_service.calculate_final_grade(db, student_debate.id)
                
                # Increment fallacy counter after each debate
                student_debate.fallacy_counter += 1
                if student_debate.fallacy_counter >= 3:
                    student_debate.fallacy_counter = 0
        
        await db.commit()
    
    async def determine_next_action(
        self,
        db: AsyncSession,
        student_debate: StudentDebate,
        current_posts: List[DebatePost]
    ) -> Literal['submit_post', 'await_ai', 'choose_position', 'debate_complete', 'assignment_complete']:
        """Determine what action the student should take next."""
        
        if student_debate.status == 'completed':
            return 'assignment_complete'
        
        if student_debate.status == 'not_started':
            return 'submit_post'
        
        # Check if we need position selection for debate 3
        if student_debate.current_debate == 3 and not student_debate.debate_3_position:
            return 'choose_position'
        
        # Check last post type
        if not current_posts:
            return 'submit_post'
        
        last_post = current_posts[-1]
        
        if last_post.post_type == 'student':
            return 'await_ai'
        else:
            # Check if debate is complete
            debate_assignment = await db.get(DebateAssignment, student_debate.assignment_id)
            total_rounds = debate_assignment.rounds_per_debate
            
            if student_debate.current_round > total_rounds:
                return 'debate_complete'
            else:
                return 'submit_post'
    
    def calculate_time_remaining(self, student_debate: Optional[StudentDebate]) -> Optional[int]:
        """Calculate seconds remaining in current debate."""
        
        if not student_debate or not student_debate.current_debate_deadline:
            return None
        
        remaining = (student_debate.current_debate_deadline - datetime.now(timezone.utc)).total_seconds()
        return max(0, int(remaining))
    
    def get_available_challenges(self) -> List[Dict]:
        """Get list of available challenge options."""
        return self._challenge_options
    
    async def get_post_challenges(
        self,
        db: AsyncSession,
        post_id: UUID,
        student_id: UUID
    ) -> Optional[DebateChallenge]:
        """Check if student has already challenged a post."""
        
        result = await db.execute(
            select(DebateChallenge)
            .where(
                and_(
                    DebateChallenge.post_id == post_id,
                    DebateChallenge.student_id == student_id
                )
            )
        )
        
        return result.scalar_one_or_none()
    
    async def create_challenge(
        self,
        db: AsyncSession,
        post_id: UUID,
        student_id: UUID,
        challenge_type: str,
        challenge_value: str,
        explanation: Optional[str],
        is_correct: bool,
        points_awarded: Decimal,
        ai_feedback: str
    ) -> DebateChallenge:
        """Create a challenge record."""
        
        challenge = DebateChallenge(
            post_id=post_id,
            student_id=student_id,
            challenge_type=challenge_type,
            challenge_value=challenge_value,
            explanation=explanation,
            is_correct=is_correct,
            points_awarded=points_awarded,
            ai_feedback=ai_feedback
        )
        
        db.add(challenge)
        await db.commit()
        await db.refresh(challenge)
        
        return challenge
    
    async def add_bonus_points(
        self,
        db: AsyncSession,
        student_debate_id: UUID,
        points: Decimal
    ):
        """Add bonus points to the current round's student post."""
        
        # Get the most recent student post
        result = await db.execute(
            select(DebatePost)
            .where(
                and_(
                    DebatePost.student_debate_id == student_debate_id,
                    DebatePost.post_type == 'student'
                )
            )
            .order_by(DebatePost.created_at.desc())
            .limit(1)
        )
        
        post = result.scalar_one_or_none()
        
        if post:
            post.bonus_points = post.bonus_points + points
            post.final_percentage = post.base_percentage + post.bonus_points
            await db.commit()
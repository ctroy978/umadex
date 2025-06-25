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
    AIPersonality, FallacyTemplate, DebateRoundFeedback, AIDebatePoint
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
        
        # Fixed positions: Debate 1 = PRO, Debate 2 = CON, Debate 3 = student choice
        debate_1_position = 'pro'
        debate_2_position = 'con'
        
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
        moderation_status: str = 'approved',
        selected_technique: Optional[str] = None
    ) -> DebatePost:
        """Create a student post."""
        
        # Calculate statement number based on existing posts
        statement_number = await self._get_next_statement_number(db, student_debate_id, debate_number)
        
        post = DebatePost(
            student_debate_id=student_debate_id,
            debate_number=debate_number,
            round_number=round_number,
            statement_number=statement_number,
            post_type='student',
            content=content,
            word_count=word_count,
            moderation_status=moderation_status,
            selected_technique=selected_technique
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
        
        # Calculate statement number based on existing posts
        statement_number = await self._get_next_statement_number(db, student_debate_id, debate_number)
        
        post = DebatePost(
            student_debate_id=student_debate_id,
            debate_number=debate_number,
            round_number=round_number,
            statement_number=statement_number,
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
        
        # Update technique bonus if present
        if hasattr(scores, 'technique_bonus') and scores.technique_bonus is not None:
            post.technique_bonus_awarded = scores.technique_bonus
        
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
        
        # Check if current round is complete (5 statements)
        posts_in_round = await db.execute(
            select(func.count(DebatePost.id))
            .where(
                and_(
                    DebatePost.student_debate_id == student_debate.id,
                    DebatePost.debate_number == student_debate.current_debate
                )
            )
        )
        
        posts_count = posts_in_round.scalar()
        
        # Round is complete when we have 5 statements
        if posts_count >= 5:
            # Check if feedback already exists for this round
            if debate_assignment.coaching_enabled:
                # Check if feedback already exists
                existing_feedback = await db.execute(
                    select(DebateRoundFeedback)
                    .where(
                        and_(
                            DebateRoundFeedback.student_debate_id == student_debate.id,
                            DebateRoundFeedback.debate_number == student_debate.current_debate
                        )
                    )
                )
                
                # Only generate feedback if it doesn't exist yet
                if not existing_feedback.scalar_one_or_none():
                    await self._generate_round_feedback(db, student_debate.id, student_debate.current_debate)
            
            # Move to next debate
            if student_debate.current_debate < 3:
                student_debate.current_debate += 1
                student_debate.current_round = 1  # Always 1 round per debate now
                student_debate.status = f'debate_{student_debate.current_debate}'
                student_debate.current_debate_started_at = datetime.now(timezone.utc)
                student_debate.current_debate_deadline = datetime.now(timezone.utc) + timedelta(hours=debate_assignment.time_limit_hours)
                
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
        
        # Count posts in current debate
        posts_count = len([p for p in current_posts if p.debate_number == student_debate.current_debate])
        
        # Check if round is complete (5 statements)
        if posts_count >= 5:
            return 'debate_complete'
        
        # Determine based on statement pattern (student: 1,3,5; AI: 2,4)
        if posts_count == 0:  # No posts yet
            return 'submit_post'
        elif posts_count == 1:  # Student posted 1st
            return 'await_ai'
        elif posts_count == 2:  # AI posted 2nd
            return 'submit_post'
        elif posts_count == 3:  # Student posted 3rd
            return 'await_ai'
        elif posts_count == 4:  # AI posted 4th
            return 'submit_post'
        else:
            return 'debate_complete'
    
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
    
    async def _get_next_statement_number(
        self,
        db: AsyncSession,
        student_debate_id: UUID,
        debate_number: int
    ) -> int:
        """Get the next statement number for a debate."""
        result = await db.execute(
            select(func.count(DebatePost.id))
            .where(
                and_(
                    DebatePost.student_debate_id == student_debate_id,
                    DebatePost.debate_number == debate_number
                )
            )
        )
        count = result.scalar() or 0
        return count + 1
    
    async def _generate_round_feedback(
        self,
        db: AsyncSession,
        student_debate_id: UUID,
        debate_number: int
    ):
        """Generate AI coaching feedback after a round."""
        # Get all posts from this round
        posts = await self.get_debate_posts(db, student_debate_id, debate_number)
        
        # Get the student debate and assignment info
        student_debate = await db.get(StudentDebate, student_debate_id)
        debate_assignment = await db.get(DebateAssignment, student_debate.assignment_id)
        
        # Analyze student performance
        student_posts = [p for p in posts if p.post_type == 'student']
        
        # Generate coaching feedback using AI
        from app.services.debate_ai import DebateAIService
        ai_service = DebateAIService()
        
        # Calculate average scores
        avg_clarity = sum(p.clarity_score for p in student_posts if p.clarity_score) / len(student_posts)
        avg_evidence = sum(p.evidence_score for p in student_posts if p.evidence_score) / len(student_posts)
        avg_logic = sum(p.logic_score for p in student_posts if p.logic_score) / len(student_posts)
        
        # Generate feedback based on performance
        strengths = []
        improvements = []
        suggestions = []
        
        if avg_clarity >= Decimal('4.0'):
            strengths.append("Clear and well-structured arguments")
        else:
            improvements.append("Organize arguments more clearly")
            suggestions.append("Start each response with a clear thesis statement")
        
        if avg_evidence >= Decimal('4.0'):
            strengths.append("Strong use of evidence and examples")
        elif avg_evidence < Decimal('3.0'):
            improvements.append("Include more specific evidence")
            suggestions.append("Cite specific facts, statistics, or examples to support your points")
        
        if avg_logic >= Decimal('4.0'):
            strengths.append("Logical and coherent reasoning")
        else:
            improvements.append("Strengthen logical connections")
            suggestions.append("Use transitional phrases to connect your ideas")
        
        # Create feedback record
        feedback = DebateRoundFeedback(
            student_debate_id=student_debate_id,
            debate_number=debate_number,
            coaching_feedback=f"Round {debate_number} complete! You demonstrated {', '.join(strengths) if strengths else 'good effort'}. Focus on: {', '.join(improvements) if improvements else 'maintaining consistency'}.",
            strengths='; '.join(strengths) if strengths else None,
            improvement_areas='; '.join(improvements) if improvements else None,
            specific_suggestions='; '.join(suggestions) if suggestions else None
        )
        
        db.add(feedback)
        await db.commit()
    
    async def get_or_create_debate_point(
        self,
        db: AsyncSession,
        assignment_id: UUID,
        debate_number: int,
        position: str
    ) -> str:
        """Get or create a debate point for the AI."""
        # Check if we have a pre-generated point
        result = await db.execute(
            select(AIDebatePoint)
            .where(
                and_(
                    AIDebatePoint.assignment_id == assignment_id,
                    AIDebatePoint.debate_number == debate_number,
                    AIDebatePoint.position == position
                )
            )
            .limit(1)
        )
        
        existing_point = result.scalar_one_or_none()
        
        if existing_point:
            return existing_point.debate_point
        
        # Generate a new point based on the topic
        debate_assignment = await db.get(DebateAssignment, assignment_id)
        
        if not debate_assignment:
            # Return a generic point if assignment not found
            if position == 'pro':
                return "The primary argument in favor is the potential for positive change and improvement."
            else:
                return "The main concern is the risk of unintended negative consequences."
        
        # Default points based on position
        if position == 'pro':
            if debate_number == 1:
                return f"A key benefit of {debate_assignment.topic} is increased efficiency and effectiveness in achieving stated goals."
            else:
                return f"Supporting {debate_assignment.topic} leads to positive long-term outcomes for all stakeholders involved."
        else:
            if debate_number == 2:
                return f"The primary concern with {debate_assignment.topic} is the significant resource allocation required without guaranteed results."
            else:
                return f"Opposing {debate_assignment.topic} protects against unintended negative consequences and preserves existing systems."
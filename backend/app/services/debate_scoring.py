from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.debate import StudentDebate, DebatePost, DebateChallenge
from app.schemas.student_debate import PostScore, DebateScore, AssignmentScore
from app.services.debate_ai import DebateAIService


class DebateScoringService:
    def __init__(self):
        self.ai_service = DebateAIService()
    
    async def score_student_post(
        self,
        post_content: str,
        round_number: int,
        topic: str,
        difficulty: str,
        grade_level: str,
        student_position: str = 'pro',
        selected_technique: Optional[str] = None
    ) -> PostScore:
        """Score a student post using AI evaluation."""
        return await self.ai_service.evaluate_student_post(
            post_content,
            round_number,
            topic,
            difficulty,
            grade_level,
            student_position,
            selected_technique
        )
    
    async def calculate_debate_average(
        self,
        db: AsyncSession,
        student_debate_id: UUID,
        debate_number: int
    ) -> Decimal:
        """Calculate average percentage for a completed debate."""
        
        # Get all student posts for this debate
        result = await db.execute(
            select(DebatePost)
            .where(
                DebatePost.student_debate_id == student_debate_id,
                DebatePost.debate_number == debate_number,
                DebatePost.post_type == 'student'
            )
            .order_by(DebatePost.round_number)
        )
        posts = result.scalars().all()
        
        if not posts:
            return Decimal('0')
        
        # Calculate average of final percentages (which already include technique bonuses)
        total_percentage = sum(p.final_percentage for p in posts if p.final_percentage)
        post_count = len([p for p in posts if p.final_percentage])
        
        if post_count == 0:
            return Decimal('0')
        
        return total_percentage / post_count
    
    async def calculate_debate_scores(
        self,
        db: AsyncSession,
        student_debate_id: UUID,
        debate_number: int
    ) -> DebateScore:
        """Get detailed scores for a specific debate."""
        
        # Get all student posts
        result = await db.execute(
            select(DebatePost)
            .where(
                DebatePost.student_debate_id == student_debate_id,
                DebatePost.debate_number == debate_number,
                DebatePost.post_type == 'student'
            )
            .order_by(DebatePost.round_number)
        )
        posts = result.scalars().all()
        
        # Get total bonus points from challenges
        challenge_result = await db.execute(
            select(func.sum(DebateChallenge.points_awarded))
            .join(DebatePost, DebatePost.id == DebateChallenge.post_id)
            .where(
                DebatePost.student_debate_id == student_debate_id,
                DebatePost.debate_number == debate_number
            )
        )
        total_bonus = challenge_result.scalar() or Decimal('0')
        
        # Convert posts to scores
        post_scores = []
        for post in posts:
            if post.clarity_score:
                post_scores.append(PostScore(
                    clarity=post.clarity_score,
                    evidence=post.evidence_score,
                    logic=post.logic_score,
                    persuasiveness=post.persuasiveness_score,
                    rebuttal=post.rebuttal_score,
                    base_percentage=post.base_percentage,
                    bonus_points=post.bonus_points,
                    final_percentage=post.final_percentage,
                    feedback=post.ai_feedback or ""
                ))
        
        # Calculate averages
        avg_percentage = await self.calculate_debate_average(db, student_debate_id, debate_number)
        final_percentage = avg_percentage + total_bonus
        
        return DebateScore(
            debate_number=debate_number,
            posts=post_scores,
            average_percentage=avg_percentage,
            total_bonus_points=total_bonus,
            final_percentage=min(final_percentage, Decimal('105'))  # Cap at 105%
        )
    
    async def calculate_assignment_scores(
        self,
        db: AsyncSession,
        student_debate: StudentDebate
    ) -> AssignmentScore:
        """Calculate all scores for a debate assignment."""
        
        # Get scores for each completed debate
        debate_scores = []
        for i in range(1, 4):
            if getattr(student_debate, f'debate_{i}_percentage') is not None:
                score = await self.calculate_debate_scores(db, student_debate.id, i)
                debate_scores.append(score)
        
        # Calculate bonuses
        improvement_bonus = Decimal('0')
        consistency_bonus = Decimal('0')
        
        if len(debate_scores) == 3:
            # Improvement bonus: +3% if debate 3 > average of debates 1&2
            avg_first_two = (debate_scores[0].final_percentage + debate_scores[1].final_percentage) / 2
            if debate_scores[2].final_percentage > avg_first_two:
                improvement_bonus = Decimal('3.0')
            
            # Consistency bonus: +2% if all debates within 15% of each other
            all_percentages = [s.final_percentage for s in debate_scores]
            score_range = max(all_percentages) - min(all_percentages)
            if score_range <= Decimal('15.0'):
                consistency_bonus = Decimal('2.0')
        
        # Calculate final grade
        if debate_scores:
            base_grade = sum(s.final_percentage for s in debate_scores) / len(debate_scores)
            final_grade = base_grade + improvement_bonus + consistency_bonus
            final_grade = min(final_grade, Decimal('105.0'))  # Cap at 105%
        else:
            final_grade = Decimal('0')
        
        return AssignmentScore(
            debate_1_score=debate_scores[0] if len(debate_scores) > 0 else None,
            debate_2_score=debate_scores[1] if len(debate_scores) > 1 else None,
            debate_3_score=debate_scores[2] if len(debate_scores) > 2 else None,
            improvement_bonus=improvement_bonus,
            consistency_bonus=consistency_bonus,
            final_grade=final_grade
        )
    
    async def update_debate_percentage(
        self,
        db: AsyncSession,
        student_debate_id: UUID,
        debate_number: int
    ):
        """Update the stored percentage for a completed debate."""
        
        percentage = await self.calculate_debate_average(db, student_debate_id, debate_number)
        
        # Update the appropriate field
        student_debate = await db.get(StudentDebate, student_debate_id)
        if student_debate:
            if debate_number == 1:
                student_debate.debate_1_percentage = percentage
            elif debate_number == 2:
                student_debate.debate_2_percentage = percentage
            elif debate_number == 3:
                student_debate.debate_3_percentage = percentage
            
            await db.commit()
    
    async def calculate_final_grade(
        self,
        db: AsyncSession,
        student_debate_id: UUID
    ):
        """Calculate and update the final grade for a completed assignment."""
        
        student_debate = await db.get(StudentDebate, student_debate_id)
        if not student_debate:
            return
        
        scores = await self.calculate_assignment_scores(db, student_debate)
        student_debate.final_percentage = scores.final_grade
        
        await db.commit()
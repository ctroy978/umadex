"""
Vocabulary practice activity service
Manages student progress through vocabulary practice games
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update
from sqlalchemy.orm import selectinload
import json
import logging

from app.models.vocabulary import VocabularyList, VocabularyWord
from app.models.vocabulary_practice import (
    VocabularyGameQuestion, 
    VocabularyPracticeProgress,
    VocabularyGameAttempt
)
from app.models.classroom import ClassroomAssignment
from app.models.user import User
from app.services.vocabulary_game_generator import VocabularyGameGenerator

logger = logging.getLogger(__name__)


class VocabularyPracticeService:
    """Service for managing vocabulary practice activities"""
    
    PASSING_THRESHOLD = 0.7  # 70% to pass
    ASSIGNMENTS_TO_COMPLETE = 3  # Need 3 of 4 to unlock test
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_or_create_practice_progress(
        self,
        student_id: UUID,
        vocabulary_list_id: UUID,
        classroom_assignment_id: int
    ) -> VocabularyPracticeProgress:
        """Get or create practice progress for a student"""
        
        # Try to find existing progress
        result = await self.db.execute(
            select(VocabularyPracticeProgress)
            .where(
                and_(
                    VocabularyPracticeProgress.student_id == student_id,
                    VocabularyPracticeProgress.vocabulary_list_id == vocabulary_list_id,
                    VocabularyPracticeProgress.classroom_assignment_id == classroom_assignment_id
                )
            )
        )
        progress = result.scalar_one_or_none()
        
        if not progress:
            # Create new progress record
            progress = VocabularyPracticeProgress(
                student_id=student_id,
                vocabulary_list_id=vocabulary_list_id,
                classroom_assignment_id=classroom_assignment_id
            )
            self.db.add(progress)
            await self.db.commit()
            await self.db.refresh(progress)
        
        return progress
    
    async def start_vocabulary_challenge(
        self,
        student_id: UUID,
        vocabulary_list_id: UUID,
        classroom_assignment_id: int
    ) -> Dict[str, Any]:
        """Start a new vocabulary challenge game"""
        
        # Get or create progress
        progress = await self.get_or_create_practice_progress(
            student_id, vocabulary_list_id, classroom_assignment_id
        )
        
        # Check if vocabulary challenge is already completed
        completed_assignments = progress.practice_status.get('completed_assignments', [])
        if 'vocabulary_challenge' in completed_assignments:
            raise ValueError("Vocabulary challenge has already been completed. Cannot retake completed activities.")
        
        # Check if questions exist, generate if not
        questions_result = await self.db.execute(
            select(VocabularyGameQuestion)
            .where(VocabularyGameQuestion.vocabulary_list_id == vocabulary_list_id)
            .order_by(VocabularyGameQuestion.question_order)
        )
        questions = questions_result.scalars().all()
        
        if not questions:
            # Generate questions
            generator = VocabularyGameGenerator(self.db)
            question_data = await generator.generate_game_questions(vocabulary_list_id)
            
            # Save questions to database
            for q_data in question_data:
                question = VocabularyGameQuestion(**q_data)
                self.db.add(question)
            
            await self.db.commit()
            
            # Reload questions
            questions_result = await self.db.execute(
                select(VocabularyGameQuestion)
                .where(VocabularyGameQuestion.vocabulary_list_id == vocabulary_list_id)
                .order_by(VocabularyGameQuestion.question_order)
            )
            questions = questions_result.scalars().all()
        
        # Calculate scoring
        total_questions = len(questions)
        max_possible_score = total_questions * 5  # 5 points per question
        passing_score = int(max_possible_score * self.PASSING_THRESHOLD)
        
        # Get current attempt number
        vocab_challenge_status = progress.practice_status.get('assignments', {}).get('vocabulary_challenge', {})
        attempt_number = vocab_challenge_status.get('attempts', 0) + 1
        
        # Create new game attempt
        game_attempt = VocabularyGameAttempt(
            student_id=student_id,
            vocabulary_list_id=vocabulary_list_id,
            practice_progress_id=progress.id,
            game_type='vocabulary_challenge',
            attempt_number=attempt_number,
            total_questions=total_questions,
            max_possible_score=max_possible_score,
            passing_score=passing_score
        )
        self.db.add(game_attempt)
        await self.db.commit()
        await self.db.refresh(game_attempt)
        
        # Update progress to mark as in progress
        practice_status = progress.practice_status.copy()
        practice_status['assignments']['vocabulary_challenge']['status'] = 'in_progress'
        practice_status['assignments']['vocabulary_challenge']['attempts'] = attempt_number
        practice_status['assignments']['vocabulary_challenge']['last_attempt_at'] = datetime.now(timezone.utc).isoformat()
        
        progress.practice_status = practice_status
        progress.current_game_session = {
            'game_attempt_id': str(game_attempt.id),
            'current_question': 0,
            'questions_remaining': total_questions
        }
        
        await self.db.commit()
        
        # Return first question
        first_question = questions[0] if questions else None
        
        return {
            'game_attempt_id': str(game_attempt.id),
            'total_questions': total_questions,
            'passing_score': passing_score,
            'max_possible_score': max_possible_score,
            'current_question': 1,
            'question': self._format_question(first_question) if first_question else None
        }
    
    async def submit_answer(
        self,
        game_attempt_id: UUID,
        question_id: UUID,
        student_answer: str,
        attempt_number: int,
        time_spent_seconds: int
    ) -> Dict[str, Any]:
        """Submit an answer for a vocabulary challenge question"""
        
        # Get game attempt
        result = await self.db.execute(
            select(VocabularyGameAttempt)
            .where(VocabularyGameAttempt.id == game_attempt_id)
            .options(selectinload(VocabularyGameAttempt.practice_progress))
        )
        game_attempt = result.scalar_one_or_none()
        
        if not game_attempt or game_attempt.status != 'in_progress':
            raise ValueError("Invalid or completed game attempt")
        
        # Get the question
        question_result = await self.db.execute(
            select(VocabularyGameQuestion)
            .where(VocabularyGameQuestion.id == question_id)
        )
        question = question_result.scalar_one_or_none()
        
        if not question:
            raise ValueError("Question not found")
        
        # Check answer (case-insensitive, trimmed)
        is_correct = student_answer.strip().lower() == question.correct_answer.strip().lower()
        
        # Calculate points
        points_earned = 0
        if is_correct:
            points_earned = 5 if attempt_number == 1 else 3
        
        # Update game attempt
        question_responses = game_attempt.question_responses.copy()
        question_responses.append({
            'question_id': str(question_id),
            'question_order': len(question_responses) + 1,
            'attempts': attempt_number,
            'correct': is_correct,
            'points_earned': points_earned,
            'student_answer': student_answer,
            'time_spent_seconds': time_spent_seconds
        })
        
        game_attempt.question_responses = question_responses
        game_attempt.questions_answered = len(question_responses)
        game_attempt.current_score += points_earned
        
        # Check if game is complete
        is_complete = game_attempt.questions_answered >= game_attempt.total_questions
        
        if is_complete:
            game_attempt.status = 'passed' if game_attempt.current_score >= game_attempt.passing_score else 'failed'
            game_attempt.completed_at = datetime.now(timezone.utc)
            
            # Calculate total time spent
            if game_attempt.started_at:
                time_diff = game_attempt.completed_at - game_attempt.started_at
                game_attempt.time_spent_seconds = int(time_diff.total_seconds())
            
            # Update practice progress
            await self._update_practice_progress(game_attempt)
        
        await self.db.commit()
        
        # Get next question if not complete
        next_question = None
        if not is_complete and attempt_number == 2:  # Move to next question after 2 attempts
            questions_result = await self.db.execute(
                select(VocabularyGameQuestion)
                .where(VocabularyGameQuestion.vocabulary_list_id == game_attempt.vocabulary_list_id)
                .order_by(VocabularyGameQuestion.question_order)
            )
            all_questions = questions_result.scalars().all()
            
            if len(question_responses) < len(all_questions):
                next_question = all_questions[len(question_responses)]
        
        return {
            'correct': is_correct,
            'points_earned': points_earned,
            'explanation': question.explanation,
            'correct_answer': question.correct_answer if not is_correct else None,
            'current_score': game_attempt.current_score,
            'questions_remaining': game_attempt.total_questions - game_attempt.questions_answered,
            'is_complete': is_complete,
            'passed': game_attempt.status == 'passed' if is_complete else None,
            'next_question': self._format_question(next_question) if next_question else None,
            'can_retry': attempt_number < 2 and not is_correct
        }
    
    async def get_next_question(
        self,
        game_attempt_id: UUID
    ) -> Dict[str, Any]:
        """Get the next question in the game"""
        
        # Get game attempt
        result = await self.db.execute(
            select(VocabularyGameAttempt)
            .where(VocabularyGameAttempt.id == game_attempt_id)
        )
        game_attempt = result.scalar_one_or_none()
        
        if not game_attempt or game_attempt.status != 'in_progress':
            raise ValueError("Invalid or completed game attempt")
        
        # Get all questions
        questions_result = await self.db.execute(
            select(VocabularyGameQuestion)
            .where(VocabularyGameQuestion.vocabulary_list_id == game_attempt.vocabulary_list_id)
            .order_by(VocabularyGameQuestion.question_order)
        )
        all_questions = questions_result.scalars().all()
        
        # Get next unanswered question
        answered_count = game_attempt.questions_answered
        if answered_count < len(all_questions):
            next_question = all_questions[answered_count]
            return {
                'question': self._format_question(next_question),
                'current_question': answered_count + 1,
                'total_questions': game_attempt.total_questions,
                'current_score': game_attempt.current_score
            }
        
        return {'question': None, 'is_complete': True}
    
    async def get_practice_status(
        self,
        student_id: UUID,
        vocabulary_list_id: UUID,
        classroom_assignment_id: int
    ) -> Dict[str, Any]:
        """Get practice status for a student"""
        
        progress = await self.get_or_create_practice_progress(
            student_id, vocabulary_list_id, classroom_assignment_id
        )
        
        # Count completed assignments
        completed_count = len(progress.practice_status.get('completed_assignments', []))
        test_unlocked = completed_count >= self.ASSIGNMENTS_TO_COMPLETE
        
        # Format assignment statuses
        assignments = []
        completed_assignments = progress.practice_status.get('completed_assignments', [])
        
        for assignment_type in ['vocabulary_challenge', 'definition_match', 'context_clues', 'word_builder']:
            assignment_data = progress.practice_status.get('assignments', {}).get(assignment_type, {})
            is_completed = assignment_type in completed_assignments
            
            assignments.append({
                'type': assignment_type,
                'display_name': self._get_assignment_display_name(assignment_type),
                'status': assignment_data.get('status', 'not_started'),
                'attempts': assignment_data.get('attempts', 0),
                'best_score': assignment_data.get('best_score', 0),
                'completed_at': assignment_data.get('completed_at'),
                'available': assignment_type == 'vocabulary_challenge',  # Only vocabulary challenge in Phase 2A
                'can_start': assignment_type == 'vocabulary_challenge' and not is_completed,  # Can't retake completed activities
                'is_completed': is_completed
            })
        
        return {
            'assignments': assignments,
            'completed_count': completed_count,
            'required_count': self.ASSIGNMENTS_TO_COMPLETE,
            'test_unlocked': test_unlocked,
            'test_unlock_date': progress.practice_status.get('test_unlock_date')
        }
    
    def _format_question(self, question: VocabularyGameQuestion) -> Dict[str, Any]:
        """Format a question for the frontend"""
        if not question:
            return None
        
        return {
            'id': str(question.id),
            'question_type': question.question_type,
            'difficulty_level': question.difficulty_level,
            'question_text': question.question_text,
            'question_number': question.question_order
        }
    
    async def _update_practice_progress(self, game_attempt: VocabularyGameAttempt):
        """Update practice progress after game completion"""
        
        progress = game_attempt.practice_progress
        practice_status = progress.practice_status.copy()
        
        # Update vocabulary challenge status
        vocab_challenge = practice_status['assignments']['vocabulary_challenge']
        
        if game_attempt.status == 'passed':
            vocab_challenge['status'] = 'completed'
            vocab_challenge['completed_at'] = datetime.now(timezone.utc).isoformat()
            
            # Add to completed assignments if not already there
            if 'vocabulary_challenge' not in practice_status.get('completed_assignments', []):
                practice_status.setdefault('completed_assignments', []).append('vocabulary_challenge')
        else:
            vocab_challenge['status'] = 'failed'
        
        # Update best score
        if game_attempt.current_score > vocab_challenge.get('best_score', 0):
            vocab_challenge['best_score'] = game_attempt.current_score
        
        # Check if test should be unlocked
        completed_count = len(practice_status.get('completed_assignments', []))
        if completed_count >= self.ASSIGNMENTS_TO_COMPLETE and not practice_status.get('test_unlocked'):
            practice_status['test_unlocked'] = True
            practice_status['test_unlock_date'] = datetime.now(timezone.utc).isoformat()
        
        progress.practice_status = practice_status
        progress.current_game_session = None  # Clear current session
    
    def _get_assignment_display_name(self, assignment_type: str) -> str:
        """Get display name for assignment type"""
        names = {
            'vocabulary_challenge': 'Vocabulary Challenge',
            'definition_match': 'Definition Match',
            'context_clues': 'Context Clues',
            'word_builder': 'Word Builder'
        }
        return names.get(assignment_type, assignment_type.replace('_', ' ').title())
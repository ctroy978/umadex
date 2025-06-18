"""
Vocabulary practice activity service
Manages student progress through vocabulary practice games
"""
from typing import List, Dict, Any, Optional
from uuid import UUID
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update, func, text, delete
from sqlalchemy.orm import selectinload
import json
import logging
import random
import asyncio

from app.models.vocabulary import VocabularyList, VocabularyWord
from app.models.vocabulary_practice import (
    VocabularyPracticeProgress,
    VocabularyStoryPrompt,
    VocabularyStoryResponse,
    VocabularyStoryAttempt,
    VocabularyConceptMap,
    VocabularyConceptMapAttempt,
    VocabularyPuzzleGame,
    VocabularyPuzzleResponse,
    VocabularyPuzzleAttempt,
    VocabularyFillInBlankSentence,
    VocabularyFillInBlankResponse,
    VocabularyFillInBlankAttempt
)
from app.models.classroom import ClassroomAssignment, StudentAssignment
from app.models.user import User
from app.services.vocabulary_story_generator import VocabularyStoryGenerator
from app.services.vocabulary_story_evaluator import VocabularyStoryEvaluator
from app.services.vocabulary_concept_map_evaluator import VocabularyConceptMapEvaluator
from app.services.vocabulary_puzzle_generator import VocabularyPuzzleGenerator
from app.services.vocabulary_puzzle_evaluator import VocabularyPuzzleEvaluator
from app.services.vocabulary_session import VocabularySessionManager

logger = logging.getLogger(__name__)


class VocabularyPracticeService:
    """Service for managing vocabulary practice activities"""
    
    PASSING_THRESHOLD = 0.7  # 70% to pass
    ASSIGNMENTS_TO_COMPLETE = 3  # Need 3 of 4 to unlock test
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.session_manager = VocabularySessionManager()
    
    def _ensure_assignment_status(self, practice_status: dict, assignment_type: str, extra_fields: dict = None) -> dict:
        """Safely ensure assignment status structure exists in practice_status"""
        if 'assignments' not in practice_status:
            practice_status['assignments'] = {}
        
        if assignment_type not in practice_status['assignments']:
            base_structure = {
                'status': 'not_started',
                'attempts': 0,
                'best_score': 0,
                'last_attempt_at': None,
                'completed_at': None
            }
            
            # Add extra fields for specific assignment types
            if extra_fields:
                base_structure.update(extra_fields)
            
            practice_status['assignments'][assignment_type] = base_structure
        
        return practice_status['assignments'][assignment_type]
    
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
            try:
                # Create new progress record
                progress = VocabularyPracticeProgress(
                    student_id=student_id,
                    vocabulary_list_id=vocabulary_list_id,
                    classroom_assignment_id=classroom_assignment_id
                )
                self.db.add(progress)
                await self.db.commit()
                await self.db.refresh(progress)
            except Exception as e:
                # Handle race condition where another request created the record
                await self.db.rollback()
                # Try to get the record again
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
                    # If we still can't find it, re-raise the original exception
                    raise e
        
        return progress
    
    async def get_practice_status(
        self,
        student_id: UUID,
        vocabulary_list_id: UUID,
        classroom_assignment_id: int
    ) -> Dict[str, Any]:
        """Get practice status for a student with session restoration"""
        
        progress = await self.get_or_create_practice_progress(
            student_id, vocabulary_list_id, classroom_assignment_id
        )
        
        # Update activity tracking
        await self.session_manager.update_activity(student_id, vocabulary_list_id)
        
        # Restore session state from database if not in Redis
        current_session = await self.session_manager.get_current_session(student_id, vocabulary_list_id)
        if not current_session and progress.current_game_session:
            await self.session_manager.restore_session_from_db(
                student_id, vocabulary_list_id, progress.current_game_session
            )
        
        # Restore progress state to Redis for faster access
        await self.session_manager.restore_progress_from_db(
            student_id, vocabulary_list_id, progress.practice_status
        )
        
        # Check StudentAssignment for completion status (new authoritative source)
        assignment_completions = {}
        for assignment_type in ['story_builder', 'concept_mapping', 'puzzle_path', 'fill_in_blank']:
            # Map assignment types to specific vocabulary subtypes
            student_assignment_type = f"vocabulary_{assignment_type}" if assignment_type != 'story_builder' else "vocabulary_story_builder"
            
            result = await self.db.execute(
                select(StudentAssignment.completed_at)
                .where(
                    and_(
                        StudentAssignment.student_id == student_id,
                        StudentAssignment.assignment_id == vocabulary_list_id,
                        StudentAssignment.classroom_assignment_id == classroom_assignment_id,
                        StudentAssignment.assignment_type == "vocabulary",
                        StudentAssignment.progress_metadata['completed_subtypes'].contains([assignment_type])
                    )
                )
            )
            completion_date = result.scalar_one_or_none()
            assignment_completions[assignment_type] = completion_date
        
        # Count completed assignments based on StudentAssignment records
        completed_count = sum(1 for completion in assignment_completions.values() if completion is not None)
        test_unlocked = completed_count >= self.ASSIGNMENTS_TO_COMPLETE
        
        # Check vocabulary test completion status
        test_completion_result = await self.db.execute(
            text("""
                SELECT COUNT(*) as attempt_count,
                       MAX(score_percentage) as best_score,
                       MAX(completed_at) as last_completed,
                       MAX(vt.max_attempts) as max_attempts
                FROM vocabulary_test_attempts vta
                JOIN vocabulary_tests vt ON vt.id = vta.test_id  
                WHERE vta.student_id = :student_id 
                AND vt.vocabulary_list_id = :vocabulary_list_id
                AND vt.classroom_assignment_id = :classroom_assignment_id
                AND vta.status = 'completed'
            """),
            {
                "student_id": str(student_id),
                "vocabulary_list_id": str(vocabulary_list_id), 
                "classroom_assignment_id": classroom_assignment_id
            }
        )
        test_completion_data = test_completion_result.fetchone()
        
        test_attempts_count = test_completion_data.attempt_count if test_completion_data else 0
        best_test_score = test_completion_data.best_score if test_completion_data else None
        last_test_completed_at = test_completion_data.last_completed if test_completion_data else None
        max_test_attempts = test_completion_data.max_attempts if test_completion_data and test_completion_data.max_attempts else 3
        test_completed = test_attempts_count > 0
        
        # Format assignment statuses
        assignments = []
        
        for assignment_type in ['story_builder', 'concept_mapping', 'puzzle_path', 'fill_in_blank']:
            assignment_data = progress.practice_status.get('assignments', {}).get(assignment_type, {})
            is_completed = assignment_completions[assignment_type] is not None
            
            # Check if there's an active session for this assignment type
            has_active_session = False
            if current_session:
                session_type = None
                if 'story_attempt_id' in current_session:
                    session_type = 'story_builder'
                elif 'concept_attempt_id' in current_session:
                    session_type = 'concept_mapping'
                elif 'puzzle_attempt_id' in current_session:
                    session_type = 'puzzle_path'
                elif 'fill_in_blank_attempt_id' in current_session:
                    session_type = 'fill_in_blank'
                
                has_active_session = (session_type == assignment_type)
            
            # Available assignments (All 4 assignments are now available)
            is_available = assignment_type in ['story_builder', 'concept_mapping', 'puzzle_path', 'fill_in_blank']
            
            assignments.append({
                'type': assignment_type,
                'display_name': self._get_assignment_display_name(assignment_type),
                'status': 'completed' if is_completed else assignment_data.get('status', 'not_started'),
                'attempts': assignment_data.get('attempts', 0),
                'best_score': assignment_data.get('best_score', 0),
                'completed_at': assignment_completions[assignment_type].isoformat() if assignment_completions[assignment_type] else None,
                'available': is_available,
                'can_start': is_available and not is_completed,  # Can't retake completed activities
                'is_completed': is_completed,
                'has_active_session': has_active_session
            })
        
        return {
            'assignments': assignments,
            'completed_count': completed_count,
            'required_count': self.ASSIGNMENTS_TO_COMPLETE,
            'test_unlocked': test_unlocked,
            'test_unlock_date': progress.practice_status.get('test_unlock_date'),
            'test_completed': test_completed,
            'test_attempts_count': test_attempts_count,
            'max_test_attempts': max_test_attempts,
            'best_test_score': best_test_score,
            'last_test_completed_at': last_test_completed_at,
            'current_session': current_session
        }
    
    def _get_assignment_display_name(self, assignment_type: str) -> str:
        """Get display name for assignment type"""
        names = {
            'story_builder': 'Story Builder',
            'concept_mapping': 'Concept Mapping',
            'puzzle_path': 'Word Puzzle Path',
            'fill_in_blank': 'Fill in the Blank'
        }
        return names.get(assignment_type, assignment_type.replace('_', ' ').title())
    
    async def _get_next_attempt_number(
        self,
        student_id: UUID,
        vocabulary_list_id: UUID,
        attempt_model_class
    ) -> int:
        """Get the next attempt number for a specific assignment type"""
        
        # Get progress to access practice_status
        progress_result = await self.db.execute(
            select(VocabularyPracticeProgress).where(
                and_(
                    VocabularyPracticeProgress.student_id == student_id,
                    VocabularyPracticeProgress.vocabulary_list_id == vocabulary_list_id
                )
            )
        )
        progress = progress_result.scalar_one_or_none()
        
        if not progress:
            return 1
        
        # Determine assignment type based on attempt model class
        if attempt_model_class == VocabularyFillInBlankAttempt:
            assignment_type = 'fill_in_blank'
        elif attempt_model_class == VocabularyStoryAttempt:
            assignment_type = 'story_builder'
        elif attempt_model_class == VocabularyConceptMapAttempt:
            assignment_type = 'concept_mapping'
        elif attempt_model_class == VocabularyPuzzleAttempt:
            assignment_type = 'puzzle_path'
        else:
            # Fallback: return 1 for unknown types
            return 1
        
        # Also check for the highest attempt number in the database
        # This handles cases where attempts were deleted but progress wasn't updated
        max_attempt_result = await self.db.execute(
            select(func.max(attempt_model_class.attempt_number))
            .where(
                and_(
                    attempt_model_class.student_id == student_id,
                    attempt_model_class.vocabulary_list_id == vocabulary_list_id
                )
            )
        )
        max_db_attempt = max_attempt_result.scalar() or 0
        
        # Get current attempt number from practice_status
        assignment_status = progress.practice_status.get('assignments', {}).get(assignment_type, {})
        status_attempt = assignment_status.get('attempts', 0)
        
        # Use the higher of the two values
        current_max = max(max_db_attempt, status_attempt)
        logger.info(f"Getting next attempt number for {assignment_type}: max_db={max_db_attempt}, status={status_attempt}, next={current_max + 1}")
        
        return current_max + 1
    
    # Concept Mapping Methods
    
    async def start_concept_mapping(
        self,
        student_id: UUID,
        vocabulary_list_id: UUID,
        classroom_assignment_id: int
    ) -> Dict[str, Any]:
        """Start a new concept mapping activity with session management"""
        
        # Check for existing active session first
        existing_session = await self.session_manager.get_current_session(student_id, vocabulary_list_id)
        if existing_session and 'concept_attempt_id' in existing_session:
            # Try to resume existing concept mapping attempt
            try:
                return await self._resume_concept_mapping(student_id, vocabulary_list_id, existing_session)
            except ValueError:
                # Session is stale, continue to create new attempt
                pass
        
        # Get or create progress
        progress = await self.get_or_create_practice_progress(
            student_id, vocabulary_list_id, classroom_assignment_id
        )
        
        # Check if concept mapping is already completed
        completed_assignments = progress.practice_status.get('completed_assignments', [])
        if 'concept_mapping' in completed_assignments:
            raise ValueError("Concept mapping has already been completed. Cannot retake completed activities.")
        
        # Get vocabulary words
        vocab_list_result = await self.db.execute(
            select(VocabularyList)
            .where(VocabularyList.id == vocabulary_list_id)
            .options(selectinload(VocabularyList.words))
        )
        vocab_list = vocab_list_result.scalar_one_or_none()
        
        if not vocab_list or not vocab_list.words:
            raise ValueError("Vocabulary list not found or has no words")
        
        # Sort words by their original order
        words = sorted(vocab_list.words, key=lambda w: w.id)
        total_words = len(words)
        
        # Calculate scoring
        max_possible_score = total_words * 4.0  # 4 points per word
        passing_score = max_possible_score * self.PASSING_THRESHOLD
        
        # Get current attempt number
        concept_mapping_status = progress.practice_status.get('assignments', {}).get('concept_mapping', {})
        attempt_number = concept_mapping_status.get('attempts', 0) + 1
        
        # Create new concept map attempt
        concept_attempt = VocabularyConceptMapAttempt(
            student_id=student_id,
            vocabulary_list_id=vocabulary_list_id,
            practice_progress_id=progress.id,
            attempt_number=attempt_number,
            total_words=total_words,
            max_possible_score=max_possible_score,
            passing_score=passing_score
        )
        self.db.add(concept_attempt)
        await self.db.commit()
        await self.db.refresh(concept_attempt)
        
        # Update progress to mark as in progress
        practice_status = progress.practice_status.copy()
        
        # Ensure concept_mapping status exists with special fields and update it
        concept_mapping = self._ensure_assignment_status(practice_status, 'concept_mapping', {
            "average_score": 0,
            "current_word_index": 0,
            "total_words": 0,
            "words_completed": 0
        })
        concept_mapping['status'] = 'in_progress'
        concept_mapping['attempts'] = attempt_number
        concept_mapping['last_attempt_at'] = datetime.now(timezone.utc).isoformat()
        concept_mapping['total_words'] = total_words
        concept_mapping['current_word_index'] = 0
        
        progress.practice_status = practice_status
        session_data = {
            'concept_attempt_id': str(concept_attempt.id),
            'current_word_index': 0,
            'words_remaining': total_words
        }
        progress.current_game_session = session_data
        
        await self.db.commit()
        
        # Store session in Redis for fast access
        await self.session_manager.set_current_session(student_id, vocabulary_list_id, session_data)
        await self.session_manager.set_current_attempt(
            student_id, vocabulary_list_id, 'concept_mapping',
            {
                'attempt_id': str(concept_attempt.id),
                'attempt_number': attempt_number,
                'started_at': datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Return first word
        first_word = words[0] if words else None
        
        return {
            'concept_attempt_id': str(concept_attempt.id),
            'total_words': total_words,
            'passing_score': float(passing_score),
            'max_possible_score': float(max_possible_score),
            'current_word_index': 0,
            'word': self._format_vocabulary_word(first_word) if first_word else None,
            'grade_level': vocab_list.grade_level
        }
    
    async def _resume_concept_mapping(
        self,
        student_id: UUID,
        vocabulary_list_id: UUID,
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resume an existing concept mapping session"""
        
        concept_attempt_id = UUID(session_data['concept_attempt_id'])
        
        # Get the concept attempt
        result = await self.db.execute(
            select(VocabularyConceptMapAttempt)
            .where(VocabularyConceptMapAttempt.id == concept_attempt_id)
            .options(
                selectinload(VocabularyConceptMapAttempt.practice_progress),
                selectinload(VocabularyConceptMapAttempt.vocabulary_list)
            )
        )
        concept_attempt = result.scalar_one_or_none()
        
        if not concept_attempt or concept_attempt.status != 'in_progress':
            # Session is stale, clear it and start fresh
            await self.session_manager.clear_session(student_id, vocabulary_list_id)
            raise ValueError("Concept mapping session is no longer valid")
        
        # Get all words to determine current position
        words_result = await self.db.execute(
            select(VocabularyWord)
            .where(VocabularyWord.list_id == vocabulary_list_id)
            .order_by(VocabularyWord.id)
        )
        words = words_result.scalars().all()
        
        # Determine current word based on completed count
        current_word_index = concept_attempt.current_word_index
        current_word = words[current_word_index] if current_word_index < len(words) else None
        
        # Update session with current state
        session_data = {
            'concept_attempt_id': str(concept_attempt.id),
            'current_word_index': current_word_index,
            'words_remaining': concept_attempt.total_words - concept_attempt.words_completed
        }
        
        await self.session_manager.set_current_session(student_id, vocabulary_list_id, session_data)
        await self.session_manager.update_activity(student_id, vocabulary_list_id)
        
        return {
            'concept_attempt_id': str(concept_attempt.id),
            'total_words': concept_attempt.total_words,
            'passing_score': float(concept_attempt.passing_score),
            'max_possible_score': float(concept_attempt.max_possible_score),
            'current_word_index': current_word_index,
            'word': self._format_vocabulary_word(current_word) if current_word else None,
            'grade_level': concept_attempt.vocabulary_list.grade_level,
            'current_score': float(concept_attempt.total_score),
            'words_completed': concept_attempt.words_completed,
            'is_resuming': True
        }
    
    async def submit_concept_map(
        self,
        concept_attempt_id: UUID,
        word_id: UUID,
        definition: str,
        synonyms: str,
        antonyms: str,
        context_theme: str,
        connotation: str,
        example_sentence: str,
        time_spent_seconds: int
    ) -> Dict[str, Any]:
        """Submit a concept map for evaluation"""
        
        # Get concept attempt
        result = await self.db.execute(
            select(VocabularyConceptMapAttempt)
            .where(VocabularyConceptMapAttempt.id == concept_attempt_id)
            .options(
                selectinload(VocabularyConceptMapAttempt.practice_progress),
                selectinload(VocabularyConceptMapAttempt.vocabulary_list)
            )
        )
        concept_attempt = result.scalar_one_or_none()
        
        if not concept_attempt or concept_attempt.status != 'in_progress':
            raise ValueError("Invalid or completed concept mapping attempt")
        
        # Get the word
        word_result = await self.db.execute(
            select(VocabularyWord)
            .where(VocabularyWord.id == word_id)
        )
        word = word_result.scalar_one_or_none()
        
        if not word:
            raise ValueError("Word not found")
        
        # Validate input
        evaluator = VocabularyConceptMapEvaluator()
        validation = await evaluator.validate_student_input(
            definition=definition,
            synonyms=synonyms,
            antonyms=antonyms,
            context_theme=context_theme,
            connotation=connotation,
            example_sentence=example_sentence,
            word=word.word
        )
        
        if not validation['valid']:
            return {
                'valid': False,
                'errors': validation['errors']
            }
        
        # Evaluate the concept map
        evaluation = await evaluator.evaluate_concept_map(
            word=word.word,
            grade_level=concept_attempt.vocabulary_list.grade_level,
            definition=definition,
            synonyms=synonyms,
            antonyms=antonyms,
            context_theme=context_theme,
            connotation=connotation,
            example_sentence=example_sentence
        )
        
        # Save concept map
        concept_map = VocabularyConceptMap(
            student_id=concept_attempt.student_id,
            vocabulary_list_id=concept_attempt.vocabulary_list_id,
            practice_progress_id=concept_attempt.practice_progress_id,
            word_id=word_id,
            definition=definition,
            synonyms=synonyms,
            antonyms=antonyms,
            context_theme=context_theme,
            connotation=connotation,
            example_sentence=example_sentence,
            ai_evaluation=evaluation,
            word_score=evaluation['overall_score'],
            attempt_number=concept_attempt.attempt_number,
            word_order=concept_attempt.current_word_index + 1,
            time_spent_seconds=time_spent_seconds
        )
        self.db.add(concept_map)
        
        # Update concept attempt
        concept_attempt.words_completed += 1
        concept_attempt.current_word_index += 1
        concept_attempt.total_score = float(concept_attempt.total_score) + evaluation['overall_score']
        
        # Update word scores tracking
        word_scores = concept_attempt.word_scores.copy() if concept_attempt.word_scores else {}
        word_scores[str(word_id)] = {
            'score': evaluation['overall_score'],
            'completed_at': datetime.now(timezone.utc).isoformat()
        }
        concept_attempt.word_scores = word_scores
        
        # Calculate average score
        if concept_attempt.words_completed > 0:
            concept_attempt.average_score = float(concept_attempt.total_score) / concept_attempt.words_completed
        
        # Check if all words are complete or student is finishing early
        is_complete = concept_attempt.words_completed >= concept_attempt.total_words
        
        if is_complete:
            # Calculate percentage score for determination
            percentage_score = (float(concept_attempt.average_score) / 4.0) * 100
            
            # Set status to pending_confirmation for both pass and fail
            # This ensures the dialog shows for both scenarios
            concept_attempt.status = 'pending_confirmation'
            
            concept_attempt.completed_at = datetime.now(timezone.utc)
            
            # Calculate total time spent
            if concept_attempt.started_at:
                time_diff = concept_attempt.completed_at - concept_attempt.started_at
                concept_attempt.time_spent_seconds = int(time_diff.total_seconds())
        
        await self.db.commit()
        
        # Update Redis session if not complete
        if not is_complete:
            session_data = {
                'concept_attempt_id': str(concept_attempt.id),
                'current_word_index': concept_attempt.current_word_index,
                'words_remaining': concept_attempt.total_words - concept_attempt.words_completed
            }
            await self.session_manager.set_current_session(
                concept_attempt.student_id, concept_attempt.vocabulary_list_id, session_data
            )
            await self.session_manager.update_activity(
                concept_attempt.student_id, concept_attempt.vocabulary_list_id
            )
        
        # Get next word if not complete
        next_word = None
        if not is_complete and concept_attempt.current_word_index < concept_attempt.total_words:
            words_result = await self.db.execute(
                select(VocabularyWord)
                .where(VocabularyWord.list_id == concept_attempt.vocabulary_list_id)
                .order_by(VocabularyWord.id)
            )
            all_words = words_result.scalars().all()
            
            if concept_attempt.current_word_index < len(all_words):
                next_word = all_words[concept_attempt.current_word_index]
        
        return {
            'valid': True,
            'evaluation': evaluation,
            'current_score': float(concept_attempt.total_score),
            'average_score': float(concept_attempt.average_score) if concept_attempt.average_score else 0,
            'words_remaining': concept_attempt.total_words - concept_attempt.words_completed,
            'is_complete': is_complete,
            'passed': concept_attempt.status == 'passed' if is_complete else None,
            'percentage_score': (float(concept_attempt.average_score) / 4.0) * 100 if is_complete and concept_attempt.average_score else None,
            'needs_confirmation': concept_attempt.status == 'pending_confirmation' if is_complete else False,
            'next_word': self._format_vocabulary_word(next_word) if next_word else None,
            'progress_percentage': (concept_attempt.words_completed / concept_attempt.total_words) * 100
        }
    
    async def get_concept_map_progress(
        self,
        concept_attempt_id: UUID
    ) -> Dict[str, Any]:
        """Get current progress in concept mapping"""
        
        # Get concept attempt with related data
        result = await self.db.execute(
            select(VocabularyConceptMapAttempt)
            .where(VocabularyConceptMapAttempt.id == concept_attempt_id)
            .options(
                selectinload(VocabularyConceptMapAttempt.vocabulary_list).selectinload(VocabularyList.words)
            )
        )
        concept_attempt = result.scalar_one_or_none()
        
        if not concept_attempt:
            raise ValueError("Concept mapping attempt not found")
        
        # Get completed concept maps
        maps_result = await self.db.execute(
            select(VocabularyConceptMap)
            .where(
                and_(
                    VocabularyConceptMap.practice_progress_id == concept_attempt.practice_progress_id,
                    VocabularyConceptMap.attempt_number == concept_attempt.attempt_number
                )
            )
            .options(selectinload(VocabularyConceptMap.word))
        )
        completed_maps = maps_result.scalars().all()
        
        # Get current or next word
        current_word = None
        if concept_attempt.status == 'in_progress' and concept_attempt.current_word_index < concept_attempt.total_words:
            words = sorted(concept_attempt.vocabulary_list.words, key=lambda w: w.id)
            if concept_attempt.current_word_index < len(words):
                current_word = words[concept_attempt.current_word_index]
        
        return {
            'concept_attempt_id': str(concept_attempt.id),
            'status': concept_attempt.status,
            'total_words': concept_attempt.total_words,
            'words_completed': concept_attempt.words_completed,
            'current_word_index': concept_attempt.current_word_index,
            'current_score': float(concept_attempt.total_score),
            'average_score': float(concept_attempt.average_score) if concept_attempt.average_score else 0,
            'passing_score': float(concept_attempt.passing_score),
            'max_possible_score': float(concept_attempt.max_possible_score),
            'progress_percentage': (concept_attempt.words_completed / concept_attempt.total_words) * 100,
            'current_word': self._format_vocabulary_word(current_word) if current_word else None,
            'completed_words': [
                {
                    'word': cm.word.word,
                    'score': float(cm.word_score),
                    'completed_at': cm.completed_at.isoformat()
                }
                for cm in completed_maps
            ]
        }
    
    async def finish_concept_mapping_early(
        self,
        concept_attempt_id: UUID
    ) -> Dict[str, Any]:
        """Finish concept mapping early with partial completion"""
        
        # Get concept attempt
        result = await self.db.execute(
            select(VocabularyConceptMapAttempt)
            .where(VocabularyConceptMapAttempt.id == concept_attempt_id)
        )
        concept_attempt = result.scalar_one_or_none()
        
        if not concept_attempt or concept_attempt.status != 'in_progress':
            raise ValueError("Invalid or already completed concept mapping attempt")
        
        # Check minimum completion requirement (80% of words)
        min_words_required = int(concept_attempt.total_words * 0.8)
        if concept_attempt.words_completed < min_words_required:
            return {
                'success': False,
                'message': f'Please complete at least {min_words_required} words before finishing early. You have completed {concept_attempt.words_completed} words.'
            }
        
        # Calculate final score based on completed words
        # Adjust passing threshold based on words completed
        adjusted_max_score = concept_attempt.words_completed * 4.0
        adjusted_passing_score = adjusted_max_score * self.PASSING_THRESHOLD
        
        concept_attempt.status = 'passed' if float(concept_attempt.total_score) >= adjusted_passing_score else 'failed'
        concept_attempt.completed_at = datetime.now(timezone.utc)
        
        # Calculate total time spent
        if concept_attempt.started_at:
            time_diff = concept_attempt.completed_at - concept_attempt.started_at
            concept_attempt.time_spent_seconds = int(time_diff.total_seconds())
        
        # Update practice progress
        await self._update_concept_mapping_progress(concept_attempt)
        
        await self.db.commit()
        
        return {
            'success': True,
            'status': concept_attempt.status,
            'final_score': float(concept_attempt.total_score),
            'average_score': float(concept_attempt.average_score) if concept_attempt.average_score else 0,
            'words_completed': concept_attempt.words_completed,
            'total_words': concept_attempt.total_words,
            'passed': concept_attempt.status == 'passed'
        }
    
    async def confirm_concept_completion(
        self,
        concept_attempt_id: UUID,
        student_id: UUID
    ) -> Dict[str, Any]:
        """Confirm concept mapping completion and create StudentAssignment record"""
        
        # Get concept attempt with related data
        result = await self.db.execute(
            select(VocabularyConceptMapAttempt)
            .where(
                and_(
                    VocabularyConceptMapAttempt.id == concept_attempt_id,
                    VocabularyConceptMapAttempt.student_id == student_id
                )
            )
            .options(selectinload(VocabularyConceptMapAttempt.practice_progress))
        )
        concept_attempt = result.scalar_one_or_none()
        
        if not concept_attempt:
            raise ValueError("Concept mapping attempt not found")
        
        if concept_attempt.status != 'pending_confirmation':
            raise ValueError("Concept mapping attempt is not pending confirmation")
        
        # Calculate percentage score
        percentage_score = (float(concept_attempt.average_score) / 4.0) * 100
        
        if percentage_score < 70:
            raise ValueError("Cannot confirm completion with score below 70%")
        
        # Update concept attempt status
        concept_attempt.status = 'passed'
        
        # Update practice progress
        await self._update_concept_mapping_progress(concept_attempt)
        
        # Create or update StudentAssignment record
        student_assignment = await self._create_or_update_student_assignment(
            student_id=student_id,
            assignment_id=concept_attempt.vocabulary_list_id,
            classroom_assignment_id=concept_attempt.practice_progress.classroom_assignment_id,
            assignment_type="vocabulary",
            subtype="concept_mapping"
        )
        
        await self.db.commit()
        
        # Clear all Redis data for this assignment
        await self.session_manager.clear_all_session_data(student_id, concept_attempt.vocabulary_list_id)
        
        return {
            'success': True,
            'message': 'Concept mapping assignment completed successfully',
            'final_score': float(concept_attempt.average_score),
            'percentage_score': percentage_score
        }
    
    async def decline_concept_completion(
        self,
        concept_attempt_id: UUID,
        student_id: UUID
    ) -> Dict[str, Any]:
        """Decline concept mapping completion and prepare for retake"""
        
        # Get concept attempt
        result = await self.db.execute(
            select(VocabularyConceptMapAttempt)
            .where(
                and_(
                    VocabularyConceptMapAttempt.id == concept_attempt_id,
                    VocabularyConceptMapAttempt.student_id == student_id
                )
            )
            .options(selectinload(VocabularyConceptMapAttempt.practice_progress))
        )
        concept_attempt = result.scalar_one_or_none()
        
        if not concept_attempt:
            raise ValueError("Concept mapping attempt not found")
        
        # Calculate percentage score
        percentage_score = (float(concept_attempt.average_score) / 4.0) * 100
        
        # Store final score for return
        final_score = float(concept_attempt.average_score)
        
        # Delete all concept map records for this attempt to allow retake
        await self.db.execute(
            delete(VocabularyConceptMap)
            .where(
                and_(
                    VocabularyConceptMap.practice_progress_id == concept_attempt.practice_progress_id,
                    VocabularyConceptMap.attempt_number == concept_attempt.attempt_number
                )
            )
        )
        
        # Delete the concept attempt itself
        await self.db.delete(concept_attempt)
        
        # Clear Redis session data AFTER deleting the attempt
        # This ensures the session is cleared and won't reference the deleted attempt
        await self.session_manager.clear_all_session_data(student_id, concept_attempt.vocabulary_list_id)
        
        # Also clear the practice progress current_game_session to ensure clean state
        if concept_attempt.practice_progress:
            concept_attempt.practice_progress.current_game_session = {}
        
        await self.db.commit()
        
        return {
            'success': True,
            'message': 'Assignment declined. You can retake it later.',
            'final_score': final_score,
            'percentage_score': percentage_score
        }
    
    def _format_vocabulary_word(self, word: VocabularyWord) -> Dict[str, Any]:
        """Format a vocabulary word for the frontend"""
        if not word:
            return None
        
        return {
            'id': str(word.id),
            'word': word.word,
            'definition': word.definition,
            'part_of_speech': word.part_of_speech
        }
    
    async def _update_concept_mapping_progress(self, concept_attempt: VocabularyConceptMapAttempt):
        """Update practice progress after concept mapping completion"""
        
        progress = concept_attempt.practice_progress
        practice_status = progress.practice_status.copy()
        
        # Ensure assignments dict and concept_mapping entry exist
        if 'assignments' not in practice_status:
            practice_status['assignments'] = {}
        if 'concept_mapping' not in practice_status['assignments']:
            practice_status['assignments']['concept_mapping'] = {
                "status": "not_started",
                "attempts": 0,
                "best_score": 0,
                "average_score": 0,
                "last_attempt_at": None,
                "completed_at": None,
                "words_completed": 0
            }
        
        # Update concept mapping status
        concept_mapping = practice_status['assignments']['concept_mapping']
        
        if concept_attempt.status == 'passed':
            concept_mapping['status'] = 'completed'
            concept_mapping['completed_at'] = datetime.now(timezone.utc).isoformat()
            
            # Add to completed assignments if not already there
            if 'concept_mapping' not in practice_status.get('completed_assignments', []):
                practice_status.setdefault('completed_assignments', []).append('concept_mapping')
        else:
            concept_mapping['status'] = 'failed'
        
        # Update attempt count and scores
        concept_mapping['attempts'] = concept_attempt.attempt_number
        percentage_score = (float(concept_attempt.total_score) / float(concept_attempt.max_possible_score)) * 100
        if percentage_score > concept_mapping.get('best_score', 0):
            concept_mapping['best_score'] = percentage_score
        
        concept_mapping['average_score'] = float(concept_attempt.average_score) if concept_attempt.average_score else 0
        concept_mapping['words_completed'] = concept_attempt.words_completed
        
        # Check if test should be unlocked
        completed_count = len(practice_status.get('completed_assignments', []))
        if completed_count >= self.ASSIGNMENTS_TO_COMPLETE and not practice_status.get('test_unlocked'):
            practice_status['test_unlocked'] = True
            practice_status['test_unlock_date'] = datetime.now(timezone.utc).isoformat()
        
        progress.practice_status = practice_status
        progress.current_game_session = None  # Clear current session
        
        # Create StudentAssignment record if passed
        if concept_attempt.status == 'passed':
            await self._create_or_update_student_assignment(
                student_id=concept_attempt.student_id,
                assignment_id=concept_attempt.vocabulary_list_id,
                classroom_assignment_id=progress.classroom_assignment_id,
                assignment_type="vocabulary",
                subtype="concept_mapping"
            )
        
        # Clear Redis session data
        await self.session_manager.clear_session(concept_attempt.student_id, concept_attempt.vocabulary_list_id)
        await self.session_manager.clear_attempt(concept_attempt.student_id, concept_attempt.vocabulary_list_id, 'concept_mapping')
    
    # Puzzle Path Methods
    
    async def start_puzzle_path(
        self,
        student_id: UUID,
        vocabulary_list_id: UUID,
        classroom_assignment_id: int
    ) -> Dict[str, Any]:
        """Start a new puzzle path activity with session management"""
        
        # Check for existing active session first
        existing_session = await self.session_manager.get_current_session(student_id, vocabulary_list_id)
        if existing_session and 'puzzle_attempt_id' in existing_session:
            try:
                # Resume existing puzzle path attempt
                return await self._resume_puzzle_path(student_id, vocabulary_list_id, existing_session)
            except ValueError:
                # Session is stale, continue to create new attempt
                pass
        
        # Get or create progress
        progress = await self.get_or_create_practice_progress(
            student_id, vocabulary_list_id, classroom_assignment_id
        )
        
        # Check if puzzle path is already completed
        completed_assignments = progress.practice_status.get('completed_assignments', [])
        if 'puzzle_path' in completed_assignments:
            raise ValueError("Puzzle path has already been completed. Cannot retake completed activities.")
        
        # Check for existing pending confirmation attempt
        existing_attempt_result = await self.db.execute(
            select(VocabularyPuzzleAttempt)
            .where(
                and_(
                    VocabularyPuzzleAttempt.student_id == student_id,
                    VocabularyPuzzleAttempt.vocabulary_list_id == vocabulary_list_id,
                    VocabularyPuzzleAttempt.status == 'pending_confirmation'
                )
            )
        )
        existing_attempt = existing_attempt_result.scalar_one_or_none()
        
        if existing_attempt:
            # Return the existing attempt data with a flag to show confirmation dialog
            return {
                'puzzle_attempt_id': str(existing_attempt.id),
                'total_puzzles': existing_attempt.total_puzzles,
                'passing_score': existing_attempt.passing_score,
                'max_possible_score': existing_attempt.max_possible_score,
                'current_puzzle_index': existing_attempt.total_puzzles,  # All puzzles completed
                'puzzle': None,  # No current puzzle
                'is_complete': True,
                'needs_confirmation': True,
                'current_score': existing_attempt.total_score,
                'percentage_score': (existing_attempt.total_score / existing_attempt.max_possible_score) * 100 if existing_attempt.max_possible_score > 0 else 0
            }
        
        # Check if puzzles exist, generate if not
        puzzles_result = await self.db.execute(
            select(VocabularyPuzzleGame)
            .where(VocabularyPuzzleGame.vocabulary_list_id == vocabulary_list_id)
            .options(selectinload(VocabularyPuzzleGame.word))
            .order_by(VocabularyPuzzleGame.puzzle_order)
        )
        puzzles = puzzles_result.scalars().all()
        
        if not puzzles:
            # Generate puzzles
            generator = VocabularyPuzzleGenerator(self.db)
            puzzle_data = await generator.generate_puzzle_set(vocabulary_list_id)
            
            # Save puzzles to database
            for p_data in puzzle_data:
                puzzle = VocabularyPuzzleGame(**p_data)
                self.db.add(puzzle)
            
            await self.db.commit()
            
            # Reload puzzles
            puzzles_result = await self.db.execute(
                select(VocabularyPuzzleGame)
                .where(VocabularyPuzzleGame.vocabulary_list_id == vocabulary_list_id)
                .options(selectinload(VocabularyPuzzleGame.word))
                .order_by(VocabularyPuzzleGame.puzzle_order)
            )
            puzzles = puzzles_result.scalars().all()
        
        total_puzzles = len(puzzles)
        max_possible_score = total_puzzles * 4  # 4 points per puzzle
        passing_score = int(max_possible_score * self.PASSING_THRESHOLD)
        
        # Get next attempt number using the helper method
        attempt_number = await self._get_next_attempt_number(
            student_id, vocabulary_list_id, VocabularyPuzzleAttempt
        )
        
        # Create new puzzle attempt
        logger.info(f"Creating new puzzle attempt: student={student_id}, vocab_list={vocabulary_list_id}, attempt_num={attempt_number}")
        puzzle_attempt = VocabularyPuzzleAttempt(
            student_id=student_id,
            vocabulary_list_id=vocabulary_list_id,
            practice_progress_id=progress.id,
            attempt_number=attempt_number,
            total_puzzles=total_puzzles,
            max_possible_score=max_possible_score,
            passing_score=passing_score
        )
        self.db.add(puzzle_attempt)
        await self.db.commit()
        await self.db.refresh(puzzle_attempt)
        logger.info(f"Created puzzle attempt with id={puzzle_attempt.id}")
        
        # Update progress to mark as in progress
        practice_status = progress.practice_status.copy()
        
        # Ensure puzzle_path status exists with special fields and update it
        puzzle_path = self._ensure_assignment_status(practice_status, 'puzzle_path', {
            "current_puzzle": 0,
            "total_puzzles": 0,
            "puzzles_completed": 0
        })
        puzzle_path['status'] = 'in_progress'
        puzzle_path['attempts'] = attempt_number
        puzzle_path['last_attempt_at'] = datetime.now(timezone.utc).isoformat()
        puzzle_path['total_puzzles'] = total_puzzles
        puzzle_path['current_puzzle'] = 0
        
        progress.practice_status = practice_status
        session_data = {
            'puzzle_attempt_id': str(puzzle_attempt.id),
            'current_puzzle_index': 0,
            'puzzles_remaining': total_puzzles
        }
        progress.current_game_session = session_data
        
        await self.db.commit()
        
        # Store session in Redis for fast access
        await self.session_manager.set_current_session(student_id, vocabulary_list_id, session_data)
        await self.session_manager.set_current_attempt(
            student_id, vocabulary_list_id, 'puzzle_path',
            {
                'attempt_id': str(puzzle_attempt.id),
                'attempt_number': attempt_number,
                'started_at': datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Return first puzzle
        first_puzzle = puzzles[0] if puzzles else None
        
        return {
            'puzzle_attempt_id': str(puzzle_attempt.id),
            'total_puzzles': total_puzzles,
            'passing_score': passing_score,
            'max_possible_score': max_possible_score,
            'current_puzzle_index': 0,
            'puzzle': self._format_puzzle(first_puzzle) if first_puzzle else None
        }
    
    async def _resume_puzzle_path(
        self,
        student_id: UUID,
        vocabulary_list_id: UUID,
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resume an existing puzzle path session"""
        
        puzzle_attempt_id = UUID(session_data['puzzle_attempt_id'])
        
        # Get the puzzle attempt
        result = await self.db.execute(
            select(VocabularyPuzzleAttempt)
            .where(VocabularyPuzzleAttempt.id == puzzle_attempt_id)
            .options(selectinload(VocabularyPuzzleAttempt.practice_progress))
        )
        puzzle_attempt = result.scalar_one_or_none()
        
        if not puzzle_attempt or puzzle_attempt.status != 'in_progress':
            # Session is stale, clear it and start fresh
            await self.session_manager.clear_session(student_id, vocabulary_list_id)
            raise ValueError("Puzzle path session is no longer valid")
        
        # Get all puzzles to determine current position
        puzzles_result = await self.db.execute(
            select(VocabularyPuzzleGame)
            .where(VocabularyPuzzleGame.vocabulary_list_id == vocabulary_list_id)
            .options(selectinload(VocabularyPuzzleGame.word))
            .order_by(VocabularyPuzzleGame.puzzle_order)
        )
        puzzles = puzzles_result.scalars().all()
        
        # Determine current puzzle based on completed count
        current_puzzle_index = puzzle_attempt.current_puzzle_index
        current_puzzle = puzzles[current_puzzle_index] if current_puzzle_index < len(puzzles) else None
        
        # Update session with current state
        session_data = {
            'puzzle_attempt_id': str(puzzle_attempt.id),
            'current_puzzle_index': current_puzzle_index,
            'puzzles_remaining': puzzle_attempt.total_puzzles - puzzle_attempt.puzzles_completed
        }
        
        await self.session_manager.set_current_session(student_id, vocabulary_list_id, session_data)
        await self.session_manager.update_activity(student_id, vocabulary_list_id)
        
        return {
            'puzzle_attempt_id': str(puzzle_attempt.id),
            'total_puzzles': puzzle_attempt.total_puzzles,
            'passing_score': puzzle_attempt.passing_score,
            'max_possible_score': puzzle_attempt.max_possible_score,
            'current_puzzle_index': current_puzzle_index,
            'puzzle': self._format_puzzle(current_puzzle) if current_puzzle else None,
            'current_score': puzzle_attempt.total_score,
            'puzzles_completed': puzzle_attempt.puzzles_completed,
            'is_resuming': True
        }
    
    async def submit_puzzle_answer(
        self,
        puzzle_attempt_id: UUID,
        puzzle_id: UUID,
        student_answer: str,
        time_spent_seconds: int
    ) -> Dict[str, Any]:
        """Submit an answer for a puzzle"""
        
        logger.info(f"submit_puzzle_answer called: attempt_id={puzzle_attempt_id}, puzzle_id={puzzle_id}, answer={student_answer}")
        
        # Get puzzle attempt
        result = await self.db.execute(
            select(VocabularyPuzzleAttempt)
            .where(VocabularyPuzzleAttempt.id == puzzle_attempt_id)
            .options(selectinload(VocabularyPuzzleAttempt.practice_progress))
        )
        puzzle_attempt = result.scalar_one_or_none()
        
        if not puzzle_attempt:
            logger.error(f"Puzzle attempt not found: {puzzle_attempt_id}")
            raise ValueError("Puzzle attempt not found")
            
        logger.info(f"Puzzle attempt found: status={puzzle_attempt.status}, puzzles_completed={puzzle_attempt.puzzles_completed}/{puzzle_attempt.total_puzzles}, current_index={puzzle_attempt.current_puzzle_index}")
        
        if puzzle_attempt.status != 'in_progress':
            logger.error(f"Puzzle attempt not in progress: status={puzzle_attempt.status}")
            raise ValueError("Invalid or completed puzzle attempt")
        
        # Get the puzzle
        puzzle_result = await self.db.execute(
            select(VocabularyPuzzleGame)
            .where(VocabularyPuzzleGame.id == puzzle_id)
            .options(selectinload(VocabularyPuzzleGame.word))
        )
        puzzle = puzzle_result.scalar_one_or_none()
        
        if not puzzle:
            raise ValueError("Puzzle not found")
        
        # Validate input
        evaluator = VocabularyPuzzleEvaluator()
        validation = evaluator.validate_student_input(
            puzzle_type=puzzle.puzzle_type,
            student_answer=student_answer,
            puzzle_data=puzzle.puzzle_data
        )
        
        if not validation['valid']:
            return {
                'valid': False,
                'errors': validation['errors']
            }
        
        # Get vocabulary list for grade level
        vocab_list_result = await self.db.execute(
            select(VocabularyList)
            .where(VocabularyList.id == puzzle.vocabulary_list_id)
        )
        vocab_list = vocab_list_result.scalar_one_or_none()
        
        if not vocab_list:
            raise ValueError("Vocabulary list not found")
        
        # Evaluate the puzzle response
        try:
            evaluation = await evaluator.evaluate_puzzle_response(
                puzzle_type=puzzle.puzzle_type,
                puzzle_data=puzzle.puzzle_data,
                correct_answer=puzzle.correct_answer,
                student_answer=student_answer,
                word=puzzle.word.word,
                grade_level=vocab_list.grade_level
            )
            # Validate evaluation format
            if not isinstance(evaluation, dict) or 'score' not in evaluation:
                raise ValueError("Invalid evaluation response format")
            if not isinstance(evaluation['score'], int) or not (1 <= evaluation['score'] <= 4):
                raise ValueError(f"Invalid score value: {evaluation['score']}")
        except Exception as e:
            logger.error(f"AI evaluation failed: {e}")
            # Fallback evaluation
            evaluation = {
                'score': 1,
                'accuracy': 'system_error', 
                'feedback': 'Unable to evaluate response due to system error',
                'areas_checked': ['system_fallback']
            }
        
        # Check if puzzle response already exists (avoid duplicates)
        logger.info(f"Checking for existing response: progress_id={puzzle_attempt.practice_progress_id}, puzzle_id={puzzle_id}, attempt_num={puzzle_attempt.attempt_number}")
        existing_response_result = await self.db.execute(
            select(VocabularyPuzzleResponse)
            .where(
                and_(
                    VocabularyPuzzleResponse.practice_progress_id == puzzle_attempt.practice_progress_id,
                    VocabularyPuzzleResponse.puzzle_id == puzzle_id,
                    VocabularyPuzzleResponse.attempt_number == puzzle_attempt.attempt_number
                )
            )
        )
        existing_response = existing_response_result.scalar_one_or_none()
        
        # Also check if there are ANY responses for this puzzle from other attempts
        # This helps debug if old responses are interfering
        all_responses_result = await self.db.execute(
            select(VocabularyPuzzleResponse)
            .where(
                and_(
                    VocabularyPuzzleResponse.student_id == puzzle_attempt.student_id,
                    VocabularyPuzzleResponse.puzzle_id == puzzle_id
                )
            )
        )
        all_responses = all_responses_result.scalars().all()
        if all_responses:
            logger.warning(f"Found {len(all_responses)} total responses for puzzle {puzzle_id} across all attempts")
            for resp in all_responses:
                logger.info(f"  - Attempt {resp.attempt_number}: score={resp.puzzle_score}, created={resp.created_at}, progress_id={resp.practice_progress_id}")
                # Delete any response that doesn't match our current progress_id
                # These are orphaned responses from previous attempts
                if resp.practice_progress_id != puzzle_attempt.practice_progress_id:
                    logger.warning(f"Deleting orphaned response from different progress: {resp.id}")
                    await self.db.delete(resp)
            
            # Commit the deletions
            if len(all_responses) > 0:
                await self.db.commit()
                # Re-check for existing response after cleanup
                existing_response_result = await self.db.execute(
                    select(VocabularyPuzzleResponse)
                    .where(
                        and_(
                            VocabularyPuzzleResponse.practice_progress_id == puzzle_attempt.practice_progress_id,
                            VocabularyPuzzleResponse.puzzle_id == puzzle_id,
                            VocabularyPuzzleResponse.attempt_number == puzzle_attempt.attempt_number
                        )
                    )
                )
                existing_response = existing_response_result.scalar_one_or_none()
        
        if not existing_response:
            # Save new puzzle response
            try:
                puzzle_response = VocabularyPuzzleResponse(
                    student_id=puzzle_attempt.student_id,
                    vocabulary_list_id=puzzle_attempt.vocabulary_list_id,
                    practice_progress_id=puzzle_attempt.practice_progress_id,
                    puzzle_id=puzzle_id,
                    student_answer=student_answer,
                    ai_evaluation=evaluation,
                    puzzle_score=evaluation['score'],
                    attempt_number=puzzle_attempt.attempt_number,
                    time_spent_seconds=time_spent_seconds
                )
                self.db.add(puzzle_response)
            except Exception as e:
                logger.error(f"Failed to create puzzle response: {e}")
                raise ValueError(f"Database constraint violation: {str(e)}")
                
            # Update puzzle attempt only for new responses
            logger.info(f"Updating puzzle attempt {puzzle_attempt.id}: current_score={puzzle_attempt.total_score}, adding={evaluation['score']}")
            puzzle_attempt.puzzles_completed += 1
            puzzle_attempt.current_puzzle_index += 1
            puzzle_attempt.total_score += evaluation['score']
            logger.info(f"After update: puzzles_completed={puzzle_attempt.puzzles_completed}/{puzzle_attempt.total_puzzles}, total_score={puzzle_attempt.total_score}")
            
            # Update puzzle scores tracking
            puzzle_scores = puzzle_attempt.puzzle_scores.copy() if puzzle_attempt.puzzle_scores else {}
            puzzle_scores[str(puzzle_id)] = {
                'score': evaluation['score'],
                'type': puzzle.puzzle_type,
                'word': puzzle.word.word,
                'completed_at': datetime.now(timezone.utc).isoformat()
            }
            puzzle_attempt.puzzle_scores = puzzle_scores
        else:
            logger.warning(f"Puzzle response already exists for puzzle {puzzle_id}, attempt {puzzle_attempt.attempt_number}")
            logger.info(f"Attempt state: puzzles_completed={puzzle_attempt.puzzles_completed}, current_index={puzzle_attempt.current_puzzle_index}")
            
            # Use the existing evaluation
            evaluation = existing_response.ai_evaluation
            
            # Check if this is a stale state - response exists but counters are not updated
            # This can happen if there was an error after saving response but before updating counters
            puzzle_already_counted = str(puzzle_id) in (puzzle_attempt.puzzle_scores or {})
            
            if not puzzle_already_counted:
                logger.warning(f"Found stale state - response exists but not counted. Fixing...")
                # Update the counters that should have been updated
                puzzle_attempt.puzzles_completed += 1
                puzzle_attempt.current_puzzle_index += 1
                puzzle_attempt.total_score += existing_response.puzzle_score
                
                # Update puzzle scores tracking
                puzzle_scores = puzzle_attempt.puzzle_scores.copy() if puzzle_attempt.puzzle_scores else {}
                puzzle_scores[str(puzzle_id)] = {
                    'score': existing_response.puzzle_score,
                    'type': puzzle.puzzle_type,
                    'word': puzzle.word.word,
                    'completed_at': existing_response.created_at.isoformat()
                }
                puzzle_attempt.puzzle_scores = puzzle_scores
                logger.info(f"Fixed stale state: puzzles_completed={puzzle_attempt.puzzles_completed}, current_index={puzzle_attempt.current_puzzle_index}")
        
        # Check if all puzzles are complete
        is_complete = puzzle_attempt.puzzles_completed >= puzzle_attempt.total_puzzles
        
        if is_complete:
            # Calculate percentage score
            if puzzle_attempt.max_possible_score > 0:
                percentage_score = (puzzle_attempt.total_score / puzzle_attempt.max_possible_score) * 100
            else:
                percentage_score = 0
                logger.warning(f"Max possible score is 0 for puzzle attempt {puzzle_attempt.id}")
            # Set status to pending_confirmation for BOTH pass and fail
            # This ensures the dialog shows for both scenarios
            puzzle_attempt.status = 'pending_confirmation'
            puzzle_attempt.completed_at = datetime.now(timezone.utc)
            
            # Calculate total time spent
            if puzzle_attempt.started_at:
                time_diff = puzzle_attempt.completed_at - puzzle_attempt.started_at
                puzzle_attempt.time_spent_seconds = int(time_diff.total_seconds())
            
            # DO NOT update practice progress here - wait for explicit confirmation
        
        try:
            await self.db.commit()
        except Exception as e:
            await self.db.rollback()
            logger.error(f"Database commit failed: {e}")
            raise
        
        # Update Redis session if not complete
        if not is_complete:
            try:
                session_data = {
                    'puzzle_attempt_id': str(puzzle_attempt.id),
                    'current_puzzle_index': puzzle_attempt.current_puzzle_index,
                    'puzzles_remaining': puzzle_attempt.total_puzzles - puzzle_attempt.puzzles_completed
                }
                await self.session_manager.set_current_session(
                    puzzle_attempt.student_id, puzzle_attempt.vocabulary_list_id, session_data
                )
                await self.session_manager.update_activity(
                    puzzle_attempt.student_id, puzzle_attempt.vocabulary_list_id
                )
            except Exception as e:
                logger.warning(f"Redis session update failed: {e}")
                # Continue execution - Redis failures shouldn't break the main flow
        
        # Get next puzzle if not complete
        next_puzzle = None
        if not is_complete and puzzle_attempt.current_puzzle_index < puzzle_attempt.total_puzzles:
            logger.info(f"Getting next puzzle: current_index={puzzle_attempt.current_puzzle_index}, total={puzzle_attempt.total_puzzles}")
            puzzles_result = await self.db.execute(
                select(VocabularyPuzzleGame)
                .where(VocabularyPuzzleGame.vocabulary_list_id == puzzle_attempt.vocabulary_list_id)
                .options(selectinload(VocabularyPuzzleGame.word))
                .order_by(VocabularyPuzzleGame.puzzle_order)
            )
            all_puzzles = puzzles_result.scalars().all()
            logger.info(f"Found {len(all_puzzles)} puzzles total")
            
            if puzzle_attempt.current_puzzle_index < len(all_puzzles):
                next_puzzle = all_puzzles[puzzle_attempt.current_puzzle_index]
                logger.info(f"Next puzzle found: puzzle_id={next_puzzle.id}, type={next_puzzle.puzzle_type}")
        
        # Calculate percentage for return
        percentage_score = None
        if is_complete:
            if puzzle_attempt.max_possible_score > 0:
                percentage_score = (puzzle_attempt.total_score / puzzle_attempt.max_possible_score) * 100
            else:
                percentage_score = 0
        
        return {
            'valid': True,
            'evaluation': evaluation,
            'current_score': puzzle_attempt.total_score,
            'puzzles_remaining': puzzle_attempt.total_puzzles - puzzle_attempt.puzzles_completed,
            'is_complete': is_complete,
            'passed': puzzle_attempt.status == 'pending_confirmation' if is_complete else None,
            'percentage_score': percentage_score,
            'needs_confirmation': puzzle_attempt.status == 'pending_confirmation' if is_complete else False,
            'next_puzzle': self._format_puzzle(next_puzzle) if next_puzzle else None,
            'progress_percentage': (puzzle_attempt.puzzles_completed / puzzle_attempt.total_puzzles) * 100 if puzzle_attempt.total_puzzles > 0 else 0
        }
    
    async def get_puzzle_path_progress(
        self,
        puzzle_attempt_id: UUID
    ) -> Dict[str, Any]:
        """Get current progress in puzzle path"""
        
        # Get puzzle attempt with related data
        result = await self.db.execute(
            select(VocabularyPuzzleAttempt)
            .where(VocabularyPuzzleAttempt.id == puzzle_attempt_id)
        )
        puzzle_attempt = result.scalar_one_or_none()
        
        if not puzzle_attempt:
            raise ValueError("Puzzle attempt not found")
        
        # Get current or next puzzle
        current_puzzle = None
        if puzzle_attempt.status == 'in_progress' and puzzle_attempt.current_puzzle_index < puzzle_attempt.total_puzzles:
            puzzles_result = await self.db.execute(
                select(VocabularyPuzzleGame)
                .where(VocabularyPuzzleGame.vocabulary_list_id == puzzle_attempt.vocabulary_list_id)
                .options(selectinload(VocabularyPuzzleGame.word))
                .order_by(VocabularyPuzzleGame.puzzle_order)
            )
            all_puzzles = puzzles_result.scalars().all()
            
            if puzzle_attempt.current_puzzle_index < len(all_puzzles):
                current_puzzle = all_puzzles[puzzle_attempt.current_puzzle_index]
        
        # Get completed puzzles info
        completed_puzzles = []
        if puzzle_attempt.puzzle_scores:
            for puzzle_id, score_data in puzzle_attempt.puzzle_scores.items():
                completed_puzzles.append({
                    'word': score_data['word'],
                    'puzzle_type': score_data['type'],
                    'score': score_data['score'],
                    'completed_at': score_data['completed_at']
                })
        
        return {
            'puzzle_attempt_id': str(puzzle_attempt.id),
            'status': puzzle_attempt.status,
            'total_puzzles': puzzle_attempt.total_puzzles,
            'puzzles_completed': puzzle_attempt.puzzles_completed,
            'current_puzzle_index': puzzle_attempt.current_puzzle_index,
            'current_score': puzzle_attempt.total_score,
            'passing_score': puzzle_attempt.passing_score,
            'max_possible_score': puzzle_attempt.max_possible_score,
            'progress_percentage': (puzzle_attempt.puzzles_completed / puzzle_attempt.total_puzzles) * 100,
            'current_puzzle': self._format_puzzle(current_puzzle) if current_puzzle else None,
            'completed_puzzles': completed_puzzles
        }
    
    def _format_puzzle(self, puzzle: VocabularyPuzzleGame) -> Dict[str, Any]:
        """Format a puzzle for the frontend"""
        if not puzzle:
            return None
        
        # Safely get the word text without triggering lazy loading
        word_text = None
        try:
            if hasattr(puzzle, 'word') and puzzle.word is not None:
                word_text = puzzle.word.word
        except Exception:
            # If there's any issue accessing the word, just skip it
            word_text = None
        
        return {
            'id': str(puzzle.id),
            'puzzle_type': puzzle.puzzle_type,
            'puzzle_data': puzzle.puzzle_data,
            'puzzle_order': puzzle.puzzle_order,
            'word': word_text
        }
    
    async def _update_puzzle_path_progress(self, puzzle_attempt: VocabularyPuzzleAttempt):
        """Update practice progress after puzzle path completion"""
        
        progress = puzzle_attempt.practice_progress
        practice_status = progress.practice_status.copy()
        
        # Ensure assignments dict and puzzle_path entry exist
        if 'assignments' not in practice_status:
            practice_status['assignments'] = {}
        if 'puzzle_path' not in practice_status['assignments']:
            practice_status['assignments']['puzzle_path'] = {
                "status": "not_started",
                "attempts": 0,
                "best_score": 0,
                "last_attempt_at": None,
                "completed_at": None,
                "puzzles_completed": 0
            }
        
        # Update puzzle path status
        puzzle_path = practice_status['assignments']['puzzle_path']
        
        if puzzle_attempt.status == 'passed':
            puzzle_path['status'] = 'completed'
            puzzle_path['completed_at'] = datetime.now(timezone.utc).isoformat()
            
            # Add to completed assignments if not already there
            if 'puzzle_path' not in practice_status.get('completed_assignments', []):
                practice_status.setdefault('completed_assignments', []).append('puzzle_path')
        else:
            puzzle_path['status'] = 'failed'
        
        # Update attempt count and scores
        puzzle_path['attempts'] = puzzle_attempt.attempt_number
        percentage_score = (puzzle_attempt.total_score / puzzle_attempt.max_possible_score) * 100
        if percentage_score > puzzle_path.get('best_score', 0):
            puzzle_path['best_score'] = percentage_score
        
        puzzle_path['puzzles_completed'] = puzzle_attempt.puzzles_completed
        
        # Check if test should be unlocked
        completed_count = len(practice_status.get('completed_assignments', []))
        if completed_count >= self.ASSIGNMENTS_TO_COMPLETE and not practice_status.get('test_unlocked'):
            practice_status['test_unlocked'] = True
            practice_status['test_unlock_date'] = datetime.now(timezone.utc).isoformat()
        
        progress.practice_status = practice_status
        progress.current_game_session = None  # Clear current session
        
        # Clear Redis session data
        await self.session_manager.clear_session(puzzle_attempt.student_id, puzzle_attempt.vocabulary_list_id)
        await self.session_manager.clear_attempt(puzzle_attempt.student_id, puzzle_attempt.vocabulary_list_id, 'puzzle_path')
    
    async def confirm_puzzle_completion(
        self,
        puzzle_attempt_id: UUID,
        student_id: UUID
    ) -> Dict[str, Any]:
        """Confirm puzzle path completion and create StudentAssignment record"""
        
        # Get puzzle attempt with related data
        result = await self.db.execute(
            select(VocabularyPuzzleAttempt)
            .where(
                and_(
                    VocabularyPuzzleAttempt.id == puzzle_attempt_id,
                    VocabularyPuzzleAttempt.student_id == student_id
                )
            )
            .options(selectinload(VocabularyPuzzleAttempt.practice_progress))
        )
        puzzle_attempt = result.scalar_one_or_none()
        
        if not puzzle_attempt:
            raise ValueError("Puzzle attempt not found")
        
        if puzzle_attempt.status != 'pending_confirmation':
            raise ValueError("Puzzle attempt is not pending confirmation")
        
        # Check if this subtype was already completed
        ca_result = await self.db.execute(
            select(ClassroomAssignment.id)
            .where(
                and_(
                    ClassroomAssignment.vocabulary_list_id == puzzle_attempt.vocabulary_list_id,
                    ClassroomAssignment.assignment_type == "vocabulary"
                )
            )
        )
        classroom_assignment_id = ca_result.scalar_one()
        
        # Check for existing StudentAssignment record
        existing_result = await self.db.execute(
            select(StudentAssignment)
            .where(
                and_(
                    StudentAssignment.student_id == student_id,
                    StudentAssignment.assignment_id == puzzle_attempt.vocabulary_list_id,
                    StudentAssignment.classroom_assignment_id == classroom_assignment_id,
                    StudentAssignment.assignment_type == "vocabulary"
                )
            )
        )
        existing_assignment = existing_result.scalar_one_or_none()
        
        if existing_assignment and existing_assignment.progress_metadata:
            completed_subtypes = existing_assignment.progress_metadata.get('completed_subtypes', [])
            if 'puzzle_path' in completed_subtypes:
                raise ValueError("Puzzle path assignment already completed for this vocabulary list")
        
        # Calculate percentage score
        percentage_score = (puzzle_attempt.total_score / puzzle_attempt.max_possible_score) * 100
        
        if percentage_score < 70:
            raise ValueError("Cannot confirm completion with score below 70%")
        
        # Update puzzle attempt status
        puzzle_attempt.status = 'passed'
        
        # Update practice progress
        await self._update_puzzle_path_progress(puzzle_attempt)
        
        # Create or update StudentAssignment record
        student_assignment = await self._create_or_update_student_assignment(
            student_id=student_id,
            assignment_id=puzzle_attempt.vocabulary_list_id,
            classroom_assignment_id=classroom_assignment_id,
            assignment_type="vocabulary",
            subtype="puzzle_path"
        )
        
        await self.db.commit()
        
        # Clear all Redis data for this assignment
        await self.session_manager.clear_all_session_data(student_id, puzzle_attempt.vocabulary_list_id)
        
        return {
            'success': True,
            'message': 'Puzzle path assignment completed successfully',
            'final_score': puzzle_attempt.total_score,
            'percentage_score': percentage_score
        }
    
    async def decline_puzzle_completion(
        self,
        puzzle_attempt_id: UUID,
        student_id: UUID
    ) -> Dict[str, Any]:
        """Decline puzzle completion and prepare for retake"""
        
        # Get puzzle attempt
        result = await self.db.execute(
            select(VocabularyPuzzleAttempt)
            .where(
                and_(
                    VocabularyPuzzleAttempt.id == puzzle_attempt_id,
                    VocabularyPuzzleAttempt.student_id == student_id
                )
            )
            .options(selectinload(VocabularyPuzzleAttempt.practice_progress))
        )
        puzzle_attempt = result.scalar_one_or_none()
        
        if not puzzle_attempt:
            raise ValueError("Puzzle attempt not found")
        
        # Calculate percentage score
        percentage_score = (puzzle_attempt.total_score / puzzle_attempt.max_possible_score) * 100
        
        # Store final score for return
        final_score = puzzle_attempt.total_score
        
        # Delete all puzzle response records for this attempt to allow retake
        delete_result = await self.db.execute(
            delete(VocabularyPuzzleResponse)
            .where(
                and_(
                    VocabularyPuzzleResponse.practice_progress_id == puzzle_attempt.practice_progress_id,
                    VocabularyPuzzleResponse.attempt_number == puzzle_attempt.attempt_number
                )
            )
        )
        logger.info(f"Deleted {delete_result.rowcount} puzzle responses for attempt {puzzle_attempt.attempt_number}")
        
        # Also delete any orphaned responses for this student and vocabulary list
        # This handles cases where responses exist without proper attempt records
        orphan_delete_result = await self.db.execute(
            delete(VocabularyPuzzleResponse)
            .where(
                and_(
                    VocabularyPuzzleResponse.student_id == student_id,
                    VocabularyPuzzleResponse.vocabulary_list_id == puzzle_attempt.vocabulary_list_id
                )
            )
        )
        if orphan_delete_result.rowcount > 0:
            logger.warning(f"Deleted {orphan_delete_result.rowcount} additional orphaned puzzle responses")
        
        # Delete the puzzle attempt itself
        await self.db.delete(puzzle_attempt)
        
        # Clear Redis session data AFTER deleting the attempt
        # This ensures the session is cleared and won't reference the deleted attempt
        await self.session_manager.clear_all_session_data(student_id, puzzle_attempt.vocabulary_list_id)
        
        # Also clear the practice progress current_game_session to ensure clean state
        if puzzle_attempt.practice_progress:
            puzzle_attempt.practice_progress.current_game_session = {}
        
        await self.db.commit()
        
        return {
            'success': True,
            'message': 'Assignment declined. You can retake it later.',
            'final_score': final_score,
            'percentage_score': percentage_score
        }
    
    # Story Builder Methods
    
    async def start_story_builder(
        self,
        student_id: UUID,
        vocabulary_list_id: UUID,
        classroom_assignment_id: int
    ) -> Dict[str, Any]:
        """Start a new story builder challenge with session management"""
        
        # Get or create progress to check for failed attempts
        progress = await self.get_or_create_practice_progress(
            student_id, vocabulary_list_id, classroom_assignment_id
        )
        
        # Check if story builder is already completed
        completed_assignments = progress.practice_status.get('completed_assignments', [])
        if 'story_builder' in completed_assignments:
            raise ValueError("Story builder challenge has already been completed. Cannot retake completed activities.")
        
        # Check for existing failed attempts and clean them up for retry
        story_builder_status = progress.practice_status.get('assignments', {}).get('story_builder', {})
        if story_builder_status.get('status') == 'failed':
            # Clean up failed story attempts from database
            failed_attempts = await self.db.execute(
                select(VocabularyStoryAttempt)
                .where(
                    and_(
                        VocabularyStoryAttempt.student_id == student_id,
                        VocabularyStoryAttempt.vocabulary_list_id == vocabulary_list_id,
                        VocabularyStoryAttempt.status == 'failed'
                    )
                )
            )
            for attempt in failed_attempts.scalars():
                await self.db.delete(attempt)
            
            # Clean up any StudentAssignment records created for failed attempts
            existing_assignment = await self.db.execute(
                select(StudentAssignment)
                .where(
                    and_(
                        StudentAssignment.student_id == student_id,
                        StudentAssignment.assignment_id == vocabulary_list_id,
                        StudentAssignment.assignment_type == "vocabulary",
                        StudentAssignment.assignment_subtype == "story_builder",
                        StudentAssignment.passed == False
                    )
                )
            )
            failed_assignment = existing_assignment.scalar_one_or_none()
            if failed_assignment:
                await self.db.delete(failed_assignment)
            
            # Clear sessions and force fresh start by clearing status
            await self.session_manager.clear_session(student_id, vocabulary_list_id)
            await self.session_manager.clear_attempt(student_id, vocabulary_list_id, 'story_builder')
            
            # Reset the failed status to allow fresh attempt
            story_builder_status['status'] = 'not_started'
            progress.practice_status['assignments']['story_builder'] = story_builder_status
            
            # Commit the cleanup changes
            await self.db.commit()
        
        # Check for existing active session after cleanup
        existing_session = await self.session_manager.get_current_session(student_id, vocabulary_list_id)
        if existing_session and 'story_attempt_id' in existing_session:
            # Resume existing story attempt
            return await self._resume_story_builder(student_id, vocabulary_list_id, existing_session)
        
        # Check if prompts exist, generate if not
        prompts_result = await self.db.execute(
            select(VocabularyStoryPrompt)
            .where(VocabularyStoryPrompt.vocabulary_list_id == vocabulary_list_id)
            .order_by(VocabularyStoryPrompt.prompt_order)
        )
        prompts = prompts_result.scalars().all()
        
        if not prompts:
            # Generate prompts
            generator = VocabularyStoryGenerator(self.db)
            prompt_data = await generator.generate_story_prompts(vocabulary_list_id)
            
            # Reload prompts
            prompts_result = await self.db.execute(
                select(VocabularyStoryPrompt)
                .where(VocabularyStoryPrompt.vocabulary_list_id == vocabulary_list_id)
                .order_by(VocabularyStoryPrompt.prompt_order)
            )
            prompts = prompts_result.scalars().all()
        
        # Calculate scoring
        total_prompts = len(prompts)
        max_possible_score = total_prompts * 100  # 100 points per prompt
        passing_score = int(max_possible_score * self.PASSING_THRESHOLD)
        
        # Get current attempt number
        story_builder_status = progress.practice_status.get('assignments', {}).get('story_builder', {})
        attempt_number = story_builder_status.get('attempts', 0) + 1
        
        # Create new story attempt
        story_attempt = VocabularyStoryAttempt(
            student_id=student_id,
            vocabulary_list_id=vocabulary_list_id,
            practice_progress_id=progress.id,
            attempt_number=attempt_number,
            total_prompts=total_prompts,
            max_possible_score=max_possible_score,
            passing_score=passing_score
        )
        self.db.add(story_attempt)
        await self.db.commit()
        await self.db.refresh(story_attempt)
        
        # Update progress to mark as in progress
        practice_status = progress.practice_status.copy()
        
        # Ensure story_builder status exists and update it
        story_builder = self._ensure_assignment_status(practice_status, 'story_builder')
        story_builder['status'] = 'in_progress'
        story_builder['attempts'] = attempt_number
        story_builder['last_attempt_at'] = datetime.now(timezone.utc).isoformat()
        
        progress.practice_status = practice_status
        session_data = {
            'story_attempt_id': str(story_attempt.id),
            'current_prompt': 0,
            'prompts_remaining': total_prompts
        }
        progress.current_game_session = session_data
        
        await self.db.commit()
        
        # Store session in Redis for fast access
        await self.session_manager.set_current_session(student_id, vocabulary_list_id, session_data)
        await self.session_manager.set_current_attempt(
            student_id, vocabulary_list_id, 'story_builder',
            {
                'attempt_id': str(story_attempt.id),
                'attempt_number': attempt_number,
                'started_at': datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Return first prompt
        first_prompt = prompts[0] if prompts else None
        
        return {
            'story_attempt_id': str(story_attempt.id),
            'total_prompts': total_prompts,
            'passing_score': passing_score,
            'max_possible_score': max_possible_score,
            'current_prompt': 1,
            'prompt': self._format_story_prompt(first_prompt) if first_prompt else None
        }
    
    async def _resume_story_builder(
        self,
        student_id: UUID,
        vocabulary_list_id: UUID,
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resume an existing story builder session"""
        
        story_attempt_id = UUID(session_data['story_attempt_id'])
        
        # Get the story attempt
        result = await self.db.execute(
            select(VocabularyStoryAttempt)
            .where(VocabularyStoryAttempt.id == story_attempt_id)
            .options(selectinload(VocabularyStoryAttempt.practice_progress))
        )
        story_attempt = result.scalar_one_or_none()
        
        if not story_attempt or story_attempt.status != 'in_progress':
            # Session is stale, clear it and start fresh
            await self.session_manager.clear_session(student_id, vocabulary_list_id)
            raise ValueError("Story session is no longer valid")
        
        # Get all prompts to determine current position
        prompts_result = await self.db.execute(
            select(VocabularyStoryPrompt)
            .where(VocabularyStoryPrompt.vocabulary_list_id == vocabulary_list_id)
            .order_by(VocabularyStoryPrompt.prompt_order)
        )
        prompts = prompts_result.scalars().all()
        
        # Determine current prompt based on completed responses
        current_prompt_index = story_attempt.prompts_completed
        current_prompt = prompts[current_prompt_index] if current_prompt_index < len(prompts) else None
        
        # Update session with current state
        session_data = {
            'story_attempt_id': str(story_attempt.id),
            'current_prompt': current_prompt_index,
            'prompts_remaining': story_attempt.total_prompts - story_attempt.prompts_completed
        }
        
        await self.session_manager.set_current_session(student_id, vocabulary_list_id, session_data)
        await self.session_manager.update_activity(student_id, vocabulary_list_id)
        
        return {
            'story_attempt_id': str(story_attempt.id),
            'total_prompts': story_attempt.total_prompts,
            'passing_score': story_attempt.passing_score,
            'max_possible_score': story_attempt.max_possible_score,
            'current_prompt': current_prompt_index + 1,
            'prompt': self._format_story_prompt(current_prompt) if current_prompt else None,
            'current_score': story_attempt.current_score,
            'prompts_completed': story_attempt.prompts_completed,
            'is_resuming': True
        }
    
    async def submit_story(
        self,
        story_attempt_id: UUID,
        prompt_id: UUID,
        story_text: str,
        attempt_number: int = 1
    ) -> Dict[str, Any]:
        """Submit a story for evaluation"""
        
        # Get story attempt
        result = await self.db.execute(
            select(VocabularyStoryAttempt)
            .where(VocabularyStoryAttempt.id == story_attempt_id)
            .options(selectinload(VocabularyStoryAttempt.practice_progress))
        )
        story_attempt = result.scalar_one_or_none()
        
        if not story_attempt:
            raise ValueError("Story attempt not found")
        
        if story_attempt.status not in ['in_progress', 'pending_confirmation']:
            raise ValueError("Story attempt is already completed or invalid")
        
        # If already pending confirmation, return the completion status
        if story_attempt.status == 'pending_confirmation':
            percentage_score = (story_attempt.current_score / story_attempt.max_possible_score) * 100
            return {
                'evaluation': {'total_score': story_attempt.current_score},
                'current_score': story_attempt.current_score,
                'prompts_remaining': 0,
                'is_complete': True,
                'passed': story_attempt.status == 'pending_confirmation',
                'percentage_score': percentage_score,
                'needs_confirmation': True,
                'next_prompt': None,
                'can_revise': False
            }
        
        # Get the prompt
        prompt_result = await self.db.execute(
            select(VocabularyStoryPrompt)
            .where(VocabularyStoryPrompt.id == prompt_id)
        )
        prompt = prompt_result.scalar_one_or_none()
        
        if not prompt:
            raise ValueError("Prompt not found")
        
        # Evaluate the story
        evaluator = VocabularyStoryEvaluator()
        evaluation = await evaluator.evaluate_story(
            story_text=story_text,
            required_words=prompt.required_words,
            setting=prompt.setting,
            tone=prompt.tone,
            max_score=prompt.max_score
        )
        
        # Save story response
        story_response = VocabularyStoryResponse(
            student_id=story_attempt.student_id,
            vocabulary_list_id=story_attempt.vocabulary_list_id,
            practice_progress_id=story_attempt.practice_progress_id,
            prompt_id=prompt_id,
            story_text=story_text,
            ai_evaluation=evaluation,
            total_score=evaluation['total_score'],
            attempt_number=attempt_number
        )
        self.db.add(story_response)
        
        # Update story attempt
        story_responses = story_attempt.story_responses.copy()
        story_responses.append({
            'prompt_id': str(prompt_id),
            'prompt_order': len(story_responses) + 1,
            'attempts': attempt_number,
            'score': evaluation['total_score'],
            'story_text': story_text,
            'evaluation': evaluation
        })
        
        story_attempt.story_responses = story_responses
        story_attempt.prompts_completed = len(story_responses)
        story_attempt.current_score += evaluation['total_score']
        
        # Check if all prompts are complete
        is_complete = story_attempt.prompts_completed >= story_attempt.total_prompts
        
        if is_complete:
            # Calculate percentage score
            percentage_score = (story_attempt.current_score / story_attempt.max_possible_score) * 100
            story_attempt.status = 'pending_confirmation' if percentage_score >= 70 else 'failed'
            story_attempt.completed_at = datetime.now(timezone.utc)
            
            # Calculate total time spent
            if story_attempt.started_at:
                time_diff = story_attempt.completed_at - story_attempt.started_at
                story_attempt.time_spent_seconds = int(time_diff.total_seconds())
            
            # DO NOT update practice progress here - wait for explicit confirmation
        
        await self.db.commit()
        
        # Update Redis session if not complete
        if not is_complete:
            session_data = {
                'story_attempt_id': str(story_attempt.id),
                'current_prompt': story_attempt.prompts_completed,
                'prompts_remaining': story_attempt.total_prompts - story_attempt.prompts_completed
            }
            await self.session_manager.set_current_session(
                story_attempt.student_id, story_attempt.vocabulary_list_id, session_data
            )
            await self.session_manager.update_activity(
                story_attempt.student_id, story_attempt.vocabulary_list_id
            )
        
        # Get next prompt if not complete
        next_prompt = None
        if not is_complete:
            prompts_result = await self.db.execute(
                select(VocabularyStoryPrompt)
                .where(VocabularyStoryPrompt.vocabulary_list_id == story_attempt.vocabulary_list_id)
                .order_by(VocabularyStoryPrompt.prompt_order)
            )
            all_prompts = prompts_result.scalars().all()
            
            if len(story_responses) < len(all_prompts):
                next_prompt = all_prompts[len(story_responses)]
        
        # Calculate percentage for return
        percentage_score = None
        if is_complete:
            percentage_score = (story_attempt.current_score / story_attempt.max_possible_score) * 100
        
        return {
            'evaluation': evaluation,
            'current_score': story_attempt.current_score,
            'prompts_remaining': story_attempt.total_prompts - story_attempt.prompts_completed,
            'is_complete': is_complete,
            'passed': story_attempt.status == 'pending_confirmation' if is_complete else None,
            'percentage_score': percentage_score,
            'needs_confirmation': is_complete,
            'next_prompt': self._format_story_prompt(next_prompt) if next_prompt else None,
            'can_revise': attempt_number < 2  # Allow one revision
        }
    
    async def get_next_story_prompt(
        self,
        story_attempt_id: UUID
    ) -> Dict[str, Any]:
        """Get the next story prompt in the challenge"""
        
        # Get story attempt
        result = await self.db.execute(
            select(VocabularyStoryAttempt)
            .where(VocabularyStoryAttempt.id == story_attempt_id)
        )
        story_attempt = result.scalar_one_or_none()
        
        if not story_attempt or story_attempt.status != 'in_progress':
            raise ValueError("Invalid or completed story attempt")
        
        # Get all prompts
        prompts_result = await self.db.execute(
            select(VocabularyStoryPrompt)
            .where(VocabularyStoryPrompt.vocabulary_list_id == story_attempt.vocabulary_list_id)
            .order_by(VocabularyStoryPrompt.prompt_order)
        )
        all_prompts = prompts_result.scalars().all()
        
        # Get next unanswered prompt
        completed_count = story_attempt.prompts_completed
        if completed_count < len(all_prompts):
            next_prompt = all_prompts[completed_count]
            return {
                'prompt': self._format_story_prompt(next_prompt),
                'current_prompt': completed_count + 1,
                'total_prompts': story_attempt.total_prompts,
                'current_score': story_attempt.current_score
            }
        
        return {'prompt': None, 'is_complete': True}
    
    def _format_story_prompt(self, prompt: VocabularyStoryPrompt) -> Dict[str, Any]:
        """Format a story prompt for the frontend"""
        if not prompt:
            return None
        
        return {
            'id': str(prompt.id),
            'prompt_text': prompt.prompt_text,
            'required_words': prompt.required_words,
            'setting': prompt.setting,
            'tone': prompt.tone,
            'max_score': prompt.max_score,
            'prompt_order': prompt.prompt_order
        }
    
    async def _update_story_practice_progress(self, story_attempt: VocabularyStoryAttempt):
        """Update practice progress after story challenge completion"""
        
        progress = story_attempt.practice_progress
        practice_status = progress.practice_status.copy()
        
        # Ensure assignments dict and story_builder entry exist
        if 'assignments' not in practice_status:
            practice_status['assignments'] = {}
        if 'story_builder' not in practice_status['assignments']:
            practice_status['assignments']['story_builder'] = {
                "status": "not_started",
                "attempts": 0,
                "best_score": 0,
                "last_attempt_at": None,
                "completed_at": None
            }
        
        # Update story builder status
        story_builder = practice_status['assignments']['story_builder']
        
        if story_attempt.status == 'passed':
            story_builder['status'] = 'completed'
            story_builder['completed_at'] = datetime.now(timezone.utc).isoformat()
            
            # Add to completed assignments if not already there
            if 'story_builder' not in practice_status.get('completed_assignments', []):
                practice_status.setdefault('completed_assignments', []).append('story_builder')
        else:
            story_builder['status'] = 'failed'
        
        # Update attempt count and best score
        story_builder['attempts'] = story_attempt.attempt_number
        if story_attempt.current_score > story_builder.get('best_score', 0):
            story_builder['best_score'] = story_attempt.current_score
        
        # Check if test should be unlocked
        completed_count = len(practice_status.get('completed_assignments', []))
        if completed_count >= self.ASSIGNMENTS_TO_COMPLETE and not practice_status.get('test_unlocked'):
            practice_status['test_unlocked'] = True
            practice_status['test_unlock_date'] = datetime.now(timezone.utc).isoformat()
        
        progress.practice_status = practice_status
        progress.current_game_session = None  # Clear current session
        
        # Clear Redis session data
        await self.session_manager.clear_session(story_attempt.student_id, story_attempt.vocabulary_list_id)
        await self.session_manager.clear_attempt(story_attempt.student_id, story_attempt.vocabulary_list_id, 'story_builder')
    
    async def confirm_story_completion(
        self,
        story_attempt_id: UUID,
        student_id: UUID
    ) -> Dict[str, Any]:
        """Confirm story builder completion and create StudentAssignment record"""
        
        # Get story attempt with related data
        result = await self.db.execute(
            select(VocabularyStoryAttempt)
            .where(
                and_(
                    VocabularyStoryAttempt.id == story_attempt_id,
                    VocabularyStoryAttempt.student_id == student_id
                )
            )
            .options(selectinload(VocabularyStoryAttempt.practice_progress))
        )
        story_attempt = result.scalar_one_or_none()
        
        if not story_attempt:
            raise ValueError("Story attempt not found")
        
        if story_attempt.status != 'pending_confirmation':
            raise ValueError("Story attempt is not pending confirmation")
        
        # Calculate percentage score
        percentage_score = (story_attempt.current_score / story_attempt.max_possible_score) * 100
        
        if percentage_score < 70:
            raise ValueError("Cannot confirm completion with score below 70%")
        
        # Update story attempt status
        story_attempt.status = 'passed'
        
        # Update practice progress
        await self._update_story_practice_progress(story_attempt)
        
        # Create or update StudentAssignment record only if passed
        if story_attempt.status == 'passed':
            student_assignment = await self._create_or_update_student_assignment(
                student_id=student_id,
                assignment_id=story_attempt.vocabulary_list_id,
                classroom_assignment_id=story_attempt.practice_progress.classroom_assignment_id,
                assignment_type="vocabulary",
                subtype="story_builder"
            )
        
        await self.db.commit()
        
        # Clear all Redis data for this assignment
        await self.session_manager.clear_all_session_data(student_id, story_attempt.vocabulary_list_id)
        
        return {
            'success': True,
            'message': 'Story builder assignment completed successfully',
            'final_score': story_attempt.current_score,
            'percentage_score': percentage_score
        }
    
    async def decline_story_completion(
        self,
        story_attempt_id: UUID,
        student_id: UUID
    ) -> Dict[str, Any]:
        """Decline story completion and prepare for retake"""
        
        # Get story attempt
        result = await self.db.execute(
            select(VocabularyStoryAttempt)
            .where(
                and_(
                    VocabularyStoryAttempt.id == story_attempt_id,
                    VocabularyStoryAttempt.student_id == student_id
                )
            )
            .options(selectinload(VocabularyStoryAttempt.practice_progress))
        )
        story_attempt = result.scalar_one_or_none()
        
        if not story_attempt:
            raise ValueError("Story attempt not found")
        
        # Calculate percentage score
        percentage_score = (story_attempt.current_score / story_attempt.max_possible_score) * 100
        
        # Update story attempt status
        story_attempt.status = 'declined'
        
        # Clear Redis session data
        await self.session_manager.clear_all_session_data(student_id, story_attempt.vocabulary_list_id)
        
        await self.db.commit()
        
        return {
            'success': True,
            'message': 'Assignment declined. You can retake it later.',
            'final_score': story_attempt.current_score,
            'percentage_score': percentage_score
        }
    
    async def _create_or_update_student_assignment(
        self,
        student_id: UUID,
        assignment_id: UUID,
        classroom_assignment_id: int,
        assignment_type: str,
        subtype: str = None
    ) -> StudentAssignment:
        """Create or update StudentAssignment record"""
        
        # Check if record exists (search without subtype to find existing record)
        search_conditions = [
            StudentAssignment.student_id == student_id,
            StudentAssignment.assignment_id == assignment_id,
            StudentAssignment.classroom_assignment_id == classroom_assignment_id,
            StudentAssignment.assignment_type == assignment_type
        ]
        
        result = await self.db.execute(
            select(StudentAssignment)
            .where(and_(*search_conditions))
        )
        student_assignment = result.scalar_one_or_none()
        
        if not student_assignment:
            # Create new record
            progress_metadata = {}
            if subtype:
                progress_metadata = {
                    'completed_subtypes': [subtype],
                    'latest_subtype': subtype
                }
            
            student_assignment = StudentAssignment(
                student_id=student_id,
                assignment_id=assignment_id,
                classroom_assignment_id=classroom_assignment_id,
                assignment_type=assignment_type,
                status="completed",
                started_at=datetime.now(timezone.utc),
                completed_at=datetime.now(timezone.utc),
                progress_metadata=progress_metadata
            )
            self.db.add(student_assignment)
        else:
            # Update existing record - add new completed subtype
            current_metadata = student_assignment.progress_metadata or {}
            completed_subtypes = current_metadata.get('completed_subtypes', [])
            
            if subtype and subtype not in completed_subtypes:
                completed_subtypes.append(subtype)
                student_assignment.progress_metadata = {
                    **current_metadata,
                    'completed_subtypes': completed_subtypes,
                    'latest_subtype': subtype
                }
                student_assignment.completed_at = datetime.now(timezone.utc)
                # Update status based on completion count (need 3 out of 4)
                if len(completed_subtypes) >= 3:
                    student_assignment.status = "completed"
        
        return student_assignment
    
    # Fill-in-the-Blank Methods
    
    async def start_fill_in_blank(
        self,
        student_id: UUID,
        vocabulary_list_id: UUID,
        classroom_assignment_id: int
    ) -> Dict[str, Any]:
        """Start a new fill-in-the-blank activity with session management"""
        
        # Check for existing active session first
        existing_session = await self.session_manager.get_current_session(student_id, vocabulary_list_id)
        if existing_session and 'fill_in_blank_attempt_id' in existing_session:
            try:
                # Resume existing fill-in-blank attempt
                return await self._resume_fill_in_blank(student_id, vocabulary_list_id, existing_session)
            except ValueError:
                # Session is stale, continue to create new attempt
                pass
        
        # Get or create progress
        progress = await self.get_or_create_practice_progress(
            student_id, vocabulary_list_id, classroom_assignment_id
        )
        
        # Check if fill-in-blank is already completed
        completed_assignments = progress.practice_status.get('completed_assignments', [])
        if 'fill_in_blank' in completed_assignments:
            raise ValueError("Fill-in-the-blank has already been completed. Cannot retake completed activities.")
        
        # Check for existing pending confirmation attempt
        existing_attempt_result = await self.db.execute(
            select(VocabularyFillInBlankAttempt)
            .where(
                and_(
                    VocabularyFillInBlankAttempt.student_id == student_id,
                    VocabularyFillInBlankAttempt.vocabulary_list_id == vocabulary_list_id,
                    VocabularyFillInBlankAttempt.status == 'pending_confirmation'
                )
            )
        )
        existing_attempt = existing_attempt_result.scalar_one_or_none()
        
        if existing_attempt:
            # Return the existing attempt data with a flag to show confirmation dialog
            score_percentage = (existing_attempt.correct_answers / existing_attempt.total_sentences) * 100 if existing_attempt.total_sentences > 0 else 0
            return {
                'fill_in_blank_attempt_id': str(existing_attempt.id),
                'total_sentences': existing_attempt.total_sentences,
                'passing_score': existing_attempt.passing_score,
                'current_sentence_index': existing_attempt.total_sentences,  # All sentences completed
                'sentence': None,  # No current sentence
                'is_complete': True,
                'needs_confirmation': True,
                'correct_answers': existing_attempt.correct_answers,
                'score_percentage': score_percentage
            }
        
        # Get fill-in-blank sentences for this vocabulary list
        sentences_result = await self.db.execute(
            select(VocabularyFillInBlankSentence)
            .where(VocabularyFillInBlankSentence.vocabulary_list_id == vocabulary_list_id)
            .order_by(VocabularyFillInBlankSentence.sentence_order)
        )
        sentences = sentences_result.scalars().all()
        
        if not sentences:
            raise ValueError("No fill-in-the-blank sentences found for this vocabulary list")
        
        # Get vocabulary words for answer choices
        words_result = await self.db.execute(
            select(VocabularyWord)
            .where(VocabularyWord.list_id == vocabulary_list_id)
            .order_by(VocabularyWord.position)
        )
        words = words_result.scalars().all()
        vocabulary_words = [word.word for word in words]
        
        # Create new attempt
        attempt_number = await self._get_next_attempt_number(
            student_id, vocabulary_list_id, VocabularyFillInBlankAttempt
        )
        
        # Shuffle sentence order
        sentence_ids = [str(sentence.id) for sentence in sentences]
        random.shuffle(sentence_ids)
        
        fill_in_blank_attempt = VocabularyFillInBlankAttempt(
            student_id=student_id,
            vocabulary_list_id=vocabulary_list_id,
            practice_progress_id=progress.id,
            attempt_number=attempt_number,
            total_sentences=len(sentences),
            sentence_order=sentence_ids,
            passing_score=70
        )
        
        self.db.add(fill_in_blank_attempt)
        
        # Update progress to mark as in progress
        practice_status = progress.practice_status.copy()
        fill_in_blank_status = self._ensure_assignment_status(practice_status, 'fill_in_blank')
        fill_in_blank_status['status'] = 'in_progress'
        fill_in_blank_status['attempts'] = attempt_number
        fill_in_blank_status['last_attempt_at'] = datetime.now(timezone.utc).isoformat()
        
        progress.practice_status = practice_status
        
        await self.db.commit()
        await self.db.refresh(fill_in_blank_attempt)
        await self.db.refresh(progress)  # Ensure progress is also refreshed
        
        # Get first sentence
        first_sentence_id = UUID(sentence_ids[0])
        first_sentence_result = await self.db.execute(
            select(VocabularyFillInBlankSentence)
            .where(VocabularyFillInBlankSentence.id == first_sentence_id)
        )
        first_sentence = first_sentence_result.scalar_one()
        
        # Create session data
        session_data = {
            'fill_in_blank_attempt_id': str(fill_in_blank_attempt.id),
            'activity_type': 'fill_in_blank',
            'vocabulary_words': vocabulary_words,
            'started_at': datetime.now(timezone.utc).isoformat()
        }
        
        # Save session
        await self.session_manager.set_current_session(
            student_id, vocabulary_list_id, session_data
        )
        
        return {
            'fill_in_blank_attempt_id': str(fill_in_blank_attempt.id),
            'total_sentences': fill_in_blank_attempt.total_sentences,
            'passing_score': fill_in_blank_attempt.passing_score,
            'current_sentence_index': 0,
            'sentence': {
                'id': str(first_sentence.id),
                'sentence_with_blank': first_sentence.sentence_with_blank,
                'vocabulary_words': vocabulary_words
            },
            'is_complete': False,
            'needs_confirmation': False,
            'correct_answers': 0,
            'score_percentage': 0.0
        }
    
    async def _resume_fill_in_blank(
        self,
        student_id: UUID,
        vocabulary_list_id: UUID,
        session_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Resume an existing fill-in-blank attempt from session"""
        
        fill_in_blank_attempt_id = UUID(session_data['fill_in_blank_attempt_id'])
        
        # Get the attempt
        result = await self.db.execute(
            select(VocabularyFillInBlankAttempt)
            .where(VocabularyFillInBlankAttempt.id == fill_in_blank_attempt_id)
        )
        attempt = result.scalar_one_or_none()
        
        if not attempt:
            # Session is stale, clear it
            await self.session_manager.clear_session(student_id, vocabulary_list_id)
            raise ValueError("Fill-in-blank attempt not found. Please start a new attempt.")
        
        # Check if already complete
        if attempt.status == 'pending_confirmation':
            score_percentage = (attempt.correct_answers / attempt.total_sentences) * 100 if attempt.total_sentences > 0 else 0
            return {
                'fill_in_blank_attempt_id': str(attempt.id),
                'total_sentences': attempt.total_sentences,
                'passing_score': attempt.passing_score,
                'current_sentence_index': attempt.total_sentences,
                'sentence': None,
                'is_complete': True,
                'needs_confirmation': True,
                'correct_answers': attempt.correct_answers,
                'score_percentage': score_percentage
            }
        
        # Get current sentence
        if attempt.current_sentence_index < len(attempt.sentence_order):
            current_sentence_id = UUID(attempt.sentence_order[attempt.current_sentence_index])
            sentence_result = await self.db.execute(
                select(VocabularyFillInBlankSentence)
                .where(VocabularyFillInBlankSentence.id == current_sentence_id)
            )
            current_sentence = sentence_result.scalar_one()
            
            sentence_data = {
                'id': str(current_sentence.id),
                'sentence_with_blank': current_sentence.sentence_with_blank,
                'vocabulary_words': session_data.get('vocabulary_words', [])
            }
        else:
            sentence_data = None
        
        score_percentage = (attempt.correct_answers / attempt.total_sentences) * 100 if attempt.total_sentences > 0 else 0
        
        return {
            'fill_in_blank_attempt_id': str(attempt.id),
            'total_sentences': attempt.total_sentences,
            'passing_score': attempt.passing_score,
            'current_sentence_index': attempt.current_sentence_index,
            'sentence': sentence_data,
            'is_complete': attempt.current_sentence_index >= attempt.total_sentences,
            'needs_confirmation': False,
            'correct_answers': attempt.correct_answers,
            'score_percentage': score_percentage
        }
    
    async def submit_fill_in_blank_answer(
        self,
        fill_in_blank_attempt_id: UUID,
        sentence_id: UUID,
        student_answer: str,
        time_spent_seconds: int
    ) -> Dict[str, Any]:
        """Submit an answer for a fill-in-the-blank sentence"""
        
        # Get the attempt
        attempt_result = await self.db.execute(
            select(VocabularyFillInBlankAttempt)
            .where(VocabularyFillInBlankAttempt.id == fill_in_blank_attempt_id)
        )
        attempt = attempt_result.scalar_one_or_none()
        
        if not attempt:
            raise ValueError("Fill-in-blank attempt not found")
        
        if attempt.status not in ['in_progress']:
            raise ValueError("Cannot submit answer - attempt is not in progress")
        
        # Get the sentence
        sentence_result = await self.db.execute(
            select(VocabularyFillInBlankSentence)
            .where(VocabularyFillInBlankSentence.id == sentence_id)
        )
        sentence = sentence_result.scalar_one_or_none()
        
        if not sentence:
            raise ValueError("Sentence not found")
        
        # Evaluate the answer (case-insensitive exact match)
        is_correct = student_answer.strip().lower() == sentence.correct_answer.lower()
        
        # Create response record
        response = VocabularyFillInBlankResponse(
            student_id=attempt.student_id,
            vocabulary_list_id=attempt.vocabulary_list_id,
            practice_progress_id=attempt.practice_progress_id,
            sentence_id=sentence_id,
            student_answer=student_answer.strip(),
            is_correct=is_correct,
            attempt_number=attempt.attempt_number,
            time_spent_seconds=time_spent_seconds
        )
        
        self.db.add(response)
        
        # Update attempt progress
        if is_correct:
            attempt.correct_answers += 1
        else:
            attempt.incorrect_answers += 1
        
        attempt.sentences_completed += 1
        attempt.current_sentence_index += 1
        
        # Store response in attempt data
        response_data = {
            'sentence_id': str(sentence_id),
            'student_answer': student_answer.strip(),
            'is_correct': is_correct,
            'correct_answer': sentence.correct_answer,
            'time_spent_seconds': time_spent_seconds
        }
        
        if not attempt.responses:
            attempt.responses = {}
        attempt.responses[str(sentence_id)] = response_data
        
        # Check if assignment is complete
        is_complete = attempt.current_sentence_index >= attempt.total_sentences
        score_percentage = (attempt.correct_answers / attempt.total_sentences) * 100 if attempt.total_sentences > 0 else 0
        
        if is_complete:
            attempt.score_percentage = score_percentage
            attempt.completed_at = datetime.now(timezone.utc)
            
            # Set status to pending_confirmation for BOTH pass and fail
            # This ensures the dialog shows for both scenarios
            attempt.status = 'pending_confirmation'
        
        await self.db.commit()
        
        # Get next sentence if not complete
        next_sentence = None
        if not is_complete:
            next_sentence_id = UUID(attempt.sentence_order[attempt.current_sentence_index])
            next_sentence_result = await self.db.execute(
                select(VocabularyFillInBlankSentence)
                .where(VocabularyFillInBlankSentence.id == next_sentence_id)
            )
            next_sentence_obj = next_sentence_result.scalar_one()
            
            # Get vocabulary words from session
            session_data = await self.session_manager.get_current_session(
                attempt.student_id, attempt.vocabulary_list_id
            )
            vocabulary_words = session_data.get('vocabulary_words', []) if session_data else []
            
            next_sentence = {
                'id': str(next_sentence_obj.id),
                'sentence_with_blank': next_sentence_obj.sentence_with_blank,
                'vocabulary_words': vocabulary_words
            }
        
        progress_percentage = (attempt.sentences_completed / attempt.total_sentences) * 100
        
        return {
            'valid': True,
            'is_correct': is_correct,
            'correct_answer': sentence.correct_answer,
            'correct_answers': attempt.correct_answers,
            'sentences_remaining': attempt.total_sentences - attempt.sentences_completed,
            'is_complete': is_complete,
            'passed': score_percentage >= attempt.passing_score if is_complete else None,
            'score_percentage': score_percentage,
            'needs_confirmation': is_complete,
            'next_sentence': next_sentence,
            'progress_percentage': progress_percentage
        }
    
    async def get_fill_in_blank_progress(self, fill_in_blank_attempt_id: UUID) -> Dict[str, Any]:
        """Get current progress for fill-in-the-blank attempt"""
        
        result = await self.db.execute(
            select(VocabularyFillInBlankAttempt)
            .where(VocabularyFillInBlankAttempt.id == fill_in_blank_attempt_id)
        )
        attempt = result.scalar_one_or_none()
        
        if not attempt:
            raise ValueError("Fill-in-blank attempt not found")
        
        # Get current sentence if not complete
        current_sentence = None
        if attempt.current_sentence_index < len(attempt.sentence_order):
            current_sentence_id = UUID(attempt.sentence_order[attempt.current_sentence_index])
            sentence_result = await self.db.execute(
                select(VocabularyFillInBlankSentence)
                .where(VocabularyFillInBlankSentence.id == current_sentence_id)
            )
            sentence_obj = sentence_result.scalar_one()
            
            # Get vocabulary words from session
            session_data = await self.session_manager.get_current_session(
                attempt.student_id, attempt.vocabulary_list_id
            )
            vocabulary_words = session_data.get('vocabulary_words', []) if session_data else []
            
            current_sentence = {
                'id': str(sentence_obj.id),
                'sentence_with_blank': sentence_obj.sentence_with_blank,
                'vocabulary_words': vocabulary_words
            }
        
        # Get vocabulary words
        words_result = await self.db.execute(
            select(VocabularyWord.word)
            .where(VocabularyWord.list_id == attempt.vocabulary_list_id)
            .order_by(VocabularyWord.position)
        )
        vocabulary_words = [word for word, in words_result.fetchall()]
        
        progress_percentage = (attempt.sentences_completed / attempt.total_sentences) * 100
        
        return {
            'fill_in_blank_attempt_id': str(attempt.id),
            'status': attempt.status,
            'total_sentences': attempt.total_sentences,
            'sentences_completed': attempt.sentences_completed,
            'current_sentence_index': attempt.current_sentence_index,
            'correct_answers': attempt.correct_answers,
            'incorrect_answers': attempt.incorrect_answers,
            'passing_score': attempt.passing_score,
            'progress_percentage': progress_percentage,
            'current_sentence': current_sentence,
            'vocabulary_words': vocabulary_words
        }
    
    async def confirm_fill_in_blank_completion(
        self,
        fill_in_blank_attempt_id: UUID,
        student_id: UUID
    ) -> Dict[str, Any]:
        """Confirm completion of fill-in-the-blank assignment"""
        
        # Get the attempt
        result = await self.db.execute(
            select(VocabularyFillInBlankAttempt)
            .where(VocabularyFillInBlankAttempt.id == fill_in_blank_attempt_id)
        )
        attempt = result.scalar_one_or_none()
        
        if not attempt:
            raise ValueError("Fill-in-blank attempt not found")
        
        if attempt.student_id != student_id:
            raise ValueError("Not authorized to confirm this attempt")
        
        if attempt.status != 'pending_confirmation':
            raise ValueError("Attempt is not pending confirmation")
        
        # Check if this subtype was already completed
        ca_result = await self.db.execute(
            select(ClassroomAssignment.id)
            .where(
                and_(
                    ClassroomAssignment.vocabulary_list_id == attempt.vocabulary_list_id,
                    ClassroomAssignment.assignment_type == "vocabulary"
                )
            )
        )
        classroom_assignment_id = ca_result.scalar_one()
        
        # Check for existing StudentAssignment record
        existing_result = await self.db.execute(
            select(StudentAssignment)
            .where(
                and_(
                    StudentAssignment.student_id == student_id,
                    StudentAssignment.assignment_id == attempt.vocabulary_list_id,
                    StudentAssignment.classroom_assignment_id == classroom_assignment_id,
                    StudentAssignment.assignment_type == "vocabulary"
                )
            )
        )
        existing_assignment = existing_result.scalar_one_or_none()
        
        if existing_assignment and existing_assignment.progress_metadata:
            completed_subtypes = existing_assignment.progress_metadata.get('completed_subtypes', [])
            if 'fill_in_blank' in completed_subtypes:
                raise ValueError("Fill-in-blank assignment already completed for this vocabulary list")
        
        # Check if passed
        score_percentage = attempt.score_percentage or 0
        passed = score_percentage >= attempt.passing_score
        
        # Mark attempt status based on score
        if passed:
            attempt.status = 'passed'
        else:
            attempt.status = 'failed'
        
        # Update practice progress
        progress_result = await self.db.execute(
            select(VocabularyPracticeProgress)
            .where(VocabularyPracticeProgress.id == attempt.practice_progress_id)
        )
        progress = progress_result.scalar_one_or_none()
        
        # If progress doesn't exist (due to transaction issues), recreate it
        if not progress:
            progress = await self.get_or_create_practice_progress(
                student_id=student_id,
                vocabulary_list_id=attempt.vocabulary_list_id,
                classroom_assignment_id=classroom_assignment_id
            )
        
        # Update assignment status in practice_status
        practice_status = progress.practice_status.copy()
        fill_in_blank_status = self._ensure_assignment_status(practice_status, 'fill_in_blank')
        
        # Update status based on pass/fail
        if passed:
            fill_in_blank_status['status'] = 'completed'
            fill_in_blank_status['completed_at'] = datetime.now(timezone.utc).isoformat()
            fill_in_blank_status['best_score'] = int(score_percentage)
            
            # Ensure completed_assignments list exists
            if 'completed_assignments' not in practice_status:
                practice_status['completed_assignments'] = []
            practice_status['completed_assignments'].append('fill_in_blank')
            
            # Remove duplicates
            practice_status['completed_assignments'] = list(set(practice_status['completed_assignments']))
            
            progress.practice_status = practice_status
            
            # Create or update StudentAssignment record only if passed
            await self._create_or_update_student_assignment(
                student_id=student_id,
                assignment_id=attempt.vocabulary_list_id,
                classroom_assignment_id=classroom_assignment_id,
                assignment_type="vocabulary",
                subtype="fill_in_blank"
            )
        else:
            # Failed - just update the status, don't mark as completed
            fill_in_blank_status['status'] = 'failed'
            fill_in_blank_status['last_attempt_at'] = datetime.now(timezone.utc).isoformat()
            fill_in_blank_status['last_score'] = int(score_percentage)
            progress.practice_status = practice_status
        
        await self.db.commit()
        
        # Clear Redis session data
        await self.session_manager.clear_all_session_data(student_id, attempt.vocabulary_list_id)
        
        return {
            'success': True,
            'message': 'Fill-in-the-blank assignment completed successfully!',
            'final_score': attempt.correct_answers,
            'score_percentage': score_percentage
        }
    
    async def decline_fill_in_blank_completion(
        self,
        fill_in_blank_attempt_id: UUID,
        student_id: UUID
    ) -> Dict[str, Any]:
        """Decline fill-in-the-blank completion and prepare for retake"""
        
        # Get the attempt
        result = await self.db.execute(
            select(VocabularyFillInBlankAttempt)
            .where(VocabularyFillInBlankAttempt.id == fill_in_blank_attempt_id)
        )
        attempt = result.scalar_one_or_none()
        
        if not attempt:
            raise ValueError("Fill-in-blank attempt not found")
        
        if attempt.student_id != student_id:
            raise ValueError("Not authorized to decline this attempt")
        
        if attempt.status != 'pending_confirmation':
            raise ValueError("Attempt is not pending confirmation")
        
        score_percentage = attempt.score_percentage or 0
        
        # 1. Delete all response records for this attempt
        await self.db.execute(
            delete(VocabularyFillInBlankResponse)
            .where(
                and_(
                    VocabularyFillInBlankResponse.practice_progress_id == attempt.practice_progress_id,
                    VocabularyFillInBlankResponse.attempt_number == attempt.attempt_number
                )
            )
        )
        
        # 2. Delete the attempt record itself
        await self.db.delete(attempt)
        
        # 3. Clear Redis session data
        await self.session_manager.clear_all_session_data(student_id, attempt.vocabulary_list_id)
        
        # 4. Clear practice progress game session
        if attempt.practice_progress_id:
            progress_result = await self.db.execute(
                select(VocabularyPracticeProgress)
                .where(VocabularyPracticeProgress.id == attempt.practice_progress_id)
            )
            progress = progress_result.scalar_one_or_none()
            if progress:
                progress.current_game_session = {}
        
        await self.db.commit()
        
        return {
            'success': True,
            'message': 'Assignment declined. You can retake it later.',
            'final_score': attempt.correct_answers,
            'score_percentage': score_percentage
        }
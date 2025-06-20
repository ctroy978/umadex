"""
Vocabulary Test Service
Handles test generation, evaluation, and management
"""

import json
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, and_, or_, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.vocabulary import VocabularyList, VocabularyWord
from app.models.classroom import ClassroomAssignment
from app.services.ai_vocabulary_evaluator import AIVocabularyEvaluator

logger = logging.getLogger(__name__)


class VocabularyTestService:
    """Service for managing vocabulary tests"""

    @staticmethod
    async def check_test_eligibility(
        db: AsyncSession, 
        student_id: UUID, 
        vocabulary_list_id: UUID,
        classroom_assignment_id: UUID
    ) -> Dict[str, Any]:
        """Check if student is eligible to take vocabulary test"""
        
        # Check actual completion from StudentAssignment table
        from app.models.classroom import StudentAssignment
        from sqlalchemy import select, and_
        
        # Check completion for each vocabulary practice activity
        assignment_types = ['story_builder', 'concept_mapping', 'puzzle_path', 'fill_in_blank']
        completed_assignments = {}
        completed_count = 0
        
        for assignment_type in assignment_types:
            result = await db.execute(
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
            is_completed = completion_date is not None
            completed_assignments[assignment_type] = is_completed
            
            if is_completed:
                completed_count += 1
        
        # Student is eligible if they've completed 3 or more activities
        is_eligible = completed_count >= 3
        
        # Get test attempt information
        test_attempt_result = await db.execute(
            text("""
                SELECT COUNT(DISTINCT vta.id) as attempt_count,
                       MAX(vt.max_attempts) as max_attempts
                FROM vocabulary_tests vt
                LEFT JOIN vocabulary_test_attempts vta ON vta.test_id = vt.id 
                    AND vta.student_id = :student_id 
                    AND vta.status = 'completed'
                WHERE vt.vocabulary_list_id = :vocabulary_list_id
                AND vt.classroom_assignment_id = :classroom_assignment_id
                GROUP BY vt.vocabulary_list_id, vt.classroom_assignment_id
            """),
            {
                "student_id": str(student_id),
                "vocabulary_list_id": str(vocabulary_list_id),
                "classroom_assignment_id": classroom_assignment_id
            }
        )
        test_data = test_attempt_result.fetchone()
        
        attempts_used = test_data.attempt_count if test_data else 0
        max_attempts = test_data.max_attempts if test_data and test_data.max_attempts else 3
        attempts_remaining = max_attempts - attempts_used
        
        # Update eligibility if all attempts are used
        if is_eligible and attempts_remaining <= 0:
            is_eligible = False
            reason = f"You have used all {max_attempts} test attempts."
        else:
            reason = None if is_eligible else f"Complete at least 3 vocabulary assignments to unlock test. You have completed {completed_count} out of 4."
        
        return {
            "eligible": is_eligible,
            "reason": reason,
            "assignments_completed": completed_count,
            "assignments_required": 3,
            "progress_details": {
                "story_builder_completed": completed_assignments.get('story_builder', False),
                "concept_mapping_completed": completed_assignments.get('concept_mapping', False), 
                "puzzle_path_completed": completed_assignments.get('puzzle_path', False),
                "fill_in_blank_completed": completed_assignments.get('fill_in_blank', False)
            },
            "attempts_used": attempts_used,
            "max_attempts": max_attempts,
            "attempts_remaining": attempts_remaining
        }

    @staticmethod
    async def update_assignment_progress(
        db: AsyncSession,
        student_id: UUID,
        vocabulary_list_id: UUID,
        classroom_assignment_id: UUID,
        assignment_type: str,
        completed: bool = True
    ) -> Dict[str, Any]:
        """Update student progress for a specific assignment type"""
        
        # Map assignment types to database columns
        type_mapping = {
            "flashcards": "flashcards_completed",
            "practice": "practice_completed", 
            "challenge": "challenge_completed",
            "sentences": "sentences_completed"
        }
        
        if assignment_type not in type_mapping:
            raise ValueError(f"Invalid assignment type: {assignment_type}")
        
        column_name = type_mapping[assignment_type]
        
        # Update the specific assignment completion
        result = await db.execute(
            text(f"""
                INSERT INTO student_vocabulary_progress 
                (student_id, vocabulary_list_id, classroom_assignment_id, {column_name})
                VALUES (:student_id, :vocabulary_list_id, :classroom_assignment_id, :completed)
                ON CONFLICT (student_id, vocabulary_list_id, classroom_assignment_id) 
                DO UPDATE SET 
                    {column_name} = :completed,
                    updated_at = NOW()
                RETURNING *
            """),
            {
                "student_id": str(student_id),
                "vocabulary_list_id": str(vocabulary_list_id),
                "classroom_assignment_id": classroom_assignment_id,
                "completed": completed
            }
        )
        
        await db.commit()
        progress = result.fetchone()
        
        return {
            "assignment_type": assignment_type,
            "completed": completed,
            "total_completed": progress.assignments_completed_count,
            "test_eligible": progress.test_eligible
        }

    @staticmethod
    async def get_test_config(
        db: AsyncSession, 
        vocabulary_list_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get test configuration for a vocabulary list"""
        
        result = await db.execute(
            text("""
                SELECT * FROM vocabulary_test_configs 
                WHERE vocabulary_list_id = :vocabulary_list_id
            """),
            {"vocabulary_list_id": str(vocabulary_list_id)}
        )
        config = result.fetchone()
        
        if not config:
            return None
            
        return {
            "id": config.id,
            "vocabulary_list_id": config.vocabulary_list_id,
            "chain_enabled": config.chain_enabled,
            "chain_type": config.chain_type if hasattr(config, 'chain_type') else "weeks",
            "weeks_to_include": config.weeks_to_include,
            "questions_per_week": config.questions_per_week,
            "chained_list_ids": list(config.chained_list_ids) if hasattr(config, 'chained_list_ids') and config.chained_list_ids else [],
            "chain_id": config.chain_id if hasattr(config, 'chain_id') else None,
            "total_review_words": config.total_review_words if hasattr(config, 'total_review_words') else 3,
            "current_week_questions": config.current_week_questions,
            "max_attempts": config.max_attempts,
            "time_limit_minutes": config.time_limit_minutes,
            "created_at": config.created_at,
            "updated_at": config.updated_at
        }

    @staticmethod
    async def save_test_config(
        db: AsyncSession,
        vocabulary_list_id: UUID,
        config_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Save or update test configuration"""
        
        # Get chained_list_ids as a list (asyncpg expects a Python list for arrays)
        chained_list_ids = config_data.get("chained_list_ids", [])
        # Convert to list of strings for UUID array
        chained_list_ids_list = [str(id) for id in chained_list_ids] if chained_list_ids else []
        
        # Also get chain_id if present
        chain_id = config_data.get("chain_id")
        
        result = await db.execute(
            text("""
                INSERT INTO vocabulary_test_configs 
                (vocabulary_list_id, chain_enabled, chain_type, weeks_to_include, questions_per_week, 
                 chained_list_ids, chain_id, total_review_words, current_week_questions, max_attempts, time_limit_minutes)
                VALUES (:vocabulary_list_id, :chain_enabled, :chain_type, :weeks_to_include, :questions_per_week,
                        :chained_list_ids, :chain_id, :total_review_words, :current_week_questions, :max_attempts, :time_limit_minutes)
                ON CONFLICT (vocabulary_list_id) 
                DO UPDATE SET 
                    chain_enabled = :chain_enabled,
                    chain_type = :chain_type,
                    weeks_to_include = :weeks_to_include,
                    questions_per_week = :questions_per_week,
                    chained_list_ids = :chained_list_ids,
                    chain_id = :chain_id,
                    total_review_words = :total_review_words,
                    current_week_questions = :current_week_questions,
                    max_attempts = :max_attempts,
                    time_limit_minutes = :time_limit_minutes,
                    updated_at = NOW()
                RETURNING *
            """),
            {
                "vocabulary_list_id": str(vocabulary_list_id),
                "chain_enabled": config_data.get("chain_enabled", False),
                "chain_type": config_data.get("chain_type", "weeks"),
                "weeks_to_include": config_data.get("weeks_to_include", 1),
                "questions_per_week": config_data.get("questions_per_week", 5),
                "chained_list_ids": chained_list_ids_list,
                "chain_id": str(chain_id) if chain_id else None,
                "total_review_words": config_data.get("total_review_words", 3),
                "current_week_questions": config_data.get("current_week_questions", 10),
                "max_attempts": config_data.get("max_attempts", 3),
                "time_limit_minutes": config_data.get("time_limit_minutes", 30)
            }
        )
        
        await db.commit()
        config = result.fetchone()
        
        return {
            "id": config.id,
            "vocabulary_list_id": config.vocabulary_list_id,
            "chain_enabled": config.chain_enabled,
            "chain_type": config.chain_type if hasattr(config, 'chain_type') else "weeks",
            "weeks_to_include": config.weeks_to_include,
            "questions_per_week": config.questions_per_week,
            "chained_list_ids": list(config.chained_list_ids) if hasattr(config, 'chained_list_ids') and config.chained_list_ids else [],
            "chain_id": config.chain_id if hasattr(config, 'chain_id') else None,
            "total_review_words": config.total_review_words if hasattr(config, 'total_review_words') else 3,
            "current_week_questions": config.current_week_questions,
            "max_attempts": config.max_attempts,
            "time_limit_minutes": config.time_limit_minutes,
            "created_at": config.created_at,
            "updated_at": config.updated_at
        }

    @staticmethod
    async def generate_test(
        db: AsyncSession,
        vocabulary_list_id: UUID,
        classroom_assignment_id: UUID,
        student_id: UUID
    ) -> Dict[str, Any]:
        """Generate a new vocabulary test"""
        
        # Get test configuration
        config = await VocabularyTestService.get_test_config(db, vocabulary_list_id)
        if not config:
            # Create default config
            config = {
                "chain_enabled": False,
                "chain_type": "weeks",
                "weeks_to_include": 1,
                "questions_per_week": 5,
                "chained_list_ids": [],
                "total_review_words": 3,
                "current_week_questions": 10,
                "max_attempts": 3,
                "time_limit_minutes": 30
            }
        
        # Get vocabulary words for the current list
        result = await db.execute(
            select(VocabularyList)
            .where(VocabularyList.id == vocabulary_list_id)
            .options(selectinload(VocabularyList.words))
        )
        current_list = result.scalar_one_or_none()
        
        if not current_list or not current_list.words:
            raise ValueError("Vocabulary list not found or has no words")
        
        questions = []
        chained_lists = []
        
        # Generate questions for current week
        current_questions = await VocabularyTestService._generate_questions_for_list(
            db, current_list, config["current_week_questions"]
        )
        questions.extend(current_questions)
        
        # Handle chaining if enabled
        if config["chain_enabled"]:
            chained_questions, chained_list_ids = await VocabularyTestService._generate_chained_questions(
                db, vocabulary_list_id, classroom_assignment_id, config
            )
            questions.extend(chained_questions)
            chained_lists.extend(chained_list_ids)
        
        # Shuffle questions
        import random
        random.shuffle(questions)
        
        # Create test record
        test_id = await VocabularyTestService._create_test_record(
            db, vocabulary_list_id, classroom_assignment_id, questions, 
            chained_lists, config
        )
        
        return {
            "test_id": test_id,
            "vocabulary_list_id": vocabulary_list_id,
            "total_questions": len(questions),
            "questions": questions,
            "time_limit_minutes": config["time_limit_minutes"],
            "max_attempts": config["max_attempts"],
            "chained_lists": chained_lists,
            "expires_at": datetime.now(timezone.utc) + timedelta(hours=24),
            "created_at": datetime.now(timezone.utc)
        }

    @staticmethod
    async def _generate_questions_for_list(
        db: AsyncSession,
        vocabulary_list: VocabularyList,
        num_questions: int
    ) -> List[Dict[str, Any]]:
        """Generate questions for a specific vocabulary list"""
        
        words = vocabulary_list.words
        if len(words) < num_questions:
            num_questions = len(words)
        
        # Select random words
        import random
        selected_words = random.sample(words, num_questions)
        
        questions = []
        for word in selected_words:
            # All questions now use the same format
            question = await VocabularyTestService._create_question(
                word, "definition_from_context", vocabulary_list.id
            )
            questions.append(question)
        
        return questions

    @staticmethod
    async def _create_question(
        word: VocabularyWord,
        question_type: str,
        vocabulary_list_id: UUID
    ) -> Dict[str, Any]:
        """Create a single question for a vocabulary word with context"""
        
        # Get the best example sentence (teacher examples preferred)
        example_sentence = (
            word.teacher_example_1 or 
            word.teacher_example_2 or 
            word.ai_example_1 or 
            word.ai_example_2
        )
        
        # Get reference definition (teacher preferred)
        reference_definition = word.teacher_definition or word.ai_definition
        
        # Ensure we have both an example and definition
        if not example_sentence:
            # Generate a basic example if none exists
            example_sentence = f"The student showed {word.word} when completing the assignment."
        
        if not reference_definition:
            reference_definition = "No reference definition available"
        
        return {
            "id": str(word.id),
            "word": word.word,
            "example_sentence": example_sentence,
            "reference_definition": reference_definition,
            "question_type": "definition_from_context",
            "vocabulary_list_id": str(vocabulary_list_id)
        }

    @staticmethod
    async def _generate_chained_questions(
        db: AsyncSession,
        current_list_id: UUID,
        classroom_assignment_id: UUID,
        config: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], List[UUID]]:
        """Generate questions from previous vocabulary lists (chaining)"""
        
        # Get classroom for this assignment
        result = await db.execute(
            select(ClassroomAssignment)
            .where(ClassroomAssignment.id == classroom_assignment_id)
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            return [], []
        
        # Check chain type
        chain_type = config.get("chain_type", "weeks")
        
        if chain_type == "named_chain":
            # Use named chain
            chain_id = config.get("chain_id")
            if not chain_id:
                return [], []
            
            # Get all words from chain members
            from app.services.vocabulary_chain import VocabularyChainService
            chain_lists = await VocabularyChainService.get_lists_for_chain(db, chain_id)
            
            all_words = []
            valid_list_ids = []
            
            for vocab_list in chain_lists:
                if vocab_list.status == 'published' and vocab_list.id != current_list_id:
                    # Load words for this list
                    result = await db.execute(
                        select(VocabularyList)
                        .where(VocabularyList.id == vocab_list.id)
                        .options(selectinload(VocabularyList.words))
                    )
                    list_with_words = result.scalar_one_or_none()
                    
                    if list_with_words and list_with_words.words:
                        for word in list_with_words.words:
                            all_words.append((word, vocab_list.id))
                        valid_list_ids.append(vocab_list.id)
            
            # Get total review words from chain configuration
            result = await db.execute(
                text("""
                    SELECT total_review_words FROM vocabulary_chains 
                    WHERE id = :chain_id
                """),
                {"chain_id": str(chain_id)}
            )
            chain_data = result.fetchone()
            total_review_words = chain_data.total_review_words if chain_data else config.get("total_review_words", 3)
            
            # Randomly select review words
            if all_words:
                total_review_words = min(total_review_words, len(all_words))
                import random
                selected_word_pairs = random.sample(all_words, total_review_words)
                
                questions = []
                for word, list_id in selected_word_pairs:
                    # Use consistent question format
                    question = await VocabularyTestService._create_question(
                        word, "definition_from_context", list_id
                    )
                    questions.append(question)
                
                return questions, valid_list_ids
            
            return [], []
            
        elif chain_type == "specific_lists":
            # Use specific lists provided in config
            chained_list_ids = config.get("chained_list_ids", [])
            if not chained_list_ids:
                return [], []
            
            # Get all words from chained lists
            all_words = []
            valid_list_ids = []
            
            for list_id in chained_list_ids:
                result = await db.execute(
                    select(VocabularyList)
                    .where(VocabularyList.id == list_id)
                    .where(VocabularyList.status == 'published')
                    .options(selectinload(VocabularyList.words))
                )
                vocab_list = result.scalar_one_or_none()
                
                if vocab_list and vocab_list.words:
                    for word in vocab_list.words:
                        all_words.append((word, vocab_list.id))
                    valid_list_ids.append(vocab_list.id)
            
            # Randomly select total_review_words from all available words
            if all_words:
                total_review_words = min(config.get("total_review_words", 3), len(all_words))
                import random
                selected_word_pairs = random.sample(all_words, total_review_words)
                
                questions = []
                for word, list_id in selected_word_pairs:
                    # Use consistent question format
                    question = await VocabularyTestService._create_question(
                        word, "definition_from_context", list_id
                    )
                    questions.append(question)
                
                return questions, valid_list_ids
            
            return [], []
        
        else:  # weeks-based chaining (existing logic)
            # Find previous vocabulary assignments in the same classroom
            weeks_back = config["weeks_to_include"]
            cutoff_date = datetime.now(timezone.utc) - timedelta(weeks=weeks_back)
            
            result = await db.execute(
                text("""
                    SELECT DISTINCT vl.* FROM vocabulary_lists vl
                    JOIN classroom_assignments ca ON ca.assignment_id = vl.id
                    WHERE ca.classroom_id = :classroom_id
                    AND ca.assignment_type = 'vocabulary'
                    AND ca.id != :current_assignment_id
                    AND ca.created_at >= :cutoff_date
                    AND vl.status = 'published'
                    ORDER BY ca.created_at DESC
                    LIMIT :max_lists
                """),
                {
                    "classroom_id": str(assignment.classroom_id),
                    "current_assignment_id": classroom_assignment_id,
                    "cutoff_date": cutoff_date,
                    "max_lists": weeks_back
                }
            )
            
            previous_assignments = result.fetchall()
            
            all_questions = []
            chained_list_ids = []
            
            for prev_assignment in previous_assignments:
                # Get vocabulary list with words
                result = await db.execute(
                    select(VocabularyList)
                    .where(VocabularyList.id == prev_assignment.id)
                    .options(selectinload(VocabularyList.words))
                )
                prev_list = result.scalar_one_or_none()
                
                if prev_list and prev_list.words:
                    questions = await VocabularyTestService._generate_questions_for_list(
                        db, prev_list, config["questions_per_week"]
                    )
                    all_questions.extend(questions)
                    chained_list_ids.append(prev_list.id)
            
            return all_questions, chained_list_ids

    @staticmethod
    async def _create_test_record(
        db: AsyncSession,
        vocabulary_list_id: UUID,
        classroom_assignment_id: UUID,
        questions: List[Dict[str, Any]],
        chained_lists: List[UUID],
        config: Dict[str, Any]
    ) -> UUID:
        """Create a test record in the database"""
        
        expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
        
        result = await db.execute(
            text("""
                INSERT INTO vocabulary_tests 
                (vocabulary_list_id, classroom_assignment_id, questions, total_questions,
                 chained_lists, expires_at, max_attempts, time_limit_minutes)
                VALUES (:vocabulary_list_id, :classroom_assignment_id, :questions, :total_questions,
                        :chained_lists, :expires_at, :max_attempts, :time_limit_minutes)
                RETURNING id
            """),
            {
                "vocabulary_list_id": str(vocabulary_list_id),
                "classroom_assignment_id": classroom_assignment_id,
                "questions": json.dumps(questions),
                "total_questions": len(questions),
                "chained_lists": json.dumps([str(id) for id in chained_lists]),
                "expires_at": expires_at,
                "max_attempts": config["max_attempts"],
                "time_limit_minutes": config["time_limit_minutes"]
            }
        )
        
        await db.commit()
        test = result.fetchone()
        return test.id

    @staticmethod
    async def start_test_attempt(
        db: AsyncSession,
        test_id: UUID,
        student_id: UUID
    ) -> UUID:
        """Start a new test attempt"""
        
        # Check if test exists and is not expired
        result = await db.execute(
            text("""
                SELECT * FROM vocabulary_tests 
                WHERE id = :test_id AND expires_at > NOW()
            """),
            {"test_id": str(test_id)}
        )
        test = result.fetchone()
        
        if not test:
            raise ValueError("Test not found or expired")
        
        # Check if student has attempts remaining
        result = await db.execute(
            text("""
                SELECT COUNT(*) FROM vocabulary_test_attempts 
                WHERE test_id = :test_id AND student_id = :student_id
                AND status = 'completed'
            """),
            {"test_id": str(test_id), "student_id": str(student_id)}
        )
        attempts_count = result.scalar()
        
        if attempts_count >= test.max_attempts:
            raise ValueError("Maximum attempts exceeded")
        
        # Create test attempt
        result = await db.execute(
            text("""
                INSERT INTO vocabulary_test_attempts 
                (test_id, student_id, responses, score_percentage, questions_correct,
                 total_questions, started_at, status)
                VALUES (:test_id, :student_id, '{}', 0, 0, :total_questions, NOW(), 'in_progress')
                RETURNING id
            """),
            {
                "test_id": str(test_id),
                "student_id": str(student_id),
                "total_questions": test.total_questions
            }
        )
        
        await db.commit()
        attempt = result.fetchone()
        return attempt.id

    @staticmethod
    async def evaluate_test_attempt(
        db: AsyncSession,
        test_attempt_id: UUID,
        responses: Dict[str, str]
    ) -> Dict[str, Any]:
        """Evaluate and score a completed test attempt"""
        
        # Get test attempt and test data
        result = await db.execute(
            text("""
                SELECT ta.*, vt.questions, vt.total_questions, vt.vocabulary_list_id,
                       vt.classroom_assignment_id, vt.chained_lists
                FROM vocabulary_test_attempts ta
                JOIN vocabulary_tests vt ON vt.id = ta.test_id
                WHERE ta.id = :test_attempt_id
            """),
            {"test_attempt_id": str(test_attempt_id)}
        )
        attempt_data = result.fetchone()
        
        if not attempt_data:
            raise ValueError("Test attempt not found")
        
        questions = attempt_data.questions
        detailed_results = []
        correct_count = 0
        
        # Initialize AI evaluator
        ai_evaluator = AIVocabularyEvaluator()
        
        # For now, we'll skip grade level since it's not in the users table
        grade_level = None
        
        # Evaluate each question
        for question in questions:
            question_id = question["id"]
            word = question["word"]
            example_sentence = question["example_sentence"]
            reference_definition = question["reference_definition"]
            student_answer = responses.get(question_id, "").strip()
            
            # Evaluate answer using AI service
            evaluation = await ai_evaluator.evaluate_definition(
                word=word,
                example_sentence=example_sentence,
                reference_definition=reference_definition,
                student_definition=student_answer,
                grade_level=grade_level
            )
            
            is_correct = evaluation["score"] >= 70  # 70% threshold for correct
            if is_correct:
                correct_count += 1
            
            detailed_results.append({
                "question_id": question_id,
                "word": word,
                "example_sentence": example_sentence,
                "student_answer": student_answer,
                "score": evaluation["score"],
                "is_correct": is_correct,
                "feedback": evaluation["feedback"],
                "strengths": evaluation["strengths"],
                "areas_for_growth": evaluation["areas_for_growth"],
                "component_scores": evaluation.get("component_scores", {})
            })
        
        # Calculate final score
        total_questions = len(questions)
        score_percentage = (correct_count / total_questions) * 100 if total_questions > 0 else 0
        
        # Update test attempt and get the updated record
        completed_at = datetime.now(timezone.utc)
        result = await db.execute(
            text("""
                UPDATE vocabulary_test_attempts 
                SET responses = :responses,
                    score_percentage = :score_percentage,
                    questions_correct = :questions_correct,
                    completed_at = :completed_at,
                    status = 'completed',
                    time_spent_seconds = EXTRACT(EPOCH FROM (:completed_at - started_at))
                WHERE id = :test_attempt_id
                RETURNING time_spent_seconds
            """),
            {
                "test_attempt_id": str(test_attempt_id),
                "responses": json.dumps(responses),
                "score_percentage": score_percentage,
                "questions_correct": correct_count,
                "completed_at": completed_at
            }
        )
        
        updated_attempt = result.fetchone()
        time_spent_seconds = int(updated_attempt.time_spent_seconds) if updated_attempt.time_spent_seconds else None
        
        # Create gradebook entry
        await VocabularyTestService._create_gradebook_entry(
            db, attempt_data, score_percentage, correct_count, detailed_results
        )
        
        await db.commit()
        
        return {
            "test_attempt_id": test_attempt_id,
            "test_id": attempt_data.test_id,
            "score_percentage": score_percentage,
            "questions_correct": correct_count,
            "total_questions": total_questions,
            "time_spent_seconds": time_spent_seconds,
            "status": "completed",
            "started_at": attempt_data.started_at,
            "completed_at": completed_at,
            "detailed_results": detailed_results
        }


    @staticmethod
    async def _create_gradebook_entry(
        db: AsyncSession,
        attempt_data: Any,
        score_percentage: float,
        questions_correct: int,
        detailed_results: List[Dict[str, Any]]
    ) -> None:
        """Create or update gradebook entry for the test score - only keeping the highest score"""
        
        # Get classroom ID from the assignment
        result = await db.execute(
            text("""
                SELECT classroom_id FROM classroom_assignments 
                WHERE id = :assignment_id
            """),
            {"assignment_id": attempt_data.classroom_assignment_id}
        )
        classroom = result.fetchone()
        
        if not classroom:
            return
        
        # Check if a gradebook entry already exists for this student/assignment
        existing_entry_result = await db.execute(
            text("""
                SELECT id, score_percentage, attempt_number 
                FROM gradebook_entries 
                WHERE student_id = :student_id 
                AND classroom_id = :classroom_id 
                AND assignment_type = 'umavocab_test' 
                AND assignment_id = :assignment_id
                ORDER BY score_percentage DESC
                LIMIT 1
            """),
            {
                "student_id": str(attempt_data.student_id),
                "classroom_id": str(classroom.classroom_id),
                "assignment_id": str(attempt_data.vocabulary_list_id)
            }
        )
        existing_entry = existing_entry_result.fetchone()
        
        # Calculate the attempt number
        if existing_entry:
            current_attempt_number = (existing_entry.attempt_number or 1) + 1
            
            # Only update if the new score is higher
            if score_percentage > existing_entry.score_percentage:
                # Update the existing entry with the higher score
                await db.execute(
                    text("""
                        UPDATE gradebook_entries 
                        SET score_percentage = :score_percentage,
                            points_earned = :points_earned,
                            points_possible = :points_possible,
                            completed_at = NOW(),
                            attempt_number = :attempt_number,
                            metadata = :metadata,
                            updated_at = NOW()
                        WHERE id = :entry_id
                    """),
                    {
                        "entry_id": str(existing_entry.id),
                        "score_percentage": score_percentage,
                        "points_earned": questions_correct,
                        "points_possible": attempt_data.total_questions,
                        "attempt_number": current_attempt_number,
                        "metadata": json.dumps({
                            "test_attempt_id": str(attempt_data.id),
                            "questions_correct": questions_correct,
                            "total_questions": attempt_data.total_questions,
                            "chained_lists": attempt_data.chained_lists if hasattr(attempt_data, 'chained_lists') else [],
                            "time_spent_seconds": None,  # Will be calculated after completion
                            "previous_best_score": float(existing_entry.score_percentage)
                        })
                    }
                )
            else:
                # Still update the attempt number even if score is lower
                await db.execute(
                    text("""
                        UPDATE gradebook_entries 
                        SET attempt_number = :attempt_number,
                            updated_at = NOW()
                        WHERE id = :entry_id
                    """),
                    {
                        "entry_id": str(existing_entry.id),
                        "attempt_number": current_attempt_number
                    }
                )
        else:
            # Create new gradebook entry for first attempt
            await db.execute(
                text("""
                    INSERT INTO gradebook_entries 
                    (student_id, classroom_id, assignment_type, assignment_id, score_percentage,
                     points_earned, points_possible, completed_at, attempt_number, metadata)
                    VALUES (:student_id, :classroom_id, 'umavocab_test', :assignment_id, 
                            :score_percentage, :points_earned, :points_possible, NOW(), 1, :metadata)
                """),
                {
                    "student_id": str(attempt_data.student_id),
                    "classroom_id": str(classroom.classroom_id),
                    "assignment_id": str(attempt_data.vocabulary_list_id),
                    "score_percentage": score_percentage,
                    "points_earned": questions_correct,
                    "points_possible": attempt_data.total_questions,
                    "metadata": json.dumps({
                        "test_attempt_id": str(attempt_data.id),
                        "questions_correct": questions_correct,
                        "total_questions": attempt_data.total_questions,
                        "chained_lists": attempt_data.chained_lists if hasattr(attempt_data, 'chained_lists') else [],
                        "time_spent_seconds": None  # Will be calculated after completion
                    })
                }
            )

    @staticmethod
    async def check_test_time_allowed(
        db: AsyncSession,
        classroom_assignment_id: UUID,
        check_time: Optional[datetime] = None
    ) -> Tuple[bool, Optional[str]]:
        """Check if test taking is allowed at the current time"""
        
        if check_time is None:
            check_time = datetime.now(timezone.utc)
        
        result = await db.execute(
            text("SELECT is_test_time_allowed(:assignment_id, :check_time)"),
            {
                "assignment_id": classroom_assignment_id,
                "check_time": check_time
            }
        )
        
        is_allowed = result.scalar()
        
        if not is_allowed:
            # Get restriction details for explanation
            result = await db.execute(
                text("""
                    SELECT test_start_date, test_end_date, test_time_restrictions
                    FROM classroom_assignments 
                    WHERE id = :assignment_id
                """),
                {"assignment_id": classroom_assignment_id}
            )
            assignment = result.fetchone()
            
            if assignment:
                if assignment.test_start_date and check_time < assignment.test_start_date:
                    return False, f"Test not available until {assignment.test_start_date.strftime('%Y-%m-%d %H:%M')}"
                elif assignment.test_end_date and check_time > assignment.test_end_date:
                    return False, "Test period has ended"
                else:
                    return False, "Test not available during current time"
        
        return True, None
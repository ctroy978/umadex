"""
UMATest Evaluation Service
Implements AI evaluation for UMATest following UMARead patterns
"""
import json
import logging
import asyncio
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field, validator
import google.generativeai as genai

from app.models.tests import StudentTestAttempt, TestQuestionEvaluation
from app.models.umatest import TestAssignment
from app.models.user import User
from app.config.ai_models import ANSWER_EVALUATION_MODEL
from app.config.ai_config import get_gemini_config
from app.config.rubric_config import (
    UMAREAD_SCORING_RUBRIC,
    get_rubric_score_points,
    calculate_total_score,
    get_grade_adjustment_factor
)

logger = logging.getLogger(__name__)

# Gemini configuration will be done in the evaluation method


# Pydantic models for structured AI responses
class QuestionEvaluation(BaseModel):
    """Individual question evaluation result"""
    rubric_score: int = Field(ge=0, le=4, description="Score on 4-point rubric (0-4)")
    scoring_rationale: str = Field(description="Explanation for the score")
    feedback: Optional[str] = Field(None, description="Feedback for improvement")
    key_concepts_identified: List[str] = Field(default_factory=list)
    misconceptions_detected: List[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0, description="Evaluation confidence")
    
    @validator('feedback')
    def feedback_required_for_low_scores(cls, v, values):
        if 'rubric_score' in values and values['rubric_score'] < 4:
            if not v or len(v.strip()) < 10:
                raise ValueError("Feedback required for scores below 4")
        return v


class TestEvaluationResult(BaseModel):
    """Complete test evaluation result"""
    question_evaluations: List[QuestionEvaluation]
    overall_quality_notes: Optional[str] = None
    evaluation_confidence: float = Field(ge=0.0, le=1.0)
    unusual_patterns: List[str] = Field(default_factory=list)


class UMATestEvaluationService:
    """Service for evaluating UMATest submissions using AI and rubric."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        
    async def evaluate_test_submission(
        self,
        test_attempt_id: UUID,
        trigger_source: str = "student_submission"
    ) -> Dict[str, Any]:
        """
        Evaluate a completed UMATest using AI.
        
        Args:
            test_attempt_id: The UUID of the test attempt to evaluate
            trigger_source: Source of evaluation trigger
            
        Returns:
            Dict containing evaluation results and status
        """
        logger.info(f"\n{'='*60}")
        logger.info(f"STARTING UMATEST EVALUATION")
        logger.info(f"Test Attempt ID: {test_attempt_id}")
        logger.info(f"Trigger Source: {trigger_source}")
        logger.info(f"{'='*60}\n")
        
        try:
            # Load test data
            test_data = await self._load_test_data(test_attempt_id)
            if not test_data:
                raise ValueError(f"Test attempt {test_attempt_id} not found or not ready for evaluation")
            
            # Perform AI evaluation
            evaluation_result = await self._perform_ai_evaluation(test_data)
            
            # Store evaluation results
            await self._store_evaluation_results(test_attempt_id, evaluation_result, test_data)
            
            # Calculate final score
            final_score = await self._calculate_and_store_final_score(test_attempt_id, test_data)
            
            # Update attempt status
            await self._update_attempt_status(test_attempt_id, "graded")
            
            return {
                "success": True,
                "test_attempt_id": str(test_attempt_id),
                "score": float(final_score),
                "evaluation_confidence": evaluation_result.evaluation_confidence
            }
            
        except Exception as e:
            logger.error(f"Error evaluating test {test_attempt_id}: {str(e)}", exc_info=True)
            await self._handle_evaluation_failure(test_attempt_id, str(e))
            raise
    
    async def _load_test_data(self, test_attempt_id: UUID) -> Optional[Dict[str, Any]]:
        """Load all necessary data for test evaluation."""
        # Get test attempt with related data
        result = await self.db.execute(
            select(StudentTestAttempt)
            .where(StudentTestAttempt.id == test_attempt_id)
            .options(selectinload(StudentTestAttempt.student))
        )
        test_attempt = result.scalar_one_or_none()
        
        if not test_attempt or test_attempt.status != 'submitted':
            return None
        
        # Get test assignment
        result = await self.db.execute(
            select(TestAssignment)
            .where(TestAssignment.id == test_attempt.test_id)
        )
        test_assignment = result.scalar_one_or_none()
        
        if not test_assignment:
            return None
        
        # Get student info
        student = test_attempt.student
        
        return {
            "test_attempt": test_attempt,
            "test_assignment": test_assignment,
            "student": student,
            "questions": test_assignment.test_structure.get('topics', {}),
            "answers": test_attempt.answers_data or {}
        }
    
    async def _perform_ai_evaluation(self, test_data: Dict[str, Any]) -> TestEvaluationResult:
        """Perform AI evaluation of all test answers."""
        questions = test_data["questions"]
        answers = test_data["answers"]
        test_assignment = test_data["test_assignment"]
        
        logger.info(f"Processing test with {len(questions)} topics")
        logger.info(f"Answers data keys: {list(answers.keys()) if answers else 'No answers'}")
        logger.info(f"Answers data: {answers}")
        logger.info(f"Question structure sample: {list(questions.keys())[:3] if questions else 'No questions'}")
        
        # Build list of questions with answers
        question_list = []
        question_index_map = {}
        index = 0
        
        for topic_id, topic_data in questions.items():
            topic_questions = topic_data.get('questions', [])
            logger.info(f"Topic {topic_id}: {len(topic_questions)} questions, topic_data keys: {list(topic_data.keys())}")
            
            for q_idx, question in enumerate(topic_questions):
                answer = answers.get(str(index), '')
                logger.info(f"Question {index} (topic {topic_id}, q_idx {q_idx}): Has answer: {bool(answer)}, Answer length: {len(answer)}")
                logger.info(f"Question type: {type(question)}, Question keys: {list(question.keys()) if isinstance(question, dict) else 'Not a dict'}")
                
                question_list.append({
                    'index': index,
                    'question': question,
                    'topic': topic_data.get('topic_title', ''),
                    'lecture': topic_data.get('source_lecture_title', ''),
                    'answer': answer
                })
                question_index_map[index] = question
                index += 1
        
        # Evaluate each question
        evaluations = []
        logger.info(f"Starting evaluation of {len(question_list)} questions")
        
        for item in question_list:
            try:
                logger.info(f"\n=== EVALUATING QUESTION {item['index']} ===")
                logger.info(f"Question text: {item['question'].get('question_text', '')[:100]}...")
                logger.info(f"Student answer present: {bool(item['answer'])}, Length: {len(item['answer']) if item['answer'] else 0}")
                
                evaluation = await self._evaluate_single_question(
                    question_data=item['question'],
                    student_answer=item['answer'],
                    topic_context=item['topic'],
                    lecture_context=item['lecture']
                )
                evaluations.append(evaluation)
                
                logger.info(f"Question {item['index']} evaluated successfully - Score: {evaluation.rubric_score}")
                logger.info(f"Total evaluations completed: {len(evaluations)} of {len(question_list)}")
                
                # Add small delay between evaluations to avoid rate limiting
                if item['index'] < len(question_list) - 1:
                    logger.info(f"Waiting 0.5s before next evaluation...")
                    await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"\n!!! EVALUATION FAILED for question {item['index']} !!!", exc_info=True)
                # Add a failed evaluation so we don't skip questions
                evaluations.append(QuestionEvaluation(
                    rubric_score=0,
                    scoring_rationale=f"Evaluation failed: {str(e)[:100]}",
                    feedback="Please ask your teacher to review this question.",
                    key_concepts_identified=[],
                    misconceptions_detected=[],
                    confidence=0.1
                ))
                logger.info(f"Added fallback evaluation for question {item['index']}")
        
        # Calculate overall confidence
        avg_confidence = sum(e.confidence for e in evaluations) / len(evaluations) if evaluations else 0.5
        
        logger.info(f"Completed evaluation of {len(evaluations)} questions (expected {len(question_list)})")
        
        return TestEvaluationResult(
            question_evaluations=evaluations,
            evaluation_confidence=avg_confidence,
            overall_quality_notes=self._generate_overall_notes(evaluations)
        )
    
    async def _evaluate_single_question(
        self,
        question_data: Dict[str, Any],
        student_answer: str,
        topic_context: str,
        lecture_context: str
    ) -> QuestionEvaluation:
        """Evaluate a single question using AI."""
        if not student_answer or not student_answer.strip():
            # Return no credit for blank answers
            return QuestionEvaluation(
                rubric_score=0,
                scoring_rationale="No answer provided",
                feedback="Please provide an answer to receive credit for this question.",
                key_concepts_identified=[],
                misconceptions_detected=[],
                confidence=1.0
            )
        
        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(
            question_data=question_data,
            student_answer=student_answer,
            topic_context=topic_context,
            lecture_context=lecture_context
        )
        
        # Try AI evaluation with retries
        for attempt in range(self.max_retries):
            try:
                # Configure Gemini for each attempt to ensure fresh connection
                gemini_config = get_gemini_config()
                if not gemini_config.api_key:
                    logger.error("GEMINI_API_KEY not found in configuration!")
                    raise ValueError("GEMINI_API_KEY is not configured")
                genai.configure(api_key=gemini_config.api_key)
                
                logger.info(f"Creating Gemini model {ANSWER_EVALUATION_MODEL} for question evaluation (attempt {attempt + 1})")
                
                model = genai.GenerativeModel(
                    model_name=ANSWER_EVALUATION_MODEL,
                    generation_config={
                        "temperature": 0.3,
                        "top_p": 0.95,
                        "max_output_tokens": 1000,
                    }
                )
                
                # Use asyncio.to_thread for async compatibility
                logger.info(f"Sending request to Gemini API for question evaluation...")
                response = await asyncio.to_thread(
                    model.generate_content,
                    prompt
                )
                
                logger.info(f"Received response from Gemini API")
                logger.debug(f"Raw AI response: {response.text[:500]}...")
                
                # Parse the response
                evaluation = self._parse_ai_response(response.text)
                logger.info(f"Successfully parsed AI response - Score: {evaluation.rubric_score}")
                return evaluation
                
            except Exception as e:
                logger.error(f"AI evaluation attempt {attempt + 1} failed for question: {str(e)}")
                logger.error(f"Question text: {question_data.get('question_text', '')[:100]}...")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay)
                else:
                    # Fallback to basic evaluation
                    logger.warning("Using fallback basic evaluation")
                    return self._basic_evaluation(student_answer, question_data)
    
    def _build_evaluation_prompt(
        self,
        question_data: Dict[str, Any],
        student_answer: str,
        topic_context: str,
        lecture_context: str
    ) -> str:
        """Build the evaluation prompt for AI."""
        answer_key = question_data.get('answer_key', {})
        
        prompt = f"""You are evaluating a student's answer to a test question based on UMALecture content.

**Context:**
- Lecture: {lecture_context}
- Topic: {topic_context}
- Difficulty Level: {question_data.get('difficulty_level', 'intermediate')}

**Question:**
{question_data.get('question_text', '')}

**Expected Answer (Teacher Reference):**
{answer_key.get('correct_answer', '')}

**Evaluation Criteria:**
{answer_key.get('evaluation_rubric', '')}

**Student's Answer:**
{student_answer}

**Scoring Rubric (0-4 points):**
4 (Excellent): Complete understanding with accurate response. All key concepts present.
3 (Good): Adequate understanding with minor gaps. Most concepts correct.
2 (Fair): Partial understanding with some key elements missing or incorrect.
1 (Poor): Limited understanding with significant gaps or errors.
0 (No Credit): No understanding demonstrated or completely incorrect.

**IMPORTANT - Reasonable Accuracy Standard:**
- Students don't need perfect wording or complete sentences
- Accept paraphrasing and informal language
- Focus on conceptual understanding over memorization
- Be supportive and encouraging in feedback
- Consider the difficulty level when evaluating

Please evaluate the student's answer and provide:
1. Rubric Score (0-4)
2. Scoring Rationale (2-3 sentences explaining the score)
3. Feedback (if score < 4, provide constructive feedback for improvement)
4. Key Concepts Identified (list concepts the student understood)
5. Misconceptions Detected (list any misunderstandings)
6. Confidence (0.0-1.0, your confidence in this evaluation)

Format your response as JSON:
{{
    "rubric_score": <0-4>,
    "scoring_rationale": "<explanation>",
    "feedback": "<constructive feedback or null>",
    "key_concepts_identified": ["concept1", "concept2"],
    "misconceptions_detected": ["misconception1"],
    "confidence": <0.0-1.0>
}}"""
        
        return prompt
    
    def _parse_ai_response(self, response_text: str) -> QuestionEvaluation:
        """Parse AI response into QuestionEvaluation object."""
        try:
            logger.debug(f"Parsing AI response of length: {len(response_text)}")
            
            # Clean up response text
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]
            
            # Parse JSON
            data = json.loads(response_text)
            logger.debug(f"Parsed JSON data keys: {list(data.keys())}")
            
            # Create evaluation object
            evaluation = QuestionEvaluation(
                rubric_score=int(data.get('rubric_score', 0)),
                scoring_rationale=data.get('scoring_rationale', 'Unable to parse evaluation'),
                feedback=data.get('feedback'),
                key_concepts_identified=data.get('key_concepts_identified', []),
                misconceptions_detected=data.get('misconceptions_detected', []),
                confidence=float(data.get('confidence', 0.5))
            )
            
            logger.debug(f"Created evaluation object with score: {evaluation.rubric_score}")
            return evaluation
            
        except Exception as e:
            logger.error(f"Failed to parse AI response: {str(e)}", exc_info=True)
            logger.error(f"Response text that failed to parse: {response_text[:200]}...")
            # Return a conservative evaluation
            return QuestionEvaluation(
                rubric_score=1,
                scoring_rationale="Evaluation parsing failed; conservative score assigned",
                feedback="Please review this answer with your teacher",
                key_concepts_identified=[],
                misconceptions_detected=[],
                confidence=0.3
            )
    
    def _basic_evaluation(self, student_answer: str, question_data: Dict[str, Any]) -> QuestionEvaluation:
        """Fallback basic evaluation when AI fails."""
        answer_length = len(student_answer.strip().split())
        
        if answer_length < 5:
            rubric_score = 1
            rationale = "Very brief answer provided"
            feedback = "Try to provide more detail in your answer"
        elif answer_length < 20:
            rubric_score = 2
            rationale = "Moderate length answer provided"
            feedback = "Consider expanding your answer with more details"
        else:
            rubric_score = 3
            rationale = "Detailed answer provided"
            feedback = "Good effort on providing a detailed response"
        
        return QuestionEvaluation(
            rubric_score=rubric_score,
            scoring_rationale=rationale,
            feedback=feedback,
            key_concepts_identified=[],
            misconceptions_detected=[],
            confidence=0.3
        )
    
    def _generate_overall_notes(self, evaluations: List[QuestionEvaluation]) -> str:
        """Generate overall quality notes for the test."""
        avg_score = sum(e.rubric_score for e in evaluations) / len(evaluations) if evaluations else 0
        low_scores = sum(1 for e in evaluations if e.rubric_score <= 1)
        
        notes = []
        if avg_score >= 3.5:
            notes.append("Strong overall performance")
        elif avg_score >= 2.5:
            notes.append("Good understanding with room for improvement")
        else:
            notes.append("Needs additional review of material")
        
        if low_scores > len(evaluations) * 0.3:
            notes.append(f"Multiple questions ({low_scores}) need review")
        
        return "; ".join(notes)
    
    async def _store_evaluation_results(
        self,
        test_attempt_id: UUID,
        evaluation_result: TestEvaluationResult,
        test_data: Dict[str, Any]
    ):
        """Store evaluation results in the database."""
        try:
            # Delete any existing evaluations
            logger.info(f"Deleting existing evaluations for test {test_attempt_id}")
            await self.db.execute(
                TestQuestionEvaluation.__table__.delete().where(
                    TestQuestionEvaluation.test_attempt_id == test_attempt_id
                )
            )
            
            # Calculate points per question
            total_questions = len(evaluation_result.question_evaluations)
            points_per_question = 100.0 / total_questions if total_questions > 0 else 0
            
            # Store each question evaluation
            logger.info(f"Starting to store {len(evaluation_result.question_evaluations)} question evaluations")
            
            for index, evaluation in enumerate(evaluation_result.question_evaluations):
                points_earned = (evaluation.rubric_score / 4.0) * points_per_question
                
                logger.info(f"Creating evaluation record for question {index}: Score {evaluation.rubric_score}, Points: {points_earned}")
                
                question_eval = TestQuestionEvaluation(
                    test_attempt_id=test_attempt_id,
                    question_index=index,
                    rubric_score=evaluation.rubric_score,
                    points_earned=Decimal(str(round(points_earned, 2))),
                    max_points=Decimal(str(round(points_per_question, 2))),
                    scoring_rationale=evaluation.scoring_rationale,
                    feedback=evaluation.feedback,
                    key_concepts_identified=evaluation.key_concepts_identified,
                    misconceptions_detected=evaluation.misconceptions_detected,
                    evaluation_confidence=evaluation.confidence
                )
                self.db.add(question_eval)
                logger.info(f"Added evaluation for question {index} to session")
            
            logger.info(f"Committing {len(evaluation_result.question_evaluations)} evaluations to database")
            await self.db.commit()
            logger.info(f"Successfully committed all evaluations to database")
            
        except Exception as e:
            logger.error(f"Error storing evaluation results: {str(e)}", exc_info=True)
            await self.db.rollback()
            raise
    
    async def _calculate_and_store_final_score(
        self,
        test_attempt_id: UUID,
        test_data: Dict[str, Any]
    ) -> Decimal:
        """Calculate and store the final test score."""
        # Get all question evaluations
        result = await self.db.execute(
            select(TestQuestionEvaluation)
            .where(TestQuestionEvaluation.test_attempt_id == test_attempt_id)
        )
        evaluations = result.scalars().all()
        
        # Calculate total score
        total_score = sum(eval.points_earned for eval in evaluations)
        
        # Update test attempt
        await self.db.execute(
            update(StudentTestAttempt)
            .where(StudentTestAttempt.id == test_attempt_id)
            .values(
                score=total_score,
                evaluated_at=datetime.now(timezone.utc),
                feedback=self._generate_test_feedback(total_score, len(evaluations))
            )
        )
        await self.db.commit()
        
        return total_score
    
    def _generate_test_feedback(self, score: Decimal, total_questions: int) -> str:
        """Generate overall test feedback."""
        percentage = float(score)
        
        if percentage >= 90:
            return "Excellent work! You demonstrated strong understanding of the material."
        elif percentage >= 80:
            return "Great job! You showed good comprehension with minor areas for improvement."
        elif percentage >= 70:
            return "Good effort! Review the questions you missed to strengthen your understanding."
        elif percentage >= 60:
            return "Fair performance. Consider reviewing the lecture material for better understanding."
        else:
            return "This material seems challenging. Please review the lectures and consider asking your teacher for help."
    
    async def _update_attempt_status(self, test_attempt_id: UUID, status: str):
        """Update the test attempt status."""
        await self.db.execute(
            update(StudentTestAttempt)
            .where(StudentTestAttempt.id == test_attempt_id)
            .values(status=status)
        )
        await self.db.commit()
    
    async def _handle_evaluation_failure(self, test_attempt_id: UUID, error_message: str):
        """Handle evaluation failure by marking for manual review."""
        await self.db.execute(
            update(StudentTestAttempt)
            .where(StudentTestAttempt.id == test_attempt_id)
            .values(
                status='submitted',  # Keep as submitted for retry
                feedback=f"Evaluation pending. Error: {error_message[:200]}"
            )
        )
        await self.db.commit()
"""
Enhanced Test Evaluation Service with 4-point Rubric

This service implements the comprehensive test evaluation system using
the UmaRead 4-point scoring rubric and PydanticAI for structured responses.
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

from app.models.tests import StudentTestAttempt, AssignmentTest
from app.models.reading import ReadingAssignment
from app.models.user import User
from app.config.ai_models import ANSWER_EVALUATION_MODEL
from app.config.rubric_config import (
    UMAREAD_SCORING_RUBRIC,
    get_rubric_score_points,
    calculate_total_score,
    get_grade_adjustment_factor,
    EVALUATION_PROMPT_INTRO,
    FEEDBACK_GUIDELINES
)
from app.core.database import get_db

logger = logging.getLogger(__name__)


# Pydantic models for structured AI responses
class QuestionEvaluation(BaseModel):
    """Individual question evaluation result"""
    rubric_score: int = Field(ge=0, le=4, description="Score on 4-point rubric (0-4)")
    scoring_rationale: str = Field(description="Explanation for the score")
    feedback: Optional[str] = Field(None, description="Feedback for scores below 4")
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


class TestEvaluationServiceV2:
    """Enhanced service for evaluating student test responses using AI and rubric."""
    
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
        Main entry point for evaluating a completed test.
        
        Args:
            test_attempt_id: The UUID of the test attempt to evaluate
            trigger_source: Source of evaluation trigger (student_submission, manual, etc.)
            
        Returns:
            Dict containing evaluation results and status
        """
        print(f"=== TEST EVALUATION V2: evaluate_test_submission called ===")
        print(f"=== Test Attempt ID: {test_attempt_id} ===")
        print(f"=== Trigger Source: {trigger_source} ===")
        
        try:
            # Start evaluation tracking (disabled for now - table may not exist)
            # audit_id = await self._start_evaluation_audit(test_attempt_id)
            audit_id = None
            
            # Load test data
            test_data = await self._load_test_data(test_attempt_id)
            if not test_data:
                raise ValueError(f"Test attempt {test_attempt_id} not found or not ready for evaluation")
            
            # Keep status as 'submitted' during evaluation (evaluating is not a valid status)
            # await self._update_attempt_status(test_attempt_id, "evaluating")
            
            # Perform AI evaluation
            evaluation_result = await self._perform_ai_evaluation(test_data)
            
            # Store evaluation results
            await self._store_evaluation_results(test_attempt_id, evaluation_result, test_data)
            
            # Calculate final score
            final_score = await self._calculate_and_store_final_score(test_attempt_id)
            
            # Check if review needed
            needs_review = await self._check_evaluation_quality(test_attempt_id, evaluation_result)
            
            # Complete evaluation audit (disabled for now)
            # await self._complete_evaluation_audit(audit_id, evaluation_result, needs_review)
            
            # Update attempt status (only use valid status values from constraint)
            await self._update_attempt_status(
                test_attempt_id, 
                "graded"  # Use 'graded' for completed evaluations
            )
            
            return {
                "success": True,
                "test_attempt_id": str(test_attempt_id),
                "score": float(final_score),
                "needs_review": needs_review,
                "evaluation_confidence": evaluation_result.evaluation_confidence
            }
            
        except Exception as e:
            logger.error(f"Error evaluating test {test_attempt_id}: {str(e)}")
            await self._handle_evaluation_failure(test_attempt_id, str(e))
            raise
    
    async def _load_test_data(self, test_attempt_id: UUID) -> Optional[Dict[str, Any]]:
        """Load all necessary data for test evaluation."""
        # Import necessary models
        from app.models.tests import AssignmentTest
        from app.models.user import User
        
        # Get test attempt with related data
        result = await self.db.execute(
            select(StudentTestAttempt)
            .where(StudentTestAttempt.id == test_attempt_id)
        )
        test_attempt = result.scalar_one_or_none()
        
        if not test_attempt:
            return None
            
        # Validate test is ready for evaluation
        if test_attempt.status not in ["submitted", "completed"]:
            logger.warning(f"Test attempt {test_attempt_id} not ready for evaluation. Status: {test_attempt.status}")
            return None
            
        # Get related data separately
        assignment_test_result = await self.db.execute(
            select(AssignmentTest)
            .where(AssignmentTest.id == test_attempt.assignment_test_id)
        )
        assignment_test = assignment_test_result.scalar_one_or_none()
        
        assignment_result = await self.db.execute(
            select(ReadingAssignment)
            .where(ReadingAssignment.id == test_attempt.assignment_id)
        )
        assignment = assignment_result.scalar_one_or_none()
        
        student_result = await self.db.execute(
            select(User)
            .where(User.id == test_attempt.student_id)
        )
        student = student_result.scalar_one_or_none()
        
        return {
            "test_attempt": test_attempt,
            "student": student,
            "assignment": assignment,
            "test_questions": assignment_test.test_questions if assignment_test else [],
            "student_answers": test_attempt.answers_data or {},
            "grade_level": assignment.grade_level,
            "assignment_metadata": {
                "type": assignment.assignment_type,
                "difficulty_level": "standard",
                "subject": assignment.subject,
                "genre": assignment.genre
            }
        }
    
    async def _perform_ai_evaluation(self, test_data: Dict[str, Any]) -> TestEvaluationResult:
        """Perform AI evaluation of all test questions."""
        questions = test_data["test_questions"]
        student_answers = test_data["student_answers"]
        grade_level = test_data["grade_level"]
        
        # Build evaluation prompt
        prompt = self._build_evaluation_prompt(
            questions=questions,
            student_answers=student_answers,
            grade_level=grade_level,
            assignment_metadata=test_data["assignment_metadata"]
        )
        
        # Retry logic for AI calls
        for attempt in range(self.max_retries):
            try:
                # Configure Gemini
                import os
                print(f"=== TEST EVALUATION V2: Starting AI evaluation attempt {attempt + 1} ===")
                print(f"=== Using GEMINI_API_KEY: {'SET' if os.getenv('GEMINI_API_KEY') else 'NOT SET'} ===")
                
                genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
                # TEMPORARY: Using hardcoded model like UMARead for testing
                # model = genai.GenerativeModel(ANSWER_EVALUATION_MODEL)
                model = genai.GenerativeModel('gemini-2.0-flash')
                print(f"=== Configured Gemini with model: gemini-2.0-flash (hardcoded) ===")
                
                # Generate evaluation
                print(f"=== Sending prompt to Gemini (length: {len(prompt)} chars) ===")
                response = model.generate_content(prompt)
                print(f"=== Received response from Gemini ===")
                
                # Parse response into structured format
                print(f"=== Raw response text: {response.text[:200]}... ===")
                evaluation_data = json.loads(response.text)
                
                # Validate with Pydantic
                result = TestEvaluationResult(**evaluation_data)
                
                # Validate we have exactly 10 evaluations
                if len(result.question_evaluations) != 10:
                    raise ValueError(f"Expected 10 evaluations, got {len(result.question_evaluations)}")
                
                return result
                
            except Exception as e:
                logger.warning(f"AI evaluation attempt {attempt + 1} failed: {str(e)}")
                print(f"=== TEST EVALUATION V2 ERROR: Attempt {attempt + 1} failed ===")
                print(f"=== Error Type: {type(e).__name__} ===")
                print(f"=== Error Message: {str(e)} ===")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                else:
                    # Final attempt failed, use fallback
                    return self._get_fallback_evaluation(questions, student_answers)
    
    def _build_evaluation_prompt(
        self, 
        questions: List[Dict],
        student_answers: Dict[str, str],
        grade_level: str,
        assignment_metadata: Dict[str, Any]
    ) -> str:
        """Build comprehensive evaluation prompt."""
        
        # Start with the evaluation prompt intro (already includes rubric)
        prompt = EVALUATION_PROMPT_INTRO.format(grade_level=grade_level)
        
        prompt += f"\n\n## Assignment Context:\n"
        prompt += f"- Type: {assignment_metadata.get('type', 'Unknown')}\n"
        prompt += f"- Difficulty: {assignment_metadata.get('difficulty_level', 'Unknown')}\n"
        prompt += f"- Subject: {assignment_metadata.get('subject', 'Unknown')}\n"
        prompt += f"- Genre: {assignment_metadata.get('genre', 'Unknown')}\n"
        
        prompt += "\n## Questions and Student Responses:\n\n"
        prompt += "Evaluate each response carefully according to the rubric above.\n\n"
        
        for i, question in enumerate(questions):
            student_answer = student_answers.get(str(i), "")
            
            prompt += f"### Question {i+1}:\n"
            prompt += f"**Question Text:** {question['question']}\n"
            prompt += f"**Answer Key:** {question['answer_key']}\n"
            prompt += f"**Answer Explanation:** {question.get('answer_explanation', 'Not provided')}\n"
            prompt += f"**Evaluation Criteria:** {question.get('evaluation_criteria', 'Standard criteria apply')}\n"
            prompt += f"**Question Difficulty:** {question.get('difficulty', 5)}/8\n"
            prompt += f"**Student Answer:** {student_answer if student_answer else '[No answer provided]'}\n"
            prompt += "\n"
        
        prompt += FEEDBACK_GUIDELINES
        
        prompt += "\n\n## CRITICAL EVALUATION INSTRUCTIONS:\n"
        prompt += "1. Compare each student answer directly to the answer key and evaluation criteria\n"
        prompt += "2. Apply the 4-point rubric scoring STRICTLY:\n"
        prompt += "   - Score 4 (10 pts): Answer matches answer key, includes all required elements, proper evidence\n"
        prompt += "   - Score 3 (8 pts): Most elements correct, minor gaps or missing details\n"
        prompt += "   - Score 2 (5 pts): Some correct elements but missing key information\n"
        prompt += "   - Score 1 (2 pts): Very limited correct information, major gaps\n"
        prompt += "   - Score 0 (0 pts): No relevant answer or completely incorrect\n"
        prompt += "3. Be rigorous - do NOT default to score 3. Most answers should vary between 0-4 based on actual quality\n"
        prompt += "4. Provide specific, actionable feedback for any score below 4\n"
        prompt += "5. Base your evaluation on content accuracy, NOT on writing style or length alone\n\n"
        
        prompt += "Provide your evaluation as a JSON object with this structure:\n"
        prompt += """
{
    "question_evaluations": [
        {
            "rubric_score": <0-4>,
            "scoring_rationale": "<specific explanation comparing answer to answer key>",
            "feedback": "<constructive feedback for scores below 4, null for score 4>",
            "key_concepts_identified": ["concept1", "concept2"],
            "misconceptions_detected": ["misconception1"],
            "confidence": <0.0-1.0>
        }
        // ... for all 10 questions
    ],
    "overall_quality_notes": "<any notes about unusual patterns or concerns>",
    "evaluation_confidence": <0.0-1.0>,
    "unusual_patterns": ["pattern1", "pattern2"]
}
"""
        
        return prompt
    
    async def _store_evaluation_results(
        self, 
        test_attempt_id: UUID,
        evaluation: TestEvaluationResult,
        test_data: Dict[str, Any]
    ):
        """Store detailed evaluation results in database."""
        questions = test_data["test_questions"]
        student_answers = test_data["student_answers"]
        
        # Store individual question evaluations
        for i, (question, eval_result) in enumerate(zip(questions, evaluation.question_evaluations)):
            # Calculate points earned
            points_earned = get_rubric_score_points(eval_result.rubric_score)
            
            # Insert question evaluation using text() for raw SQL
            from sqlalchemy import text
            await self.db.execute(
                text("""
                INSERT INTO test_question_evaluations (
                    test_attempt_id, question_index, question_number, question_text,
                    student_answer, rubric_score, points_earned, max_points,
                    scoring_rationale, feedback_text, key_concepts_identified, 
                    misconceptions_detected, evaluation_confidence
                ) VALUES (
                    :test_attempt_id, :question_index, :question_number, :question_text,
                    :student_answer, :rubric_score, :points_earned, :max_points,
                    :scoring_rationale, :feedback_text, :key_concepts, 
                    :misconceptions, :confidence
                )
                """),
                {
                    "test_attempt_id": test_attempt_id,
                    "question_index": i,
                    "question_number": i + 1,
                    "question_text": question["question"],
                    "student_answer": student_answers.get(str(i), ""),
                    "rubric_score": eval_result.rubric_score,
                    "points_earned": float(points_earned),
                    "max_points": 10.0,
                    "scoring_rationale": eval_result.scoring_rationale,
                    "feedback_text": eval_result.feedback,
                    "key_concepts": json.dumps(eval_result.key_concepts_identified),
                    "misconceptions": json.dumps(eval_result.misconceptions_detected),
                    "confidence": eval_result.confidence
                }
            )
        
        # Update test attempt with evaluation metadata
        # Store basic evaluation completion status 
        # Note: Many evaluation columns don't exist in current schema, so we'll use feedback field
        await self.db.execute(
            update(StudentTestAttempt)
            .where(StudentTestAttempt.id == test_attempt_id)
            .values(
                feedback={
                    "evaluation_status": "completed",
                    "evaluated_at": datetime.now(timezone.utc).isoformat(),
                    "evaluation_model": ANSWER_EVALUATION_MODEL,
                    "evaluation_version": "v2.0",
                    "overall_quality_notes": evaluation.overall_quality_notes,
                    "evaluation_confidence": evaluation.evaluation_confidence,
                    "unusual_patterns": evaluation.unusual_patterns
                }
            )
        )
        
        await self.db.commit()
    
    async def _calculate_and_store_final_score(self, test_attempt_id: UUID) -> Decimal:
        """Calculate final score and update test attempt."""
        # Get all rubric scores
        from sqlalchemy import text
        result = await self.db.execute(
            text("""
            SELECT rubric_score FROM test_question_evaluations
            WHERE test_attempt_id = :test_attempt_id
            ORDER BY question_number
            """),
            {"test_attempt_id": test_attempt_id}
        )
        rubric_scores = [row[0] for row in result]
        
        # Calculate total score
        total_score = calculate_total_score(rubric_scores)
        
        # Determine if passed (typically 70% = 70 points)
        passed = total_score >= 70
        
        # Build feedback summary
        feedback_result = await self.db.execute(
            text("""
            SELECT question_number, feedback_text 
            FROM test_question_evaluations
            WHERE test_attempt_id = :test_attempt_id
            AND feedback_text IS NOT NULL
            ORDER BY question_number
            """),
            {"test_attempt_id": test_attempt_id}
        )
        
        feedback_data = {
            "question_feedback": {
                str(row[0]): row[1] for row in feedback_result
            },
            "summary": f"You scored {total_score}/100. " + 
                      ("Great job!" if passed else "Keep practicing to improve your score.")
        }
        
        # Update test attempt
        await self.db.execute(
            update(StudentTestAttempt)
            .where(StudentTestAttempt.id == test_attempt_id)
            .values(
                score=Decimal(str(total_score)),
                passed=passed,
                feedback=feedback_data,
                status="graded"
            )
        )
        
        await self.db.commit()
        
        return Decimal(str(total_score))
    
    async def _check_evaluation_quality(
        self, 
        test_attempt_id: UUID,
        evaluation: TestEvaluationResult
    ) -> bool:
        """Check if evaluation needs manual review."""
        # Use database function
        from sqlalchemy import text
        result = await self.db.execute(
            text("SELECT check_evaluation_quality(:test_attempt_id)"),
            {"test_attempt_id": test_attempt_id}
        )
        needs_review = result.scalar()
        
        # Additional checks from evaluation result
        if evaluation.evaluation_confidence < 0.7:
            needs_review = True
        
        if len(evaluation.unusual_patterns) > 0:
            needs_review = True
            
        return needs_review
    
    async def _start_evaluation_audit(self, test_attempt_id: UUID) -> UUID:
        """Start evaluation audit tracking."""
        from sqlalchemy import text
        result = await self.db.execute(
            text("""
            INSERT INTO test_evaluation_audits (
                test_attempt_id, ai_model, started_at
            ) VALUES (
                :test_attempt_id, :ai_model, :started_at
            ) RETURNING id
            """),
            {
                "test_attempt_id": test_attempt_id,
                "ai_model": ANSWER_EVALUATION_MODEL,
                "started_at": datetime.now(timezone.utc)
            }
        )
        await self.db.commit()
        return result.scalar()
    
    async def _complete_evaluation_audit(
        self, 
        audit_id: UUID,
        evaluation: TestEvaluationResult,
        needs_review: bool
    ):
        """Complete evaluation audit with results."""
        # Calculate score distribution
        score_distribution = {}
        for eval in evaluation.question_evaluations:
            score = str(eval.rubric_score)
            score_distribution[score] = score_distribution.get(score, 0) + 1
        
        # Calculate average confidence
        avg_confidence = sum(e.confidence for e in evaluation.question_evaluations) / 10
        
        from sqlalchemy import text
        await self.db.execute(
            text("""
            UPDATE test_evaluation_audits SET
                completed_at = :completed_at,
                duration_ms = EXTRACT(EPOCH FROM (:completed_at - started_at)) * 1000,
                average_confidence = :avg_confidence,
                score_distribution = :score_dist,
                unusual_patterns = :patterns,
                requires_review = :needs_review
            WHERE id = :audit_id
            """),
            {
                "audit_id": audit_id,
                "completed_at": datetime.now(timezone.utc),
                "avg_confidence": avg_confidence,
                "score_dist": json.dumps(score_distribution),
                "patterns": json.dumps(evaluation.unusual_patterns),
                "needs_review": needs_review
            }
        )
        await self.db.commit()
    
    async def _update_attempt_status(self, test_attempt_id: UUID, status: str):
        """Update test attempt status."""
        await self.db.execute(
            update(StudentTestAttempt)
            .where(StudentTestAttempt.id == test_attempt_id)
            .values(
                status=status
                # Note: evaluation_status column doesn't exist in current schema
            )
        )
        await self.db.commit()
    
    async def _handle_evaluation_failure(self, test_attempt_id: UUID, error_message: str):
        """Handle evaluation failure."""
        # Rollback any failed transaction first
        await self.db.rollback()
        
        # Store failure info in feedback field since evaluation columns don't exist
        await self.db.execute(
            update(StudentTestAttempt)
            .where(StudentTestAttempt.id == test_attempt_id)
            .values(
                feedback={
                    "evaluation_status": "failed",
                    "error": error_message,
                    "failed_at": datetime.now(timezone.utc).isoformat()
                }
            )
        )
        await self.db.commit()
    
    def _get_fallback_evaluation(
        self, 
        questions: List[Dict],
        student_answers: Dict[str, str]
    ) -> TestEvaluationResult:
        """Provide fallback evaluation if AI fails."""
        logger.warning("Using fallback evaluation due to AI failure")
        
        evaluations = []
        for i, question in enumerate(questions):
            answer = student_answers.get(str(i), "").strip()
            
            if not answer:
                score = 0
                rationale = "No answer provided"
                feedback = "Please provide an answer to receive credit."
            elif len(answer) < 20:
                score = 1
                rationale = "Answer is too brief"
                feedback = "Your answer needs more detail. Try to fully explain your thinking."
            elif len(answer) < 50:
                score = 2
                rationale = "Answer shows some understanding"
                feedback = "Good start! Add more specific details from the text to support your answer."
            else:
                score = 3
                rationale = "Answer shows good effort"
                feedback = "Nice work! Review the answer key to see if you missed any key points."
            
            evaluations.append(QuestionEvaluation(
                rubric_score=score,
                scoring_rationale=rationale,
                feedback=feedback if score < 4 else None,
                key_concepts_identified=[],
                misconceptions_detected=[],
                confidence=0.5  # Low confidence for fallback
            ))
        
        return TestEvaluationResult(
            question_evaluations=evaluations,
            overall_quality_notes="Evaluation performed using fallback method due to AI unavailability",
            evaluation_confidence=0.5,
            unusual_patterns=["fallback_evaluation_used"]
        )
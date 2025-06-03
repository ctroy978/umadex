import json
from typing import Dict, Any, List
from uuid import UUID
from datetime import datetime
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.config.ai_models import ANSWER_EVALUATION_MODEL

logger = logging.getLogger(__name__)


class TestEvaluationService:
    """Service for evaluating student test responses using AI."""
    
    async def evaluate_test_response(
        self,
        test_questions: List[Dict[str, Any]],
        student_responses: Dict[str, str],
        grade_level: str
    ) -> Dict[str, Any]:
        """Evaluate all student responses and calculate overall score."""
        
        evaluated_responses = {}
        total_score = 0
        
        for i, question in enumerate(test_questions):
            question_key = f"question_{i + 1}"
            student_answer = student_responses.get(question_key, "")
            
            if not student_answer.strip():
                # No answer provided
                evaluated_responses[question_key] = {
                    "student_answer": "",
                    "ai_score": 0,
                    "ai_justification": "No answer provided.",
                    "what_was_good": "",
                    "what_was_missing": "Student did not provide an answer."
                }
                continue
            
            # Evaluate individual response
            evaluation = await self._evaluate_single_response(
                question=question,
                student_answer=student_answer,
                grade_level=grade_level
            )
            
            evaluated_responses[question_key] = evaluation
            total_score += evaluation["ai_score"]
        
        # Calculate overall score (average of all questions)
        overall_score = total_score / len(test_questions) if test_questions else 0
        
        return {
            "responses": evaluated_responses,
            "overall_score": round(overall_score, 2)
        }
    
    async def _evaluate_single_response(
        self,
        question: Dict[str, Any],
        student_answer: str,
        grade_level: str
    ) -> Dict[str, Any]:
        """Evaluate a single student response using AI."""
        
        prompt = f"""Grade this student answer using the provided context.

Question: {question['question']}
Student Answer: {student_answer}
Answer Key: {question['answer_key']}
Grading Context: {question['grading_context']}
Student Grade Level: {grade_level}

Provide:
1. Score (0-100)
2. Brief justification explaining the score
3. What the student did well
4. What was missing (if anything)

Be encouraging and focus on understanding over perfect writing. Accept spelling/grammar variations appropriate for the grade level.

Format your response as JSON with these fields:
- score: number (0-100)
- justification: string
- what_was_good: string
- what_was_missing: string"""

        try:
            # Use Gemini for answer evaluation
            import os
            import google.generativeai as genai
            
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel(ANSWER_EVALUATION_MODEL)
            response = model.generate_content(prompt)
            
            # Parse the JSON response
            evaluation = json.loads(response.text)
            
            # Validate and sanitize the response
            score = max(0, min(100, evaluation.get('score', 0)))
            
            return {
                "student_answer": student_answer,
                "ai_score": score,
                "ai_justification": evaluation.get('justification', 'Score assigned based on answer quality.'),
                "what_was_good": evaluation.get('what_was_good', ''),
                "what_was_missing": evaluation.get('what_was_missing', '')
            }
            
        except Exception as e:
            logger.error(f"Error evaluating response: {e}")
            # Fallback evaluation
            return self._get_fallback_evaluation(student_answer)
    
    def _get_fallback_evaluation(self, student_answer: str) -> Dict[str, Any]:
        """Provide fallback evaluation if AI fails."""
        
        # Simple heuristic-based scoring
        answer_length = len(student_answer.strip())
        
        if answer_length < 10:
            score = 20
            justification = "Answer is very brief."
            good = "Attempted to answer the question."
            missing = "More detail and explanation needed."
        elif answer_length < 50:
            score = 50
            justification = "Answer shows some understanding but lacks detail."
            good = "Provided a basic response."
            missing = "Could use more specific examples or elaboration."
        else:
            score = 70
            justification = "Answer shows effort and understanding."
            good = "Provided a detailed response."
            missing = "Review the answer key for any missing elements."
        
        return {
            "student_answer": student_answer,
            "ai_score": score,
            "ai_justification": justification,
            "what_was_good": good,
            "what_was_missing": missing
        }
    
    def calculate_time_spent(self, started_at: datetime, completed_at: datetime) -> int:
        """Calculate time spent in minutes."""
        if not completed_at or not started_at:
            return 0
        
        delta = completed_at - started_at
        return int(delta.total_seconds() / 60)
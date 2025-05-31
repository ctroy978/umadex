"""
UMARead AI Service using PydanticAI
Handles question generation and answer evaluation with structured outputs
"""
import hashlib
import json
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime

from pydantic import BaseModel
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.anthropic import AnthropicModel

from app.core.config import settings
from app.schemas.umaread import (
    QuestionRequest,
    GeneratedQuestion,
    AnswerEvaluation,
    QuestionType,
    DifficultyAdjustment,
    AssignmentMetadata
)
from app.services.umaread_prompts import PromptTemplateManager


class QuestionGenerationResult(BaseModel):
    """Structured output for question generation"""
    question_text: str
    content_focus: str
    expected_answer_elements: list[str]
    evaluation_criteria: str


class AnswerEvaluationResult(BaseModel):
    """Structured output for answer evaluation"""
    is_correct: bool
    confidence_score: float
    feedback_text: str
    content_specific_feedback: str
    key_missing_elements: list[str]
    suggested_difficulty_change: int  # -1, 0, or 1


class UMAReadAI:
    """AI service for UMARead using PydanticAI for structured responses"""
    
    def __init__(self):
        self.prompt_manager = PromptTemplateManager()
        
        # Initialize PydanticAI agents
        self.question_agent = Agent(
            model=AnthropicModel(
                api_key=settings.ANTHROPIC_API_KEY,
                model_name="claude-3-5-sonnet-20241022"
            ),
            result_type=QuestionGenerationResult,
            system_prompt="""You are an expert educational content creator specializing in reading comprehension questions.
            Generate clear, age-appropriate questions that test understanding rather than memorization.
            Always provide structured output with the question and evaluation criteria."""
        )
        
        self.evaluation_agent = Agent(
            model=AnthropicModel(
                api_key=settings.ANTHROPIC_API_KEY,
                model_name="claude-3-5-sonnet-20241022"
            ),
            result_type=AnswerEvaluationResult,
            system_prompt="""You are an expert educator evaluating student reading comprehension.
            Provide encouraging, constructive feedback that helps students learn.
            Be specific about what was done well and what could be improved."""
        )
    
    async def generate_question(self, request: QuestionRequest) -> GeneratedQuestion:
        """Generate a question using PydanticAI with content-specific prompts"""
        
        if request.question_type == QuestionType.SUMMARY:
            # Summary questions are standardized based on content type
            question_text = self.prompt_manager.get_summary_prompt(request.assignment_metadata)
            
            return GeneratedQuestion(
                question_text=question_text,
                question_type=QuestionType.SUMMARY,
                difficulty_level=None,  # Summary questions don't have difficulty
                content_focus="summary",
                expected_answer_elements=[
                    "Main events or concepts",
                    "Key details",
                    "Logical flow"
                ],
                evaluation_criteria="Completeness, accuracy, and conciseness of summary"
            )
        
        else:
            # Comprehension questions use AI generation
            prompt = self.prompt_manager.get_comprehension_prompt(
                request.assignment_metadata,
                request.difficulty_level,
                request.chunk_content
            )
            
            # Use PydanticAI to generate structured question
            result = await self.question_agent.run(prompt)
            
            return GeneratedQuestion(
                question_text=result.data.question_text,
                question_type=QuestionType.COMPREHENSION,
                difficulty_level=request.difficulty_level,
                content_focus=result.data.content_focus,
                expected_answer_elements=result.data.expected_answer_elements,
                evaluation_criteria=result.data.evaluation_criteria
            )
    
    async def evaluate_answer(self,
                            question: str,
                            student_answer: str,
                            chunk_content: str,
                            metadata: AssignmentMetadata,
                            question_type: str,
                            difficulty: Optional[int] = None) -> AnswerEvaluation:
        """Evaluate student answer using PydanticAI"""
        
        prompt = self.prompt_manager.get_evaluation_prompt(
            question=question,
            student_answer=student_answer,
            chunk_content=chunk_content,
            metadata=metadata,
            question_type=question_type,
            difficulty=difficulty
        )
        
        # Use PydanticAI to evaluate answer
        result = await self.evaluation_agent.run(prompt)
        
        # Convert difficulty change to enum
        difficulty_change = DifficultyAdjustment(
            max(-1, min(1, result.data.suggested_difficulty_change))
        )
        
        return AnswerEvaluation(
            is_correct=result.data.is_correct,
            confidence_score=result.data.confidence_score,
            feedback_text=result.data.feedback_text,
            suggested_difficulty_change=difficulty_change,
            content_specific_feedback=result.data.content_specific_feedback,
            key_missing_elements=result.data.key_missing_elements
        )
    
    def generate_content_hash(self, content: str) -> str:
        """Generate hash of content for cache key"""
        # Normalize content by removing extra whitespace
        normalized = ' '.join(content.split())
        return hashlib.md5(normalized.encode()).hexdigest()[:8]
    
    async def generate_comprehensive_test(self, 
                                        assignment_id: UUID,
                                        chunks: list[str],
                                        metadata: AssignmentMetadata,
                                        num_questions: int = 10) -> Dict[str, Any]:
        """Generate a comprehensive test covering all chunks"""
        
        # This would use AI to generate a mix of question types
        # For now, return a placeholder structure
        test_questions = []
        
        # Distribute questions across chunks
        questions_per_chunk = max(1, num_questions // len(chunks))
        
        for i, chunk in enumerate(chunks[:num_questions]):
            # Mix of question types
            if i % 3 == 0:
                question_type = "multiple_choice"
            elif i % 3 == 1:
                question_type = "short_answer"
            else:
                question_type = "essay"
            
            test_questions.append({
                "question_number": i + 1,
                "question_type": question_type,
                "question_text": f"Test question {i+1} about chunk {i+1}",
                "chunk_reference": i + 1,
                "points": 10,
                "rubric": {
                    "excellent": "Demonstrates complete understanding",
                    "good": "Shows good grasp of material",
                    "fair": "Basic understanding evident",
                    "poor": "Misses key concepts"
                }
            })
        
        return {
            "assignment_id": str(assignment_id),
            "total_questions": len(test_questions),
            "passing_score": int(len(test_questions) * 0.7 * 10),  # 70% to pass
            "time_limit_minutes": len(test_questions) * 5,  # 5 min per question
            "test_questions": test_questions,
            "ai_model": "claude-3-5-sonnet-20241022",
            "generation_timestamp": datetime.utcnow().isoformat()
        }
"""
UMATest AI Assistant Service using Google Generative AI and Pydantic AI
Helps teachers improve hand-built test questions
"""
import json
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
from pydantic_ai import Agent
import google.generativeai as genai

from app.config.ai_config import get_gemini_config
from app.config.ai_models import LECTURE_QUESTION_MODEL


class ImprovedQuestion(BaseModel):
    """Model for an improved test question"""
    question_text: str = Field(description="The improved question text with corrected grammar and clarity")
    correct_answer: str = Field(description="The improved correct answer with better clarity and completeness")
    explanation: str = Field(description="The improved explanation that clearly explains why the answer is correct")
    evaluation_rubric: str = Field(description="The improved evaluation rubric with clear grading criteria")
    difficulty_level: str = Field(description="The appropriate difficulty level (basic, intermediate, advanced, or expert)")
    points: int = Field(description="Suggested points for this question based on difficulty and complexity")
    improvements_made: List[str] = Field(description="List of improvements made to the original question")


class UMATestAIAssistant:
    """AI Assistant for improving hand-built test questions"""
    
    def __init__(self):
        # Configure Google Generative AI
        self.config = get_gemini_config()
        genai.configure(api_key=self.config.api_key)
        
        # Initialize Pydantic AI agent for structured question improvement
        self.improvement_agent = Agent(
            LECTURE_QUESTION_MODEL,  # Use the same model as UMALecture
            result_type=ImprovedQuestion,
            system_prompt="""You are an expert educational content assistant helping teachers create high-quality test questions.
Your role is to:
1. Fix grammar and spelling errors
2. Improve clarity and remove ambiguity
3. Ensure the question is appropriate for the difficulty level
4. Make sure the answer is complete and accurate
5. Create a clear explanation that helps students learn
6. Develop a comprehensive evaluation rubric for grading
7. Suggest appropriate point values based on difficulty

Always maintain the teacher's original intent while making improvements."""
        )
    
    async def improve_question(
        self,
        question_text: str,
        correct_answer: str,
        explanation: str,
        evaluation_rubric: str,
        difficulty_level: str,
        points: int
    ) -> Dict[str, Any]:
        """
        Improve a hand-built test question using AI
        
        Args:
            question_text: The original question text
            correct_answer: The original correct answer
            explanation: The original explanation
            evaluation_rubric: The original evaluation rubric
            difficulty_level: The difficulty level (basic, intermediate, advanced, expert)
            points: The original points value
            
        Returns:
            Dictionary containing improved question and list of improvements made
        """
        try:
            # If evaluation_rubric is empty or very short, provide guidance
            if not evaluation_rubric or len(evaluation_rubric.strip()) < 20:
                evaluation_rubric = f"Create a comprehensive rubric for a {points}-point question at {difficulty_level} level"
            
            # Create the prompt for improvement
            prompt = f"""Please improve the following test question:

ORIGINAL QUESTION:
Question: {question_text}
Correct Answer: {correct_answer}
Explanation: {explanation}
Evaluation Rubric: {evaluation_rubric}
Difficulty Level: {difficulty_level}
Points: {points}

IMPROVEMENT GUIDELINES:
1. Grammar and Spelling: Fix any grammatical errors or typos
2. Clarity: Make the question clear and unambiguous
3. Completeness: Ensure all necessary information is provided
4. Difficulty Appropriateness: Ensure the question matches the {difficulty_level} difficulty level
5. Answer Quality: Make sure the correct answer is complete and accurate
6. Explanation Quality: Provide a clear explanation that helps students understand the concept
7. Rubric Quality: Create a comprehensive rubric that clearly defines grading criteria

For {difficulty_level} level:
- Basic: Simple recall, fundamental concepts, straightforward language
- Intermediate: Application of concepts, some analysis required, moderate complexity
- Advanced: Critical thinking, synthesis of ideas, complex problem-solving
- Expert: Deep analysis, evaluation, creation of new ideas, mastery-level understanding

IMPORTANT: Preserve the teacher's original intent and subject matter while making improvements."""

            # Use Pydantic AI agent to generate structured improvements
            result = await self.improvement_agent.run(prompt)
            
            # Extract improvements made
            improvements = result.data.improvements_made
            
            # If no significant improvements, note that
            if not improvements:
                improvements = ["No significant improvements needed - the question is well-written"]
            
            # Return the improved question and metadata
            return {
                "status": "success",
                "original": {
                    "question_text": question_text,
                    "correct_answer": correct_answer,
                    "explanation": explanation,
                    "evaluation_rubric": evaluation_rubric,
                    "difficulty_level": difficulty_level,
                    "points": points
                },
                "improved": {
                    "question_text": result.data.question_text,
                    "correct_answer": result.data.correct_answer,
                    "explanation": result.data.explanation,
                    "evaluation_rubric": result.data.evaluation_rubric,
                    "difficulty_level": result.data.difficulty_level,
                    "points": result.data.points
                },
                "improvements_made": improvements,
                "ai_model": LECTURE_QUESTION_MODEL
            }
            
        except Exception as e:
            print(f"Error improving question with AI: {str(e)}")
            import traceback
            traceback.print_exc()
            
            # Return error response
            return {
                "status": "error",
                "error": str(e),
                "message": "Failed to improve question with AI assistant. Please try again.",
                "original": {
                    "question_text": question_text,
                    "correct_answer": correct_answer,
                    "explanation": explanation,
                    "evaluation_rubric": evaluation_rubric,
                    "difficulty_level": difficulty_level,
                    "points": points
                }
            }
    
    async def suggest_additional_questions(
        self,
        existing_questions: List[Dict[str, Any]],
        test_title: str,
        test_description: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Suggest additional questions based on existing questions and test context
        
        Args:
            existing_questions: List of existing questions in the test
            test_title: Title of the test
            test_description: Optional description of the test
            
        Returns:
            List of suggested questions
        """
        # This could be implemented in the future to suggest new questions
        # based on gaps in the existing questions
        pass
    
    async def validate_question_set(
        self,
        questions: List[Dict[str, Any]],
        test_title: str
    ) -> Dict[str, Any]:
        """
        Validate a set of questions for completeness and balance
        
        Args:
            questions: List of questions to validate
            test_title: Title of the test
            
        Returns:
            Validation report with suggestions
        """
        # This could be implemented to check for:
        # - Difficulty balance
        # - Topic coverage
        # - Question variety
        # - Total points distribution
        pass
from typing import Optional, Tuple
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime
import uuid

from ..config.ai_models import ANSWER_EVALUATION_MODEL
from ..models.reading import ReadingChunk, ReadingAssignment, QuestionCache
from ..services.question_generation import Question, QuestionPair


class EvaluationResult(BaseModel):
    """Structured evaluation response"""
    is_correct: bool = Field(description="Whether the answer demonstrates understanding")
    confidence: float = Field(description="Confidence level 0.0-1.0")
    feedback: str = Field(description="Encouraging feedback message")


# Difficulty-specific evaluation guidelines
DIFFICULTY_GUIDELINES = {
    1: "Very lenient: Accept if any core fact is present. Ignore spelling, grammar, and accept single words.",
    2: "Lenient: Accept if main idea is present. Ignore spelling and accept incomplete answers.",
    3: "Moderate: Accept if main idea is captured. Allow paraphrasing and minor errors.",
    4: "Moderate: Accept if key details and main idea are present. Allow some errors.",
    5: "Careful: Require main points with some detail. Accept reasonable interpretations.",
    6: "Careful: Require good understanding with key details. Limited tolerance for errors.",
    7: "Strict: Require nuanced understanding and analysis. Expect connections to be made.",
    8: "Very strict: Require sophisticated understanding. Expect critical thinking and analysis."
}

# Encouraging feedback templates by difficulty
FEEDBACK_TEMPLATES = {
    "incorrect_low": [
        "Good try! Look at the text again and see if you can find the answer.",
        "You're on the right track! Try reading that part once more.",
        "Almost there! The answer is in the text - keep looking!",
        "Nice effort! Read through that section again carefully."
    ],
    "incorrect_medium": [
        "Good thinking! Try to focus on what the text specifically says about this.",
        "You're getting close! Look more carefully at the details in that passage.",
        "Almost! Think about what the author is really saying here.",
        "Good effort! Consider re-reading and looking for the key information."
    ],
    "incorrect_high": [
        "Interesting interpretation! Consider what evidence the text provides for this.",
        "You're thinking deeply! Try to connect your ideas more directly to the passage.",
        "Good analysis! Look again at how the author develops this idea.",
        "Thoughtful response! Consider the specific details that support your answer."
    ],
    "correct": [
        "Excellent! You've understood this well!",
        "Great job! You've captured the key idea!",
        "Wonderful! Your answer shows good comprehension!",
        "Perfect! You've demonstrated clear understanding!"
    ]
}


def build_evaluation_prompt(
    question: str,
    student_answer: str,
    correct_answer: str,
    question_type: str,
    difficulty_level: int,
    chunk_content: str,
    grade_level: str
) -> str:
    """Build a comprehensive prompt for answer evaluation"""
    
    difficulty_guideline = DIFFICULTY_GUIDELINES.get(difficulty_level, DIFFICULTY_GUIDELINES[3])
    
    prompt = f"""You are an empathetic teacher evaluating a student's reading comprehension answer. Your goal is to assess understanding, not perfection.

QUESTION: {question}
STUDENT'S ANSWER: {student_answer}
EXPECTED ANSWER: {correct_answer}
QUESTION TYPE: {question_type}
DIFFICULTY LEVEL: {difficulty_level} - {difficulty_guideline}
GRADE LEVEL: {grade_level}

ORIGINAL TEXT:
{chunk_content}

EVALUATION GUIDELINES:
1. Focus on comprehension but REQUIRE actual understanding
2. Accept misspellings and grammar errors that don't affect meaning
3. For difficulty {difficulty_level}: {difficulty_guideline}
4. Be encouraging but HONEST - if they're wrong, they need to try again
5. Provide SPECIFIC feedback about what they got right or wrong

CRITICAL EVALUATION CRITERIA:
- The answer MUST show understanding of the text, not just guessing
- For comprehension questions, the answer MUST address the specific question asked
- For SUMMARY questions: Accept answers that capture the MAIN IDEA or CENTRAL THEME
  * Student does NOT need to list every detail or event
  * 1-2 key points that show understanding of the main idea is sufficient
  * Focus on whether they understood what the passage is ABOUT
  * A good summary shows they grasped the core message, not memorized details
- Vague or generic answers should NOT be accepted
- For summaries, even a single sentence is fine IF it captures the essence

CRITICAL FEEDBACK RULES:
- NEVER reveal what actually happens in the story
- NEVER name characters, objects, or events the student missed
- NEVER say things like "the golden bird", "the eldest son", "the fox's warning"
- Instead say things like "something important happens at night", "another character becomes involved", "there's a warning given"
- Your job is to guide, not to teach the content

EVALUATE THE ANSWER:
1. Does it ACTUALLY answer the question asked?
2. Does it show they READ and UNDERSTOOD the text?
3. For SUMMARIES: Does it capture the MAIN POINT? (Not every detail needed)
4. For COMPREHENSION: Does it answer the specific question accurately?

BE SPECIFIC in your feedback BUT DO NOT REVEAL THE ANSWER:
- If correct: Mention ONE specific thing they understood well
- If incorrect: Give HINTS about what they missed WITHOUT revealing details
- NEVER list the events or facts they should have included
- NEVER complete their answer for them
- Use phrases like "there's more to discover about...", "you missed what happens after...", "think about who else is involved..."
- Guide them to look for specific types of information (characters, actions, consequences) without naming them

GOOD FEEDBACK EXAMPLES:
- "You got the basic situation right. However, a lot more happens in this section! Look for what happens during the night and who else gets involved after that."
- "You understood the problem correctly, but there's more to discover about how it gets resolved. Pay attention to what different characters do."
- "Good start! You missed some important events that happen between the beginning and end. Look for what each person discovers."

BAD FEEDBACK EXAMPLES (DON'T DO THIS):
- "You missed that the golden bird steals apples and the eldest son goes to an inn"
- "You forgot to mention the fox's warning"
- "The youngest son gets a golden feather - include that next time"

REMEMBER FOR SUMMARIES:
- The student does NOT need to mention every character, event, or detail
- They should capture the MAIN IDEA or CENTRAL CONFLICT
- Accept answers that show they understood WHAT THE PASSAGE IS ABOUT
- Don't penalize for missing minor details if the core message is understood

Provide your evaluation in this format:
Correct: [Yes/No - for summaries, be lenient if main idea is captured]
Confidence: [0.0-1.0]
Feedback: [Specific but non-revealing feedback that guides without giving answers]"""
    
    return prompt


async def evaluate_answer(
    question: Question,
    student_answer: str,
    difficulty_level: int,
    chunk: ReadingChunk,
    assignment: ReadingAssignment,
    db: AsyncSession
) -> EvaluationResult:
    """Evaluate a student's answer using AI"""
    
    # Basic validation
    if not student_answer or len(student_answer.strip()) < 2:
        return EvaluationResult(
            is_correct=False,
            confidence=1.0,
            feedback="Please provide an answer before submitting. Even a short answer is better than none!"
        )
    
    # Check for copy-paste of the entire chunk
    if len(student_answer) > 1000 and chunk.content in student_answer:
        return EvaluationResult(
            is_correct=False,
            confidence=1.0,
            feedback="It looks like you copied the text. Try answering in your own words to show your understanding!"
        )
    
    try:
        # Build evaluation prompt
        prompt = build_evaluation_prompt(
            question=question.question,
            student_answer=student_answer,
            correct_answer=question.answer,
            question_type=question.question_type,
            difficulty_level=difficulty_level,
            chunk_content=chunk.content,
            grade_level=assignment.grade_level
        )
        
        # Use Gemini 2.0 Flash for evaluation
        import os
        import google.generativeai as genai
        
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-2.0-flash')
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Parse the response
        evaluation = parse_evaluation_response(response_text, difficulty_level)
        
        return evaluation
        
    except Exception as e:
        print(f"Error evaluating answer: {e}")
        # Fallback evaluation - be conservative and ask them to try again
        return EvaluationResult(
            is_correct=False,
            confidence=0.5,
            feedback="I'm having trouble evaluating your answer. Please try rephrasing it with more detail about what you read in this section."
        )


def parse_evaluation_response(response_text: str, difficulty_level: int) -> EvaluationResult:
    """Parse the AI evaluation response"""
    lines = response_text.strip().split('\n')
    
    is_correct = False
    confidence = 0.5
    feedback = ""
    
    for line in lines:
        line = line.strip()
        if line.startswith("Correct:"):
            is_correct = "yes" in line.lower()
        elif line.startswith("Confidence:"):
            try:
                confidence = float(line.split(":")[1].strip())
            except:
                confidence = 0.7
        elif line.startswith("Feedback:"):
            feedback = line.replace("Feedback:", "").strip()
    
    # If no feedback was parsed, use a default
    if not feedback:
        if is_correct:
            feedback = "Great job! You've shown good understanding!"
        else:
            if difficulty_level <= 3:
                feedback = "Good try! Look at the text again and see if you can find the answer."
            elif difficulty_level <= 6:
                feedback = "You're getting close! Try to focus on what the text specifically says."
            else:
                feedback = "Interesting response! Consider what evidence the text provides."
    
    return EvaluationResult(
        is_correct=is_correct,
        confidence=confidence,
        feedback=feedback
    )


async def should_increase_difficulty(
    current_difficulty: int,
    question_type: str,
    evaluation_result: EvaluationResult
) -> bool:
    """Determine if difficulty should increase based on performance"""
    
    # Only increase difficulty after successful comprehension questions
    if question_type != "comprehension":
        return False
    
    # Don't increase if already at max
    if current_difficulty >= 8:
        return False
    
    # Only increase if answer was clearly correct with high confidence
    return evaluation_result.is_correct and evaluation_result.confidence >= 0.8


async def should_decrease_difficulty(
    current_difficulty: int,
    consecutive_errors: int
) -> bool:
    """Determine if difficulty should decrease based on struggles"""
    
    # Don't decrease below minimum
    if current_difficulty <= 1:
        return False
    
    # Decrease after 3 consecutive errors at the same difficulty
    return consecutive_errors >= 3
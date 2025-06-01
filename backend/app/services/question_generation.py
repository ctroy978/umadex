import hashlib
import json
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, delete
from datetime import datetime
import uuid
import re

from ..config.ai_models import QUESTION_GENERATION_MODEL
from ..models.reading import ReadingChunk, ReadingAssignment, QuestionCache, AssignmentImage


class Question(BaseModel):
    """Single question model"""
    question: str = Field(description="The question text")
    answer: str = Field(description="The correct answer")
    question_type: str = Field(description="Type of question: 'summary' or 'comprehension'")


class QuestionPair(BaseModel):
    """Pair of questions for a chunk"""
    summary_question: Question
    comprehension_question: Question


# Summary templates by content type
SUMMARY_TEMPLATES = {
    ("fiction", "prose"): "Summarize what happens in this section of the story.",
    ("fiction", "drama"): "Summarize what happens in this part of the play.",
    ("fiction", "poetry"): "Describe what the speaker is expressing in these lines.",
    ("non-fiction", "prose"): "Summarize the information presented in this section.",
    ("non-fiction", "poetry"): "Explain the main ideas expressed in these lines.",
    ("non-fiction", "drama"): "Summarize the key points made in this dialogue.",
    ("default", "default"): "Summarize the main points of this section."
}

# Difficulty level definitions
DIFFICULTY_DEFINITIONS = {
    1: "Very basic literal - Simple yes/no or one-word answers about explicitly stated facts",
    2: "Basic literal - Simple recall of directly stated information using short phrases",
    3: "Intermediate literal - Understanding of clearly stated main ideas",
    4: "Advanced literal - Connecting multiple explicitly stated details",
    5: "Basic inferential - Simple conclusions from obvious context clues",
    6: "Intermediate inferential - Understanding implied meanings and relationships",
    7: "Advanced inferential - Complex analysis of themes and author's purpose",
    8: "Expert inferential - Sophisticated interpretation and critical thinking"
}

# Fallback questions for error cases
FALLBACK_QUESTIONS = {
    "summary": "Please summarize what you read in this section.",
    "comprehension": "What was the most important information in this passage?"
}


def build_question_prompt(
    chunk_text: str,
    image_descriptions: List[str],
    work_type: str,
    literary_form: str,
    grade_level: str,
    difficulty_level: int
) -> str:
    """Build a comprehensive prompt for question generation"""
    
    # Get appropriate summary template
    template_key = (work_type.lower(), literary_form.lower())
    if template_key not in SUMMARY_TEMPLATES:
        template_key = ("default", "default")
    summary_template = SUMMARY_TEMPLATES[template_key]
    
    # Build image description section
    image_section = ""
    if image_descriptions:
        image_section = "\n\nIMAGES IN THIS SECTION:\n"
        for i, desc in enumerate(image_descriptions, 1):
            image_section += f"Image {i}: {desc}\n"
    
    prompt = f"""You are an expert reading comprehension question generator. Your task is to create exactly TWO questions based ONLY on the content provided below.

CONTENT TO USE:
Text: {chunk_text}
{image_section}

METADATA:
- Work Type: {work_type}
- Literary Form: {literary_form}
- Grade Level: {grade_level}
- Difficulty Level: {difficulty_level} - {DIFFICULTY_DEFINITIONS.get(difficulty_level, DIFFICULTY_DEFINITIONS[1])}

CRITICAL RULES:
1. Questions MUST ONLY reference information explicitly present in the provided text and images
2. Do NOT ask about content that might come before or after this section
3. Use vocabulary appropriate for {grade_level} grade students
4. Ensure answers can be verified objectively from the content
5. If images are present, at least one question should reference them when relevant

QUESTION REQUIREMENTS:

1. SUMMARY QUESTION:
   - Use this exact format: "{summary_template}"
   - The answer should be 2-4 sentences that capture the main points
   - For difficulty {difficulty_level}, ensure the summary complexity matches the level

2. COMPREHENSION QUESTION:
   - Ask about a specific detail, concept, or relationship in the text
   - Match difficulty level {difficulty_level}:
     * Levels 1-2: Ask about explicitly stated facts
     * Levels 3-4: Ask about main ideas or connections
     * Levels 5-6: Ask about implied meanings or "why" questions
     * Levels 7-8: Ask about themes, author's purpose, or critical analysis
   - Ensure the answer is clear and can be found/inferred from the content

FORMAT YOUR RESPONSE AS:
Summary Question: [question text]
Summary Answer: [2-4 sentence answer]

Comprehension Question: [question text]
Comprehension Answer: [clear, specific answer]"""
    
    return prompt


def calculate_content_hash(chunk_text: str, image_descriptions: List[str]) -> str:
    """Calculate a hash of the content for caching"""
    content = chunk_text + " ".join(image_descriptions)
    return hashlib.sha256(content.encode()).hexdigest()


async def generate_questions_for_chunk(
    chunk: ReadingChunk,
    assignment: ReadingAssignment,
    student_difficulty: int,
    db: AsyncSession
) -> QuestionPair:
    """Generate questions for a reading chunk using AI"""
    
    # Extract image descriptions from chunk content
    image_pattern = re.compile(r'<image>(.*?)</image>')
    image_tags = image_pattern.findall(chunk.content)
    
    image_descriptions = []
    if image_tags:
        # Fetch images for these tags
        images_result = await db.execute(
            select(AssignmentImage).where(
                and_(
                    AssignmentImage.assignment_id == assignment.id,
                    AssignmentImage.image_tag.in_(image_tags)
                )
            )
        )
        images = images_result.scalars().all()
        
        for image in images:
            if image.ai_description:
                image_descriptions.append(image.ai_description)
    
    # Calculate content hash for caching
    content_hash = calculate_content_hash(chunk.content, image_descriptions)
    
    # Check cache first
    cached_result = await db.execute(
        select(QuestionCache).where(
            QuestionCache.assignment_id == assignment.id,
            QuestionCache.chunk_id == chunk.chunk_order,
            QuestionCache.difficulty_level == student_difficulty,
            QuestionCache.content_hash == content_hash
        )
    )
    cached = cached_result.scalar_one_or_none()
    
    if cached:
        # Return cached questions
        data = cached.question_data
        return QuestionPair(
            summary_question=Question(**data['summary_question']),
            comprehension_question=Question(**data['comprehension_question'])
        )
    
    try:
        # Build prompt
        prompt = build_question_prompt(
            chunk_text=chunk.content,
            image_descriptions=image_descriptions,
            work_type=assignment.work_type,
            literary_form=assignment.literary_form,
            grade_level=assignment.grade_level,
            difficulty_level=student_difficulty
        )
        
        # For now, use Google Generative AI directly since PydanticAI Gemini integration seems broken
        import google.generativeai as genai
        import os
        
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        # Generate questions
        response = model.generate_content(prompt)
        response_text = response.text
        
        # Parse the response
        questions = parse_question_response(response_text)
        
        # Cache the results
        cache_entry = QuestionCache(
            id=str(uuid.uuid4()),
            assignment_id=assignment.id,
            chunk_id=chunk.chunk_order,
            difficulty_level=student_difficulty,
            content_hash=content_hash,
            question_data={
                'summary_question': questions.summary_question.model_dump(),
                'comprehension_question': questions.comprehension_question.model_dump()
            }
        )
        db.add(cache_entry)
        await db.commit()
        
        return questions
        
    except Exception as e:
        print(f"Error generating questions: {e}")
        # Return fallback questions
        return QuestionPair(
            summary_question=Question(
                question=FALLBACK_QUESTIONS["summary"],
                answer="Please provide a summary based on what you read.",
                question_type="summary"
            ),
            comprehension_question=Question(
                question=FALLBACK_QUESTIONS["comprehension"],
                answer="Please identify the key information from the passage.",
                question_type="comprehension"
            )
        )


def parse_question_response(response_text: str) -> QuestionPair:
    """Parse the AI response into structured questions"""
    lines = response_text.strip().split('\n')
    
    summary_question = ""
    summary_answer = ""
    comprehension_question = ""
    comprehension_answer = ""
    
    current_section = None
    
    for line in lines:
        line = line.strip()
        if line.startswith("Summary Question:"):
            summary_question = line.replace("Summary Question:", "").strip()
            current_section = "summary_q"
        elif line.startswith("Summary Answer:"):
            summary_answer = line.replace("Summary Answer:", "").strip()
            current_section = "summary_a"
        elif line.startswith("Comprehension Question:"):
            comprehension_question = line.replace("Comprehension Question:", "").strip()
            current_section = "comp_q"
        elif line.startswith("Comprehension Answer:"):
            comprehension_answer = line.replace("Comprehension Answer:", "").strip()
            current_section = "comp_a"
        elif line and current_section:
            # Handle multi-line answers
            if current_section == "summary_a":
                summary_answer += " " + line
            elif current_section == "comp_a":
                comprehension_answer += " " + line
    
    return QuestionPair(
        summary_question=Question(
            question=summary_question or FALLBACK_QUESTIONS["summary"],
            answer=summary_answer or "Please provide a summary.",
            question_type="summary"
        ),
        comprehension_question=Question(
            question=comprehension_question or FALLBACK_QUESTIONS["comprehension"],
            answer=comprehension_answer or "Please identify key information.",
            question_type="comprehension"
        )
    )


async def clear_assignment_question_cache(assignment_id: str, db: AsyncSession):
    """Clear all cached questions for an assignment"""
    await db.execute(
        delete(QuestionCache).where(
            QuestionCache.assignment_id == assignment_id
        )
    )
    await db.commit()
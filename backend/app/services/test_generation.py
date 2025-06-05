import json
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from uuid import UUID
import logging

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.models.reading import ReadingAssignment, ReadingChunk, AssignmentImage
from app.core.database import get_db
from app.config.ai_models import QUESTION_GENERATION_MODEL
from app.services.image_analyzer import ImageAnalyzer

logger = logging.getLogger(__name__)


class TestGenerationService:
    """Service for generating tests from UMARead assignments."""
    
    def __init__(self):
        self.image_analyzer = ImageAnalyzer()
    
    async def generate_test_for_assignment(
        self,
        assignment_id: UUID,
        db: AsyncSession
    ) -> Dict[str, Any]:
        """Generate a test for a completed UMARead assignment."""
        
        # Fetch assignment with all related data
        result = await db.execute(
            select(ReadingAssignment)
            .options(
                selectinload(ReadingAssignment.chunks),
                selectinload(ReadingAssignment.images)
            )
            .where(ReadingAssignment.id == assignment_id)
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            raise ValueError(f"Assignment {assignment_id} not found")
        
        # Prepare content for AI
        chunk_texts = self._prepare_chunk_texts(assignment.chunks)
        important_sections = self._extract_important_sections(assignment.chunks)
        image_descriptions = await self._prepare_image_descriptions(assignment.images)
        
        # Generate test questions using AI
        test_questions = await self._generate_questions(
            assignment=assignment,
            chunk_texts=chunk_texts,
            important_sections=important_sections,
            image_descriptions=image_descriptions
        )
        
        # Create test record
        test_data = {
            "assignment_id": assignment_id,
            "status": "draft",
            "test_questions": test_questions,
            "time_limit_minutes": 60,
            "max_attempts": 1
        }
        
        return test_data
    
    def _prepare_chunk_texts(self, chunks: List[ReadingChunk]) -> str:
        """Prepare chunk texts with numbers for AI processing."""
        sorted_chunks = sorted(chunks, key=lambda c: c.chunk_order)
        chunk_texts = []
        
        for chunk in sorted_chunks:
            chunk_texts.append(f"Chunk {chunk.chunk_order}: {chunk.content}")
        
        return "\n\n".join(chunk_texts)
    
    def _extract_important_sections(self, chunks: List[ReadingChunk]) -> str:
        """Extract sections marked as important."""
        important_sections = []
        sorted_chunks = sorted(chunks, key=lambda c: c.chunk_order)
        
        for chunk in sorted_chunks:
            # Look for **Important:** markers in the content
            content = chunk.content
            if "**Important:**" in content or "**IMPORTANT:**" in content or chunk.has_important_sections:
                # Extract the important parts
                lines = content.split('\n')
                in_important = False
                important_text = []
                
                for line in lines:
                    if "**Important:**" in line or "**IMPORTANT:**" in line:
                        in_important = True
                        important_text.append(line)
                    elif in_important and line.strip() and not line.startswith("**"):
                        important_text.append(line)
                    elif in_important and (line.startswith("**") or not line.strip()):
                        in_important = False
                
                if important_text:
                    important_sections.append(f"Important Section from Chunk {chunk.chunk_order}:\n" + "\n".join(important_text))
                elif chunk.has_important_sections:
                    # If marked as having important sections but no markers found, include the whole chunk
                    important_sections.append(f"Important Section (Chunk {chunk.chunk_order}): {chunk.content}")
        
        if not important_sections:
            return "No sections specifically marked as important."
        
        return "\n\n".join(important_sections)
    
    async def _prepare_image_descriptions(self, images: List[AssignmentImage]) -> str:
        """Prepare image descriptions for AI."""
        if not images:
            return "No images included in this assignment."
        
        descriptions = []
        for image in images:
            if image.ai_description:
                image_label = image.image_tag if image.image_tag else f"Image {len(descriptions) + 1}"
                descriptions.append(
                    f"{image_label}: {image.ai_description}"
                )
        
        return "\n\n".join(descriptions) if descriptions else "Images present but no descriptions available."
    
    async def _generate_questions(
        self,
        assignment: ReadingAssignment,
        chunk_texts: str,
        important_sections: str,
        image_descriptions: str
    ) -> List[Dict[str, Any]]:
        """Generate test questions using AI."""
        
        prompt = f"""You are creating a comprehensive test for students who have just completed reading this assignment. Generate exactly 10 questions that test their understanding of the SPECIFIC content they read.

Assignment Details:
- Title: {assignment.assignment_title} by {assignment.author}
- Work: {assignment.work_title}
- Grade Level: {assignment.grade_level}
- Type: {assignment.work_type}

ACTUAL TEXT CONTENT THE STUDENTS READ:
{chunk_texts}

SPECIALLY MARKED IMPORTANT SECTIONS:
{important_sections}

IMAGE DESCRIPTIONS:
{image_descriptions}

IMPORTANT INSTRUCTIONS:
1. Base EVERY question on the SPECIFIC content provided above
2. Reference specific events, characters, concepts, or details from the text
3. For sections marked as "Important", create at least 2-3 questions focusing on those parts
4. Do NOT ask generic questions that could apply to any text
5. Include the actual text or quote in the grading_context when relevant

For each question provide:
- question: A specific question about the content (mention characters, events, or concepts by name)
- answer_key: The specific information from the text that constitutes a complete answer
- grading_context: The exact passage or information from the text needed to evaluate the answer
- difficulty: 1-8 based on grade level (1=easiest, 8=hardest)

Question types to include:
- 2-3 literal comprehension (what happened, who did what)
- 2-3 inference questions (why did X happen, what can we conclude)
- 2-3 analysis questions (compare/contrast, cause/effect, author's purpose)
- 1-2 questions about important sections or images

Return ONLY a JSON array with exactly 10 question objects. No other text."""

        try:
            # Use Gemini for question generation
            import os
            import google.generativeai as genai
            
            logger.info(f"Generating test questions for assignment: {assignment.assignment_title}")
            logger.debug(f"Chunk texts length: {len(chunk_texts)}")
            logger.debug(f"Important sections: {important_sections}")
            
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel(QUESTION_GENERATION_MODEL)
            
            generation_config = genai.GenerationConfig(
                temperature=0.7,
                top_p=0.95,
                top_k=40,
                max_output_tokens=4096,
            )
            
            response = model.generate_content(
                prompt,
                generation_config=generation_config
            )
            
            # Log the raw response for debugging
            logger.debug(f"AI Response: {response.text[:500]}...")
            
            # Clean the response text to extract JSON
            response_text = response.text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            response_text = response_text.strip()
            
            # Parse the JSON response
            questions = json.loads(response_text)
            
            # Validate the structure
            if not isinstance(questions, list):
                raise ValueError("Response is not a JSON array")
            
            if len(questions) != 10:
                logger.warning(f"Expected 10 questions, got {len(questions)}")
            
            for i, q in enumerate(questions):
                if not all(key in q for key in ['question', 'answer_key', 'grading_context', 'difficulty']):
                    raise ValueError(f"Question {i+1} missing required fields")
                if not isinstance(q['difficulty'], (int, float)) or q['difficulty'] < 1 or q['difficulty'] > 8:
                    q['difficulty'] = min(max(int(q['difficulty']), 1), 8)  # Clamp to valid range
            
            logger.info(f"Successfully generated {len(questions)} test questions")
            return questions[:10]  # Ensure we return exactly 10
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            logger.error(f"Response text: {response.text[:1000] if 'response' in locals() else 'No response'}")
            return self._get_fallback_questions()
        except Exception as e:
            logger.error(f"Error generating test questions: {e}")
            logger.error(f"Exception type: {type(e).__name__}")
            return self._get_fallback_questions()
    
    def _get_fallback_questions(self) -> List[Dict[str, Any]]:
        """Provide fallback questions if AI generation fails."""
        return [
            {
                "question": "What is the main idea or theme of this text?",
                "answer_key": "Student should identify the central theme or main message of the reading.",
                "grading_context": "Look for understanding of the overall message, not just plot details.",
                "difficulty": 5
            },
            {
                "question": "Describe the main character or subject of this reading.",
                "answer_key": "Student should describe key characteristics, motivations, or features.",
                "grading_context": "Check for specific details from the text that support their description.",
                "difficulty": 4
            },
            {
                "question": "What is the most important event or concept presented in this reading?",
                "answer_key": "Student should identify a key event or concept and explain its significance.",
                "grading_context": "Look for understanding of why this event/concept matters to the overall text.",
                "difficulty": 6
            },
            {
                "question": "How does the beginning of the text connect to the ending?",
                "answer_key": "Student should explain the relationship between opening and conclusion.",
                "grading_context": "Check for understanding of story/text structure and development.",
                "difficulty": 7
            },
            {
                "question": "What did you learn from this reading?",
                "answer_key": "Student should identify specific lessons or new information gained.",
                "grading_context": "Look for personal connection and understanding of content.",
                "difficulty": 3
            },
            {
                "question": "Describe the setting or context of this reading.",
                "answer_key": "Student should identify when/where the text takes place or its context.",
                "grading_context": "Check for specific details about time, place, or circumstances.",
                "difficulty": 3
            },
            {
                "question": "What questions do you still have after reading this text?",
                "answer_key": "Student should formulate thoughtful questions showing engagement.",
                "grading_context": "Look for questions that demonstrate they understood and thought about the content.",
                "difficulty": 5
            },
            {
                "question": "How does this text relate to something you already know?",
                "answer_key": "Student should make connections to prior knowledge or experiences.",
                "grading_context": "Check for meaningful connections that show understanding.",
                "difficulty": 6
            },
            {
                "question": "What was the author's purpose in writing this text?",
                "answer_key": "Student should identify whether to inform, persuade, entertain, etc.",
                "grading_context": "Look for evidence from the text supporting their answer.",
                "difficulty": 7
            },
            {
                "question": "Summarize this reading in your own words.",
                "answer_key": "Student should provide a concise summary covering main points.",
                "grading_context": "Check for completeness, accuracy, and use of own words.",
                "difficulty": 5
            }
        ]
    
    async def update_test_questions(
        self,
        test_id: UUID,
        questions: List[Dict[str, Any]],
        db: AsyncSession
    ) -> bool:
        """Update test questions after teacher review."""
        
        # Validate questions structure
        for q in questions:
            if not all(key in q for key in ['question', 'answer_key', 'grading_context', 'difficulty']):
                raise ValueError("Invalid question structure")
        
        # Import here to avoid circular imports
        from app.models.tests import AssignmentTest
        
        # Update in database
        result = await db.execute(
            update(AssignmentTest)
            .where(AssignmentTest.id == test_id)
            .values(
                test_questions=questions,
                updated_at=datetime.utcnow()
            )
        )
        
        await db.commit()
        return result.rowcount > 0
    
    async def approve_test(
        self,
        test_id: UUID,
        teacher_id: UUID,
        expires_days: int,
        db: AsyncSession
    ) -> bool:
        """Approve a test for student access."""
        
        expires_at = datetime.utcnow() + timedelta(days=expires_days)
        
        # Import here to avoid circular imports
        from app.models.tests import AssignmentTest
        
        result = await db.execute(
            update(AssignmentTest)
            .where(AssignmentTest.id == test_id)
            .values(
                status="approved",
                approved_by=teacher_id,
                approved_at=datetime.utcnow(),
                expires_at=expires_at,
                updated_at=datetime.utcnow()
            )
        )
        
        await db.commit()
        return result.rowcount > 0
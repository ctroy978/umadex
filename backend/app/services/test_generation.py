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
- answer_explanation: A comprehensive explanation (1500-2500 tokens) for AI evaluation that includes:
  * Complete Answer Overview: What constitutes a full, correct answer to this question
  * Key Points Required: Essential concepts, facts, or insights students must demonstrate
  * Acceptable Variations: Different ways students might correctly express the same understanding
  * Partial Understanding: What to accept as partial credit and what shows insufficient comprehension
  * Common Student Errors: Typical misconceptions or mistakes students make on this type of question
  * Grade-Level Expectations: Appropriate depth and sophistication for this grade level
  * Evidence Requirements: What level of text support or examples students should provide
  * Evaluation Boundaries: Clear guidelines for distinguishing between score levels
- evaluation_criteria: Specific rubric points for scoring this question

Question types to include:
- 2-3 literal comprehension (what happened, who did what)
- 2-3 inference questions (why did X happen, what can we conclude)
- 2-3 analysis questions (compare/contrast, cause/effect, author's purpose)
- 1-2 questions about important sections or images

For each answer_explanation, be comprehensive enough that an AI evaluator can assess student responses without needing access to the original text. Make the explanations detailed and specific to this particular content.

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
                max_output_tokens=8192,  # Increased for comprehensive answer explanations
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
                required_fields = ['question', 'answer_key', 'grading_context', 'difficulty']
                # Check for required fields (answer_explanation and evaluation_criteria are optional for backward compatibility)
                if not all(key in q for key in required_fields):
                    raise ValueError(f"Question {i+1} missing required fields")
                if not isinstance(q['difficulty'], (int, float)) or q['difficulty'] < 1 or q['difficulty'] > 8:
                    q['difficulty'] = min(max(int(q['difficulty']), 1), 8)  # Clamp to valid range
                
                # Validate answer_explanation if present
                if 'answer_explanation' in q:
                    if not isinstance(q['answer_explanation'], str) or len(q['answer_explanation']) < 1000:
                        logger.warning(f"Question {i+1} has insufficient answer_explanation (minimum 1000 characters)")
                
                # Ensure evaluation_criteria exists (use answer_key as fallback)
                if 'evaluation_criteria' not in q:
                    q['evaluation_criteria'] = f"Evaluate based on: {q['answer_key']}"
            
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
                "difficulty": 5,
                "answer_explanation": "A complete answer should demonstrate understanding of the central theme or main message. Students should identify what the text is fundamentally about - not just surface events but the deeper meaning or purpose. Full credit responses will clearly state the main idea and may include supporting details from the text. Partial credit can be given for identifying related themes or sub-themes. Common errors include confusing plot events with theme, or providing overly general statements that could apply to any text. Grade-level expectations vary: younger students may identify basic themes while older students should articulate more complex thematic elements and their significance.",
                "evaluation_criteria": "Full understanding of central theme with supporting evidence"
            },
            {
                "question": "Describe the main character or subject of this reading.",
                "answer_key": "Student should describe key characteristics, motivations, or features.",
                "grading_context": "Check for specific details from the text that support their description.",
                "difficulty": 4,
                "answer_explanation": "A strong response will include specific character traits, motivations, and behaviors supported by textual evidence. Students should go beyond basic physical descriptions to include personality, goals, conflicts, or development. Full credit requires multiple specific details from the text. Partial credit for identifying some characteristics with limited support. Common errors include generic descriptions without textual support or confusing characters. Age-appropriate expectations: younger students focus on observable traits, older students analyze complex motivations and character development.",
                "evaluation_criteria": "Specific character traits with textual evidence and analysis"
            },
            {
                "question": "What is the most important event or concept presented in this reading?",
                "answer_key": "Student should identify a key event or concept and explain its significance.",
                "grading_context": "Look for understanding of why this event/concept matters to the overall text.",
                "difficulty": 6,
                "answer_explanation": "Excellence requires identifying a truly significant event/concept and explaining its importance to the overall meaning. Students must demonstrate understanding of why this element matters, not just what happened. Full credit includes explanation of significance, consequences, or connections to the broader text. Partial credit for identifying important elements without adequate explanation of significance. Common errors include choosing minor details or failing to explain importance. Grade-level expectations: younger students identify obvious important events, older students analyze complex concepts and their implications.",
                "evaluation_criteria": "Identification of key element with clear explanation of its significance"
            },
            {
                "question": "How does the beginning of the text connect to the ending?",
                "answer_key": "Student should explain the relationship between opening and conclusion.",
                "grading_context": "Check for understanding of story/text structure and development.",
                "difficulty": 7,
                "answer_explanation": "This requires sophisticated understanding of text structure and development. Students should identify specific connections between opening and conclusion - themes that develop, conflicts that resolve, or ideas that come full circle. Full credit requires clear identification of connections with specific examples from both beginning and end. Partial credit for recognizing some connection without detailed analysis. Common errors include forcing connections that don't exist or providing superficial observations. This is advanced thinking requiring students to see the text as a cohesive whole rather than isolated parts.",
                "evaluation_criteria": "Clear analysis of structural connections between beginning and ending"
            },
            {
                "question": "What did you learn from this reading?",
                "answer_key": "Student should identify specific lessons or new information gained.",
                "grading_context": "Look for personal connection and understanding of content.",
                "difficulty": 3,
                "answer_explanation": "Students should identify specific new knowledge, insights, or lessons from the text. Full credit requires clear connection between the text content and what was learned, with specific examples. Responses should go beyond plot summary to include genuine learning or reflection. Partial credit for identifying learning without specific connections to text. Common errors include vague generalizations or restating plot without showing learning. Age-appropriate: younger students may identify factual learning, older students should demonstrate deeper insights or changed perspectives.",
                "evaluation_criteria": "Specific learning identified with clear connections to text content"
            },
            {
                "question": "Describe the setting or context of this reading.",
                "answer_key": "Student should identify when/where the text takes place or its context.",
                "grading_context": "Check for specific details about time, place, or circumstances.",
                "difficulty": 3,
                "answer_explanation": "Complete answers include multiple aspects of setting: time period, geographical location, social context, or circumstances. Students should use specific details from the text to support their description. Full credit requires accurate identification of setting elements with textual evidence. Partial credit for identifying some setting elements with limited detail. Common errors include confusing different time periods or locations, or providing unsupported assumptions. Grade-level expectations: younger students identify basic where/when, older students analyze how setting influences events or themes.",
                "evaluation_criteria": "Accurate setting description with specific textual details"
            },
            {
                "question": "What questions do you still have after reading this text?",
                "answer_key": "Student should formulate thoughtful questions showing engagement.",
                "grading_context": "Look for questions that demonstrate they understood and thought about the content.",
                "difficulty": 5,
                "answer_explanation": "Quality responses demonstrate engagement and deeper thinking through thoughtful questions that extend beyond the text. Good questions show the student understood the content well enough to wonder about implications, connections, or deeper meanings. Full credit for questions that demonstrate comprehension and genuine curiosity. Partial credit for basic questions that show some engagement. Common errors include questions answered in the text or superficial questions showing minimal engagement. Questions should reveal thinking rather than confusion about basic content.",
                "evaluation_criteria": "Thoughtful questions demonstrating engagement and comprehension"
            },
            {
                "question": "How does this text relate to something you already know?",
                "answer_key": "Student should make connections to prior knowledge or experiences.",
                "grading_context": "Check for meaningful connections that show understanding.",
                "difficulty": 6,
                "answer_explanation": "Strong responses make meaningful connections between text content and prior knowledge, experiences, or other texts. Connections should enhance understanding rather than be superficial similarities. Full credit requires clear explanation of how the connection helps understanding or adds meaning. Partial credit for identifying connections without explaining their significance. Common errors include forced or irrelevant connections. Age-appropriate expectations: younger students make basic personal connections, older students make complex thematic or conceptual connections across texts or experiences.",
                "evaluation_criteria": "Meaningful connections with explanation of relevance to understanding"
            },
            {
                "question": "What was the author's purpose in writing this text?",
                "answer_key": "Student should identify whether to inform, persuade, entertain, etc.",
                "grading_context": "Look for evidence from the text supporting their answer.",
                "difficulty": 7,
                "answer_explanation": "Students must analyze author's intent and support their conclusion with textual evidence. Complete answers identify the primary purpose (inform, persuade, entertain, express) and explain how text elements support this purpose. Full credit requires clear identification with strong supporting evidence. Partial credit for correct identification with limited evidence. Common errors include confusing author's purpose with theme or providing unsupported opinions. Advanced students should recognize multiple purposes or sophisticated techniques authors use to achieve their goals.",
                "evaluation_criteria": "Clear identification of author's purpose with supporting textual evidence"
            },
            {
                "question": "Summarize this reading in your own words.",
                "answer_key": "Student should provide a concise summary covering main points.",
                "grading_context": "Check for completeness, accuracy, and use of own words.",
                "difficulty": 5,
                "answer_explanation": "Effective summaries capture main ideas and key supporting points in the student's own words without excessive detail or personal opinions. Full credit requires accurate, complete coverage of main points in appropriate length. Partial credit for summaries that miss some main points or include too much detail. Common errors include copying text directly, including too many minor details, or missing central ideas. Grade-level expectations: younger students may include more details, older students should demonstrate sophisticated synthesis and prioritization of information.",
                "evaluation_criteria": "Complete, accurate summary in student's own words covering main points"
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
            required_fields = ['question', 'answer_key', 'grading_context', 'difficulty']
            if not all(key in q for key in required_fields):
                raise ValueError("Invalid question structure")
            
            # Ensure evaluation_criteria exists (use answer_key as fallback)
            if 'evaluation_criteria' not in q:
                q['evaluation_criteria'] = f"Evaluate based on: {q['answer_key']}"
        
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
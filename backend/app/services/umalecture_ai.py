"""
UMALecture AI Service using Google Generative AI
Handles lecture content generation, image analysis, and question creation
"""
import json
import asyncio
from typing import Dict, Any, List, Optional
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text as sql_text
import google.generativeai as genai
import os
from concurrent.futures import ThreadPoolExecutor

from app.core.database import get_db
from app.services.image_processing import ImageProcessor
from app.services.umalecture_prompts import UMALecturePromptManager
from app.config.ai_config import get_gemini_config
from app.config.ai_models import LECTURE_GENERATION_MODEL


class UMALectureAIService:
    """AI service for UMALecture content generation and processing"""
    
    def __init__(self):
        # Configure Google Generative AI using centralized config
        self.config = get_gemini_config()
        genai.configure(api_key=self.config.api_key)
        # Use the centralized model configuration
        model_name = LECTURE_GENERATION_MODEL or 'gemini-2.0-flash'
        self.model = genai.GenerativeModel(model_name)
        self.prompt_manager = UMALecturePromptManager()
        self.executor = ThreadPoolExecutor(max_workers=3)
    
    async def _generate_content_async(self, prompt: Any) -> str:
        """Wrapper to run synchronous generate_content in thread pool"""
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            self.executor,
            self.model.generate_content,
            prompt
        )
        return response.text
    
    async def process_lecture(self, lecture_id: UUID):
        """Main processing function for a lecture"""
        print(f"Starting AI processing for lecture {lecture_id}")
        # Create a new database session for this background task
        async for db in get_db():
            try:
                await self._process_lecture_internal(db, lecture_id)
            except Exception as e:
                print(f"Error processing lecture {lecture_id}: {str(e)}")
                # Update status with error
                await self._update_lecture_status(db, lecture_id, "draft", str(e))
                raise
            finally:
                await db.close()
    
    async def _process_lecture_internal(self, db: AsyncSession, lecture_id: UUID):
        """Internal processing logic"""
        print(f"Processing lecture internally: {lecture_id}")
        
        # Update step: parse
        await self._update_processing_step(db, lecture_id, "parse", "in_progress")
        
        # Get lecture data
        lecture_query = sql_text("""
            SELECT id, teacher_id, assignment_title as title, subject, grade_level,
                   raw_content, status
            FROM reading_assignments
            WHERE id = :lecture_id
            AND assignment_type = 'UMALecture'
        """)
        result = await db.execute(lecture_query, {"lecture_id": lecture_id})
        lecture = result.mappings().first()
        
        if not lecture:
            raise ValueError(f"Lecture not found: {lecture_id}")
        
        # Extract metadata from raw_content
        metadata = json.loads(lecture.get("raw_content", "{}"))
        topic_outline = metadata.get("topic_outline")
        learning_objectives = metadata.get("learning_objectives", [])
        
        if not topic_outline:
            raise ValueError(f"Lecture missing outline: {lecture_id}")
        
        await self._update_processing_step(db, lecture_id, "parse", "completed")
        
        # Update step: analyze
        await self._update_processing_step(db, lecture_id, "analyze", "in_progress")
        
        # Process images first
        image_descriptions = await self._process_images(db, lecture_id)
        
        await self._update_processing_step(db, lecture_id, "analyze", "completed")
        
        # Update step: generate
        await self._update_processing_step(db, lecture_id, "generate", "in_progress")
        
        # Generate lecture structure
        print(f"Generating structure for lecture with {len(image_descriptions)} images")
        try:
            structure = await self._generate_lecture_structure(
                topic_outline,
                learning_objectives,
                lecture["grade_level"],
                lecture["subject"],
                image_descriptions
            )
            print(f"Generated structure with {len(structure.get('topics', {}))} topics")
        except Exception as e:
            print(f"Error generating structure: {str(e)}")
            raise
        
        await self._update_processing_step(db, lecture_id, "generate", "completed")
        await self._update_processing_step(db, lecture_id, "questions", "in_progress")
        
        # Add a small delay to show questions step
        await asyncio.sleep(2)
        
        await self._update_processing_step(db, lecture_id, "questions", "completed")
        await self._update_processing_step(db, lecture_id, "finalize", "in_progress")
        
        # Update lecture with generated structure
        # Need to update the metadata JSON with the structure
        metadata["lecture_structure"] = structure
        metadata["processing_completed_at"] = datetime.utcnow().isoformat()
        
        update_query = sql_text("""
            UPDATE reading_assignments
            SET raw_content = :metadata,
                status = 'published',
                updated_at = NOW()
            WHERE id = :lecture_id
            AND assignment_type = 'UMALecture'
        """)
        
        await db.execute(
            update_query,
            {
                "lecture_id": lecture_id,
                "metadata": json.dumps(metadata)
            }
        )
        await db.commit()
        
        await self._update_processing_step(db, lecture_id, "finalize", "completed")
    
    async def _update_lecture_status(self, db: AsyncSession, lecture_id: UUID, status: str, error: Optional[str] = None):
        """Update lecture status with error if provided"""
        # Get current metadata
        get_query = sql_text("""
            SELECT raw_content FROM reading_assignments
            WHERE id = :lecture_id
            AND assignment_type = 'UMALecture'
        """)
        
        result = await db.execute(get_query, {"lecture_id": lecture_id})
        data = result.mappings().first()
        if not data:
            return
        
        metadata = json.loads(data["raw_content"] or "{}")
        
        # Update metadata based on status
        if error:
            metadata["processing_error"] = error
        metadata["processing_completed_at"] = datetime.utcnow().isoformat()
        
        # Track processing steps for progress
        if status == "processing":
            if "processing_steps" not in metadata:
                metadata["processing_steps"] = {
                    "parse": {"status": "pending", "started_at": None, "completed_at": None},
                    "analyze": {"status": "pending", "started_at": None, "completed_at": None},
                    "generate": {"status": "pending", "started_at": None, "completed_at": None},
                    "questions": {"status": "pending", "started_at": None, "completed_at": None},
                    "finalize": {"status": "pending", "started_at": None, "completed_at": None}
                }
        
        # Update in database
        update_query = sql_text("""
            UPDATE reading_assignments
            SET status = :status,
                raw_content = :metadata,
                updated_at = NOW()
            WHERE id = :lecture_id
            AND assignment_type = 'UMALecture'
        """)
        
        await db.execute(
            update_query,
            {
                "lecture_id": lecture_id,
                "status": status,
                "metadata": json.dumps(metadata)
            }
        )
        await db.commit()
    
    async def _update_processing_step(self, db: AsyncSession, lecture_id: UUID, step: str, status: str):
        """Update individual processing step status"""
        # Get current metadata
        get_query = sql_text("""
            SELECT raw_content FROM reading_assignments
            WHERE id = :lecture_id
            AND assignment_type = 'UMALecture'
        """)
        
        result = await db.execute(get_query, {"lecture_id": lecture_id})
        data = result.mappings().first()
        if not data:
            return
        
        metadata = json.loads(data["raw_content"] or "{}")
        
        # Initialize steps if not present
        if "processing_steps" not in metadata:
            metadata["processing_steps"] = {}
        
        # Update step status
        if step not in metadata["processing_steps"]:
            metadata["processing_steps"][step] = {}
        
        metadata["processing_steps"][step]["status"] = status
        if status == "in_progress":
            metadata["processing_steps"][step]["started_at"] = datetime.utcnow().isoformat()
        elif status == "completed":
            metadata["processing_steps"][step]["completed_at"] = datetime.utcnow().isoformat()
        
        # Update in database
        update_query = sql_text("""
            UPDATE reading_assignments
            SET raw_content = :metadata,
                updated_at = NOW()
            WHERE id = :lecture_id
            AND assignment_type = 'UMALecture'
        """)
        
        await db.execute(
            update_query,
            {
                "lecture_id": lecture_id,
                "metadata": json.dumps(metadata)
            }
        )
        await db.commit()
    
    async def _process_images(self, db: AsyncSession, lecture_id: UUID) -> Dict[str, Dict[str, Any]]:
        """Process all images for a lecture"""
        # Get all images
        image_query = sql_text("""
            SELECT * FROM lecture_images
            WHERE lecture_id = :lecture_id
            ORDER BY node_id, position
        """)
        
        result = await db.execute(image_query, {"lecture_id": lecture_id})
        images = result.mappings().all()
        
        print(f"Found {len(images)} images for lecture")
        image_descriptions = {}
        
        # For now, skip image processing to test the basic flow
        for image in images:
            image_descriptions[str(image["id"])] = {
                "educational_description": image["teacher_description"] or "Image description",
                "node_id": image["node_id"]
            }
        
        return image_descriptions
    
    async def _generate_lecture_structure(
        self,
        outline: str,
        objectives: List[str],
        grade_level: str,
        subject: str,
        image_descriptions: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Generate the complete lecture structure"""
        
        # Extract subtopics from outline
        subtopics = self._extract_subtopics_from_outline(outline)
        print(f"Extracted {len(subtopics)} subtopics from outline: {subtopics}")
        
        # First, parse the outline into topics
        parse_prompt = self.prompt_manager.get_outline_parsing_prompt(outline, objectives)
        
        # Temporarily use simple parsing to test
        parsed_topics = self._simple_outline_parse(outline)
        print(f"Using simple parse: {len(parsed_topics)} topics: {[t['title'] for t in parsed_topics]}")
        
        # TODO: Re-enable AI parsing once tested
        # try:
        #     print(f"Parsing outline...")
        #     response_text = await self._generate_content_async(parse_prompt)
        #     print(f"Got response from AI for outline parsing")
        #     parsed_topics = self._parse_topics_response(response_text)
        #     print(f"Parsed {len(parsed_topics)} topics: {[t['title'] for t in parsed_topics]}")
        # except Exception as e:
        #     print(f"Error parsing outline: {str(e)}")
        #     import traceback
        #     traceback.print_exc()
        #     # Fallback to simple parsing
        #     parsed_topics = self._simple_outline_parse(outline)
        #     print(f"Using simple parse: {len(parsed_topics)} topics")
        
        # Generate content for each topic at each difficulty level
        structure = {"topics": {}}
        
        for i, topic in enumerate(parsed_topics):
            topic_id = topic["id"]
            topic_title = topic["title"]
            print(f"Processing topic {i+1}/{len(parsed_topics)}: {topic_title}")
            
            # Get images for this topic
            topic_images = [
                desc for img_id, desc in image_descriptions.items()
                if desc["node_id"].lower() == topic_id.lower() or 
                   desc["node_id"].lower() in topic_title.lower()
            ]
            
            # Generate content for each difficulty level
            difficulty_levels = {}
            
            # Generate content for each difficulty level
            for difficulty in ["basic", "intermediate", "advanced", "expert"]:
                print(f"  Generating {difficulty} content...")
                
                try:
                    # Try AI generation first
                    content_prompt = self.prompt_manager.get_content_generation_prompt(
                        topic_title,
                        difficulty,
                        grade_level,
                        subject,
                        [desc["educational_description"] for desc in topic_images],
                        objectives,  # Add this line - learning_objectives is already available in scope
                        subtopics  # Pass the subtopics
                    )
                    
                    content_text = await self._generate_content_async(content_prompt)
                    
                    # Generate questions
                    question_prompt = self.prompt_manager.get_question_generation_prompt(
                        topic_title,
                        content_text,
                        difficulty,
                        with_images=len(topic_images) > 0
                    )
                    
                    questions_text = await self._generate_content_async(question_prompt)
                    questions = self._parse_questions_response(questions_text, difficulty)
                    
                    difficulty_levels[difficulty] = {
                        "content": content_text,
                        "images": [img_id for img_id, desc in image_descriptions.items() 
                                  if desc["node_id"].lower() == topic_id.lower()],
                        "questions": questions
                    }
                    
                except Exception as e:
                    print(f"  Error generating {difficulty} content: {str(e)}")
                    # Fallback to placeholder content
                    difficulty_levels[difficulty] = {
                        "content": f"This is {difficulty} level content for {topic_title}. In a real implementation, this would contain AI-generated educational content appropriate for the {grade_level} grade level in {subject}.",
                        "images": [img_id for img_id, desc in image_descriptions.items() 
                                  if desc["node_id"].lower() == topic_id.lower()],
                        "questions": [
                            {
                                "question": f"What did you learn about {topic_title}?",
                                "question_type": "short_answer",
                                "difficulty": difficulty,
                                "correct_answer": "Student should demonstrate understanding of the topic.",
                                "options": None,
                                "uses_images": False
                            }
                        ]
                    }
            
            structure["topics"][topic_id] = {
                "title": topic_title,
                "difficulty_levels": difficulty_levels
            }
        
        print(f"Structure generation complete with {len(structure['topics'])} topics")
        return structure
    
    def _parse_topics_response(self, response_text: str) -> List[Dict[str, str]]:
        """Parse AI response into topic list"""
        topics = []
        lines = response_text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('#'):
                # Try to extract topic ID and title
                if ':' in line:
                    parts = line.split(':', 1)
                    topic_id = parts[0].strip().lower().replace(' ', '_')
                    topic_title = parts[1].strip()
                else:
                    topic_title = line.strip('- •*')
                    topic_id = topic_title.lower().replace(' ', '_').replace('-', '_')
                
                if topic_id and topic_title:
                    topics.append({
                        "id": topic_id,
                        "title": topic_title
                    })
        
        return topics
    
    def _simple_outline_parse(self, outline: str) -> List[Dict[str, str]]:
        """Simple fallback outline parser"""
        topics = []
        lines = outline.strip().split('\n')
        
        # Look for lines that are main topics (not indented sub-items)
        for i, line in enumerate(lines):
            original_line = line
            line = line.strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # Skip sub-items (lines that start with - or * after stripping)
            if line.startswith(('-', '*', '•', 'A.', 'B.', 'C.')):
                continue
                
            # Check if this line is less indented than the next line (making it a topic header)
            is_topic = False
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                # If next line is more indented or starts with a bullet, this is likely a topic
                if (len(next_line) - len(next_line.lstrip()) > len(original_line) - len(original_line.lstrip()) or
                    next_line.strip().startswith(('-', '*', '•'))):
                    is_topic = True
            
            # Also consider lines without colons that aren't sub-items as topics
            if not is_topic and len(line) > 3 and ':' not in line:
                # Check if it's not a sub-item by looking at original indentation
                if original_line == line or (len(original_line) - len(line)) < 2:
                    is_topic = True
            
            # Check for Roman numerals or "#### " headers
            if (line.startswith(('I.', 'II.', 'III.', 'IV.', 'V.', 'VI.', 'VII.')) or
                line.startswith('####')):
                is_topic = True
            
            if is_topic:
                # Clean up the title
                topic_title = line
                topic_title = topic_title.replace('####', '').strip()
                topic_title = topic_title.split('.', 1)[-1].strip() if '.' in topic_title else topic_title
                topic_title = topic_title.rstrip(':')  # Remove trailing colon if present
                
                # Generate ID
                topic_id = topic_title.lower()
                topic_id = topic_id.replace("'", "").replace(" ", "_").replace("-", "_")
                topic_id = topic_id.replace("(", "").replace(")", "").replace(".", "")
                topic_id = topic_id.replace(":", "")
                
                if topic_title and len(topic_title) > 3:
                    topics.append({
                        "id": topic_id[:50],  # Limit ID length
                        "title": topic_title
                    })
        
        # If no topics found, try a different approach
        if not topics:
            for line in lines:
                line = line.strip()
                if line and len(line) > 10 and not any(line.startswith(p) for p in [' ', '\t', '-', '*', '•']):
                    topic_title = line.rstrip(':')
                    topic_id = topic_title.lower().replace(' ', '_').replace('-', '_')[:50]
                    topics.append({
                        "id": topic_id,
                        "title": topic_title
                    })
        
        return topics if topics else [{"id": "main_topic", "title": "Main Topic"}]
    
    def _extract_subtopics_from_outline(self, outline: str) -> List[str]:
        """Extract subtopics from the outline structure"""
        subtopics = []
        lines = outline.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            # Skip empty lines
            if not line:
                continue
            
            # Skip the main topic line
            if line.startswith('Topic:'):
                continue
                
            # Extract subtopics (lines that start with -)
            if line.startswith('-'):
                subtopic = line.lstrip('- ').strip()
                if subtopic:
                    subtopics.append(subtopic)
        
        return subtopics
    
    def _parse_questions_response(self, response_text: str, difficulty: str) -> List[Dict[str, Any]]:
        """Parse AI response into question list"""
        questions = []
        
        # Split by question markers
        parts = response_text.split('Question')
        
        for i, part in enumerate(parts[1:], 1):  # Skip first empty part
            lines = part.strip().split('\n')
            question_text = ""
            correct_answer = ""
            options = []
            
            for line in lines:
                line = line.strip()
                if line.startswith(str(i) + '.') or line.startswith(':'):
                    question_text = line.lstrip(str(i) + '.').lstrip(':').strip()
                elif line.startswith('Answer:') or line.startswith('Correct answer:'):
                    correct_answer = line.split(':', 1)[1].strip()
                elif line.startswith(('A)', 'B)', 'C)', 'D)')):
                    options.append(line)
            
            if question_text:
                questions.append({
                    "question": question_text,
                    "question_type": "multiple_choice" if options else "short_answer",
                    "difficulty": difficulty,
                    "correct_answer": correct_answer,
                    "options": options if options else None,
                    "uses_images": "image" in question_text.lower() or "picture" in question_text.lower()
                })
        
        # If parsing fails, return a default question
        if not questions:
            questions.append({
                "question": f"What did you learn about this topic at the {difficulty} level?",
                "question_type": "short_answer",
                "difficulty": difficulty,
                "correct_answer": "Student should demonstrate understanding of the topic.",
                "options": None,
                "uses_images": False
            })
        
        return questions[:3]  # Limit to 3 questions per difficulty
    
    async def evaluate_student_answer(
        self,
        context: str,
        student_answer: str,
        difficulty: str
    ) -> Dict[str, Any]:
        """Evaluate a student's answer using AI"""
        
        # Create evaluation prompt
        prompt = f"""You are a teacher evaluating a student's answer to a specific question. You must determine if the answer is factually correct and relevant to the question asked.

Context/Question:
{context}

Student's Answer:
{student_answer}

EVALUATION CRITERIA:
1. The answer MUST be relevant to the specific question asked
2. The answer MUST contain correct information about the topic
3. Random or nonsensical answers are ALWAYS incorrect
4. Answers that are completely unrelated to the question are ALWAYS incorrect

DIFFICULTY LEVEL STANDARDS ({difficulty}):
- Basic: Student must show basic understanding of the core concept
- Intermediate: Student must demonstrate knowledge of key concepts and relationships
- Advanced: Student must show deeper understanding with some detail
- Expert: Student must demonstrate comprehensive understanding

MARKING AS CORRECT:
✓ Answer directly addresses the question
✓ Contains accurate information about the topic
✓ Shows understanding appropriate to the difficulty level
✓ May use simple language but concepts are correct

MARKING AS INCORRECT:
✗ Answer is unrelated to the question (e.g., random words, off-topic responses)
✗ Contains significant factual errors
✗ Shows no understanding of the concept
✗ Is nonsensical or random text
✗ Avoids answering the actual question

IMPORTANT: If the student gives a nonsensical answer like "banana", "asdf", "I don't know", or anything clearly unrelated to the question, it is ALWAYS incorrect regardless of how "creative" it might be.

FEEDBACK GUIDELINES:
- If correct: Acknowledge their understanding and reinforce the key concept
- If incorrect: Be encouraging but clearly indicate what the correct answer should address
- Always be constructive and educational

Return your evaluation in this exact JSON format:
{{
    "is_correct": true/false,
    "feedback": "Your feedback here", 
    "points_earned": 0-10
}}

Be fair but maintain standards. An answer must actually demonstrate knowledge to be marked correct."""
        
        try:
            # Generate evaluation
            response = await self._generate_content_async(prompt)
            
            # Parse JSON response
            # Remove any markdown formatting if present
            json_str = response.strip()
            if json_str.startswith("```json"):
                json_str = json_str[7:]
            if json_str.endswith("```"):
                json_str = json_str[:-3]
            
            result = json.loads(json_str.strip())
            
            # Ensure all required fields are present
            is_correct = result.get("is_correct", False)
            return {
                "is_correct": is_correct,
                "feedback": "You have answered this question correctly!" if is_correct else result.get("feedback", "Unable to evaluate response. Please try again."),
                "points_earned": result.get("points_earned", 0)
            }
            
        except Exception as e:
            print(f"Error evaluating student answer: {str(e)}")
            return {
                "is_correct": False,
                "feedback": "Sorry, I couldn't evaluate your answer right now. Please try again.",
                "points_earned": 0
            }
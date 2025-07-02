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


class UMALectureAIService:
    """AI service for UMALecture content generation and processing"""
    
    def __init__(self):
        # Configure Google Generative AI
        genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
        self.model = genai.GenerativeModel('gemini-1.5-flash')
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
        # Get lecture data
        lecture_query = sql_text("""
            SELECT * FROM lecture_assignments
            WHERE id = :lecture_id
        """)
        result = await db.execute(lecture_query, {"lecture_id": lecture_id})
        lecture = result.mappings().first()
        
        if not lecture:
            raise ValueError(f"Lecture not found: {lecture_id}")
        if not lecture["topic_outline"]:
            raise ValueError(f"Lecture missing outline: {lecture_id}")
        
        # Process images first
        image_descriptions = await self._process_images(db, lecture_id)
        
        # Generate lecture structure
        print(f"Generating structure for lecture with {len(image_descriptions)} images")
        try:
            structure = await self._generate_lecture_structure(
                lecture["topic_outline"],
                lecture["learning_objectives"],
                lecture["grade_level"],
                lecture["subject"],
                image_descriptions
            )
            print(f"Generated structure with {len(structure.get('topics', {}))} topics")
        except Exception as e:
            print(f"Error generating structure: {str(e)}")
            raise
        
        # Update lecture with generated structure
        update_query = sql_text("""
            UPDATE lecture_assignments
            SET lecture_structure = :structure,
                status = 'published',
                processing_completed_at = NOW()
            WHERE id = :lecture_id
        """)
        
        await db.execute(
            update_query,
            {
                "lecture_id": lecture_id,
                "structure": json.dumps(structure)
            }
        )
        await db.commit()
    
    async def _update_lecture_status(self, db: AsyncSession, lecture_id: UUID, status: str, error: Optional[str] = None):
        """Update lecture status with error if provided"""
        if error:
            query = sql_text("""
                UPDATE lecture_assignments
                SET status = :status,
                    processing_error = :error,
                    processing_completed_at = NOW()
                WHERE id = :lecture_id
            """)
            params = {"lecture_id": lecture_id, "status": status, "error": error}
        else:
            query = sql_text("""
                UPDATE lecture_assignments
                SET status = :status,
                    processing_completed_at = NOW()
                WHERE id = :lecture_id
            """)
            params = {"lecture_id": lecture_id, "status": status}
        
        await db.execute(query, params)
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
                        [desc["educational_description"] for desc in topic_images]
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
        
        # Look for lines that start with Roman numerals or are section headers
        for line in lines:
            line = line.strip()
            # Skip empty lines and sub-items
            if not line or line.startswith((' ', '\t', '-', '*', 'A.', 'B.', 'C.')):
                continue
            
            # Check for Roman numerals or "#### " headers
            if (line.startswith(('I.', 'II.', 'III.', 'IV.', 'V.', 'VI.', 'VII.')) or
                line.startswith('####')):
                # Clean up the title
                topic_title = line
                topic_title = topic_title.replace('####', '').strip()
                topic_title = topic_title.split('.', 1)[-1].strip() if '.' in topic_title else topic_title
                
                # Generate ID
                topic_id = topic_title.lower()
                topic_id = topic_id.replace("'", "").replace(" ", "_").replace("-", "_")
                topic_id = topic_id.replace("(", "").replace(")", "").replace(".", "")
                
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
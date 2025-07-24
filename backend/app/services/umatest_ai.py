"""
UMATest AI Service for Question Generation
Phase 1: Test Creation with 70/20/10 distribution
"""

from typing import List, Dict, Any, Optional, Tuple
from uuid import uuid4
import hashlib
import json
from datetime import datetime
import asyncio
import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import logging
import os

from app.config.ai_models import QUESTION_GENERATION_MODEL
from app.config.ai_config import get_gemini_config
from app.models.umatest import TestAssignment, TestQuestionCache, TestGenerationLog
from app.models.reading import ReadingAssignment, AssignmentImage

logger = logging.getLogger(__name__)

# Question distribution constants
QUESTIONS_PER_TOPIC = 10
BASIC_INTERMEDIATE_QUESTIONS = 7  # 70%
ADVANCED_QUESTIONS = 2  # 20%
EXPERT_QUESTIONS = 1  # 10%

# Pydantic models removed - using direct JSON parsing with Gemini instead

class UMATestAIService:
    """Service for generating test questions from UMALecture content"""
    
    def __init__(self):
        # Get configuration
        config = get_gemini_config()
        
        # Configure Gemini API
        genai.configure(api_key=config.api_key)
        
        # Use configured model
        self.model = genai.GenerativeModel(QUESTION_GENERATION_MODEL)
        
        self.system_prompt = """You are an expert educational assessment creator. 
        Generate thoughtful, comprehension-based questions that test understanding 
        of the provided content. Questions should be clear, unambiguous, and 
        appropriate for the specified grade level and difficulty."""
        
        logger.info(f"UMATestAIService initialized with model: {QUESTION_GENERATION_MODEL}")
    
    async def generate_test_questions(
        self,
        db: AsyncSession,
        test_assignment_id: str,
        regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Generate all questions for a test assignment
        
        Args:
            db: Database session
            test_assignment_id: ID of the test assignment
            regenerate: Force regeneration even if questions exist
            
        Returns:
            Dictionary with test structure and generation statistics
        """
        # Start generation log
        log_entry = TestGenerationLog(
            id=str(uuid4()),
            test_assignment_id=test_assignment_id,
            status='processing',
            started_at=datetime.utcnow()
        )
        db.add(log_entry)
        await db.commit()
        
        try:
            # Get test assignment
            test = await db.get(TestAssignment, test_assignment_id)
            if not test:
                raise ValueError("Test assignment not found")
            
            # If questions already exist and not regenerating, return existing
            if test.test_structure.get('topics') and not regenerate:
                return test.test_structure
            
            # Get all selected lectures
            lectures = await self._get_lectures(db, test.selected_lecture_ids)
            
            # Generate questions for each topic in each lecture
            test_structure = {
                'total_questions': 0,
                'topics': {},
                'generation_metadata': {
                    'generated_at': datetime.utcnow().isoformat(),
                    'ai_model': QUESTION_GENERATION_MODEL,
                    'distribution': {
                        'basic_intermediate': 70,
                        'advanced': 20,
                        'expert': 10
                    }
                }
            }
            
            total_topics = 0
            cache_hits = 0
            cache_misses = 0
            
            for lecture in lectures:
                # Parse raw_content if it's a string
                if isinstance(lecture.raw_content, str):
                    import json
                    try:
                        content = json.loads(lecture.raw_content)
                    except:
                        continue
                else:
                    content = lecture.raw_content
                
                lecture_structure = content.get('lecture_structure', {})
                topics = lecture_structure.get('topics', {})
                
                for topic_id, topic_data in topics.items():
                    total_topics += 1
                    logger.info(f"Processing topic {topic_id}: {topic_data.get('title', 'Unknown')}")
                    
                    # Generate questions for this topic
                    topic_questions, hits, misses = await self._generate_topic_questions(
                        db, lecture, topic_id, topic_data
                    )
                    
                    cache_hits += hits
                    cache_misses += misses
                    
                    # Add to test structure
                    test_structure['topics'][f"{lecture.id}_{topic_id}"] = {
                        'topic_title': topic_data.get('title', 'Unknown Topic'),
                        'source_lecture_id': str(lecture.id),
                        'source_lecture_title': lecture.assignment_title,
                        'questions': topic_questions
                    }
                    
                    test_structure['total_questions'] += len(topic_questions)
            
            # Update test assignment with generated structure
            test.test_structure = test_structure
            test.updated_at = datetime.utcnow()
            
            # Update generation log
            log_entry.completed_at = datetime.utcnow()
            log_entry.status = 'completed'
            log_entry.total_topics_processed = total_topics
            log_entry.total_questions_generated = test_structure['total_questions']
            log_entry.cache_hits = cache_hits
            log_entry.cache_misses = cache_misses
            log_entry.ai_model = QUESTION_GENERATION_MODEL
            
            await db.commit()
            
            return test_structure
            
        except Exception as e:
            logger.error(f"Error generating test questions: {str(e)}")
            log_entry.status = 'failed'
            log_entry.error_message = str(e)
            log_entry.completed_at = datetime.utcnow()
            await db.commit()
            raise
    
    async def _get_lectures(
        self,
        db: AsyncSession,
        lecture_ids: List[str]
    ) -> List[ReadingAssignment]:
        """Get all selected lectures"""
        result = await db.execute(
            select(ReadingAssignment).where(
                and_(
                    ReadingAssignment.id.in_(lecture_ids),
                    ReadingAssignment.assignment_type == 'UMALecture',
                    ReadingAssignment.deleted_at.is_(None)
                )
            )
        )
        return result.scalars().all()
    
    async def _generate_topic_questions(
        self,
        db: AsyncSession,
        lecture: ReadingAssignment,
        topic_id: str,
        topic_data: Dict[str, Any]
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """
        Generate questions for a single topic following 70/20/10 distribution
        
        Returns:
            Tuple of (questions list, cache hits, cache misses)
        """
        questions = []
        cache_hits = 0
        cache_misses = 0
        
        difficulty_levels = topic_data.get('difficulty_levels', {})
        
        # Generate questions for each difficulty level according to distribution
        # 70% from Basic + Intermediate (combined)
        basic_int_questions = await self._generate_questions_for_levels(
            db, lecture, topic_id, topic_data,
            ['basic', 'intermediate'],
            BASIC_INTERMEDIATE_QUESTIONS
        )
        questions.extend(basic_int_questions[0])
        cache_hits += basic_int_questions[1]
        cache_misses += basic_int_questions[2]
        
        # 20% from Advanced
        if 'advanced' in difficulty_levels:
            adv_questions = await self._generate_questions_for_level(
                db, lecture, topic_id, topic_data,
                'advanced',
                ADVANCED_QUESTIONS
            )
            questions.extend(adv_questions[0])
            cache_hits += adv_questions[1]
            cache_misses += adv_questions[2]
        
        # 10% from Expert
        if 'expert' in difficulty_levels:
            exp_questions = await self._generate_questions_for_level(
                db, lecture, topic_id, topic_data,
                'expert',
                EXPERT_QUESTIONS
            )
            questions.extend(exp_questions[0])
            cache_hits += exp_questions[1]
            cache_misses += exp_questions[2]
        
        return questions, cache_hits, cache_misses
    
    async def _generate_questions_for_levels(
        self,
        db: AsyncSession,
        lecture: ReadingAssignment,
        topic_id: str,
        topic_data: Dict[str, Any],
        levels: List[str],
        num_questions: int
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Generate questions from combined difficulty levels (for basic+intermediate)"""
        # Combine content from multiple levels
        combined_content = []
        for level in levels:
            level_data = topic_data.get('difficulty_levels', {}).get(level, {})
            if level_data.get('content'):
                combined_content.append(f"[{level.upper()}]\n{level_data['content']}")
        
        if not combined_content:
            return [], 0, 0
        
        content = "\n\n".join(combined_content)
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Check cache first (using 'basic' as cache key for combined)
        cached = await self._check_cache(db, lecture.id, topic_id, 'basic', content_hash)
        if cached and len(cached) >= num_questions:
            return cached[:num_questions], 1, 0
        
        # Generate new questions
        questions = await self._call_ai_for_questions(
            content,
            topic_data.get('title', 'Unknown Topic'),
            lecture.grade_level,
            'basic-intermediate',
            num_questions
        )
        
        # Cache the generated questions
        await self._cache_questions(
            db, lecture.id, topic_id, 'basic', content_hash, questions
        )
        
        return questions, 0, 1
    
    async def _generate_questions_for_level(
        self,
        db: AsyncSession,
        lecture: ReadingAssignment,
        topic_id: str,
        topic_data: Dict[str, Any],
        level: str,
        num_questions: int
    ) -> Tuple[List[Dict[str, Any]], int, int]:
        """Generate questions for a single difficulty level"""
        level_data = topic_data.get('difficulty_levels', {}).get(level, {})
        content = level_data.get('content', '')
        
        if not content:
            return [], 0, 0
        
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Check cache first
        cached = await self._check_cache(db, lecture.id, topic_id, level, content_hash)
        if cached and len(cached) >= num_questions:
            return cached[:num_questions], 1, 0
        
        # Generate new questions
        questions = await self._call_ai_for_questions(
            content,
            topic_data.get('title', 'Unknown Topic'),
            lecture.grade_level,
            level,
            num_questions
        )
        
        # Cache the generated questions
        await self._cache_questions(
            db, lecture.id, topic_id, level, content_hash, questions
        )
        
        return questions, 0, 1
    
    async def _check_cache(
        self,
        db: AsyncSession,
        lecture_id: str,
        topic_id: str,
        difficulty_level: str,
        content_hash: str
    ) -> Optional[List[Dict[str, Any]]]:
        """Check if questions are already cached"""
        result = await db.execute(
            select(TestQuestionCache).where(
                and_(
                    TestQuestionCache.lecture_id == lecture_id,
                    TestQuestionCache.topic_id == topic_id,
                    TestQuestionCache.difficulty_level == difficulty_level,
                    TestQuestionCache.content_hash == content_hash
                )
            )
        )
        cache_entry = result.scalar_one_or_none()
        
        if cache_entry:
            # Convert cached questions to test format
            return [
                {
                    'id': str(uuid4()),
                    'question_text': q['question_text'],
                    'difficulty_level': difficulty_level,
                    'source_content': q['source_excerpt'],
                    'answer_key': q['answer_key']
                }
                for q in cache_entry.questions
            ]
        
        return None
    
    async def _call_ai_for_questions(
        self,
        content: str,
        topic_title: str,
        grade_level: str,
        difficulty_level: str,
        num_questions: int
    ) -> List[Dict[str, Any]]:
        """Call AI to generate questions"""
        prompt = f"""{self.system_prompt}

Generate {num_questions} short-answer questions for the following content.

Topic: {topic_title}
Grade Level: {grade_level}
Difficulty Level: {difficulty_level}

Content:
{content}

Requirements:
1. Questions should test comprehension and understanding, not just recall
2. Questions should be appropriate for {grade_level} students
3. Each question should be answerable based on the provided content
4. Provide clear answer keys with explanations
5. Include evaluation rubrics that specify what constitutes a correct answer
6. Extract relevant source excerpts that support each answer

For {difficulty_level} level:
- Basic/Intermediate: Focus on fundamental concepts and direct comprehension
- Advanced: Include analysis, synthesis, and application questions
- Expert: Include evaluation, critical thinking, and extension questions

Return the response as a JSON object with the following structure:
{{
  "questions": [
    {{
      "question_text": "The question text",
      "correct_answer": "The correct answer",
      "explanation": "Explanation of why this is correct",
      "evaluation_rubric": "How to evaluate student answers",
      "source_excerpt": "Relevant excerpt from the content"
    }}
  ]
}}
"""
        
        try:
            # Generate content using Gemini
            response = await asyncio.to_thread(
                self.model.generate_content,
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    max_output_tokens=2048,
                    response_mime_type="application/json"
                )
            )
            
            # Parse the JSON response
            result_data = json.loads(response.text)
            
            # Convert to our format
            questions = []
            for q in result_data.get('questions', [])[:num_questions]:
                questions.append({
                    'id': str(uuid4()),
                    'question_text': q['question_text'],
                    'difficulty_level': difficulty_level,
                    'source_content': q['source_excerpt'],
                    'answer_key': {
                        'correct_answer': q['correct_answer'],
                        'explanation': q['explanation'],
                        'evaluation_rubric': q['evaluation_rubric']
                    }
                })
            
            return questions
            
        except Exception as e:
            logger.error(f"Error generating questions: {str(e)}")
            raise
    
    async def _cache_questions(
        self,
        db: AsyncSession,
        lecture_id: str,
        topic_id: str,
        difficulty_level: str,
        content_hash: str,
        questions: List[Dict[str, Any]]
    ):
        """Cache generated questions"""
        cache_entry = TestQuestionCache(
            id=str(uuid4()),
            lecture_id=lecture_id,
            topic_id=topic_id,
            difficulty_level=difficulty_level,
            content_hash=content_hash,
            questions=[
                {
                    'question_text': q['question_text'],
                    'answer_key': q['answer_key'],
                    'source_excerpt': q['source_content']
                }
                for q in questions
            ],
            ai_model=QUESTION_GENERATION_MODEL,
            generation_timestamp=datetime.utcnow()
        )
        db.add(cache_entry)
        await db.commit()

# Singleton instance
umatest_ai_service = UMATestAIService()
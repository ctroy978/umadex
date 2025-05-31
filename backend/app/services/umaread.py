"""
UMARead service layer for managing reading assignments and student progress
"""
import json
import re
from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, func, delete
from sqlalchemy.orm import selectinload

from app.models.reading import ReadingAssignment, ReadingChunk
from app.models.classroom import StudentAssignment, ClassroomAssignment
from app.models.user import User
from app.models.image_analysis import AssignmentImage
from app.schemas.umaread import (
    StudentProgress,
    ChunkProgress,
    ChunkResponse,
    QuestionRequest,
    GeneratedQuestion,
    QuestionType,
    StudentAnswer,
    AnswerEvaluation,
    AssignmentMetadata,
    WorkType,
    LiteraryForm,
    QuestionCacheKey,
    CachedQuestion,
    DifficultyAdjustment
)
from app.services.umaread_ai import UMAReadAI
from app.core.redis import redis_client
from sqlalchemy import text


class UMAReadService:
    """Service for managing UMARead assignments and progress"""
    
    def __init__(self):
        self.ai_service = UMAReadAI()
    
    async def get_student_assignment(self, 
                                   db: AsyncSession,
                                   student_id: UUID,
                                   assignment_id: UUID) -> Optional[StudentAssignment]:
        """Get student assignment with progress data"""
        result = await db.execute(
            select(StudentAssignment)
            .options(selectinload(StudentAssignment.assignment))
            .where(
                and_(
                    StudentAssignment.student_id == student_id,
                    StudentAssignment.assignment_id == assignment_id,
                    StudentAssignment.assignment_type == "reading"
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def get_assignment_metadata(self, 
                                    db: AsyncSession,
                                    assignment_id: UUID) -> AssignmentMetadata:
        """Get assignment metadata for AI prompts"""
        result = await db.execute(
            select(ReadingAssignment).where(ReadingAssignment.id == assignment_id)
        )
        assignment = result.scalar_one_or_none()
        
        if not assignment:
            raise ValueError(f"Assignment {assignment_id} not found")
        
        # Map database values to enum types
        work_type = WorkType.FICTION if assignment.work_type == "Fiction" else WorkType.NON_FICTION
        
        literary_form_map = {
            "Prose": LiteraryForm.PROSE,
            "Poetry": LiteraryForm.POETRY,
            "Drama": LiteraryForm.DRAMA,
            "Mixed": LiteraryForm.MIXED
        }
        literary_form = literary_form_map.get(assignment.literary_form, LiteraryForm.PROSE)
        
        return AssignmentMetadata(
            work_type=work_type,
            literary_form=literary_form,
            genre=assignment.genre,
            subject=assignment.subject,
            grade_level=assignment.grade_level,
            title=assignment.title,
            author=assignment.author
        )
    
    async def get_chunk_content(self,
                              db: AsyncSession,
                              assignment_id: UUID,
                              chunk_number: int) -> ChunkResponse:
        """Get chunk content with images"""
        # Get the specific chunk
        chunk_result = await db.execute(
            select(ReadingChunk).where(
                and_(
                    ReadingChunk.assignment_id == assignment_id,
                    ReadingChunk.chunk_number == chunk_number
                )
            )
        )
        chunk = chunk_result.scalar_one_or_none()
        
        if not chunk:
            raise ValueError(f"Chunk {chunk_number} not found")
        
        # Get total chunks
        total_result = await db.execute(
            select(func.count(ReadingChunk.id))
            .where(ReadingChunk.assignment_id == assignment_id)
        )
        total_chunks = total_result.scalar()
        
        # Extract image references from content
        image_pattern = re.compile(r'<image>(.*?)</image>')
        image_refs = image_pattern.findall(chunk.content)
        
        # Get image data if references exist
        images = []
        if image_refs:
            # Map references like "image-1" to actual images
            image_numbers = []
            for ref in image_refs:
                match = re.match(r'image-(\d+)', ref)
                if match:
                    image_numbers.append(int(match.group(1)))
            
            if image_numbers:
                # Get images from database
                image_result = await db.execute(
                    select(AssignmentImage)
                    .where(AssignmentImage.assignment_id == assignment_id)
                    .order_by(AssignmentImage.created_at)
                )
                all_images = list(image_result.scalars())
                
                for num in image_numbers:
                    if 0 < num <= len(all_images):
                        img = all_images[num - 1]
                        images.append({
                            "id": str(img.id),
                            "url": f"/api/v1/images/{img.id}",
                            "thumbnail_url": img.thumbnail_url,
                            "description": img.ai_description or ""
                        })
        
        # Clean content for display (remove image tags)
        display_content = image_pattern.sub('', chunk.content).strip()
        
        return ChunkResponse(
            chunk_number=chunk_number,
            total_chunks=total_chunks,
            content=display_content,
            images=images,
            has_next=chunk_number < total_chunks,
            has_previous=chunk_number > 1
        )
    
    async def get_or_generate_question(self,
                                     db: AsyncSession,
                                     student_id: UUID,
                                     assignment_id: UUID,
                                     chunk_number: int,
                                     question_type: QuestionType,
                                     difficulty_level: Optional[int] = None) -> GeneratedQuestion:
        """Get question from cache or generate new one"""
        # Get chunk content
        chunk_result = await db.execute(
            select(ReadingChunk).where(
                and_(
                    ReadingChunk.assignment_id == assignment_id,
                    ReadingChunk.chunk_number == chunk_number
                )
            )
        )
        chunk = chunk_result.scalar_one_or_none()
        
        if not chunk:
            raise ValueError(f"Chunk {chunk_number} not found")
        
        # Create cache key
        content_hash = self.ai_service.generate_content_hash(chunk.content)
        cache_key = QuestionCacheKey(
            assignment_id=assignment_id,
            chunk_number=chunk_number,
            question_type=question_type,
            difficulty_level=difficulty_level,
            content_hash=content_hash
        )
        
        # Check cache first
        cached = await self._get_cached_question(cache_key)
        if cached:
            return cached
        
        # Generate new question
        metadata = await self.get_assignment_metadata(db, assignment_id)
        
        request = QuestionRequest(
            assignment_id=assignment_id,
            chunk_number=chunk_number,
            chunk_content=chunk.content,
            difficulty_level=difficulty_level or 5,  # Default to middle difficulty
            assignment_metadata=metadata,
            question_type=question_type
        )
        
        question = await self.ai_service.generate_question(request)
        
        # Cache the question
        await self._cache_question(cache_key, question)
        
        # Store in database
        await self._store_question_in_db(db, assignment_id, chunk_number, question)
        
        return question
    
    async def evaluate_answer(self,
                            db: AsyncSession,
                            student_id: UUID,
                            answer: StudentAnswer) -> Tuple[AnswerEvaluation, bool]:
        """Evaluate student answer and update progress"""
        # Get student assignment
        student_assignment = await self.get_student_assignment(
            db, student_id, answer.assignment_id
        )
        
        if not student_assignment:
            raise ValueError("Student assignment not found")
        
        # Get chunk content for context
        chunk_result = await db.execute(
            select(ReadingChunk).where(
                and_(
                    ReadingChunk.assignment_id == answer.assignment_id,
                    ReadingChunk.chunk_number == answer.chunk_number
                )
            )
        )
        chunk = chunk_result.scalar_one_or_none()
        
        # Get question from last response or cache
        question_result = await db.execute(
            select("question_text", "difficulty_level")
            .select_from("reading_student_responses")
            .where(
                and_(
                    "student_id" == student_id,
                    "assignment_id" == answer.assignment_id,
                    "chunk_number" == answer.chunk_number,
                    "question_type" == answer.question_type.value
                )
            )
            .order_by("created_at DESC")
            .limit(1)
        )
        question_data = question_result.first()
        
        if not question_data:
            # Get from cache or generate
            progress_metadata = student_assignment.progress_metadata or {}
            difficulty = progress_metadata.get("difficulty_level", 5)
            
            question = await self.get_or_generate_question(
                db, student_id, answer.assignment_id, 
                answer.chunk_number, answer.question_type, difficulty
            )
            question_text = question.question_text
            difficulty_level = question.difficulty_level
        else:
            question_text = question_data[0]
            difficulty_level = question_data[1]
        
        # Get metadata for evaluation
        metadata = await self.get_assignment_metadata(db, answer.assignment_id)
        
        # Evaluate answer using AI
        evaluation = await self.ai_service.evaluate_answer(
            question=question_text,
            student_answer=answer.answer_text,
            chunk_content=chunk.content,
            metadata=metadata,
            question_type=answer.question_type.value,
            difficulty=difficulty_level
        )
        
        # Store response in database
        await self._store_student_response(
            db, student_id, answer, evaluation, 
            question_text, difficulty_level
        )
        
        # Update progress if both questions answered correctly
        can_proceed = await self._update_progress_if_complete(
            db, student_id, answer.assignment_id, 
            answer.chunk_number, evaluation
        )
        
        await db.commit()
        
        return evaluation, can_proceed
    
    async def _get_cached_question(self, cache_key: QuestionCacheKey) -> Optional[GeneratedQuestion]:
        """Get question from Redis cache"""
        if not redis_client:
            return None
        
        try:
            cached_json = await redis_client.get(cache_key.cache_key())
            if cached_json:
                data = json.loads(cached_json)
                return GeneratedQuestion(**data)
        except Exception:
            pass
        
        return None
    
    async def _cache_question(self, cache_key: QuestionCacheKey, question: GeneratedQuestion):
        """Store question in Redis cache"""
        if not redis_client:
            return
        
        try:
            # Cache for 7 days
            await redis_client.setex(
                cache_key.cache_key(),
                7 * 24 * 60 * 60,
                question.json()
            )
        except Exception:
            pass
    
    async def _store_question_in_db(self,
                                  db: AsyncSession,
                                  assignment_id: UUID,
                                  chunk_number: int,
                                  question: GeneratedQuestion):
        """Store generated question in database"""
        query = """
        INSERT INTO reading_question_cache (
            assignment_id, chunk_number, question_type, 
            difficulty_level, question_text, question_metadata, ai_model
        ) VALUES (
            :assignment_id, :chunk_number, :question_type,
            :difficulty_level, :question_text, :metadata::jsonb, :ai_model
        )
        ON CONFLICT (assignment_id, chunk_number, question_type, difficulty_level) 
        DO UPDATE SET
            question_text = EXCLUDED.question_text,
            question_metadata = EXCLUDED.question_metadata,
            ai_model = EXCLUDED.ai_model,
            updated_at = NOW()
        """
        
        await execute_query(
            query,
            {
                "assignment_id": assignment_id,
                "chunk_number": chunk_number,
                "question_type": question.question_type.value,
                "difficulty_level": question.difficulty_level,
                "question_text": question.question_text,
                "metadata": json.dumps({
                    "content_focus": question.content_focus,
                    "expected_answer_elements": question.expected_answer_elements,
                    "evaluation_criteria": question.evaluation_criteria
                }),
                "ai_model": question.ai_model
            }
        )
    
    async def _store_student_response(self,
                                    db: AsyncSession,
                                    student_id: UUID,
                                    answer: StudentAnswer,
                                    evaluation: AnswerEvaluation,
                                    question_text: str,
                                    difficulty_level: Optional[int]):
        """Store student response in database"""
        query = """
        INSERT INTO reading_student_responses (
            student_id, assignment_id, chunk_number, question_type,
            question_text, difficulty_level, student_answer, is_correct,
            attempt_number, time_spent_seconds, ai_feedback, feedback_metadata
        ) VALUES (
            :student_id, :assignment_id, :chunk_number, :question_type,
            :question_text, :difficulty_level, :student_answer, :is_correct,
            :attempt_number, :time_spent, :ai_feedback, :feedback_metadata::jsonb
        )
        """
        
        await execute_query(
            query,
            {
                "student_id": student_id,
                "assignment_id": answer.assignment_id,
                "chunk_number": answer.chunk_number,
                "question_type": answer.question_type.value,
                "question_text": question_text,
                "difficulty_level": difficulty_level,
                "student_answer": answer.answer_text,
                "is_correct": evaluation.is_correct,
                "attempt_number": answer.attempt_number,
                "time_spent": answer.time_spent_seconds,
                "ai_feedback": evaluation.feedback_text,
                "feedback_metadata": json.dumps({
                    "confidence_score": evaluation.confidence_score,
                    "content_specific_feedback": evaluation.content_specific_feedback,
                    "key_missing_elements": evaluation.key_missing_elements
                })
            }
        )
    
    async def _update_progress_if_complete(self,
                                         db: AsyncSession,
                                         student_id: UUID,
                                         assignment_id: UUID,
                                         chunk_number: int,
                                         evaluation: AnswerEvaluation) -> bool:
        """Update progress if chunk is complete, return if can proceed"""
        # Check if both questions answered correctly
        query = """
        SELECT 
            MAX(CASE WHEN question_type = 'summary' AND is_correct THEN 1 ELSE 0 END) as summary_correct,
            MAX(CASE WHEN question_type = 'comprehension' AND is_correct THEN 1 ELSE 0 END) as comp_correct
        FROM reading_student_responses
        WHERE student_id = :student_id
        AND assignment_id = :assignment_id
        AND chunk_number = :chunk_number
        """
        
        result = await execute_query(
            query,
            {
                "student_id": student_id,
                "assignment_id": assignment_id,
                "chunk_number": chunk_number
            }
        )
        
        row = result.first()
        both_correct = row.summary_correct == 1 and row.comp_correct == 1
        
        if both_correct:
            # Update student assignment progress
            student_assignment = await self.get_student_assignment(
                db, student_id, assignment_id
            )
            
            progress_metadata = student_assignment.progress_metadata or {}
            chunks_completed = progress_metadata.get("chunks_completed", [])
            
            if chunk_number not in chunks_completed:
                chunks_completed.append(chunk_number)
                chunks_completed.sort()
            
            # Update difficulty based on evaluation
            current_difficulty = progress_metadata.get("difficulty_level", 5)
            if evaluation.suggested_difficulty_change == DifficultyAdjustment.INCREASE:
                new_difficulty = min(8, current_difficulty + 1)
            elif evaluation.suggested_difficulty_change == DifficultyAdjustment.DECREASE:
                new_difficulty = max(1, current_difficulty - 1)
            else:
                new_difficulty = current_difficulty
            
            progress_metadata.update({
                "difficulty_level": new_difficulty,
                "chunks_completed": chunks_completed,
                "current_chunk": chunk_number + 1
            })
            
            # Update database
            await db.execute(
                update(StudentAssignment)
                .where(StudentAssignment.id == student_assignment.id)
                .values(
                    progress_metadata=progress_metadata,
                    current_position=chunk_number + 1,
                    last_activity_at=datetime.utcnow()
                )
            )
            
            # Check if assignment complete
            total_chunks_result = await db.execute(
                select(func.count(ReadingChunk.id))
                .where(ReadingChunk.assignment_id == assignment_id)
            )
            total_chunks = total_chunks_result.scalar()
            
            if len(chunks_completed) >= total_chunks:
                await db.execute(
                    update(StudentAssignment)
                    .where(StudentAssignment.id == student_assignment.id)
                    .values(
                        status="completed",
                        completed_at=datetime.utcnow()
                    )
                )
        
        return both_correct
    
    async def get_student_progress(self,
                                 db: AsyncSession,
                                 student_id: UUID,
                                 assignment_id: UUID) -> StudentProgress:
        """Get detailed student progress"""
        student_assignment = await self.get_student_assignment(
            db, student_id, assignment_id
        )
        
        if not student_assignment:
            raise ValueError("Student assignment not found")
        
        # Get total chunks
        total_result = await db.execute(
            select(func.count(ReadingChunk.id))
            .where(ReadingChunk.assignment_id == assignment_id)
        )
        total_chunks = total_result.scalar()
        
        progress_metadata = student_assignment.progress_metadata or {}
        
        # Build chunk scores from responses
        chunk_scores = {}
        responses_query = """
        SELECT 
            chunk_number,
            question_type,
            COUNT(*) as attempts,
            MAX(CASE WHEN is_correct THEN 1 ELSE 0 END) as correct,
            SUM(time_spent_seconds) as total_time
        FROM reading_student_responses
        WHERE student_id = :student_id
        AND assignment_id = :assignment_id
        GROUP BY chunk_number, question_type
        """
        
        result = await execute_query(
            responses_query,
            {"student_id": student_id, "assignment_id": assignment_id}
        )
        
        for row in result:
            chunk_key = str(row.chunk_number)
            if chunk_key not in chunk_scores:
                chunk_scores[chunk_key] = ChunkProgress(
                    chunk_number=row.chunk_number
                )
            
            if row.question_type == "summary":
                chunk_scores[chunk_key].summary_completed = bool(row.correct)
                chunk_scores[chunk_key].summary_attempts = row.attempts
            else:
                chunk_scores[chunk_key].comprehension_completed = bool(row.correct)
                chunk_scores[chunk_key].comprehension_attempts = row.attempts
            
            chunk_scores[chunk_key].time_spent_seconds += row.total_time or 0
        
        return StudentProgress(
            assignment_id=assignment_id,
            student_id=student_id,
            current_chunk=student_assignment.current_position,
            total_chunks=total_chunks,
            difficulty_level=progress_metadata.get("difficulty_level", 5),
            chunks_completed=progress_metadata.get("chunks_completed", []),
            chunk_scores=chunk_scores,
            status=student_assignment.status,
            last_activity=student_assignment.last_activity_at
        )
    
    async def flush_question_cache(self,
                                 db: AsyncSession,
                                 teacher_id: UUID,
                                 assignment_id: UUID,
                                 reason: Optional[str] = None) -> int:
        """Flush all cached questions for an assignment"""
        # Verify teacher owns assignment
        result = await db.execute(
            select(ReadingAssignment)
            .where(
                and_(
                    ReadingAssignment.id == assignment_id,
                    ReadingAssignment.teacher_id == teacher_id
                )
            )
        )
        
        if not result.scalar_one_or_none():
            raise ValueError("Assignment not found or unauthorized")
        
        # Delete from database
        delete_query = """
        DELETE FROM reading_question_cache
        WHERE assignment_id = :assignment_id
        RETURNING id
        """
        
        result = await execute_query(
            delete_query,
            {"assignment_id": assignment_id}
        )
        
        count = len(result.all())
        
        # Log the flush
        log_query = """
        INSERT INTO reading_cache_flush_log (
            assignment_id, teacher_id, reason, questions_flushed
        ) VALUES (
            :assignment_id, :teacher_id, :reason, :count
        )
        """
        
        await execute_query(
            log_query,
            {
                "assignment_id": assignment_id,
                "teacher_id": teacher_id,
                "reason": reason,
                "count": count
            }
        )
        
        # Clear Redis cache if available
        if redis_client:
            # Get all cache keys for this assignment
            pattern = f"umaread:question:{assignment_id}:*"
            try:
                keys = await redis_client.keys(pattern)
                if keys:
                    await redis_client.delete(*keys)
            except Exception:
                pass
        
        await db.commit()
        
        return count
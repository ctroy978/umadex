"""
Service layer for UMALecture functionality
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func, update, text as sql_text
from sqlalchemy.orm import selectinload
import json
import os

from app.models.user import User
from app.models.classroom import StudentAssignment, ClassroomAssignment, Classroom
from app.models.reading import ReadingAssignment, AssignmentImage
from app.schemas.umalecture import (
    LectureAssignmentCreate, 
    LectureAssignmentUpdate,
    LectureAssignmentResponse,
    LectureStudentProgress
)
from app.services.image_processing import ImageProcessor
from app.core.config import settings


class UMALectureService:
    """Service class for UMALecture operations"""
    
    def __init__(self):
        self.image_processor = ImageProcessor()
    
    async def create_lecture(
        self, 
        db: AsyncSession, 
        teacher_id: UUID, 
        lecture_data: LectureAssignmentCreate
    ) -> Dict[str, Any]:
        """Create a new lecture assignment"""
        # Execute raw SQL to insert into lecture_assignments
        query = sql_text("""
            INSERT INTO lecture_assignments (
                teacher_id, title, subject, grade_level, learning_objectives, status
            ) VALUES (
                :teacher_id, :title, :subject, :grade_level, :learning_objectives, 'draft'
            ) RETURNING *
        """)
        
        result = await db.execute(
            query,
            {
                "teacher_id": teacher_id,
                "title": lecture_data.title,
                "subject": lecture_data.subject,
                "grade_level": lecture_data.grade_level,
                "learning_objectives": lecture_data.learning_objectives
            }
        )
        
        lecture = result.mappings().first()
        await db.commit()
        
        return dict(lecture)
    
    async def list_teacher_lectures(
        self,
        db: AsyncSession,
        teacher_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """List lectures for a teacher with filtering"""
        query = """
            SELECT * FROM lecture_assignments
            WHERE teacher_id = :teacher_id
            AND deleted_at IS NULL
        """
        
        params = {"teacher_id": teacher_id}
        
        if status:
            query += " AND status = :status"
            params["status"] = status
        
        if search:
            query += " AND (title ILIKE :search OR subject ILIKE :search)"
            params["search"] = f"%{search}%"
        
        query += " ORDER BY created_at DESC LIMIT :limit OFFSET :skip"
        params["limit"] = limit
        params["skip"] = skip
        
        result = await db.execute(sql_text(query), params)
        lectures = result.mappings().all()
        
        return [dict(lecture) for lecture in lectures]
    
    async def get_lecture(
        self, 
        db: AsyncSession, 
        lecture_id: UUID, 
        teacher_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get a specific lecture assignment"""
        query = sql_text("""
            SELECT * FROM lecture_assignments
            WHERE id = :lecture_id 
            AND teacher_id = :teacher_id
            AND deleted_at IS NULL
        """)
        
        result = await db.execute(
            query,
            {"lecture_id": lecture_id, "teacher_id": teacher_id}
        )
        
        lecture = result.mappings().first()
        return dict(lecture) if lecture else None
    
    async def update_lecture(
        self,
        db: AsyncSession,
        lecture_id: UUID,
        teacher_id: UUID,
        update_data: LectureAssignmentUpdate
    ) -> Optional[Dict[str, Any]]:
        """Update a lecture assignment"""
        # Build update query dynamically
        update_fields = []
        params = {"lecture_id": lecture_id, "teacher_id": teacher_id}
        
        if update_data.title is not None:
            update_fields.append("title = :title")
            params["title"] = update_data.title
        
        if update_data.subject is not None:
            update_fields.append("subject = :subject")
            params["subject"] = update_data.subject
        
        if update_data.grade_level is not None:
            update_fields.append("grade_level = :grade_level")
            params["grade_level"] = update_data.grade_level
        
        if update_data.learning_objectives is not None:
            update_fields.append("learning_objectives = :learning_objectives")
            params["learning_objectives"] = update_data.learning_objectives
        
        if update_data.topic_outline is not None:
            update_fields.append("topic_outline = :topic_outline")
            params["topic_outline"] = update_data.topic_outline
        
        if update_data.lecture_structure is not None:
            update_fields.append("lecture_structure = :lecture_structure")
            params["lecture_structure"] = json.dumps(update_data.lecture_structure)
        
        if not update_fields:
            return await self.get_lecture(db, lecture_id, teacher_id)
        
        query = sql_text(f"""
            UPDATE lecture_assignments
            SET {', '.join(update_fields)}, updated_at = NOW()
            WHERE id = :lecture_id 
            AND teacher_id = :teacher_id
            AND deleted_at IS NULL
            RETURNING *
        """)
        
        result = await db.execute(query, params)
        lecture = result.mappings().first()
        await db.commit()
        
        return dict(lecture) if lecture else None
    
    async def delete_lecture(
        self, 
        db: AsyncSession, 
        lecture_id: UUID, 
        teacher_id: UUID
    ) -> bool:
        """Soft delete a lecture assignment"""
        query = sql_text("""
            UPDATE lecture_assignments
            SET deleted_at = NOW()
            WHERE id = :lecture_id 
            AND teacher_id = :teacher_id
            AND deleted_at IS NULL
            RETURNING id
        """)
        
        result = await db.execute(
            query,
            {"lecture_id": lecture_id, "teacher_id": teacher_id}
        )
        
        deleted = result.scalar()
        await db.commit()
        
        return bool(deleted)
    
    async def restore_lecture(
        self, 
        db: AsyncSession, 
        lecture_id: UUID, 
        teacher_id: UUID
    ) -> bool:
        """Restore a soft-deleted lecture assignment"""
        query = sql_text("""
            UPDATE lecture_assignments
            SET deleted_at = NULL
            WHERE id = :lecture_id 
            AND teacher_id = :teacher_id
            AND deleted_at IS NOT NULL
            RETURNING id
        """)
        
        result = await db.execute(
            query,
            {"lecture_id": lecture_id, "teacher_id": teacher_id}
        )
        
        restored = result.scalar()
        await db.commit()
        
        return bool(restored)
    
    async def update_lecture_status(
        self,
        db: AsyncSession,
        lecture_id: UUID,
        status: str,
        error: Optional[str] = None
    ) -> bool:
        """Update lecture processing status"""
        params = {
            "lecture_id": lecture_id,
            "status": status
        }
        
        if status == "processing":
            query = sql_text("""
                UPDATE lecture_assignments
                SET status = :status, 
                    processing_started_at = NOW(),
                    processing_error = NULL
                WHERE id = :lecture_id
                RETURNING id
            """)
        elif status == "published":
            query = sql_text("""
                UPDATE lecture_assignments
                SET status = :status, 
                    processing_completed_at = NOW()
                WHERE id = :lecture_id
                RETURNING id
            """)
        elif status == "draft" and error:
            query = sql_text("""
                UPDATE lecture_assignments
                SET status = :status, 
                    processing_error = :error
                WHERE id = :lecture_id
                RETURNING id
            """)
            params["error"] = error
        else:
            query = sql_text("""
                UPDATE lecture_assignments
                SET status = :status
                WHERE id = :lecture_id
                RETURNING id
            """)
        
        result = await db.execute(query, params)
        updated = result.scalar()
        await db.commit()
        
        return bool(updated)
    
    async def add_image(
        self,
        db: AsyncSession,
        lecture_id: UUID,
        file,
        node_id: str,
        teacher_description: str,
        position: int
    ) -> Dict[str, Any]:
        """Add an image to a lecture"""
        # Create upload directory
        upload_dir = os.path.join(settings.UPLOAD_DIR, "lectures", str(lecture_id))
        os.makedirs(upload_dir, exist_ok=True)
        
        # Generate unique filename
        file_ext = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_ext}"
        
        # Process image (create multiple sizes)
        file_content = await file.read()
        processed_images = await self.image_processor.process_image(
            file_content,
            upload_dir,
            unique_filename
        )
        
        # Insert into database
        query = sql_text("""
            INSERT INTO lecture_images (
                lecture_id, filename, teacher_description, 
                node_id, position, original_url, display_url, 
                thumbnail_url, file_size, mime_type
            ) VALUES (
                :lecture_id, :filename, :teacher_description,
                :node_id, :position, :original_url, :display_url,
                :thumbnail_url, :file_size, :mime_type
            ) RETURNING *
        """)
        
        result = await db.execute(
            query,
            {
                "lecture_id": lecture_id,
                "filename": unique_filename,
                "teacher_description": teacher_description,
                "node_id": node_id,
                "position": position,
                "original_url": processed_images["original"],
                "display_url": processed_images.get("display"),
                "thumbnail_url": processed_images.get("thumbnail"),
                "file_size": len(file_content),
                "mime_type": file.content_type
            }
        )
        
        image = result.mappings().first()
        await db.commit()
        
        return dict(image)
    
    async def list_images(
        self, 
        db: AsyncSession, 
        lecture_id: UUID
    ) -> List[Dict[str, Any]]:
        """List all images for a lecture"""
        query = sql_text("""
            SELECT * FROM lecture_images
            WHERE lecture_id = :lecture_id
            ORDER BY node_id, position
        """)
        
        result = await db.execute(query, {"lecture_id": lecture_id})
        images = result.mappings().all()
        
        return [dict(image) for image in images]
    
    async def delete_image(
        self,
        db: AsyncSession,
        lecture_id: UUID,
        image_id: UUID,
        teacher_id: UUID
    ) -> bool:
        """Delete an image from a lecture"""
        # Verify ownership through lecture
        verify_query = sql_text("""
            SELECT 1 FROM lecture_assignments
            WHERE id = :lecture_id 
            AND teacher_id = :teacher_id
            AND deleted_at IS NULL
        """)
        
        result = await db.execute(
            verify_query,
            {"lecture_id": lecture_id, "teacher_id": teacher_id}
        )
        
        if not result.scalar():
            return False
        
        # Delete image
        delete_query = sql_text("""
            DELETE FROM lecture_images
            WHERE id = :image_id AND lecture_id = :lecture_id
            RETURNING id
        """)
        
        result = await db.execute(
            delete_query,
            {"image_id": image_id, "lecture_id": lecture_id}
        )
        
        deleted = result.scalar()
        await db.commit()
        
        # TODO: Delete physical files
        
        return bool(deleted)
    
    async def update_lecture_structure(
        self,
        db: AsyncSession,
        lecture_id: UUID,
        teacher_id: UUID,
        structure: Dict[str, Any]
    ) -> bool:
        """Update the AI-generated structure"""
        query = sql_text("""
            UPDATE lecture_assignments
            SET lecture_structure = :structure,
                updated_at = NOW()
            WHERE id = :lecture_id 
            AND teacher_id = :teacher_id
            AND deleted_at IS NULL
            RETURNING id
        """)
        
        result = await db.execute(
            query,
            {
                "lecture_id": lecture_id,
                "teacher_id": teacher_id,
                "structure": json.dumps(structure)
            }
        )
        
        updated = result.scalar()
        await db.commit()
        
        return bool(updated)
    
    async def publish_lecture(
        self,
        db: AsyncSession,
        lecture_id: UUID,
        teacher_id: UUID
    ) -> bool:
        """Publish a lecture for student use"""
        # Verify lecture has structure and is ready
        query = sql_text("""
            UPDATE lecture_assignments
            SET status = 'published',
                updated_at = NOW()
            WHERE id = :lecture_id 
            AND teacher_id = :teacher_id
            AND deleted_at IS NULL
            AND lecture_structure IS NOT NULL
            AND status != 'published'
            RETURNING id
        """)
        
        result = await db.execute(
            query,
            {"lecture_id": lecture_id, "teacher_id": teacher_id}
        )
        
        published = result.scalar()
        await db.commit()
        
        return bool(published)
    
    async def create_reading_assignment_entry(
        self,
        db: AsyncSession,
        lecture_id: UUID
    ) -> UUID:
        """Create an entry in reading_assignments for classroom integration"""
        # Get lecture details
        lecture_query = sql_text("""
            SELECT title, subject, grade_level, teacher_id
            FROM lecture_assignments
            WHERE id = :lecture_id
        """)
        
        result = await db.execute(lecture_query, {"lecture_id": lecture_id})
        lecture = result.mappings().first()
        
        if not lecture:
            raise ValueError("Lecture not found")
        
        # Check if entry already exists
        check_query = sql_text("""
            SELECT id FROM reading_assignments
            WHERE id = :lecture_id
        """)
        
        existing = await db.execute(check_query, {"lecture_id": lecture_id})
        if existing.scalar():
            return lecture_id
        
        # Create reading assignment entry
        insert_query = sql_text("""
            INSERT INTO reading_assignments (
                id, teacher_id, assignment_title, subject, 
                grade_level, assignment_type, status
            ) VALUES (
                :id, :teacher_id, :title, :subject,
                :grade_level, 'UMALecture', 'published'
            ) ON CONFLICT (id) DO NOTHING
            RETURNING id
        """)
        
        result = await db.execute(
            insert_query,
            {
                "id": lecture_id,
                "teacher_id": lecture["teacher_id"],
                "title": lecture["title"],
                "subject": lecture["subject"],
                "grade_level": lecture["grade_level"]
            }
        )
        
        await db.commit()
        return lecture_id
    
    async def assign_to_classrooms(
        self,
        db: AsyncSession,
        lecture_id: UUID,
        classroom_ids: List[UUID],
        teacher_id: UUID
    ) -> List[Dict[str, Any]]:
        """Assign lecture to multiple classrooms"""
        results = []
        
        for classroom_id in classroom_ids:
            # Verify classroom ownership
            verify_query = sql_text("""
                SELECT 1 FROM classrooms
                WHERE id = :classroom_id 
                AND teacher_id = :teacher_id
                AND deleted_at IS NULL
            """)
            
            result = await db.execute(
                verify_query,
                {"classroom_id": classroom_id, "teacher_id": teacher_id}
            )
            
            if not result.scalar():
                continue
            
            # Create classroom assignment
            assign_query = sql_text("""
                INSERT INTO classroom_assignments (
                    classroom_id, assignment_id, assignment_type
                ) VALUES (
                    :classroom_id, :assignment_id, 'lecture'
                ) ON CONFLICT (_classroom_assignment_uc) 
                DO NOTHING
                RETURNING *
            """)
            
            result = await db.execute(
                assign_query,
                {
                    "classroom_id": classroom_id,
                    "assignment_id": lecture_id
                }
            )
            
            assignment = result.mappings().first()
            if assignment:
                results.append(dict(assignment))
        
        await db.commit()
        return results
    
    async def get_or_create_student_progress(
        self,
        db: AsyncSession,
        student_id: UUID,
        assignment_id: UUID
    ) -> LectureStudentProgress:
        """Get or create student progress for a lecture"""
        # Get student assignment
        sa_query = sql_text("""
            SELECT sa.*, la.id as lecture_id
            FROM student_assignments sa
            JOIN classroom_assignments ca ON ca.id = sa.classroom_assignment_id
            JOIN lecture_assignments la ON la.id = ca.assignment_id
            WHERE sa.student_id = :student_id
            AND sa.id = :assignment_id
            AND ca.assignment_type = 'UMALecture'
        """)
        
        result = await db.execute(
            sa_query,
            {"student_id": student_id, "assignment_id": assignment_id}
        )
        
        student_assignment = result.mappings().first()
        if not student_assignment:
            raise ValueError("Assignment not found")
        
        # Initialize progress if needed
        progress_metadata = student_assignment.get("progress_metadata") or {}
        if "lecture_path" not in progress_metadata:
            progress_metadata["lecture_path"] = []
            progress_metadata["topic_progress"] = {}
            progress_metadata["total_points"] = 0
            
            update_query = sql_text("""
                UPDATE student_assignments
                SET progress_metadata = :metadata,
                    started_at = COALESCE(started_at, NOW())
                WHERE id = :assignment_id
            """)
            
            await db.execute(
                update_query,
                {
                    "metadata": json.dumps(progress_metadata),
                    "assignment_id": assignment_id
                }
            )
            await db.commit()
        
        return LectureStudentProgress(
            assignment_id=assignment_id,
            lecture_id=student_assignment["lecture_id"],
            current_topic=progress_metadata.get("current_topic"),
            current_difficulty=progress_metadata.get("current_difficulty"),
            topics_completed=progress_metadata.get("topics_completed", []),
            topic_progress=progress_metadata.get("topic_progress", {}),
            total_points=progress_metadata.get("total_points", 0),
            last_activity_at=student_assignment.get("last_activity_at"),
            started_at=student_assignment["started_at"],
            completed_at=student_assignment.get("completed_at")
        )
    
    async def get_lecture_topics(
        self,
        db: AsyncSession,
        assignment_id: UUID,
        student_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get available topics for a lecture"""
        # Get lecture structure
        query = sql_text("""
            SELECT la.lecture_structure, sa.progress_metadata
            FROM lecture_assignments la
            JOIN classroom_assignments ca ON ca.assignment_id = la.id
            JOIN student_assignments sa ON sa.classroom_assignment_id = ca.id
            WHERE sa.id = :assignment_id
            AND sa.student_id = :student_id
            AND ca.assignment_type = 'UMALecture'
        """)
        
        result = await db.execute(
            query,
            {"assignment_id": assignment_id, "student_id": student_id}
        )
        
        data = result.mappings().first()
        if not data or not data["lecture_structure"]:
            return []
        
        structure = data["lecture_structure"]
        progress = data.get("progress_metadata", {})
        topic_progress = progress.get("topic_progress", {})
        
        topics = []
        for topic_id, topic_data in structure.get("topics", {}).items():
            topics.append({
                "topic_id": topic_id,
                "title": topic_data["title"],
                "available_difficulties": list(topic_data.get("difficulty_levels", {}).keys()),
                "completed_difficulties": topic_progress.get(topic_id, [])
            })
        
        return topics
    
    async def get_topic_content(
        self,
        db: AsyncSession,
        assignment_id: UUID,
        topic_id: str,
        difficulty: str,
        student_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get content for a specific topic and difficulty"""
        # Get lecture structure and images
        query = sql_text("""
            SELECT la.lecture_structure, la.id as lecture_id
            FROM lecture_assignments la
            JOIN classroom_assignments ca ON ca.assignment_id = la.id
            JOIN student_assignments sa ON sa.classroom_assignment_id = ca.id
            WHERE sa.id = :assignment_id
            AND sa.student_id = :student_id
            AND ca.assignment_type = 'UMALecture'
        """)
        
        result = await db.execute(
            query,
            {"assignment_id": assignment_id, "student_id": student_id}
        )
        
        data = result.mappings().first()
        if not data or not data["lecture_structure"]:
            return None
        
        structure = data["lecture_structure"]
        lecture_id = data["lecture_id"]
        
        # Get topic content
        topic_data = structure.get("topics", {}).get(topic_id)
        if not topic_data:
            return None
        
        difficulty_content = topic_data.get("difficulty_levels", {}).get(difficulty)
        if not difficulty_content:
            return None
        
        # Get associated images
        image_query = sql_text("""
            SELECT * FROM lecture_images
            WHERE lecture_id = :lecture_id
            AND node_id = :topic_id
            ORDER BY position
        """)
        
        image_result = await db.execute(
            image_query,
            {"lecture_id": lecture_id, "topic_id": topic_id}
        )
        
        images = [dict(img) for img in image_result.mappings().all()]
        
        # Determine next options
        difficulties = list(topic_data.get("difficulty_levels", {}).keys())
        current_idx = difficulties.index(difficulty) if difficulty in difficulties else 0
        next_difficulties = difficulties[current_idx + 1:] if current_idx < len(difficulties) - 1 else []
        
        # Get other topics
        all_topics = list(structure.get("topics", {}).keys())
        next_topics = [t for t in all_topics if t != topic_id]
        
        return {
            "topic_id": topic_id,
            "difficulty_level": difficulty,
            "content": difficulty_content.get("content", ""),
            "images": images,
            "questions": difficulty_content.get("questions", []),
            "next_difficulties": next_difficulties,
            "next_topics": next_topics
        }
    
    async def track_interaction(
        self,
        db: AsyncSession,
        student_id: UUID,
        assignment_id: UUID,
        topic_id: str,
        difficulty: str,
        interaction_type: str,
        question_data: Optional[Dict[str, Any]] = None
    ) -> None:
        """Track student interaction with lecture content"""
        # Get lecture ID
        lecture_query = sql_text("""
            SELECT la.id as lecture_id
            FROM lecture_assignments la
            JOIN classroom_assignments ca ON ca.assignment_id = la.id
            JOIN student_assignments sa ON sa.classroom_assignment_id = ca.id
            WHERE sa.id = :assignment_id
            AND sa.student_id = :student_id
        """)
        
        result = await db.execute(
            lecture_query,
            {"assignment_id": assignment_id, "student_id": student_id}
        )
        
        lecture_data = result.mappings().first()
        if not lecture_data:
            return
        
        # Insert interaction
        insert_query = sql_text("""
            INSERT INTO lecture_student_interactions (
                student_id, assignment_id, lecture_id,
                topic_id, difficulty_level, interaction_type,
                question_text, student_answer, is_correct,
                time_spent_seconds
            ) VALUES (
                :student_id, :assignment_id, :lecture_id,
                :topic_id, :difficulty_level, :interaction_type,
                :question_text, :student_answer, :is_correct,
                :time_spent
            )
        """)
        
        params = {
            "student_id": student_id,
            "assignment_id": assignment_id,
            "lecture_id": lecture_data["lecture_id"],
            "topic_id": topic_id,
            "difficulty_level": difficulty,
            "interaction_type": interaction_type,
            "question_text": question_data.get("question") if question_data else None,
            "student_answer": question_data.get("answer") if question_data else None,
            "is_correct": question_data.get("is_correct") if question_data else None,
            "time_spent": question_data.get("time_spent", 0) if question_data else 0
        }
        
        await db.execute(insert_query, params)
        
        # Update progress metadata
        if interaction_type == "answer_question" and question_data and question_data.get("is_correct"):
            update_query = sql_text("""
                UPDATE student_assignments
                SET progress_metadata = jsonb_set(
                    COALESCE(progress_metadata, '{}'::jsonb),
                    '{total_points}',
                    to_jsonb(COALESCE((progress_metadata->>'total_points')::int, 0) + :points)
                ),
                last_activity_at = NOW()
                WHERE id = :assignment_id
            """)
            
            await db.execute(
                update_query,
                {
                    "assignment_id": assignment_id,
                    "points": question_data.get("points_earned", 1)
                }
            )
        
        await db.commit()
    
    async def submit_answer(
        self,
        db: AsyncSession,
        student_id: UUID,
        assignment_id: UUID,
        topic_id: str,
        difficulty: str,
        question_index: int,
        answer: str
    ) -> Dict[str, Any]:
        """Submit and evaluate a student's answer"""
        # Get question from content
        content = await self.get_topic_content(
            db, assignment_id, topic_id, difficulty, student_id
        )
        
        if not content or question_index >= len(content["questions"]):
            return None
        
        question = content["questions"][question_index]
        
        # Simple evaluation (to be enhanced with AI)
        is_correct = answer.lower().strip() == question.get("correct_answer", "").lower().strip()
        
        # Track interaction
        await self.track_interaction(
            db, student_id, assignment_id, topic_id, difficulty, "answer_question",
            {
                "question": question["question"],
                "answer": answer,
                "is_correct": is_correct,
                "points_earned": 10 if is_correct else 0
            }
        )
        
        # Determine next action
        if question_index < len(content["questions"]) - 1:
            next_action = "next_question"
        elif content["next_difficulties"]:
            next_action = "next_difficulty"
        else:
            next_action = "complete_topic"
            
            # Mark topic as completed
            complete_query = sql_text("""
                UPDATE student_assignments
                SET progress_metadata = jsonb_set(
                    jsonb_set(
                        COALESCE(progress_metadata, '{}'::jsonb),
                        '{topic_progress,' || :topic_id || '}',
                        to_jsonb(array_append(
                            COALESCE((progress_metadata->'topic_progress'->:topic_id)::text[], ARRAY[]::text[]),
                            :difficulty
                        ))
                    ),
                    '{topics_completed}',
                    to_jsonb(array_append(
                        COALESCE((progress_metadata->>'topics_completed')::text[], ARRAY[]::text[]),
                        :topic_id
                    ))
                )
                WHERE id = :assignment_id
                AND NOT (progress_metadata->'topics_completed' ? :topic_id)
            """)
            
            await db.execute(
                complete_query,
                {
                    "assignment_id": assignment_id,
                    "topic_id": topic_id,
                    "difficulty": difficulty
                }
            )
            await db.commit()
        
        return {
            "is_correct": is_correct,
            "feedback": "Correct!" if is_correct else f"Not quite. The answer was: {question.get('correct_answer', 'N/A')}",
            "next_action": next_action,
            "points_earned": 10 if is_correct else 0
        }
    
    async def get_student_progress(
        self,
        db: AsyncSession,
        student_id: UUID,
        assignment_id: UUID
    ) -> Optional[LectureStudentProgress]:
        """Get detailed student progress"""
        return await self.get_or_create_student_progress(db, student_id, assignment_id)
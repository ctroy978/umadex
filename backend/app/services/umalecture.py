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
        # Create metadata JSON that includes learning objectives and other lecture-specific data
        metadata = {
            "learning_objectives": lecture_data.learning_objectives,
            "topic_outline": None,
            "lecture_structure": None,
            "processing_started_at": None,
            "processing_completed_at": None,
            "processing_error": None
        }
        
        # Insert into reading_assignments table with UMALecture type
        # Note: Due to schema constraints, we need to provide values for all NOT NULL fields
        query = sql_text("""
            INSERT INTO reading_assignments (
                teacher_id, assignment_title, work_title, subject, grade_level, 
                assignment_type, status, work_type, literary_form, genre, 
                raw_content, author
            ) VALUES (
                :teacher_id, :title, :title, :subject, :grade_level, 
                'UMALecture', 'draft', 'non-fiction', 'prose', 'educational',
                :metadata, 'Teacher'
            ) RETURNING *
        """)
        
        result = await db.execute(
            query,
            {
                "teacher_id": teacher_id,
                "title": lecture_data.title,
                "subject": lecture_data.subject,
                "grade_level": lecture_data.grade_level,
                "metadata": json.dumps(metadata)
            }
        )
        
        lecture = result.mappings().first()
        await db.commit()
        
        # Transform the result to match expected lecture format
        lecture_data = self._transform_to_lecture_format(dict(lecture))
        lecture_data["classroom_count"] = 0  # New lectures have no classrooms yet
        return lecture_data
    
    async def list_teacher_lectures(
        self,
        db: AsyncSession,
        teacher_id: UUID,
        skip: int = 0,
        limit: int = 100,
        status: Optional[str] = None,
        search: Optional[str] = None,
        include_archived: bool = False
    ) -> List[Dict[str, Any]]:
        """List lectures for a teacher with filtering"""
        query = """
            SELECT * FROM reading_assignments
            WHERE teacher_id = :teacher_id
            AND assignment_type = 'UMALecture'
        """
        
        # Only filter out archived if include_archived is False
        if not include_archived:
            query += " AND deleted_at IS NULL"
        
        params = {"teacher_id": teacher_id}
        
        if status:
            query += " AND status = :status"
            params["status"] = status
        
        if search:
            query += " AND (assignment_title ILIKE :search OR subject ILIKE :search)"
            params["search"] = f"%{search}%"
        
        query += " ORDER BY created_at DESC LIMIT :limit OFFSET :skip"
        params["limit"] = limit
        params["skip"] = skip
        
        result = await db.execute(sql_text(query), params)
        lectures = result.mappings().all()
        
        # Transform each lecture to expected format and add classroom count
        lecture_list = []
        for lecture in lectures:
            lecture_data = self._transform_to_lecture_format(dict(lecture))
            
            # Get classroom count
            from app.models.classroom import ClassroomAssignment
            from sqlalchemy import select, func, and_
            count_result = await db.execute(
                select(func.count(ClassroomAssignment.id))
                .where(
                    and_(
                        ClassroomAssignment.assignment_id == lecture_data["id"],
                        ClassroomAssignment.assignment_type == "UMALecture"
                    )
                )
            )
            classroom_count = count_result.scalar() or 0
            lecture_data["classroom_count"] = classroom_count
            
            lecture_list.append(lecture_data)
        
        return lecture_list
    
    async def get_lecture(
        self, 
        db: AsyncSession, 
        lecture_id: UUID, 
        teacher_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get a specific lecture assignment"""
        query = sql_text("""
            SELECT * FROM reading_assignments
            WHERE id = :lecture_id 
            AND teacher_id = :teacher_id
            AND assignment_type = 'UMALecture'
            AND deleted_at IS NULL
        """)
        
        result = await db.execute(
            query,
            {"lecture_id": lecture_id, "teacher_id": teacher_id}
        )
        
        lecture = result.mappings().first()
        if not lecture:
            return None
            
        lecture_data = self._transform_to_lecture_format(dict(lecture))
        
        # Get classroom count
        from app.models.classroom import ClassroomAssignment
        from sqlalchemy import select, func, and_
        count_result = await db.execute(
            select(func.count(ClassroomAssignment.id))
            .where(
                and_(
                    ClassroomAssignment.assignment_id == lecture_data["id"],
                    ClassroomAssignment.assignment_type == "UMALecture"
                )
            )
        )
        classroom_count = count_result.scalar() or 0
        lecture_data["classroom_count"] = classroom_count
        
        return lecture_data
    
    async def update_lecture(
        self,
        db: AsyncSession,
        lecture_id: UUID,
        teacher_id: UUID,
        update_data: LectureAssignmentUpdate
    ) -> Optional[Dict[str, Any]]:
        """Update a lecture assignment"""
        # Get current lecture to preserve metadata
        current = await self.get_lecture(db, lecture_id, teacher_id)
        if not current:
            return None
        
        # Update metadata
        metadata = json.loads(current.get("raw_content", "{}"))
        
        # Build update query dynamically
        update_fields = []
        params = {"lecture_id": lecture_id, "teacher_id": teacher_id}
        
        if update_data.title is not None:
            update_fields.append("assignment_title = :title")
            update_fields.append("work_title = :title")
            params["title"] = update_data.title
        
        if update_data.subject is not None:
            update_fields.append("subject = :subject")
            params["subject"] = update_data.subject
        
        if update_data.grade_level is not None:
            update_fields.append("grade_level = :grade_level")
            params["grade_level"] = update_data.grade_level
        
        # Update metadata fields
        metadata_updated = False
        if update_data.learning_objectives is not None:
            metadata["learning_objectives"] = update_data.learning_objectives
            metadata_updated = True
        
        if update_data.topic_outline is not None:
            metadata["topic_outline"] = update_data.topic_outline
            metadata_updated = True
        
        if update_data.lecture_structure is not None:
            metadata["lecture_structure"] = update_data.lecture_structure
            metadata_updated = True
        
        if metadata_updated:
            update_fields.append("raw_content = :metadata")
            params["metadata"] = json.dumps(metadata)
        
        if not update_fields:
            return await self.get_lecture(db, lecture_id, teacher_id)
        
        query = sql_text(f"""
            UPDATE reading_assignments
            SET {', '.join(update_fields)}, updated_at = NOW()
            WHERE id = :lecture_id 
            AND teacher_id = :teacher_id
            AND assignment_type = 'UMALecture'
            AND deleted_at IS NULL
            RETURNING *
        """)
        
        result = await db.execute(query, params)
        lecture = result.mappings().first()
        await db.commit()
        
        if not lecture:
            return None
            
        lecture_data = self._transform_to_lecture_format(dict(lecture))
        
        # Get classroom count
        from app.models.classroom import ClassroomAssignment
        from sqlalchemy import select, func, and_
        count_result = await db.execute(
            select(func.count(ClassroomAssignment.id))
            .where(
                and_(
                    ClassroomAssignment.assignment_id == lecture_data["id"],
                    ClassroomAssignment.assignment_type == "UMALecture"
                )
            )
        )
        classroom_count = count_result.scalar() or 0
        lecture_data["classroom_count"] = classroom_count
        
        return lecture_data
    
    async def delete_lecture(
        self, 
        db: AsyncSession, 
        lecture_id: UUID, 
        teacher_id: UUID
    ) -> bool:
        """Soft delete a lecture assignment"""
        query = sql_text("""
            UPDATE reading_assignments
            SET deleted_at = NOW()
            WHERE id = :lecture_id 
            AND teacher_id = :teacher_id
            AND assignment_type = 'UMALecture'
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
            UPDATE reading_assignments
            SET deleted_at = NULL
            WHERE id = :lecture_id 
            AND teacher_id = :teacher_id
            AND assignment_type = 'UMALecture'
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
        # Get current metadata
        get_query = sql_text("""
            SELECT raw_content FROM reading_assignments
            WHERE id = :lecture_id
            AND assignment_type = 'UMALecture'
        """)
        
        result = await db.execute(get_query, {"lecture_id": lecture_id})
        data = result.mappings().first()
        if not data:
            return False
        
        metadata = json.loads(data["raw_content"] or "{}")
        
        # Update metadata based on status
        if status == "processing":
            metadata["processing_started_at"] = datetime.utcnow().isoformat()
            metadata["processing_error"] = None
        elif status == "published":
            metadata["processing_completed_at"] = datetime.utcnow().isoformat()
        elif status == "draft" and error:
            metadata["processing_error"] = error
        
        # Update in database
        update_query = sql_text("""
            UPDATE reading_assignments
            SET status = :status,
                raw_content = :metadata,
                updated_at = NOW()
            WHERE id = :lecture_id
            AND assignment_type = 'UMALecture'
            RETURNING id
        """)
        
        result = await db.execute(
            update_query,
            {
                "lecture_id": lecture_id,
                "status": status,
                "metadata": json.dumps(metadata)
            }
        )
        
        updated = result.scalar()
        await db.commit()
        
        return bool(updated)
    
    async def create_image_reference(
        self,
        db: AsyncSession,
        lecture_id: UUID,
        filename: str,
        storage_path: str,
        public_url: str,
        teacher_description: str,
        node_id: str,
        position: int
    ) -> Dict[str, Any]:
        """Create a reference to an image stored in Supabase Storage"""
        import uuid
        
        # Insert into database
        query = sql_text("""
            INSERT INTO lecture_images (
                id, lecture_id, filename, teacher_description,
                node_id, position, storage_path, public_url,
                original_url, display_url, created_at
            ) VALUES (
                :id, :lecture_id, :filename, :teacher_description,
                :node_id, :position, :storage_path, :public_url,
                :public_url, :public_url, NOW()
            )
            RETURNING *
        """)
        
        result = await db.execute(
            query,
            {
                "id": str(uuid.uuid4()),
                "lecture_id": lecture_id,
                "filename": filename,
                "teacher_description": teacher_description,
                "node_id": node_id,
                "position": position,
                "storage_path": storage_path,
                "public_url": public_url
            }
        )
        
        image = result.mappings().first()
        await db.commit()
        
        return dict(image)
    
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
        # Use the same validation and processing as reading assignments
        try:
            # Process image using the same method as reading assignments
            processed_data = await self.image_processor.validate_and_process_image(
                file=file,
                assignment_id=str(lecture_id),
                image_number=position
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
                    "filename": processed_data["image_key"],
                    "teacher_description": teacher_description,
                    "node_id": node_id,
                    "position": position,
                    "original_url": processed_data["original_url"],
                    "display_url": processed_data["display_url"],
                    "thumbnail_url": processed_data["thumbnail_url"],
                    "file_size": processed_data["file_size"],
                    "mime_type": processed_data["mime_type"]
                }
            )
            
            image = result.mappings().first()
            await db.commit()
            
            return dict(image)
        except Exception as e:
            raise e
    
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
            SELECT 1 FROM reading_assignments
            WHERE id = :lecture_id 
            AND teacher_id = :teacher_id
            AND assignment_type = 'UMALecture'
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
        # Get current metadata
        current = await self.get_lecture(db, lecture_id, teacher_id)
        if not current:
            return False
        
        metadata = json.loads(current.get("raw_content", "{}"))
        metadata["lecture_structure"] = structure
        
        query = sql_text("""
            UPDATE reading_assignments
            SET raw_content = :metadata,
                updated_at = NOW()
            WHERE id = :lecture_id 
            AND teacher_id = :teacher_id
            AND assignment_type = 'UMALecture'
            AND deleted_at IS NULL
            RETURNING id
        """)
        
        result = await db.execute(
            query,
            {
                "lecture_id": lecture_id,
                "teacher_id": teacher_id,
                "metadata": json.dumps(metadata)
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
        current = await self.get_lecture(db, lecture_id, teacher_id)
        if not current:
            return False
        
        metadata = json.loads(current.get("raw_content", "{}"))
        if not metadata.get("lecture_structure"):
            return False
        
        query = sql_text("""
            UPDATE reading_assignments
            SET status = 'published',
                updated_at = NOW()
            WHERE id = :lecture_id 
            AND teacher_id = :teacher_id
            AND assignment_type = 'UMALecture'
            AND deleted_at IS NULL
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
                    :classroom_id, :assignment_id, 'UMALecture'
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
        assignment_id: int
    ) -> LectureStudentProgress:
        """Get or create student progress for a lecture"""
        # First check if student assignment exists
        query = (
            select(StudentAssignment)
            .where(
                and_(
                    StudentAssignment.student_id == student_id,
                    StudentAssignment.classroom_assignment_id == assignment_id
                )
            )
        )
        
        result = await db.execute(query)
        student_assignment = result.scalar_one_or_none()
        
        if not student_assignment:
            # Create student assignment if it doesn't exist
            # First get the classroom assignment and reading assignment
            ca_query = (
                select(ClassroomAssignment, ReadingAssignment)
                .join(ReadingAssignment, ClassroomAssignment.assignment_id == ReadingAssignment.id)
                .where(
                    and_(
                        ClassroomAssignment.id == assignment_id,
                        or_(
                            ClassroomAssignment.assignment_type == "UMALecture",
                            ClassroomAssignment.assignment_type == "lecture"
                        )
                    )
                )
            )
            
            ca_result = await db.execute(ca_query)
            ca_row = ca_result.first()
            
            if not ca_row:
                raise ValueError("Classroom assignment not found")
            
            classroom_assignment, reading_assignment = ca_row
            
            # Extract the lecture ID before any session operations
            lecture_id = reading_assignment.id
            
            # Create new student assignment
            try:
                student_assignment = StudentAssignment(
                    student_id=student_id,
                    assignment_id=lecture_id,
                    classroom_assignment_id=assignment_id,
                    assignment_type="UMALecture",
                    status="in_progress",
                    started_at=datetime.utcnow(),
                    progress_metadata={
                        "lecture_path": [],
                        "topic_progress": {},
                        "total_points": 0
                    }
                )
                db.add(student_assignment)
                await db.commit()
                await db.refresh(student_assignment)
            except Exception as e:
                # Handle duplicate key constraint - fetch the existing record
                await db.rollback()
                result = await db.execute(query)
                student_assignment = result.scalar_one_or_none()
                if not student_assignment:
                    raise e  # Re-raise if it's a different error
        else:
            # Get the lecture ID from the assignment
            lecture_id = student_assignment.assignment_id
        
        # Initialize progress if needed
        progress_metadata = student_assignment.progress_metadata or {}
        if "lecture_path" not in progress_metadata:
            progress_metadata["lecture_path"] = []
            progress_metadata["topic_progress"] = {}
            progress_metadata["total_points"] = 0
            
            # Update using SQLAlchemy
            student_assignment.progress_metadata = progress_metadata
            if not student_assignment.started_at:
                student_assignment.started_at = datetime.utcnow()
            
            await db.execute(
                update(StudentAssignment)
                .where(StudentAssignment.id == student_assignment.id)
                .values(
                    progress_metadata=progress_metadata,
                    started_at=StudentAssignment.started_at or datetime.utcnow()
                )
            )
            await db.commit()
        
        return LectureStudentProgress(
            assignment_id=assignment_id,
            lecture_id=lecture_id,
            current_topic=progress_metadata.get("current_topic"),
            current_difficulty=progress_metadata.get("current_difficulty"),
            topics_completed=progress_metadata.get("topics_completed", []),
            topic_progress=progress_metadata.get("topic_progress", {}),
            total_points=progress_metadata.get("total_points", 0),
            last_activity_at=student_assignment.last_activity_at,
            started_at=student_assignment.started_at,
            completed_at=student_assignment.completed_at
        )
    
    async def get_lecture_topics(
        self,
        db: AsyncSession,
        assignment_id: int,
        student_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get available topics for a lecture"""
        # Get lecture structure and student progress
        query = sql_text("""
            SELECT ra.raw_content, sa.progress_metadata
            FROM reading_assignments ra
            JOIN classroom_assignments ca ON ca.assignment_id = ra.id
            LEFT JOIN student_assignments sa ON sa.classroom_assignment_id = ca.id
                AND sa.student_id = :student_id
            WHERE ca.id = :assignment_id
            AND ca.assignment_type = 'UMALecture'
        """)
        
        result = await db.execute(
            query,
            {"assignment_id": assignment_id, "student_id": student_id}
        )
        
        data = result.mappings().first()
        if not data:
            return []
        
        metadata = json.loads(data.get("raw_content", "{}"))
        structure = metadata.get("lecture_structure", {})
        if not structure:
            return []
        
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
        assignment_id: int,
        topic_id: str,
        difficulty: str,
        student_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get content for a specific topic and difficulty"""
        # Get lecture structure and images
        query = sql_text("""
            SELECT ra.raw_content, ra.id as lecture_id
            FROM reading_assignments ra
            JOIN classroom_assignments ca ON ca.assignment_id = ra.id
            WHERE ca.id = :assignment_id
            AND ca.assignment_type = 'UMALecture'
        """)
        
        result = await db.execute(
            query,
            {"assignment_id": assignment_id}
        )
        
        data = result.mappings().first()
        if not data:
            return None
        
        metadata = json.loads(data.get("raw_content", "{}"))
        structure = metadata.get("lecture_structure", {})
        if not structure:
            return None
        
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
        assignment_id: int,
        topic_id: str,
        difficulty: str,
        interaction_type: str,
        question_text: Optional[str] = None,
        student_answer: Optional[str] = None,
        is_correct: Optional[bool] = None
    ) -> None:
        """Track student interaction with lecture content"""
        # Get lecture ID
        lecture_query = sql_text("""
            SELECT ra.id as lecture_id
            FROM reading_assignments ra
            JOIN classroom_assignments ca ON ca.assignment_id = ra.id
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
            "question_text": question_text,
            "student_answer": student_answer,
            "is_correct": is_correct,
            "time_spent": 0
        }
        
        await db.execute(insert_query, params)
        
        # Update progress metadata
        if interaction_type == "answer_question" and is_correct:
            update_query = sql_text("""
                UPDATE student_assignments
                SET progress_metadata = jsonb_set(
                    COALESCE(progress_metadata, '{}'::jsonb),
                    '{total_points}',
                    to_jsonb(COALESCE((progress_metadata->>'total_points')::int, 0) + :points)
                ),
                last_activity_at = NOW()
                WHERE classroom_assignment_id = :assignment_id
            """)
            
            await db.execute(
                update_query,
                {
                    "assignment_id": assignment_id,
                    "points": 1  # Default points
                }
            )
        
        await db.commit()
    
    async def submit_answer(
        self,
        db: AsyncSession,
        student_id: UUID,
        assignment_id: int,
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
            question["question"], answer, is_correct
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
                WHERE classroom_assignment_id = :assignment_id
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
        
        # If this was the last question in a difficulty level and all were correct,
        # update the student progress to trigger grade calculation
        if is_correct and next_action in ["next_difficulty", "complete_topic"]:
            # Call update_student_progress to trigger grade calculation
            await self.update_student_progress(
                db, student_id, assignment_id, topic_id, difficulty, 
                question_index, is_correct
            )
        
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
    
    async def verify_student_access(
        self,
        db: AsyncSession,
        student_id: UUID,
        assignment_id: int,
        lecture_id: UUID
    ) -> bool:
        """Verify student has access to a lecture through assignment"""
        query = sql_text("""
            SELECT 1
            FROM classroom_assignments ca
            JOIN reading_assignments ra ON ra.id = ca.assignment_id
            LEFT JOIN student_assignments sa ON sa.classroom_assignment_id = ca.id
                AND sa.student_id = :student_id
            WHERE ca.id = :assignment_id
            AND ra.id = :lecture_id
            AND ca.assignment_type IN ('UMALecture', 'lecture')
        """)
        
        result = await db.execute(
            query,
            {
                "student_id": student_id,
                "assignment_id": assignment_id,
                "lecture_id": lecture_id
            }
        )
        
        return bool(result.scalar())
    
    async def verify_student_assignment_access(
        self,
        db: AsyncSession,
        student_id: UUID,
        assignment_id: int
    ) -> bool:
        """Verify student has access to an assignment"""
        query = sql_text("""
            SELECT 1
            FROM student_assignments sa
            WHERE sa.student_id = :student_id
            AND sa.classroom_assignment_id = :assignment_id
        """)
        
        result = await db.execute(
            query,
            {"student_id": student_id, "assignment_id": assignment_id}
        )
        
        return bool(result.scalar())
    
    async def get_lecture_for_student(
        self,
        db: AsyncSession,
        lecture_id: UUID,
        assignment_id: int,
        student_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get lecture data with student progress for student view"""
        # Get lecture and progress
        query = sql_text("""
            SELECT 
                ra.*,
                sa.progress_metadata
            FROM reading_assignments ra
            JOIN classroom_assignments ca ON ca.assignment_id = ra.id
            JOIN student_assignments sa ON sa.classroom_assignment_id = ca.id
            WHERE ra.id = :lecture_id
            AND ca.id = :assignment_id
            AND sa.student_id = :student_id
        """)
        
        result = await db.execute(
            query,
            {
                "lecture_id": lecture_id,
                "assignment_id": assignment_id,
                "student_id": student_id
            }
        )
        
        data = result.mappings().first()
        if not data:
            return None
        
        # Transform to lecture format
        lecture_data = self._transform_to_lecture_format(dict(data))
        
        # Get all images for the lecture
        image_query = sql_text("""
            SELECT * FROM lecture_images
            WHERE lecture_id = :lecture_id
            ORDER BY node_id, position
        """)
        
        image_result = await db.execute(image_query, {"lecture_id": lecture_id})
        images = [dict(img) for img in image_result.mappings().all()]
        
        # Group images by topic
        images_by_topic = {}
        for img in images:
            topic_id = img["node_id"]
            if topic_id not in images_by_topic:
                images_by_topic[topic_id] = []
            images_by_topic[topic_id].append(img)
        
        return {
            **lecture_data,
            "images_by_topic": images_by_topic,
            "progress_metadata": data["progress_metadata"] or self._initialize_progress_metadata()
        }
    
    async def get_all_topic_content(
        self,
        db: AsyncSession,
        lecture_id: UUID,
        topic_id: str,
        student_id: UUID,
        assignment_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get all difficulty levels content for a topic"""
        # Clean topic_id by removing trailing periods
        topic_id = topic_id.rstrip('.')
        
        # Get lecture structure
        lecture_query = sql_text("""
            SELECT raw_content
            FROM reading_assignments
            WHERE id = :lecture_id
            AND assignment_type = 'UMALecture'
        """)
        
        result = await db.execute(lecture_query, {"lecture_id": lecture_id})
        data = result.mappings().first()
        
        if not data:
            return None
        
        metadata = json.loads(data.get("raw_content", "{}"))
        structure = metadata.get("lecture_structure", {})
        if not structure:
            return None
        
        topic_data = structure.get("topics", {}).get(topic_id)
        if not topic_data:
            return None
        
        # Get all images for this topic
        # We need to match the node_id which might have different formatting than topic_id
        # Try to find images by matching the topic title from the structure
        topic_title = topic_data.get("title", "")
        
        image_query = sql_text("""
            SELECT * FROM lecture_images
            WHERE lecture_id = :lecture_id
            AND (
                node_id = :topic_id 
                OR node_id = :topic_title
                OR LOWER(REPLACE(node_id, ' ', '_')) = LOWER(:topic_id)
                OR LOWER(node_id) = LOWER(:topic_title)
                OR LOWER(REPLACE(REPLACE(node_id, ':', ''), ' ', '_')) = LOWER(:topic_id)
                OR LOWER(REPLACE(node_id, ':', '')) = LOWER(REPLACE(:topic_title, ':', ''))
            )
            ORDER BY position
        """)
        
        image_result = await db.execute(
            image_query,
            {
                "lecture_id": lecture_id, 
                "topic_id": topic_id,
                "topic_title": topic_title
            }
        )
        
        images = [dict(img) for img in image_result.mappings().all()]
        
        # Get student progress for this topic
        progress_query = sql_text("""
            SELECT progress_metadata
            FROM student_assignments
            WHERE classroom_assignment_id = :assignment_id
            AND student_id = :student_id
        """)
        
        progress_result = await db.execute(
            progress_query,
            {"assignment_id": assignment_id, "student_id": student_id}
        )
        
        progress_data = progress_result.mappings().first()
        progress_metadata = progress_data["progress_metadata"] if progress_data else {}
        topic_progress = progress_metadata.get("topic_completion", {}).get(topic_id, {})
        
        return {
            "id": topic_id,
            "topic_id": topic_id,
            "title": topic_data.get("title", ""),
            "difficulty_levels": topic_data.get("difficulty_levels", {}),
            "images": images,
            "completed_tabs": topic_progress.get("completed_tabs", []),
            "questions_correct": topic_progress.get("questions_correct", {})
        }
    
    async def get_image_with_description(
        self,
        db: AsyncSession,
        image_id: UUID,
        lecture_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """Get image with AI-generated educational description"""
        query = sql_text("""
            SELECT * FROM lecture_images
            WHERE id = :image_id
            AND lecture_id = :lecture_id
        """)
        
        result = await db.execute(
            query,
            {"image_id": image_id, "lecture_id": lecture_id}
        )
        
        image = result.mappings().first()
        return dict(image) if image else None
    
    async def update_student_progress(
        self,
        db: AsyncSession,
        student_id: UUID,
        assignment_id: int,
        topic_id: str,
        tab: str,
        question_index: Optional[int],
        is_correct: Optional[bool]
    ) -> Optional[Dict[str, Any]]:
        """Update student progress for topic/tab/question"""
        # Clean topic_id by removing trailing periods
        topic_id = topic_id.rstrip('.')
        
        # Get current progress
        progress_query = sql_text("""
            SELECT id, progress_metadata
            FROM student_assignments
            WHERE classroom_assignment_id = :assignment_id
            AND student_id = :student_id
        """)
        
        result = await db.execute(
            progress_query,
            {"assignment_id": assignment_id, "student_id": student_id}
        )
        
        data = result.mappings().first()
        if not data:
            return None
        
        progress_metadata = data["progress_metadata"] or self._initialize_progress_metadata()
        
        # Initialize topic completion if needed
        if "topic_completion" not in progress_metadata:
            progress_metadata["topic_completion"] = {}
        
        if topic_id not in progress_metadata["topic_completion"]:
            progress_metadata["topic_completion"][topic_id] = {
                "completed_tabs": [],
                "completed_at": None,
                "questions_correct": {}
            }
        
        topic_progress = progress_metadata["topic_completion"][topic_id]
        
        # Update question correctness if provided
        if question_index is not None and is_correct is not None:
            if tab not in topic_progress["questions_correct"]:
                topic_progress["questions_correct"][tab] = []
            
            # Ensure list is long enough
            while len(topic_progress["questions_correct"][tab]) <= question_index:
                topic_progress["questions_correct"][tab].append(False)
            
            topic_progress["questions_correct"][tab][question_index] = is_correct
            
            # Check if tab is complete (all questions correct)
            if all(topic_progress["questions_correct"][tab]):
                if tab not in topic_progress["completed_tabs"]:
                    topic_progress["completed_tabs"].append(tab)
                    if not topic_progress["completed_at"]:
                        topic_progress["completed_at"] = datetime.utcnow().isoformat()
        
        # Update current position
        progress_metadata["current_topic"] = topic_id
        progress_metadata["current_tab"] = tab
        
        # Check if lecture is complete
        progress_metadata["lecture_complete"] = self._check_lecture_complete(progress_metadata)
        
        # Update in database
        update_query = sql_text("""
            UPDATE student_assignments
            SET progress_metadata = :metadata,
                updated_at = NOW()
            WHERE classroom_assignment_id = :assignment_id
            AND student_id = :student_id
        """)
        
        await db.execute(
            update_query,
            {
                "metadata": json.dumps(progress_metadata),
                "assignment_id": assignment_id,
                "student_id": student_id
            }
        )
        
        await db.commit()
        
        # After updating progress, calculate and update grade if a difficulty level was completed
        if question_index is not None and is_correct is not None and all(topic_progress["questions_correct"][tab]):
            # Get lecture ID
            lecture_query = sql_text("""
                SELECT ca.assignment_id as lecture_id
                FROM classroom_assignments ca
                WHERE ca.id = :assignment_id
                AND ca.assignment_type = 'UMALecture'
            """)
            
            result = await db.execute(
                lecture_query,
                {"assignment_id": assignment_id}
            )
            
            lecture_data = result.mappings().first()
            if lecture_data:
                # Calculate current grade
                grade = await self.calculate_lecture_grade(db, student_id, assignment_id)
                if grade is not None:
                    # Update gradebook
                    await self.create_or_update_gradebook_entry(
                        db, student_id, assignment_id, lecture_data["lecture_id"], grade
                    )
        
        return progress_metadata
    
    async def evaluate_student_response(
        self,
        question_text: str,
        student_answer: str,
        expected_answer: str,
        difficulty: str,
        includes_images: bool = False,
        image_descriptions: List[str] = None
    ) -> Dict[str, Any]:
        """Evaluate student response using AI"""
        from app.services.umalecture_ai import UMALectureAIService
        
        ai_service = UMALectureAIService()
        
        # Build context for evaluation
        context = f"Difficulty Level: {difficulty}\n"
        context += f"Question: {question_text}\n"
        
        if includes_images and image_descriptions:
            context += "\nImage Context:\n"
            for i, desc in enumerate(image_descriptions):
                context += f"Image {i+1}: {desc}\n"
        
        if expected_answer:
            context += f"\nExpected Answer Guidance: {expected_answer}\n"
        
        # Get AI evaluation
        evaluation = await ai_service.evaluate_student_answer(
            context=context,
            student_answer=student_answer,
            difficulty=difficulty
        )
        
        return evaluation
    
    async def update_current_position(
        self,
        db: AsyncSession,
        assignment_id: int,
        student_id: UUID,
        current_topic: Optional[str],
        current_tab: Optional[str]
    ) -> bool:
        """Update student's current position in lecture"""
        # Clean topic_id by removing trailing periods
        if current_topic:
            current_topic = current_topic.rstrip('.')
        
        # Get current progress
        progress_query = sql_text("""
            SELECT progress_metadata
            FROM student_assignments
            WHERE classroom_assignment_id = :assignment_id
            AND student_id = :student_id
        """)
        
        result = await db.execute(
            progress_query,
            {"assignment_id": assignment_id, "student_id": student_id}
        )
        
        data = result.mappings().first()
        if not data:
            return False
        
        progress_metadata = data["progress_metadata"] or self._initialize_progress_metadata()
        
        # Update position
        if current_topic:
            progress_metadata["current_topic"] = current_topic
        if current_tab:
            progress_metadata["current_tab"] = current_tab
        
        # Update in database
        update_query = sql_text("""
            UPDATE student_assignments
            SET progress_metadata = :metadata,
                updated_at = NOW()
            WHERE classroom_assignment_id = :assignment_id
            AND student_id = :student_id
        """)
        
        await db.execute(
            update_query,
            {
                "metadata": json.dumps(progress_metadata),
                "assignment_id": assignment_id,
                "student_id": student_id
            }
        )
        
        await db.commit()
        
        return True
    
    def _initialize_progress_metadata(self) -> Dict[str, Any]:
        """Initialize empty progress metadata structure"""
        return {
            "topic_completion": {},
            "current_topic": None,
            "current_tab": None,
            "lecture_complete": False
        }
    
    def _check_lecture_complete(self, progress_metadata: Dict[str, Any]) -> bool:
        """Check if lecture is complete (all topics have at least one completed tab)"""
        topic_completion = progress_metadata.get("topic_completion", {})
        
        if not topic_completion:
            return False
        
        # For now, just check if any topics have completed tabs
        # In production, we'd check against the actual lecture structure
        for topic_id, progress in topic_completion.items():
            if progress.get("completed_tabs"):
                return True
        
        return False
    
    def _transform_to_lecture_format(self, reading_assignment: Dict[str, Any]) -> Dict[str, Any]:
        """Transform reading_assignments row to lecture format"""
        # Parse metadata from raw_content
        metadata = json.loads(reading_assignment.get("raw_content", "{}"))
        
        return {
            "id": reading_assignment["id"],
            "teacher_id": reading_assignment["teacher_id"],
            "title": reading_assignment["assignment_title"],
            "subject": reading_assignment["subject"],
            "grade_level": reading_assignment["grade_level"],
            "learning_objectives": metadata.get("learning_objectives", []),
            "topic_outline": metadata.get("topic_outline"),
            "lecture_structure": metadata.get("lecture_structure"),
            "status": reading_assignment["status"],
            "processing_started_at": metadata.get("processing_started_at"),
            "processing_completed_at": metadata.get("processing_completed_at"),
            "processing_error": metadata.get("processing_error"),
            "created_at": reading_assignment["created_at"],
            "updated_at": reading_assignment["updated_at"],
            "deleted_at": reading_assignment["deleted_at"],
            "raw_content": reading_assignment["raw_content"]  # Keep original for reference
        }
    
    async def validate_exploration_question(
        self,
        exploration_term: str,
        student_question: str
    ) -> bool:
        """Validate if a student's question is on-topic for the exploration term"""
        from app.services.umalecture_ai import UMALectureAIService
        from app.services.umalecture_prompts import UMALecturePromptManager
        
        ai_service = UMALectureAIService()
        prompt = UMALecturePromptManager.get_exploration_validation_prompt(
            exploration_term, student_question
        )
        
        response = await ai_service._generate_content_async(prompt)
        return response.strip().upper() == "ON_TOPIC"
    
    async def generate_exploration_explanation(
        self,
        exploration_term: str,
        difficulty_level: str,
        grade_level: str,
        lecture_context: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """Generate initial explanation for an exploration term"""
        from app.services.umalecture_ai import UMALectureAIService
        from app.services.umalecture_prompts import UMALecturePromptManager
        
        ai_service = UMALectureAIService()
        prompt = UMALecturePromptManager.get_exploration_response_prompt(
            exploration_term=exploration_term,
            student_question=None,
            lecture_context=lecture_context,
            conversation_history=conversation_history,
            difficulty_level=difficulty_level,
            grade_level=grade_level
        )
        
        return await ai_service._generate_content_async(prompt)
    
    async def generate_exploration_response(
        self,
        exploration_term: str,
        student_question: str,
        difficulty_level: str,
        grade_level: str,
        lecture_context: str,
        conversation_history: List[Dict[str, str]]
    ) -> str:
        """Generate response to a student's on-topic question"""
        from app.services.umalecture_ai import UMALectureAIService
        from app.services.umalecture_prompts import UMALecturePromptManager
        
        ai_service = UMALectureAIService()
        prompt = UMALecturePromptManager.get_exploration_response_prompt(
            exploration_term=exploration_term,
            student_question=student_question,
            lecture_context=lecture_context,
            conversation_history=conversation_history,
            difficulty_level=difficulty_level,
            grade_level=grade_level
        )
        
        return await ai_service._generate_content_async(prompt)
    
    async def generate_exploration_redirect(
        self,
        exploration_term: str,
        student_question: str
    ) -> str:
        """Generate redirect message for off-topic questions"""
        from app.services.umalecture_ai import UMALectureAIService
        from app.services.umalecture_prompts import UMALecturePromptManager
        
        ai_service = UMALectureAIService()
        prompt = UMALecturePromptManager.get_exploration_redirect_prompt(
            exploration_term, student_question
        )
        
        return await ai_service._generate_content_async(prompt)
    
    async def calculate_lecture_grade(
        self,
        db: AsyncSession,
        student_id: UUID,
        assignment_id: int
    ) -> Optional[int]:
        """Calculate student's grade based on highest difficulty level completed
        
        Grading scale:
        - Basic completed: 70%
        - Intermediate completed: 80%
        - Advanced completed: 90%
        - Expert completed: 100%
        """
        # Get student progress
        progress_query = sql_text("""
            SELECT sa.progress_metadata, la.raw_content
            FROM student_assignments sa
            JOIN classroom_assignments ca ON ca.id = sa.classroom_assignment_id
            JOIN reading_assignments la ON la.id = ca.assignment_id
            WHERE sa.classroom_assignment_id = :assignment_id
            AND sa.student_id = :student_id
            AND ca.assignment_type = 'UMALecture'
        """)
        
        result = await db.execute(
            progress_query,
            {"assignment_id": assignment_id, "student_id": student_id}
        )
        
        data = result.mappings().first()
        if not data or not data["progress_metadata"]:
            return None
        
        progress_metadata = data["progress_metadata"]
        # Parse lecture structure from raw_content
        raw_content = json.loads(data["raw_content"]) if isinstance(data["raw_content"], str) else data["raw_content"]
        lecture_structure = raw_content.get("lecture_structure", {}) if raw_content else {}
        
        # Get topic completion data
        topic_completion = progress_metadata.get("topic_completion", {})
        if not topic_completion:
            return None
        
        # Define difficulty levels and their scores
        difficulty_scores = {
            "basic": 70,
            "intermediate": 80,
            "advanced": 90,
            "expert": 100
        }
        
        # Find highest completed difficulty across all topics
        highest_score = 0
        
        for topic_id, topic_progress in topic_completion.items():
            completed_tabs = topic_progress.get("completed_tabs", [])
            questions_correct = topic_progress.get("questions_correct", {})
            
            # Check each difficulty level
            for difficulty in ["expert", "advanced", "intermediate", "basic"]:
                if difficulty in completed_tabs:
                    # For expert level, verify all questions were answered correctly
                    if difficulty == "expert":
                        expert_questions = questions_correct.get("expert", [])
                        if expert_questions and all(expert_questions):
                            highest_score = max(highest_score, difficulty_scores[difficulty])
                            break
                    else:
                        # For other levels, being in completed_tabs means all questions were correct
                        highest_score = max(highest_score, difficulty_scores[difficulty])
                        break
        
        return highest_score if highest_score > 0 else None
    
    async def create_or_update_gradebook_entry(
        self,
        db: AsyncSession,
        student_id: UUID,
        assignment_id: int,
        lecture_id: UUID,
        score: int
    ) -> None:
        """Create or update gradebook entry for UMALecture"""
        # Get classroom information
        classroom_query = sql_text("""
            SELECT ca.classroom_id, c.name as classroom_name,
                   la.assignment_title as assignment_name
            FROM classroom_assignments ca
            JOIN classrooms c ON c.id = ca.classroom_id
            JOIN reading_assignments la ON la.id = ca.assignment_id
            WHERE ca.id = :assignment_id
            AND ca.assignment_type = 'UMALecture'
        """)
        
        result = await db.execute(
            classroom_query,
            {"assignment_id": assignment_id}
        )
        
        classroom_data = result.mappings().first()
        if not classroom_data:
            return
        
        # Check if gradebook entry exists
        existing_query = sql_text("""
            SELECT id, score_percentage
            FROM gradebook_entries
            WHERE student_id = :student_id
            AND classroom_id = :classroom_id
            AND assignment_type = 'umalecture'
            AND assignment_id = :lecture_id
        """)
        
        existing_result = await db.execute(
            existing_query,
            {
                "student_id": student_id,
                "classroom_id": classroom_data["classroom_id"],
                "lecture_id": lecture_id
            }
        )
        
        existing_entry = existing_result.mappings().first()
        
        if existing_entry:
            # Update existing entry if new score is higher
            if score > existing_entry["score_percentage"]:
                update_query = sql_text("""
                    UPDATE gradebook_entries
                    SET score_percentage = :score,
                        points_earned = :score,
                        points_possible = 100,
                        completed_at = NOW(),
                        updated_at = NOW()
                    WHERE id = :entry_id
                """)
                
                await db.execute(
                    update_query,
                    {
                        "score": score,
                        "entry_id": existing_entry["id"]
                    }
                )
        else:
            # Create new gradebook entry
            insert_query = sql_text("""
                INSERT INTO gradebook_entries (
                    student_id, classroom_id, assignment_type, assignment_id,
                    score_percentage, points_earned, points_possible,
                    completed_at, metadata
                ) VALUES (
                    :student_id, :classroom_id, 'umalecture', :lecture_id,
                    :score, :score, 100, NOW(), :metadata
                )
            """)
            
            metadata = {
                "assignment_name": classroom_data["assignment_name"],
                "classroom_name": classroom_data["classroom_name"]
            }
            
            await db.execute(
                insert_query,
                {
                    "student_id": student_id,
                    "classroom_id": classroom_data["classroom_id"],
                    "lecture_id": lecture_id,
                    "score": score,
                    "metadata": json.dumps(metadata)
                }
            )
        
        await db.commit()
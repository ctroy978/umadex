"""
UMALecture API endpoints for teachers and students
"""
from typing import List, Optional, Dict, Any
from uuid import UUID
import uuid
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select, and_, func, or_, update, delete as sql_delete
from datetime import datetime
import json

from app.core.database import get_db
from app.models.user import User, UserRole
from app.models.classroom import StudentAssignment, ClassroomAssignment
from app.models.reading import ReadingAssignment
from app.utils.deps import get_current_user
from app.schemas.umalecture import (
    LectureAssignmentCreate,
    LectureAssignmentResponse,
    LectureAssignmentUpdate,
    LectureImageUpload,
    LectureImageResponse,
    LectureProcessingStatus,
    LectureContentResponse,
    LectureStudentProgress,
    LectureTopicResponse
)
from app.services.umalecture import UMALectureService
from app.services.umalecture_ai import UMALectureAIService
from app.services.image_processing import ImageProcessor

router = APIRouter(prefix="/umalecture", tags=["umalecture"])

# Initialize services
lecture_service = UMALectureService()
lecture_ai_service = UMALectureAIService()
image_processor = ImageProcessor()


def require_teacher(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be a teacher"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this resource"
        )
    return current_user


def require_student(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be a student"""
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can access this resource"
        )
    return current_user


# Teacher Endpoints
@router.post("/lectures", response_model=LectureAssignmentResponse)
async def create_lecture(
    lecture_data: LectureAssignmentCreate,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Create a new lecture assignment"""
    return await lecture_service.create_lecture(db, teacher.id, lecture_data)


@router.get("/lectures", response_model=List[LectureAssignmentResponse])
async def list_lectures(
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    search: Optional[str] = None
):
    """List teacher's lecture assignments"""
    return await lecture_service.list_teacher_lectures(
        db, teacher.id, skip, limit, status, search
    )


@router.get("/lectures/{lecture_id}", response_model=LectureAssignmentResponse)
async def get_lecture(
    lecture_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific lecture assignment"""
    lecture = await lecture_service.get_lecture(db, lecture_id, teacher.id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    return lecture


@router.put("/lectures/{lecture_id}", response_model=LectureAssignmentResponse)
async def update_lecture(
    lecture_id: UUID,
    lecture_update: LectureAssignmentUpdate,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Update a lecture assignment"""
    lecture = await lecture_service.update_lecture(
        db, lecture_id, teacher.id, lecture_update
    )
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    return lecture


@router.delete("/lectures/{lecture_id}")
async def delete_lecture(
    lecture_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete a lecture assignment"""
    success = await lecture_service.delete_lecture(db, lecture_id, teacher.id)
    if not success:
        raise HTTPException(status_code=404, detail="Lecture not found")
    return {"message": "Lecture deleted successfully"}


@router.post("/lectures/{lecture_id}/restore")
async def restore_lecture(
    lecture_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Restore a soft-deleted lecture assignment"""
    success = await lecture_service.restore_lecture(db, lecture_id, teacher.id)
    if not success:
        raise HTTPException(status_code=404, detail="Lecture not found")
    return {"message": "Lecture restored successfully"}


# Image Upload Endpoints
@router.post("/lectures/{lecture_id}/images", response_model=LectureImageResponse)
async def upload_lecture_image(
    lecture_id: UUID,
    file: UploadFile = File(...),
    node_id: str = Form(...),
    teacher_description: str = Form(...),
    position: int = Form(1),
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Upload an image for a lecture"""
    # Verify lecture ownership
    lecture = await lecture_service.get_lecture(db, lecture_id, teacher.id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    
    # Validate file type
    if not file.content_type.startswith('image/'):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Process and save image
    image = await lecture_service.add_image(
        db, lecture_id, file, node_id, teacher_description, position
    )
    
    return image


@router.get("/lectures/{lecture_id}/images", response_model=List[LectureImageResponse])
async def list_lecture_images(
    lecture_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """List all images for a lecture"""
    # Verify lecture ownership
    lecture = await lecture_service.get_lecture(db, lecture_id, teacher.id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    
    return await lecture_service.list_images(db, lecture_id)


@router.delete("/lectures/{lecture_id}/images/{image_id}")
async def delete_lecture_image(
    lecture_id: UUID,
    image_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Delete an image from a lecture"""
    success = await lecture_service.delete_image(db, lecture_id, image_id, teacher.id)
    if not success:
        raise HTTPException(status_code=404, detail="Image not found")
    return {"message": "Image deleted successfully"}


# AI Processing Endpoints
@router.post("/lectures/{lecture_id}/process")
async def process_lecture(
    lecture_id: UUID,
    background_tasks: BackgroundTasks,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Trigger AI processing for a lecture"""
    # Verify lecture ownership and status
    lecture = await lecture_service.get_lecture(db, lecture_id, teacher.id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    
    if lecture.get("status") == "processing":
        raise HTTPException(status_code=400, detail="Lecture is already being processed")
    
    # Update status to processing
    await lecture_service.update_lecture_status(db, lecture_id, "processing")
    
    # Queue background processing
    background_tasks.add_task(
        lecture_ai_service.process_lecture,
        lecture_id
    )
    
    return {
        "message": "Lecture processing started",
        "lecture_id": lecture_id,
        "status": "processing"
    }


@router.get("/lectures/{lecture_id}/processing-status", response_model=LectureProcessingStatus)
async def get_processing_status(
    lecture_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get the processing status of a lecture"""
    lecture = await lecture_service.get_lecture(db, lecture_id, teacher.id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    
    return LectureProcessingStatus(
        lecture_id=lecture_id,
        status=lecture.get("status"),
        processing_started_at=lecture.get("processing_started_at"),
        processing_completed_at=lecture.get("processing_completed_at"),
        processing_error=lecture.get("processing_error")
    )


@router.put("/lectures/{lecture_id}/structure")
async def update_lecture_structure(
    lecture_id: UUID,
    structure: Dict[str, Any],
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Update the AI-generated structure of a lecture"""
    success = await lecture_service.update_lecture_structure(
        db, lecture_id, teacher.id, structure
    )
    if not success:
        raise HTTPException(status_code=404, detail="Lecture not found")
    return {"message": "Lecture structure updated successfully"}


@router.post("/lectures/{lecture_id}/publish")
async def publish_lecture(
    lecture_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Publish a lecture for student use"""
    success = await lecture_service.publish_lecture(db, lecture_id, teacher.id)
    if not success:
        raise HTTPException(status_code=404, detail="Lecture not found or not ready to publish")
    return {"message": "Lecture published successfully"}


# Classroom Assignment Endpoints
@router.post("/lectures/{lecture_id}/assign")
async def assign_to_classrooms(
    lecture_id: UUID,
    classroom_ids: List[UUID],
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Assign a lecture to classrooms"""
    # Verify lecture ownership
    lecture = await lecture_service.get_lecture(db, lecture_id, teacher.id)
    if not lecture:
        raise HTTPException(status_code=404, detail="Lecture not found")
    
    if lecture.get("status") != "published":
        raise HTTPException(status_code=400, detail="Only published lectures can be assigned")
    
    # Assign to classrooms
    results = await lecture_service.assign_to_classrooms(
        db, lecture_id, classroom_ids, teacher.id
    )
    
    return {
        "message": f"Lecture assigned to {len(results)} classrooms",
        "assignments": results
    }


# Student Endpoints
@router.get("/assignments/{assignment_id}/start")
async def start_lecture_assignment(
    assignment_id: int,
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Start or resume a lecture assignment"""
    progress = await lecture_service.get_or_create_student_progress(
        db, student.id, assignment_id
    )
    
    return progress


@router.get("/lectures/{lecture_id}/student-view")
async def get_lecture_student_view(
    lecture_id: UUID,
    assignment_id: int,
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Get lecture structure with topics and AI-generated content for student view"""
    # Verify student has access to this lecture
    access_check = await lecture_service.verify_student_access(
        db, student.id, assignment_id, lecture_id
    )
    if not access_check:
        raise HTTPException(status_code=403, detail="Access denied to this lecture")
    
    # Get lecture with progress
    lecture_data = await lecture_service.get_lecture_for_student(
        db, lecture_id, assignment_id, student.id
    )
    
    if not lecture_data:
        raise HTTPException(status_code=404, detail="Lecture not found")
    
    return lecture_data


@router.get("/lectures/{lecture_id}/topic/{topic_id}/content")
async def get_topic_all_content(
    lecture_id: UUID,
    topic_id: str,
    assignment_id: int,
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Get all tab content for a specific topic including images and questions"""
    # Verify access
    access_check = await lecture_service.verify_student_access(
        db, student.id, assignment_id, lecture_id
    )
    if not access_check:
        raise HTTPException(status_code=403, detail="Access denied to this lecture")
    
    content = await lecture_service.get_all_topic_content(
        db, lecture_id, topic_id, student.id, assignment_id
    )
    
    if not content:
        raise HTTPException(status_code=404, detail="Topic content not found")
    
    return content


@router.get("/lectures/{lecture_id}/images/{image_id}")
async def get_lecture_image(
    lecture_id: UUID,
    image_id: UUID,
    assignment_id: int,
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Get specific image with AI-generated educational description"""
    # Verify access
    access_check = await lecture_service.verify_student_access(
        db, student.id, assignment_id, lecture_id
    )
    if not access_check:
        raise HTTPException(status_code=403, detail="Access denied to this lecture")
    
    image = await lecture_service.get_image_with_description(db, image_id, lecture_id)
    
    if not image:
        raise HTTPException(status_code=404, detail="Image not found")
    
    return image


@router.get("/assignments/{assignment_id}/topics", response_model=List[LectureTopicResponse])
async def get_lecture_topics(
    assignment_id: int,
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Get available topics for a lecture"""
    topics = await lecture_service.get_lecture_topics(db, assignment_id, student.id)
    if not topics:
        raise HTTPException(status_code=404, detail="Lecture not found or not accessible")
    
    return topics


@router.get("/assignments/{assignment_id}/topics/{topic_id}/content")
async def get_topic_content(
    assignment_id: int,
    topic_id: str,
    difficulty: str = "basic",
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Get content for a specific topic at a given difficulty level"""
    content = await lecture_service.get_topic_content(
        db, assignment_id, topic_id, difficulty, student.id
    )
    
    if not content:
        raise HTTPException(status_code=404, detail="Content not found")
    
    # Track interaction
    await lecture_service.track_interaction(
        db, student.id, assignment_id, topic_id, difficulty, "view_content"
    )
    
    return content


@router.post("/assignments/{assignment_id}/topics/{topic_id}/answer")
async def answer_topic_question(
    assignment_id: int,
    topic_id: str,
    answer_data: Dict[str, Any],
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Submit an answer to a topic question"""
    difficulty = answer_data.get("difficulty")
    question_index = answer_data.get("question_index")
    answer = answer_data.get("answer")
    
    if not all([difficulty, question_index is not None, answer]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    result = await lecture_service.submit_answer(
        db, student.id, assignment_id, topic_id, difficulty, question_index, answer
    )
    
    if not result:
        raise HTTPException(status_code=400, detail="Invalid question or assignment")
    
    return result


@router.get("/assignments/{assignment_id}/progress")
async def get_student_progress(
    assignment_id: int,
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Get student's progress on a lecture assignment"""
    progress = await lecture_service.get_student_progress(db, student.id, assignment_id)
    
    if not progress:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    return progress


@router.post("/lectures/progress/update")
async def update_progress(
    progress_data: Dict[str, Any],
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Update student progress for specific topic/tab/question"""
    assignment_id = progress_data.get("assignment_id")
    topic_id = progress_data.get("topic_id")
    tab = progress_data.get("tab")  # difficulty level
    question_index = progress_data.get("question_index")
    is_correct = progress_data.get("is_correct")
    
    if not all([assignment_id, topic_id, tab]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    # Convert assignment_id to int
    try:
        assignment_id = int(assignment_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid assignment_id format")
    
    updated_progress = await lecture_service.update_student_progress(
        db, student.id, assignment_id, topic_id, tab, question_index, is_correct
    )
    
    if not updated_progress:
        raise HTTPException(status_code=404, detail="Assignment not found")
    
    return updated_progress


@router.post("/lectures/evaluate-response")
async def evaluate_response(
    eval_data: Dict[str, Any],
    background_tasks: BackgroundTasks,
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Send student response for AI evaluation"""
    assignment_id = eval_data.get("assignment_id")
    topic_id = eval_data.get("topic_id")
    difficulty = eval_data.get("difficulty")
    question_text = eval_data.get("question_text")
    student_answer = eval_data.get("student_answer")
    expected_answer = eval_data.get("expected_answer", "")
    includes_images = eval_data.get("includes_images", False)
    image_descriptions = eval_data.get("image_descriptions", [])
    
    if not all([assignment_id, topic_id, difficulty, question_text, student_answer]):
        raise HTTPException(status_code=400, detail="Missing required fields")
    
    # Convert assignment_id to int
    try:
        assignment_id = int(assignment_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid assignment_id format")
    
    # Verify access
    access_check = await lecture_service.verify_student_assignment_access(
        db, student.id, assignment_id
    )
    if not access_check:
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get AI evaluation
    result = await lecture_service.evaluate_student_response(
        question_text=question_text,
        student_answer=student_answer,
        expected_answer=expected_answer,
        difficulty=difficulty,
        includes_images=includes_images,
        image_descriptions=image_descriptions
    )
    
    # Track interaction
    background_tasks.add_task(
        lecture_service.track_interaction,
        db, student.id, assignment_id, topic_id, difficulty, "answer_question",
        question_text, student_answer, result.get("is_correct", False)
    )
    
    return result


@router.put("/lectures/progress/{assignment_id}/current-position")
async def update_current_position(
    assignment_id: int,
    position_data: Dict[str, Any],
    student: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Update current topic/tab for resume capability"""
    current_topic = position_data.get("current_topic")
    current_tab = position_data.get("current_tab")
    
    success = await lecture_service.update_current_position(
        db, assignment_id, student.id, current_topic, current_tab
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Progress record not found")
    
    return {"message": "Position updated successfully"}
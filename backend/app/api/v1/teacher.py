from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update, or_
from typing import List, Optional, Dict
from uuid import UUID
import os
import aiofiles
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.config import settings
from app.schemas.classroom import (
    ClassroomCreate, ClassroomResponse, ClassroomUpdate,
    DashboardStats, ClassroomStudentResponse, EnrollStudentRequest
)
from app.schemas.reading import (
    ReadingAssignmentCreate, ReadingAssignmentUpdate, ReadingAssignment,
    ReadingAssignmentBase, ReadingAssignmentList, MarkupValidationResult, 
    PublishResult, AssignmentImage, AssignmentImageUpload, ReadingAssignmentListResponse
)
from app.models import User, Classroom, ClassroomStudent, Assignment, UserRole
from app.models.reading import ReadingAssignment as ReadingAssignmentModel, AssignmentImage as AssignmentImageModel, ReadingChunk
from app.services.reading_async import ReadingAssignmentAsyncService
from app.services.reading import MarkupParser
from app.services.image_processing import ImageProcessor
from app.utils.deps import get_current_user

router = APIRouter()

def require_teacher(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be a teacher"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this resource"
        )
    return current_user

@router.get("/dashboard-stats", response_model=DashboardStats)
async def get_dashboard_stats(
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get dashboard statistics for teacher"""
    # Count classrooms
    classrooms_result = await db.execute(
        select(func.count(Classroom.id)).where(Classroom.teacher_id == teacher.id)
    )
    total_classrooms = classrooms_result.scalar() or 0
    
    # Count unique students across all classrooms
    students_result = await db.execute(
        select(func.count(func.distinct(ClassroomStudent.student_id)))
        .select_from(ClassroomStudent)
        .join(Classroom)
        .where(Classroom.teacher_id == teacher.id)
    )
    total_students = students_result.scalar() or 0
    
    # Count active (published) assignments
    assignments_result = await db.execute(
        select(func.count(Assignment.id))
        .where(and_(
            Assignment.teacher_id == teacher.id,
            Assignment.is_published == True
        ))
    )
    active_assignments = assignments_result.scalar() or 0
    
    # Get recent assignments
    recent_assignments_result = await db.execute(
        select(Assignment)
        .where(Assignment.teacher_id == teacher.id)
        .order_by(Assignment.created_at.desc())
        .limit(5)
    )
    recent_assignments = recent_assignments_result.scalars().all()
    
    return DashboardStats(
        total_classrooms=total_classrooms,
        total_students=total_students,
        active_assignments=active_assignments,
        recent_assignments=recent_assignments
    )

@router.get("/classrooms", response_model=List[ClassroomResponse])
async def list_classrooms(
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """List all teacher's classrooms"""
    result = await db.execute(
        select(Classroom)
        .where(Classroom.teacher_id == teacher.id)
        .order_by(Classroom.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    classrooms = result.scalars().all()
    
    # Add student count to each classroom
    classroom_responses = []
    for classroom in classrooms:
        count_result = await db.execute(
            select(func.count(ClassroomStudent.id))
            .where(ClassroomStudent.classroom_id == classroom.id)
        )
        student_count = count_result.scalar() or 0
        
        response = ClassroomResponse.model_validate(classroom)
        response.student_count = student_count
        classroom_responses.append(response)
    
    return classroom_responses

@router.post("/classrooms", response_model=ClassroomResponse)
async def create_classroom(
    classroom_data: ClassroomCreate,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Create a new classroom"""
    classroom = Classroom(
        teacher_id=teacher.id,
        **classroom_data.model_dump()
    )
    db.add(classroom)
    await db.commit()
    await db.refresh(classroom)
    
    response = ClassroomResponse.model_validate(classroom)
    response.student_count = 0
    return response

@router.put("/classrooms/{classroom_id}", response_model=ClassroomResponse)
async def update_classroom(
    classroom_id: UUID,
    classroom_data: ClassroomUpdate,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Update classroom details"""
    result = await db.execute(
        select(Classroom).where(
            and_(
                Classroom.id == classroom_id,
                Classroom.teacher_id == teacher.id
            )
        )
    )
    classroom = result.scalar_one_or_none()
    
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )
    
    # Update fields
    update_data = classroom_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(classroom, field, value)
    
    await db.commit()
    await db.refresh(classroom)
    
    # Get student count
    count_result = await db.execute(
        select(func.count(ClassroomStudent.id))
        .where(ClassroomStudent.classroom_id == classroom.id)
    )
    student_count = count_result.scalar() or 0
    
    response = ClassroomResponse.model_validate(classroom)
    response.student_count = student_count
    return response

@router.get("/classrooms/{classroom_id}/students", response_model=List[ClassroomStudentResponse])
async def list_classroom_students(
    classroom_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """List students in a classroom"""
    # Verify classroom belongs to teacher
    classroom_result = await db.execute(
        select(Classroom).where(
            and_(
                Classroom.id == classroom_id,
                Classroom.teacher_id == teacher.id
            )
        )
    )
    classroom = classroom_result.scalar_one_or_none()
    
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )
    
    # Get students
    result = await db.execute(
        select(ClassroomStudent, User)
        .join(User, User.id == ClassroomStudent.student_id)
        .where(ClassroomStudent.classroom_id == classroom_id)
        .order_by(User.last_name, User.first_name)
    )
    
    students = []
    for enrollment, student in result:
        students.append(ClassroomStudentResponse(
            id=enrollment.id,
            student_id=student.id,
            first_name=student.first_name,
            last_name=student.last_name,
            email=student.email,
            enrolled_at=enrollment.enrolled_at,
            status=enrollment.status
        ))
    
    return students

@router.post("/classrooms/{classroom_id}/students")
async def enroll_student(
    classroom_id: UUID,
    request: EnrollStudentRequest,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Enroll a student in a classroom"""
    # Verify classroom belongs to teacher
    classroom_result = await db.execute(
        select(Classroom).where(
            and_(
                Classroom.id == classroom_id,
                Classroom.teacher_id == teacher.id
            )
        )
    )
    classroom = classroom_result.scalar_one_or_none()
    
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )
    
    # Find student by email
    student_result = await db.execute(
        select(User).where(
            and_(
                User.email == request.student_email,
                User.role == UserRole.STUDENT
            )
        )
    )
    student = student_result.scalar_one_or_none()
    
    if not student:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found"
        )
    
    # Check if already enrolled
    existing_result = await db.execute(
        select(ClassroomStudent).where(
            and_(
                ClassroomStudent.classroom_id == classroom_id,
                ClassroomStudent.student_id == student.id
            )
        )
    )
    if existing_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Student already enrolled"
        )
    
    # Create enrollment
    enrollment = ClassroomStudent(
        classroom_id=classroom_id,
        student_id=student.id
    )
    db.add(enrollment)
    await db.commit()
    
    return {"message": "Student enrolled successfully"}


# Reading Assignment Endpoints

@router.post("/assignments/reading/draft", response_model=ReadingAssignmentBase)
async def create_reading_assignment_draft(
    assignment_data: ReadingAssignmentCreate,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Create a new reading assignment draft"""
    assignment = await ReadingAssignmentAsyncService.create_draft(
        db,
        teacher.id,
        assignment_data
    )
    return assignment


@router.put("/assignments/reading/{assignment_id}", response_model=ReadingAssignmentBase)
async def update_reading_assignment(
    assignment_id: UUID,
    update_data: ReadingAssignmentUpdate,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Update a reading assignment"""
    try:
        # Log the incoming data
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"Received update data: {update_data.dict()}")
        
        assignment = await ReadingAssignmentAsyncService.update_assignment(
            db,
            assignment_id,
            teacher.id,
            update_data
        )
        return assignment
    except Exception as e:
        logger.error(f"Error updating assignment: {str(e)}")
        raise


@router.post("/assignments/reading/{assignment_id}/images", response_model=AssignmentImage)
async def upload_assignment_image(
    assignment_id: UUID,
    file: UploadFile = File(...),
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Upload an image for an assignment"""
    # Verify assignment belongs to teacher
    result = await db.execute(
        select(ReadingAssignmentModel).where(
            and_(
                ReadingAssignmentModel.id == assignment_id,
                ReadingAssignmentModel.teacher_id == teacher.id,
                ReadingAssignmentModel.deleted_at.is_(None)
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Check image count limit
    existing_images = await db.execute(
        select(AssignmentImageModel).where(
            AssignmentImageModel.assignment_id == assignment_id
        )
    )
    image_count = len(existing_images.scalars().all())
    
    if image_count >= 10:  # Max 10 images per assignment
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 images allowed per assignment"
        )
    
    # Generate next image number
    image_number = image_count + 1
    
    # Process and validate image
    processor = ImageProcessor()
    try:
        image_data = await processor.validate_and_process_image(
            file=file,
            assignment_id=str(assignment_id),
            image_number=image_number
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error processing image: {str(e)}"
        )
    
    # Create database record
    image = AssignmentImageModel(
        assignment_id=assignment_id,
        image_tag=image_data["image_tag"],
        image_key=image_data["image_key"],
        file_name=image_data["file_name"],
        original_url=image_data["original_url"],
        display_url=image_data["display_url"],
        thumbnail_url=image_data["thumbnail_url"],
        image_url=image_data["image_url"],  # Backward compatibility
        width=image_data["width"],
        height=image_data["height"],
        file_size=image_data["file_size"],
        mime_type=image_data["mime_type"]
    )
    
    db.add(image)
    await db.commit()
    await db.refresh(image)
    
    return image


@router.delete("/assignments/reading/{assignment_id}/images/{image_id}")
async def delete_assignment_image(
    assignment_id: UUID,
    image_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Delete an assignment image"""
    # Verify assignment belongs to teacher
    assignment_result = await db.execute(
        select(ReadingAssignmentModel).where(
            and_(
                ReadingAssignmentModel.id == assignment_id,
                ReadingAssignmentModel.teacher_id == teacher.id
            )
        )
    )
    if not assignment_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Get and delete image
    image_result = await db.execute(
        select(AssignmentImageModel).where(
            and_(
                AssignmentImageModel.id == image_id,
                AssignmentImageModel.assignment_id == assignment_id
            )
        )
    )
    image = image_result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Delete all three image versions
    for url_attr in ['original_url', 'display_url', 'thumbnail_url']:
        if hasattr(image, url_attr):
            file_path = getattr(image, url_attr).lstrip('/')
            if os.path.exists(file_path):
                os.remove(file_path)
    
    # Delete database record
    await db.delete(image)
    await db.commit()
    
    return {"message": "Image deleted successfully"}


@router.post("/assignments/reading/{assignment_id}/validate", response_model=MarkupValidationResult)
async def validate_assignment_markup(
    assignment_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Validate assignment markup"""
    result = await ReadingAssignmentAsyncService.validate_assignment_markup(
        db,
        assignment_id,
        teacher.id
    )
    return result


@router.post("/assignments/reading/{assignment_id}/publish", response_model=PublishResult)
async def publish_assignment(
    assignment_id: UUID,
    background_tasks: BackgroundTasks,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Parse chunks and publish assignment and trigger image processing"""
    # First publish the assignment
    result = await ReadingAssignmentAsyncService.publish_assignment(
        db,
        assignment_id,
        teacher.id
    )
    
    # If publishing was successful, check for images
    if result.success:
        # Check if assignment has images
        images_result = await db.execute(
            select(func.count(AssignmentImageModel.id))
            .where(AssignmentImageModel.assignment_id == assignment_id)
        )
        image_count = images_result.scalar() or 0
        
        if image_count > 0:
            # Queue background processing
            from app.services.assignment_processor import AssignmentImageProcessor
            processor = AssignmentImageProcessor()
            background_tasks.add_task(
                processor.process_assignment_images, 
                str(assignment_id)
            )
            
            result.message = f"Assignment published. Processing {image_count} images in background."
        else:
            # Mark as fully processed if no images
            await db.execute(
                update(ReadingAssignmentModel)
                .where(ReadingAssignmentModel.id == assignment_id)
                .values(images_processed=True)
            )
            await db.commit()
    
    return result


@router.get("/assignments/reading", response_model=ReadingAssignmentListResponse)
async def list_reading_assignments(
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None, description="Search in title, work title, or author"),
    date_from: Optional[datetime] = Query(None, description="Filter by creation date from"),
    date_to: Optional[datetime] = Query(None, description="Filter by creation date to"),
    grade_level: Optional[str] = Query(None, description="Filter by grade level"),
    work_type: Optional[str] = Query(None, description="Filter by work type (fiction/non-fiction)"),
    include_archived: bool = Query(False, description="Include archived assignments")
):
    """List teacher's reading assignments with search and filter options"""
    
    # Build base query
    query = select(ReadingAssignmentModel).where(
        ReadingAssignmentModel.teacher_id == teacher.id
    )
    
    # Handle archived/deleted filter
    if not include_archived:
        query = query.where(ReadingAssignmentModel.deleted_at.is_(None))
    
    # Apply search filter
    if search:
        search_term = f"%{search}%"
        query = query.where(
            or_(
                ReadingAssignmentModel.assignment_title.ilike(search_term),
                ReadingAssignmentModel.work_title.ilike(search_term),
                ReadingAssignmentModel.author.ilike(search_term)
            )
        )
    
    # Apply date filters
    if date_from:
        query = query.where(ReadingAssignmentModel.created_at >= date_from)
    if date_to:
        # Add 1 day to include the entire end date
        query = query.where(ReadingAssignmentModel.created_at < date_to + timedelta(days=1))
    
    # Apply grade level filter
    if grade_level:
        query = query.where(ReadingAssignmentModel.grade_level == grade_level)
    
    # Apply work type filter
    if work_type:
        query = query.where(ReadingAssignmentModel.work_type == work_type.lower())
    
    # Get total count before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_count = total_result.scalar() or 0
    
    # Apply ordering and pagination
    query = query.order_by(ReadingAssignmentModel.created_at.desc()).offset(skip).limit(limit)
    
    # Execute query
    result = await db.execute(query)
    assignments = result.scalars().all()
    
    return ReadingAssignmentListResponse(
        assignments=assignments,
        total=total_count,
        filtered=total_count,  # Since we're showing filtered results
        page=(skip // limit) + 1,
        per_page=limit
    )


@router.get("/assignments/reading/{assignment_id}", response_model=ReadingAssignment)
async def get_reading_assignment(
    assignment_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific reading assignment with chunks and images"""
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(ReadingAssignmentModel)
        .options(
            selectinload(ReadingAssignmentModel.chunks),
            selectinload(ReadingAssignmentModel.images)
        )
        .where(
            and_(
                ReadingAssignmentModel.id == assignment_id,
                ReadingAssignmentModel.teacher_id == teacher.id,
                ReadingAssignmentModel.deleted_at.is_(None)
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    return assignment

@router.get("/assignments/{assignment_id}/edit", response_model=ReadingAssignment)
async def get_assignment_for_edit(
    assignment_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get assignment with all chunks and images for editing"""
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(ReadingAssignmentModel)
        .options(
            selectinload(ReadingAssignmentModel.chunks),
            selectinload(ReadingAssignmentModel.images)
        )
        .where(
            and_(
                ReadingAssignmentModel.id == assignment_id,
                ReadingAssignmentModel.teacher_id == teacher.id,
                ReadingAssignmentModel.deleted_at.is_(None)
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    return assignment


@router.put("/assignments/{assignment_id}/content")
async def update_assignment_content(
    assignment_id: UUID,
    content: dict,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Update assignment text content and re-parse chunks"""
    # Verify assignment ownership
    result = await db.execute(
        select(ReadingAssignmentModel).where(
            and_(
                ReadingAssignmentModel.id == assignment_id,
                ReadingAssignmentModel.teacher_id == teacher.id,
                ReadingAssignmentModel.deleted_at.is_(None)
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Update raw content
    assignment.raw_content = content["raw_content"]
    assignment.updated_at = datetime.utcnow()
    
    # If published, re-parse chunks
    if assignment.status == "published":
        parser = MarkupParser()
        chunks = parser.parse_chunks(content["raw_content"])
        
        # Delete existing chunks
        from sqlalchemy import delete
        await db.execute(
            delete(ReadingChunk).where(ReadingChunk.assignment_id == assignment_id)
        )
        
        # Create new chunks
        for idx, chunk_data in enumerate(chunks):
            chunk = ReadingChunk(
                assignment_id=assignment_id,
                chunk_order=idx + 1,
                content=chunk_data["content"],
                has_important_sections=chunk_data["has_important_sections"]
            )
            db.add(chunk)
        
        assignment.total_chunks = len(chunks)
    
    await db.commit()
    return {"message": "Content updated successfully"}


@router.put("/assignments/{assignment_id}/images/{image_id}/description")
async def update_image_description(
    assignment_id: UUID,
    image_id: UUID,
    description: dict,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Update AI description for a specific image"""
    # Verify assignment ownership
    assignment_result = await db.execute(
        select(ReadingAssignmentModel).where(
            and_(
                ReadingAssignmentModel.id == assignment_id,
                ReadingAssignmentModel.teacher_id == teacher.id,
                ReadingAssignmentModel.deleted_at.is_(None)
            )
        )
    )
    if not assignment_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Get and update image
    image_result = await db.execute(
        select(AssignmentImageModel).where(
            and_(
                AssignmentImageModel.id == image_id,
                AssignmentImageModel.assignment_id == assignment_id
            )
        )
    )
    image = image_result.scalar_one_or_none()
    
    if not image:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    # Validate description length
    new_description = description.get("ai_description", "").strip()
    if len(new_description) < 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Description must be at least 50 characters"
        )
    
    # Preserve JSON structure if it exists
    import json
    if image.ai_description:
        try:
            # Try to parse existing description
            existing_data = json.loads(image.ai_description)
            if isinstance(existing_data, dict) and 'description' in existing_data:
                # Update only the description field, preserve other AI analysis data
                existing_data['description'] = new_description
                image.ai_description = json.dumps(existing_data)
            else:
                # Not a structured format, just save as plain text
                image.ai_description = new_description
        except json.JSONDecodeError:
            # Not JSON, just save as plain text
            image.ai_description = new_description
    else:
        # No existing description, save as plain text
        image.ai_description = new_description
    
    image.description_generated_at = datetime.utcnow()
    
    await db.commit()
    return {"message": "Image description updated successfully"}


@router.delete("/assignments/{assignment_id}")
async def archive_assignment(
    assignment_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Archive an assignment (soft delete)"""
    result = await db.execute(
        select(ReadingAssignmentModel).where(
            and_(
                ReadingAssignmentModel.id == assignment_id,
                ReadingAssignmentModel.teacher_id == teacher.id,
                ReadingAssignmentModel.deleted_at.is_(None)
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found"
        )
    
    # Soft delete
    assignment.deleted_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Assignment archived successfully"}


@router.post("/assignments/{assignment_id}/restore")
async def restore_assignment(
    assignment_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Restore an archived assignment"""
    result = await db.execute(
        select(ReadingAssignmentModel).where(
            and_(
                ReadingAssignmentModel.id == assignment_id,
                ReadingAssignmentModel.teacher_id == teacher.id,
                ReadingAssignmentModel.deleted_at.is_not(None)
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archived assignment not found"
        )
    
    # Restore
    assignment.deleted_at = None
    await db.commit()
    
    return {"message": "Assignment restored successfully"}
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Optional
from uuid import UUID
import os
import aiofiles
from datetime import datetime

from app.core.database import get_db
from app.core.config import settings
from app.schemas.classroom import (
    ClassroomCreate, ClassroomResponse, ClassroomUpdate,
    DashboardStats, ClassroomStudentResponse, EnrollStudentRequest
)
from app.schemas.reading import (
    ReadingAssignmentCreate, ReadingAssignmentUpdate, ReadingAssignment,
    ReadingAssignmentBase, ReadingAssignmentList, MarkupValidationResult, 
    PublishResult, AssignmentImage, AssignmentImageUpload
)
from app.models import User, Classroom, ClassroomStudent, Assignment, UserRole
from app.models.reading import ReadingAssignment as ReadingAssignmentModel, AssignmentImage as AssignmentImageModel
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
                ReadingAssignmentModel.teacher_id == teacher.id
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
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Parse chunks and publish assignment"""
    result = await ReadingAssignmentAsyncService.publish_assignment(
        db,
        assignment_id,
        teacher.id
    )
    return result


@router.get("/assignments/reading", response_model=List[ReadingAssignmentList])
async def list_reading_assignments(
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 20
):
    """List teacher's reading assignments"""
    result = await db.execute(
        select(ReadingAssignmentModel)
        .where(ReadingAssignmentModel.teacher_id == teacher.id)
        .order_by(ReadingAssignmentModel.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    
    return result.scalars().all()


@router.get("/assignments/reading/{assignment_id}", response_model=ReadingAssignment)
async def get_reading_assignment(
    assignment_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific reading assignment with chunks and images"""
    result = await db.execute(
        select(ReadingAssignmentModel)
        .where(
            and_(
                ReadingAssignmentModel.id == assignment_id,
                ReadingAssignmentModel.teacher_id == teacher.id
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
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update, or_, delete
from typing import List, Optional, Dict
from uuid import UUID
import os
import aiofiles
from datetime import datetime, timedelta

from app.core.database import get_db
from app.core.config import settings
from app.schemas.classroom import (
    ClassroomCreate, ClassroomResponse, ClassroomUpdate,
    ClassroomDetailResponse, StudentInClassroom, AssignmentInClassroom,
    UpdateClassroomAssignmentsRequest, UpdateClassroomAssignmentsResponse,
    AvailableAssignment
)
from app.schemas.reading import (
    ReadingAssignmentCreate, ReadingAssignmentUpdate, ReadingAssignment,
    ReadingAssignmentBase, ReadingAssignmentList, MarkupValidationResult, 
    PublishResult, AssignmentImage, AssignmentImageUpload, ReadingAssignmentListResponse
)
from app.models import User, Classroom, ClassroomStudent, UserRole
from app.models.classroom import ClassroomAssignment
from app.models.reading import ReadingAssignment as ReadingAssignmentModel, AssignmentImage as AssignmentImageModel, ReadingChunk
from app.services.reading_async import ReadingAssignmentAsyncService
from app.services.reading import MarkupParser
from app.services.image_processing import ImageProcessor
from app.services import classroom as classroom_service
from app.utils.deps import get_current_user

# Import vocabulary router
from . import vocabulary
from . import vocabulary_chains
from . import teacher_classroom_assignments
from . import teacher_classroom_detail
from . import teacher_settings
from . import teacher_reports
from . import teacher_vocabulary_settings
from . import debate

router = APIRouter()

# Include vocabulary routes
# Important: Include chains router first to avoid route conflicts with vocabulary/{list_id}
router.include_router(vocabulary_chains.router, prefix="/vocabulary", tags=["vocabulary-chains"])
router.include_router(vocabulary.router, tags=["vocabulary"])

# Include debate routes
router.include_router(debate.router, tags=["debate"])

# Include unified classroom assignment routes
router.include_router(teacher_classroom_assignments.router, tags=["classroom-assignments"])

# Include updated classroom detail routes
router.include_router(teacher_classroom_detail.router, tags=["classroom-detail"])

# Include teacher settings routes
router.include_router(teacher_settings.router, tags=["teacher-settings"])

# Include teacher reports routes
router.include_router(teacher_reports.router, tags=["teacher-reports"])

# Include vocabulary settings routes
router.include_router(teacher_vocabulary_settings.router, tags=["vocabulary-settings"])

def require_teacher(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be a teacher"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this resource"
        )
    return current_user


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
        .where(
            and_(
                Classroom.teacher_id == teacher.id,
                Classroom.deleted_at.is_(None)
            )
        )
        .order_by(Classroom.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    classrooms = result.scalars().all()
    
    # Add counts to each classroom
    classroom_responses = []
    for classroom in classrooms:
        # Count students
        student_count_result = await db.execute(
            select(func.count(ClassroomStudent.student_id))
            .where(
                and_(
                    ClassroomStudent.classroom_id == classroom.id,
                    ClassroomStudent.removed_at.is_(None)
                )
            )
        )
        student_count = student_count_result.scalar() or 0
        
        # Count assignments
        assignment_count_result = await db.execute(
            select(func.count(ClassroomAssignment.assignment_id))
            .where(ClassroomAssignment.classroom_id == classroom.id)
        )
        assignment_count = assignment_count_result.scalar() or 0
        
        response = ClassroomResponse(
            id=classroom.id,
            name=classroom.name,
            teacher_id=classroom.teacher_id,
            class_code=classroom.class_code,
            created_at=classroom.created_at,
            deleted_at=classroom.deleted_at,
            student_count=student_count,
            assignment_count=assignment_count
        )
        classroom_responses.append(response)
    
    return classroom_responses

@router.post("/classrooms", response_model=ClassroomResponse)
async def create_classroom(
    classroom_data: ClassroomCreate,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Create a new classroom with auto-generated class code"""
    # Generate unique class code
    while True:
        class_code = classroom_service.generate_class_code()
        existing = await db.execute(
            select(Classroom).where(
                and_(Classroom.class_code == class_code, Classroom.deleted_at.is_(None))
            )
        )
        if not existing.scalar_one_or_none():
            break
    
    classroom = Classroom(
        name=classroom_data.name,
        teacher_id=teacher.id,
        class_code=class_code
    )
    db.add(classroom)
    await db.commit()
    await db.refresh(classroom)
    
    response = ClassroomResponse(
        id=classroom.id,
        name=classroom.name,
        teacher_id=classroom.teacher_id,
        class_code=classroom.class_code,
        created_at=classroom.created_at,
        deleted_at=classroom.deleted_at,
        student_count=0,
        assignment_count=0
    )
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
    
    response = ClassroomResponse(
        id=classroom.id,
        name=classroom.name,
        teacher_id=classroom.teacher_id,
        class_code=classroom.class_code,
        created_at=classroom.created_at,
        deleted_at=classroom.deleted_at,
        student_count=student_count,
        assignment_count=0
    )
    return response




# New Classroom Management Endpoints

@router.get("/classrooms/{classroom_id}", response_model=ClassroomDetailResponse)
async def get_classroom_details(
    classroom_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed classroom information including students and assignments"""
    # Get classroom
    result = await db.execute(
        select(Classroom).where(
            and_(
                Classroom.id == classroom_id,
                Classroom.teacher_id == teacher.id,
                Classroom.deleted_at.is_(None)
            )
        )
    )
    classroom = result.scalar_one_or_none()
    
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )
    
    # Get students with user info
    students_result = await db.execute(
        select(User, ClassroomStudent)
        .join(ClassroomStudent, ClassroomStudent.student_id == User.id)
        .where(
            and_(
                ClassroomStudent.classroom_id == classroom_id,
                ClassroomStudent.removed_at.is_(None),
                User.deleted_at.is_(None)  # Exclude soft deleted students
            )
        )
        .order_by(User.last_name, User.first_name)
    )
    
    student_list = []
    for user, enrollment in students_result:
        student_list.append(StudentInClassroom(
            id=user.id,
            email=user.email,
            full_name=f"{user.first_name} {user.last_name}",
            joined_at=enrollment.joined_at,
            removed_at=enrollment.removed_at
        ))
    
    # Get all classroom assignments (both reading and vocabulary)
    assignment_list = []
    
    # Get reading assignments
    reading_assignments_result = await db.execute(
        select(ReadingAssignmentModel, ClassroomAssignment)
        .join(ClassroomAssignment, 
              and_(
                  ClassroomAssignment.assignment_id == ReadingAssignmentModel.id,
                  ClassroomAssignment.assignment_type == "reading"
              ))
        .where(ClassroomAssignment.classroom_id == classroom_id)
        .order_by(ClassroomAssignment.display_order, ClassroomAssignment.assigned_at)
    )
    
    for assignment, ca in reading_assignments_result:
        assignment_list.append(AssignmentInClassroom(
            id=ca.id,
            assignment_id=assignment.id,
            title=assignment.assignment_title,
            assignment_type=assignment.assignment_type,
            assigned_at=ca.assigned_at,
            display_order=ca.display_order,
            start_date=ca.start_date,
            end_date=ca.end_date
        ))
    
    # Get vocabulary assignments
    from app.models.vocabulary import VocabularyList
    vocab_assignments_result = await db.execute(
        select(VocabularyList, ClassroomAssignment)
        .join(ClassroomAssignment,
              and_(
                  ClassroomAssignment.vocabulary_list_id == VocabularyList.id,
                  ClassroomAssignment.assignment_type == "vocabulary"
              ))
        .where(ClassroomAssignment.classroom_id == classroom_id)
        .order_by(ClassroomAssignment.display_order, ClassroomAssignment.assigned_at)
    )
    
    for vocab_list, ca in vocab_assignments_result:
        assignment_list.append(AssignmentInClassroom(
            id=ca.id,
            assignment_id=vocab_list.id,
            title=vocab_list.title,
            assignment_type="UMAVocab",
            assigned_at=ca.assigned_at,
            display_order=ca.display_order,
            start_date=ca.start_date,
            end_date=ca.end_date
        ))
    
    # Sort all assignments by display order
    assignment_list.sort(key=lambda x: (x.display_order or float('inf'), x.assigned_at))
    
    return ClassroomDetailResponse(
        id=classroom.id,
        name=classroom.name,
        teacher_id=classroom.teacher_id,
        class_code=classroom.class_code,
        created_at=classroom.created_at,
        deleted_at=classroom.deleted_at,
        student_count=len(student_list),
        assignment_count=len(assignment_list),
        students=student_list,
        assignments=assignment_list
    )


@router.delete("/classrooms/{classroom_id}")
async def delete_classroom(
    classroom_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete a classroom"""
    # Verify classroom exists and belongs to teacher
    result = await db.execute(
        select(Classroom).where(
            and_(
                Classroom.id == classroom_id,
                Classroom.teacher_id == teacher.id,
                Classroom.deleted_at.is_(None)
            )
        )
    )
    classroom = result.scalar_one_or_none()
    
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )
    
    # Soft delete the classroom
    classroom.deleted_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Classroom deleted successfully"}


@router.delete("/classrooms/{classroom_id}/students/{student_id}")
async def remove_student_from_classroom(
    classroom_id: UUID,
    student_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Remove a student from a classroom"""
    # Verify classroom exists and belongs to teacher
    result = await db.execute(
        select(Classroom).where(
            and_(
                Classroom.id == classroom_id,
                Classroom.teacher_id == teacher.id,
                Classroom.deleted_at.is_(None)
            )
        )
    )
    classroom = result.scalar_one_or_none()
    
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )
    
    # Find and soft delete the student enrollment
    enrollment_result = await db.execute(
        select(ClassroomStudent).where(
            and_(
                ClassroomStudent.classroom_id == classroom_id,
                ClassroomStudent.student_id == student_id,
                ClassroomStudent.removed_at.is_(None)
            )
        )
    )
    enrollment = enrollment_result.scalar_one_or_none()
    
    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student not found in classroom"
        )
    
    # Soft delete by setting removed_at
    enrollment.removed_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Student removed successfully"}


@router.get("/classrooms/{classroom_id}/assignments", response_model=List[AssignmentInClassroom])
async def list_classroom_assignments(
    classroom_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """List all assignments in a classroom"""
    # Verify classroom exists and belongs to teacher
    result = await db.execute(
        select(Classroom).where(
            and_(
                Classroom.id == classroom_id,
                Classroom.teacher_id == teacher.id,
                Classroom.deleted_at.is_(None)
            )
        )
    )
    classroom = result.scalar_one_or_none()
    
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )
    
    # Get assignments with their classroom assignment data
    assignments_result = await db.execute(
        select(ReadingAssignmentModel, ClassroomAssignment)
        .join(ClassroomAssignment, ClassroomAssignment.assignment_id == ReadingAssignmentModel.id)
        .where(ClassroomAssignment.classroom_id == classroom_id)
        .order_by(ClassroomAssignment.display_order, ClassroomAssignment.assigned_at)
    )
    
    assignment_list = []
    for assignment, ca in assignments_result:
        assignment_list.append(AssignmentInClassroom(
            assignment_id=assignment.id,
            title=assignment.assignment_title,
            assignment_type=assignment.assignment_type,
            assigned_at=ca.assigned_at,
            display_order=ca.display_order
        ))
    
    return assignment_list


@router.get("/classrooms/{classroom_id}/assignments/available")
async def get_classroom_available_assignments(
    classroom_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None),
    assignment_type: Optional[str] = Query(None),
    grade_level: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """Get all teacher's assignments with their assignment status for this classroom"""
    # Verify classroom ownership
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
    
    # Get currently assigned assignments with their schedules
    assigned_result = await db.execute(
        select(ClassroomAssignment).where(
            ClassroomAssignment.classroom_id == classroom_id
        )
    )
    assigned_assignments = {ca.assignment_id: ca for ca in assigned_result.scalars()}
    assigned_ids = set(assigned_assignments.keys())
    
    # Build query for all teacher's assignments (include archived)
    query = select(ReadingAssignmentModel).where(
        and_(
            ReadingAssignmentModel.teacher_id == teacher.id,
            ReadingAssignmentModel.status == "published"
        )
    )
    
    # Apply filters
    if search:
        query = query.where(
            or_(
                ReadingAssignmentModel.assignment_title.ilike(f"%{search}%"),
                ReadingAssignmentModel.work_title.ilike(f"%{search}%"),
                ReadingAssignmentModel.author.ilike(f"%{search}%")
            )
        )
    
    if assignment_type and assignment_type != "all":
        query = query.where(ReadingAssignmentModel.assignment_type == assignment_type)
    
    if grade_level and grade_level != "all":
        query = query.where(ReadingAssignmentModel.grade_level == grade_level)
    
    if status:
        if status == "assigned":
            query = query.where(ReadingAssignmentModel.id.in_(assigned_ids))
        elif status == "unassigned":
            query = query.where(ReadingAssignmentModel.id.notin_(assigned_ids))
        # Note: published filter is already applied by default
    
    # Get total count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total_count = count_result.scalar() or 0
    
    # Apply pagination and sorting
    query = query.order_by(ReadingAssignmentModel.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    # Execute query
    result = await db.execute(query)
    assignments = result.scalars().all()
    
    # Format response
    available_assignments = []
    for assignment in assignments:
        # Build assignment dict
        assignment_dict = {
            "id": assignment.id,
            "assignment_title": assignment.assignment_title,
            "work_title": assignment.work_title,
            "author": assignment.author or "",
            "assignment_type": assignment.assignment_type,
            "grade_level": assignment.grade_level,
            "work_type": assignment.work_type,
            "status": assignment.status,
            "created_at": assignment.created_at,
            "is_assigned": assignment.id in assigned_ids,
            "is_archived": assignment.deleted_at is not None
        }
        
        # Add schedule info if assigned
        if assignment.id in assigned_ids:
            ca = assigned_assignments[assignment.id]
            assignment_dict["current_schedule"] = {
                "start_date": ca.start_date,
                "end_date": ca.end_date
            }
        
        available_assignments.append(assignment_dict)
    
    return {
        "assignments": available_assignments,
        "total_count": total_count,
        "page": page,
        "per_page": per_page
    }


@router.put("/classrooms/{classroom_id}/assignments", response_model=UpdateClassroomAssignmentsResponse)
async def update_classroom_assignments(
    classroom_id: UUID,
    request: UpdateClassroomAssignmentsRequest,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Update the assignments in a classroom (bulk add/remove)"""
    # Verify classroom exists and belongs to teacher
    result = await db.execute(
        select(Classroom).where(
            and_(
                Classroom.id == classroom_id,
                Classroom.teacher_id == teacher.id,
                Classroom.deleted_at.is_(None)
            )
        )
    )
    classroom = result.scalar_one_or_none()
    
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found"
        )
    
    # Get current assignments
    current_result = await db.execute(
        select(ClassroomAssignment)
        .where(ClassroomAssignment.classroom_id == classroom_id)
    )
    current_assignments = {ca.assignment_id: ca for ca in current_result.scalars()}
    current_assignment_ids = set(current_assignments.keys())
    
    # Build lookup map for requested assignments with their schedules
    requested_schedules = {sched.assignment_id: sched for sched in request.assignments}
    requested_ids = set(requested_schedules.keys())
    
    # Calculate changes
    to_add = requested_ids - current_assignment_ids
    to_remove = current_assignment_ids - requested_ids
    to_update = requested_ids & current_assignment_ids
    
    # Remove assignments
    if to_remove:
        from sqlalchemy import delete
        await db.execute(
            delete(ClassroomAssignment).where(
                and_(
                    ClassroomAssignment.classroom_id == classroom_id,
                    ClassroomAssignment.assignment_id.in_(to_remove)
                )
            )
        )
    
    # Update existing assignments with new dates
    for assignment_id in to_update:
        ca = current_assignments[assignment_id]
        schedule = requested_schedules[assignment_id]
        ca.start_date = schedule.start_date
        ca.end_date = schedule.end_date
    
    # Add new assignments
    for idx, assignment_id in enumerate(to_add):
        # Verify assignment exists and belongs to teacher
        assignment_result = await db.execute(
            select(ReadingAssignmentModel).where(
                and_(
                    ReadingAssignmentModel.id == assignment_id,
                    ReadingAssignmentModel.teacher_id == teacher.id,
                    ReadingAssignmentModel.deleted_at.is_(None)
                )
            )
        )
        if assignment_result.scalar_one_or_none():
            schedule = requested_schedules[assignment_id]
            ca = ClassroomAssignment(
                classroom_id=classroom_id,
                assignment_id=assignment_id,
                display_order=idx + len(current_assignment_ids) - len(to_remove),
                start_date=schedule.start_date,
                end_date=schedule.end_date
            )
            db.add(ca)
    
    await db.commit()
    
    return UpdateClassroomAssignmentsResponse(
        added=list(to_add),
        removed=list(to_remove),
        total=len(requested_ids)
    )


@router.get("/assignments/available", response_model=List[AvailableAssignment])
async def get_available_assignments(
    teacher: User = Depends(require_teacher),
    classroom_id: Optional[UUID] = Query(None, description="Get assignment status for specific classroom"),
    db: AsyncSession = Depends(get_db)
):
    """Get all teacher's assignments with assignment status for a specific classroom"""
    # Get all teacher's assignments
    assignments_query = select(ReadingAssignmentModel).where(
        and_(
            ReadingAssignmentModel.teacher_id == teacher.id,
            ReadingAssignmentModel.deleted_at.is_(None),
            ReadingAssignmentModel.status == "published"
        )
    ).order_by(ReadingAssignmentModel.created_at.desc())
    
    assignments_result = await db.execute(assignments_query)
    assignments = assignments_result.scalars().all()
    
    # If classroom_id provided, get assigned status
    assigned_ids = set()
    if classroom_id:
        assigned_result = await db.execute(
            select(ClassroomAssignment.assignment_id)
            .where(ClassroomAssignment.classroom_id == classroom_id)
        )
        assigned_ids = {row[0] for row in assigned_result}
    
    # Build response
    available_assignments = []
    for assignment in assignments:
        available_assignments.append(AvailableAssignment(
            id=assignment.id,
            assignment_title=assignment.assignment_title,
            work_title=assignment.work_title,
            author=assignment.author,
            assignment_type=assignment.assignment_type,
            grade_level=assignment.grade_level,
            work_type=assignment.work_type,
            created_at=assignment.created_at,
            is_assigned=assignment.id in assigned_ids
        ))
    
    return available_assignments


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


async def generate_test_for_assignment_background(assignment_id: str, teacher_id: str):
    """Background task to generate test for an assignment."""
    from app.core.database import get_db
    from app.services.test_generation import TestGenerationService
    from app.models.tests import AssignmentTest
    from sqlalchemy import select
    import uuid
    
    async for db in get_db():
        try:
            # Check if test already exists
            existing = await db.execute(
                select(AssignmentTest).where(AssignmentTest.assignment_id == uuid.UUID(assignment_id))
            )
            if existing.scalar_one_or_none():
                return  # Test already exists
            
            # Generate test
            test_service = TestGenerationService()
            test_data = await test_service.generate_test_for_assignment(
                uuid.UUID(assignment_id),
                db
            )
            
            # Create test record
            new_test = AssignmentTest(**test_data)
            db.add(new_test)
            await db.commit()
            
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Error generating test for assignment {assignment_id}: {e}")
        finally:
            await db.close()


@router.post("/assignments/reading/{assignment_id}/publish", response_model=PublishResult)
async def publish_assignment(
    assignment_id: UUID,
    background_tasks: BackgroundTasks,
    generate_test: bool = True,  # Default to true for automatic test generation
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
    
    # If publishing was successful, check for images and generate test
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
        
        # Generate test if requested and assignment type is UMARead
        if generate_test:
            # Check if assignment is UMARead type
            assignment_result = await db.execute(
                select(ReadingAssignmentModel.assignment_type)
                .where(ReadingAssignmentModel.id == assignment_id)
            )
            assignment_type = assignment_result.scalar()
            
            if assignment_type == "UMARead":
                # Queue test generation in background
                from app.services.test_generation import TestGenerationService
                test_service = TestGenerationService()
                background_tasks.add_task(
                    generate_test_for_assignment_background,
                    str(assignment_id),
                    str(teacher.id)
                )
                
                if result.message:
                    result.message += " Test will be generated in background."
                else:
                    result.message = "Assignment published. Test will be generated in background."
    
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
        for idx, (chunk_content, has_important) in enumerate(chunks):
            chunk = ReadingChunk(
                assignment_id=assignment_id,
                chunk_order=idx + 1,
                content=chunk_content,
                has_important_sections=has_important
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


# Security monitoring endpoints (bypass codes moved to teacher_settings.py)
@router.get("/classroom/{classroom_id}/security-incidents")
async def get_classroom_security_incidents(
    classroom_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """View security incidents for all students in classroom"""
    from app.models.tests import TestSecurityIncident, StudentTestAttempt
    from app.models.reading import ReadingAssignment as ReadingAssignmentModel
    from datetime import datetime, timedelta
    
    # Verify teacher owns classroom
    classroom_query = await db.execute(
        select(Classroom)
        .where(
            and_(
                Classroom.id == classroom_id,
                Classroom.teacher_id == current_user.id
            )
        )
    )
    
    if not classroom_query.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this classroom"
        )
    
    # Get security incidents from the last 30 days for students in this classroom
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    incidents_query = await db.execute(
        select(
            TestSecurityIncident,
            StudentTestAttempt,
            User,
            ReadingAssignmentModel
        )
        .join(StudentTestAttempt, TestSecurityIncident.test_attempt_id == StudentTestAttempt.id)
        .join(User, TestSecurityIncident.student_id == User.id)
        .join(ReadingAssignmentModel, StudentTestAttempt.assignment_id == ReadingAssignmentModel.id)
        .join(ClassroomStudent, 
              and_(
                  ClassroomStudent.student_id == User.id,
                  ClassroomStudent.classroom_id == classroom_id
              ))
        .where(
            and_(
                User.deleted_at.is_(None),  # Exclude soft deleted students
                TestSecurityIncident.created_at >= thirty_days_ago  # Only last 30 days
            )
        )
        .order_by(TestSecurityIncident.created_at.desc())
    )
    
    incidents = []
    for incident, attempt, student, assignment in incidents_query.all():
        incidents.append({
            "id": incident.id,
            "student_name": f"{student.first_name} {student.last_name}",
            "student_id": student.id,
            "assignment_title": assignment.assignment_title,
            "incident_type": incident.incident_type,
            "incident_data": incident.incident_data,
            "resulted_in_lock": incident.resulted_in_lock,
            "created_at": incident.created_at,
            "test_locked": attempt.is_locked,
            "test_attempt_id": attempt.id
        })
    
    return {
        "classroom_id": classroom_id,
        "incidents": incidents,
        "total_incidents": len(incidents)
    }


@router.delete("/classroom/{classroom_id}/security-incidents/{incident_id}")
async def delete_security_incident(
    classroom_id: UUID,
    incident_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a security incident from the classroom"""
    from app.models.tests import TestSecurityIncident
    
    # Verify teacher owns classroom
    classroom_query = await db.execute(
        select(Classroom)
        .where(
            and_(
                Classroom.id == classroom_id,
                Classroom.teacher_id == current_user.id
            )
        )
    )
    
    if not classroom_query.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this classroom"
        )
    
    # Get the security incident and verify it belongs to a student in this classroom
    incident_query = await db.execute(
        select(TestSecurityIncident)
        .join(ClassroomStudent, 
              and_(
                  ClassroomStudent.student_id == TestSecurityIncident.student_id,
                  ClassroomStudent.classroom_id == classroom_id
              ))
        .where(TestSecurityIncident.id == incident_id)
    )
    
    incident = incident_query.scalar_one_or_none()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Security incident not found or not in this classroom"
        )
    
    # Delete the incident
    await db.delete(incident)
    await db.commit()
    
    return {"message": "Security incident deleted successfully"}
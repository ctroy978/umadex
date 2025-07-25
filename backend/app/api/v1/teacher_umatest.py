"""
API endpoints for UMATest teacher functionality
Phase 1: Test Creation System
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
import logging

from app.core.database import get_db, AsyncSessionLocal
from app.utils.deps import get_current_user
from app.models.user import User
from app.models.umatest import TestAssignment, TestGenerationLog
from app.models.reading import ReadingAssignment
from app.schemas.umatest import (
    CreateTestRequest,
    UpdateTestRequest,
    GenerateTestQuestionsRequest,
    TestAssignmentResponse,
    TestDetailResponse,
    TestListResponse,
    LectureInfo,
    GenerationLogResponse,
    calculate_question_counts
)
from app.services.umatest_ai import umatest_ai_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/teacher/umatest", tags=["teacher-umatest"])


async def generate_test_questions_task(test_id: str, regenerate: bool = False):
    """Background task to generate test questions with its own database session"""
    async with AsyncSessionLocal() as db:
        try:
            await umatest_ai_service.generate_test_questions(db, test_id, regenerate)
        except Exception as e:
            logger.error(f"Error generating test questions for test {test_id}: {str(e)}")
            # Update the generation log to failed status
            try:
                result = await db.execute(
                    select(TestGenerationLog).where(
                        and_(
                            TestGenerationLog.test_assignment_id == test_id,
                            TestGenerationLog.status == 'processing'
                        )
                    )
                )
                log_entry = result.scalar_one_or_none()
                
                if log_entry:
                    log_entry.status = 'failed'
                    log_entry.error_message = str(e)
                    await db.commit()
            except Exception as log_error:
                logger.error(f"Error updating generation log: {str(log_error)}")


@router.post("/tests", response_model=TestAssignmentResponse)
async def create_test(
    request: CreateTestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new test assignment"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers can create tests")
    
    # Validate that all selected lectures exist and belong to the teacher
    lecture_result = await db.execute(
        select(ReadingAssignment).where(
            and_(
                ReadingAssignment.id.in_(request.selected_lecture_ids),
                ReadingAssignment.assignment_type == 'UMALecture',
                ReadingAssignment.teacher_id == current_user.id,
                ReadingAssignment.deleted_at.is_(None)
            )
        )
    )
    lectures = lecture_result.scalars().all()
    
    if len(lectures) != len(request.selected_lecture_ids):
        raise HTTPException(status_code=400, detail="One or more selected lectures not found or not owned by teacher")
    
    # Create test assignment
    test_assignment = TestAssignment(
        teacher_id=current_user.id,
        test_title=request.test_title,
        test_description=request.test_description,
        selected_lecture_ids=request.selected_lecture_ids,
        time_limit_minutes=request.time_limit_minutes,
        attempt_limit=request.attempt_limit,
        randomize_questions=request.randomize_questions,
        show_feedback_immediately=request.show_feedback_immediately,
        status='draft',
        test_structure={}  # Initialize as empty dict
    )
    
    db.add(test_assignment)
    await db.commit()
    await db.refresh(test_assignment)
    
    return TestAssignmentResponse.from_orm(test_assignment)


@router.get("/tests", response_model=TestListResponse)
async def list_tests(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, regex='^(draft|published|archived)$'),
    search: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List teacher's test assignments with pagination"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers can view tests")
    
    # Build query
    query = select(TestAssignment).where(
        TestAssignment.teacher_id == current_user.id
    )
    
    # Handle archived status (soft-deleted tests)
    if status == 'archived':
        query = query.where(TestAssignment.deleted_at.is_not(None))
    else:
        query = query.where(TestAssignment.deleted_at.is_(None))
        if status:
            query = query.where(TestAssignment.status == status)
    
    if search:
        query = query.where(
            or_(
                TestAssignment.test_title.ilike(f"%{search}%"),
                TestAssignment.test_description.ilike(f"%{search}%")
            )
        )
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total_count = total_result.scalar()
    
    # Apply pagination
    query = query.order_by(TestAssignment.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    result = await db.execute(query)
    tests = result.scalars().all()
    
    # Build response with is_archived flag
    test_responses = []
    for test in tests:
        response = TestAssignmentResponse.from_orm(test)
        response.is_archived = test.deleted_at is not None
        test_responses.append(response)
    
    return TestListResponse(
        tests=test_responses,
        total_count=total_count,
        page=page,
        page_size=page_size
    )


@router.get("/tests/{test_id}", response_model=TestDetailResponse)
async def get_test_detail(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed information about a test"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers can view tests")
    
    # Get test
    test = await db.get(TestAssignment, test_id)
    if not test or test.teacher_id != current_user.id or test.deleted_at:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Get lecture information
    lecture_result = await db.execute(
        select(ReadingAssignment).where(
            ReadingAssignment.id.in_(test.selected_lecture_ids)
        )
    )
    lectures = lecture_result.scalars().all()
    
    # Build lecture info
    lecture_info = []
    for lecture in lectures:
        # Count topics in lecture structure
        topic_count = 0
        if lecture.raw_content:
            try:
                import json
                content = json.loads(lecture.raw_content) if isinstance(lecture.raw_content, str) else lecture.raw_content
                if 'lecture_structure' in content:
                    topics = content['lecture_structure'].get('topics', {})
                    topic_count = len(topics)
            except:
                topic_count = 0
        
        lecture_info.append(LectureInfo(
            id=lecture.id,
            title=lecture.assignment_title,
            subject=lecture.subject or '',
            grade_level=lecture.grade_level,
            topic_count=topic_count
        ))
    
    response = TestDetailResponse.from_orm(test)
    response.selected_lectures = lecture_info
    
    return response


@router.put("/tests/{test_id}", response_model=TestAssignmentResponse)
async def update_test(
    test_id: UUID,
    request: UpdateTestRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update test settings"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers can update tests")
    
    # Get test
    test = await db.get(TestAssignment, test_id)
    if not test or test.teacher_id != current_user.id or test.deleted_at:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Update fields
    update_data = request.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(test, field, value)
    
    await db.commit()
    await db.refresh(test)
    
    return TestAssignmentResponse.from_orm(test)


@router.post("/tests/{test_id}/generate-questions")
async def generate_test_questions(
    test_id: UUID,
    regenerate: bool = Query(False),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate AI questions for a test"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers can generate test questions")
    
    # Get test
    test = await db.get(TestAssignment, test_id)
    if not test or test.teacher_id != current_user.id or test.deleted_at:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Check if already generating
    existing_log = await db.execute(
        select(TestGenerationLog).where(
            and_(
                TestGenerationLog.test_assignment_id == test_id,
                TestGenerationLog.status == 'processing'
            )
        )
    )
    if existing_log.scalar():
        raise HTTPException(status_code=400, detail="Test generation already in progress")
    
    # Start generation in background
    background_tasks.add_task(
        generate_test_questions_task,
        str(test_id),
        regenerate
    )
    
    return {"message": "Test generation started", "test_id": test_id}


@router.get("/tests/{test_id}/generation-status", response_model=GenerationLogResponse)
async def get_generation_status(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get the status of test question generation"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers can view generation status")
    
    # Get test
    test = await db.get(TestAssignment, test_id)
    if not test or test.teacher_id != current_user.id:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Get most recent generation log
    result = await db.execute(
        select(TestGenerationLog)
        .where(TestGenerationLog.test_assignment_id == test_id)
        .order_by(TestGenerationLog.started_at.desc())
        .limit(1)
    )
    log = result.scalar_one_or_none()
    
    if not log:
        raise HTTPException(status_code=404, detail="No generation log found")
    
    return GenerationLogResponse.from_orm(log)


@router.delete("/tests/{test_id}")
async def soft_delete_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete a test"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers can delete tests")
    
    # Get test
    test = await db.get(TestAssignment, test_id)
    if not test or test.teacher_id != current_user.id or test.deleted_at:
        raise HTTPException(status_code=404, detail="Test not found")
    
    # Check if test is attached to any classrooms
    from app.models.classroom import ClassroomAssignment
    count_result = await db.execute(
        select(func.count(ClassroomAssignment.id))
        .where(
            and_(
                ClassroomAssignment.assignment_id == test.id,
                ClassroomAssignment.assignment_type == "test"
            )
        )
    )
    classroom_count = count_result.scalar() or 0
    
    if classroom_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot archive test attached to {classroom_count} classroom(s). Remove from classrooms first."
        )
    
    # Soft delete
    test.deleted_at = func.now()
    await db.commit()
    
    return {"message": "Test deleted successfully"}


@router.post("/tests/{test_id}/restore")
async def restore_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Restore a soft-deleted test"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers can restore tests")
    
    # Get test (including deleted)
    result = await db.execute(
        select(TestAssignment).where(
            and_(
                TestAssignment.id == test_id,
                TestAssignment.teacher_id == current_user.id
            )
        )
    )
    test = result.scalar_one_or_none()
    
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    
    if not test.deleted_at:
        raise HTTPException(status_code=400, detail="Test is not deleted")
    
    # Restore
    test.deleted_at = None
    await db.commit()
    
    return {"message": "Test restored successfully"}


@router.get("/lectures/available", response_model=List[LectureInfo])
async def get_available_lectures(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get list of UMALecture assignments available for test creation"""
    if current_user.role not in ["teacher", "admin"]:
        raise HTTPException(status_code=403, detail="Only teachers can view lectures")
    
    # Get all UMALecture assignments for this teacher
    result = await db.execute(
        select(ReadingAssignment).where(
            and_(
                ReadingAssignment.teacher_id == current_user.id,
                ReadingAssignment.assignment_type == 'UMALecture',
                ReadingAssignment.status == 'published',
                ReadingAssignment.deleted_at.is_(None)
            )
        ).order_by(ReadingAssignment.created_at.desc())
    )
    lectures = result.scalars().all()
    
    # Build lecture info
    lecture_info = []
    for lecture in lectures:
        # Count topics in lecture structure
        topic_count = 0
        if lecture.raw_content:
            try:
                import json
                content = json.loads(lecture.raw_content) if isinstance(lecture.raw_content, str) else lecture.raw_content
                if 'lecture_structure' in content:
                    topics = content['lecture_structure'].get('topics', {})
                    topic_count = len(topics)
            except:
                topic_count = 0
        
        lecture_info.append(LectureInfo(
            id=lecture.id,
            title=lecture.assignment_title,
            subject=lecture.subject or '',
            grade_level=lecture.grade_level,
            topic_count=topic_count
        ))
    
    return lecture_info
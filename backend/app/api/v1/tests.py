from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from uuid import UUID
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, update
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.utils.deps import get_current_user
from app.models.user import User, UserRole
from app.models.reading import ReadingAssignment
from app.models.tests import AssignmentTest, TestResult, StudentTestAttempt
from app.models.classroom import ClassroomAssignment
from app.models.umaread import UmareadAssignmentProgress
from app.services.test_generation import TestGenerationService
from app.services.test_evaluation import TestEvaluationService
from app.schemas.auth import UserRole

router = APIRouter(prefix="/tests", tags=["tests"])

# Initialize services
test_generator = TestGenerationService()
test_evaluator = TestEvaluationService()


# Schema classes for request/response
class TestQuestion(BaseModel):
    question: str
    answer_key: str
    grading_context: str
    difficulty: int = Field(ge=1, le=8)
    answer_explanation: Optional[str] = None  # New comprehensive explanation for AI evaluation
    evaluation_criteria: Optional[str] = None  # New rubric criteria for scoring
    
    class Config:
        extra = "allow"  # Allow extra fields for backward compatibility


class TestUpdateRequest(BaseModel):
    questions: List[TestQuestion]
    time_limit_minutes: int = Field(default=60, ge=10, le=180)
    max_attempts: int = Field(default=1, ge=1, le=3)
    teacher_notes: Optional[str] = None


class TestApproveRequest(BaseModel):
    expires_days: int = Field(default=30, ge=1, le=365)


class TestStartRequest(BaseModel):
    test_id: UUID


class TestSubmitRequest(BaseModel):
    responses: Dict[str, str]  # question_1: answer, question_2: answer, etc.


class TestResponse(BaseModel):
    id: UUID
    assignment_id: UUID
    assignment_title: str
    status: str
    test_questions: List[Dict[str, Any]]
    time_limit_minutes: int
    max_attempts: int
    expires_at: Optional[datetime]
    created_at: datetime
    teacher_notes: Optional[str] = None


class TestResultResponse(BaseModel):
    id: UUID
    test_id: UUID
    overall_score: float
    responses: Dict[str, Any]
    started_at: datetime
    completed_at: Optional[datetime]
    time_spent_minutes: Optional[int]


# Teacher endpoints

@router.post("/{assignment_id}/generate", response_model=TestResponse)
async def generate_test(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a draft test for an assignment (teacher only)."""
    
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can generate tests"
        )
    
    # Check if test already exists
    existing = await db.execute(
        select(AssignmentTest).where(AssignmentTest.assignment_id == assignment_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test already exists for this assignment"
        )
    
    # Generate test
    test_data = await test_generator.generate_test_for_assignment(assignment_id, db)
    
    # Create test record
    new_test = AssignmentTest(**test_data)
    db.add(new_test)
    await db.commit()
    await db.refresh(new_test)
    
    # Get assignment title
    assignment = await db.execute(
        select(ReadingAssignment).where(ReadingAssignment.id == assignment_id)
    )
    assignment = assignment.scalar_one()
    
    return TestResponse(
        id=new_test.id,
        assignment_id=new_test.assignment_id,
        assignment_title=assignment.assignment_title,
        status=new_test.status,
        test_questions=new_test.test_questions,
        time_limit_minutes=new_test.time_limit_minutes,
        max_attempts=new_test.max_attempts,
        expires_at=new_test.expires_at,
        created_at=new_test.created_at,
        teacher_notes=new_test.teacher_notes
    )


@router.get("/assignment/{assignment_id}", response_model=TestResponse)
async def get_test_by_assignment(
    assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get test by assignment ID (teacher only)."""
    
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can view test details"
        )
    
    result = await db.execute(
        select(AssignmentTest, ReadingAssignment.assignment_title)
        .join(ReadingAssignment, AssignmentTest.assignment_id == ReadingAssignment.id)
        .where(AssignmentTest.assignment_id == assignment_id)
    )
    
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    test, assignment_title = row
    
    return TestResponse(
        id=test.id,
        assignment_id=test.assignment_id,
        assignment_title=assignment_title,
        status=test.status,
        test_questions=test.test_questions,
        time_limit_minutes=test.time_limit_minutes,
        max_attempts=test.max_attempts,
        expires_at=test.expires_at,
        created_at=test.created_at,
        teacher_notes=test.teacher_notes
    )


@router.get("/available", response_model=List[Dict[str, Any]])
async def get_available_tests(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available tests for current student."""
    
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can view available tests"
        )
    
    # Query for available tests - only show tests for completed assignments
    query = select(
        AssignmentTest.id,
        AssignmentTest.assignment_id,
        AssignmentTest.time_limit_minutes,
        AssignmentTest.max_attempts,
        AssignmentTest.expires_at,
        ReadingAssignment.assignment_title,
        func.count(StudentTestAttempt.id).label("attempts_used")
    ).select_from(AssignmentTest).join(
        ReadingAssignment,
        AssignmentTest.assignment_id == ReadingAssignment.id
    ).join(
        UmareadAssignmentProgress,
        and_(
            UmareadAssignmentProgress.assignment_id == ReadingAssignment.id,
            UmareadAssignmentProgress.student_id == current_user.id,
            UmareadAssignmentProgress.completed_at.isnot(None)  # Must be completed
        )
    ).outerjoin(
        StudentTestAttempt,
        and_(
            StudentTestAttempt.assignment_test_id == AssignmentTest.id,
            StudentTestAttempt.student_id == current_user.id,
            StudentTestAttempt.status.in_(["submitted", "evaluated"])  # Only count completed attempts
        )
    ).where(
        and_(
            AssignmentTest.status == "approved",
            AssignmentTest.expires_at > datetime.utcnow()
        )
    ).group_by(
        AssignmentTest.id,
        AssignmentTest.assignment_id,
        AssignmentTest.time_limit_minutes,
        AssignmentTest.max_attempts,
        AssignmentTest.expires_at,
        ReadingAssignment.assignment_title
    )
    
    results = await db.execute(query)
    
    available_tests = []
    for row in results:
        if row.attempts_used < row.max_attempts:
            # Still has attempts remaining - can take test
            available_tests.append({
                "test_id": str(row.id),
                "assignment_id": str(row.assignment_id),
                "assignment_title": row.assignment_title,
                "time_limit_minutes": row.time_limit_minutes,
                "attempts_remaining": row.max_attempts - row.attempts_used,
                "expires_at": row.expires_at.isoformat(),
                "classroom_assignment_id": "",  # Simplified for now
                "status": "available"
            })
        elif row.attempts_used > 0:
            # Has used all attempts - show as completed with link to results
            # Get the most recent attempt ID for results viewing
            attempt_query = await db.execute(
                select(StudentTestAttempt.id)
                .where(
                    and_(
                        StudentTestAttempt.assignment_test_id == row.id,
                        StudentTestAttempt.student_id == current_user.id,
                        StudentTestAttempt.status.in_(["submitted", "evaluated"])
                    )
                )
                .order_by(StudentTestAttempt.created_at.desc())
                .limit(1)
            )
            latest_attempt = attempt_query.scalar_one_or_none()
            
            if latest_attempt:
                available_tests.append({
                    "test_id": str(row.id),
                    "assignment_id": str(row.assignment_id),
                    "assignment_title": row.assignment_title,
                    "time_limit_minutes": row.time_limit_minutes,
                    "attempts_remaining": 0,
                    "expires_at": row.expires_at.isoformat(),
                    "classroom_assignment_id": "",
                    "status": "completed",
                    "result_id": str(latest_attempt)
                })
    
    return available_tests


@router.get("/{test_id}", response_model=TestResponse)
async def get_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get test details (teacher only)."""
    
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can view test details"
        )
    
    result = await db.execute(
        select(AssignmentTest, ReadingAssignment.assignment_title)
        .join(ReadingAssignment, AssignmentTest.assignment_id == ReadingAssignment.id)
        .where(AssignmentTest.id == test_id)
    )
    
    row = result.first()
    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    test, assignment_title = row
    
    return TestResponse(
        id=test.id,
        assignment_id=test.assignment_id,
        assignment_title=assignment_title,
        status=test.status,
        test_questions=test.test_questions,
        time_limit_minutes=test.time_limit_minutes,
        max_attempts=test.max_attempts,
        expires_at=test.expires_at,
        created_at=test.created_at,
        teacher_notes=test.teacher_notes
    )


@router.put("/{test_id}", response_model=TestResponse)
async def update_test(
    test_id: UUID,
    request: TestUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update test questions and settings (teacher only)."""
    
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can update tests"
        )
    
    # Check test exists and is in draft status
    test = await db.execute(
        select(AssignmentTest).where(AssignmentTest.id == test_id)
    )
    test = test.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    if test.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update draft tests"
        )
    
    # Update test
    questions_dict = [q.dict() for q in request.questions]
    
    await db.execute(
        update(AssignmentTest)
        .where(AssignmentTest.id == test_id)
        .values(
            test_questions=questions_dict,
            time_limit_minutes=request.time_limit_minutes,
            max_attempts=request.max_attempts,
            teacher_notes=request.teacher_notes,
            updated_at=datetime.utcnow()
        )
    )
    await db.commit()
    
    # Return updated test
    return await get_test(test_id, current_user, db)


@router.post("/{test_id}/approve")
async def approve_test(
    test_id: UUID,
    request: TestApproveRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Approve test for student access (teacher only)."""
    
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can approve tests"
        )
    
    # Check test exists and is in draft status
    test = await db.execute(
        select(AssignmentTest).where(AssignmentTest.id == test_id)
    )
    test = test.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    if test.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test is already approved or archived"
        )
    
    # Approve test
    expires_at = datetime.utcnow() + timedelta(days=request.expires_days)
    
    await db.execute(
        update(AssignmentTest)
        .where(AssignmentTest.id == test_id)
        .values(
            status="approved",
            approved_by=current_user.id,
            approved_at=datetime.utcnow(),
            expires_at=expires_at,
            updated_at=datetime.utcnow()
        )
    )
    await db.commit()
    
    return {"message": "Test approved successfully", "expires_at": expires_at}


@router.delete("/{test_id}")
async def delete_test(
    test_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a test (teacher only, draft tests only)."""
    
    try:
        if current_user.role != UserRole.TEACHER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only teachers can delete tests"
            )
        
        # Check test exists and verify ownership through assignment
        result = await db.execute(
            select(AssignmentTest, ReadingAssignment)
            .join(ReadingAssignment, AssignmentTest.assignment_id == ReadingAssignment.id)
            .where(
                and_(
                    AssignmentTest.id == test_id,
                    ReadingAssignment.teacher_id == current_user.id
                )
            )
        )
        row = result.first()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Test not found or you don't have permission to access it"
            )
        
        test, assignment = row
        
        if test.status != "draft":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only delete draft tests"
            )
        
        # Delete the test
        await db.delete(test)
        await db.commit()
        
        return {"message": "Test deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        print(f"Error in delete_test: {str(e)}")
        print(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting test: {str(e)}"
        )


# Student endpoints


@router.post("/start", response_model=Dict[str, Any])
async def start_test(
    request: TestStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start a test attempt (student only)."""
    
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can start tests"
        )
    
    # Get test details
    test = await db.execute(
        select(AssignmentTest).where(AssignmentTest.id == request.test_id)
    )
    test = test.scalar_one_or_none()
    
    if not test:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test not found"
        )
    
    if test.status != "approved" or test.expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Test not available"
        )
    
    # Calculate attempt number
    existing_attempts = await db.execute(
        select(func.count(TestResult.id))
        .where(
            and_(
                TestResult.test_id == request.test_id,
                TestResult.student_id == current_user.id
            )
        )
    )
    attempt_number = existing_attempts.scalar() + 1
    
    if attempt_number > test.max_attempts:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Maximum attempts exceeded"
        )
    
    # Create result record
    new_result = TestResult(
        id=uuid.uuid4(),
        test_id=request.test_id,
        student_id=current_user.id,
        classroom_assignment_id=uuid.uuid4(),  # Simplified for now
        responses={},
        overall_score=0,
        started_at=datetime.utcnow(),
        attempt_number=attempt_number
    )
    
    db.add(new_result)
    await db.commit()
    
    # Return test questions without answer keys
    questions_for_student = []
    for i, q in enumerate(test.test_questions):
        questions_for_student.append({
            "question_number": i + 1,
            "question": q["question"],
            "difficulty": q["difficulty"]
        })
    
    return {
        "test_result_id": str(new_result.id),
        "questions": questions_for_student,
        "time_limit_minutes": test.time_limit_minutes,
        "started_at": new_result.started_at.isoformat()
    }


@router.put("/{test_result_id}/submit", response_model=TestResultResponse)
async def submit_test(
    test_result_id: UUID,
    request: TestSubmitRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Submit completed test for evaluation (student only)."""
    
    if current_user.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only students can submit tests"
        )
    
    # Get test result
    result = await db.execute(
        select(TestResult).where(
            and_(
                TestResult.id == test_result_id,
                TestResult.student_id == current_user.id
            )
        )
    )
    test_result = result.scalar_one_or_none()
    
    if not test_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test result not found"
        )
    
    if test_result.completed_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test already submitted"
        )
    
    # Get test questions and assignment info
    test_data = await db.execute(
        select(AssignmentTest, ReadingAssignment.grade_level)
        .join(ReadingAssignment, AssignmentTest.assignment_id == ReadingAssignment.id)
        .where(AssignmentTest.id == test_result.test_id)
    )
    test, grade_level = test_data.first()
    
    # Evaluate responses
    evaluation = await test_evaluator.evaluate_test_response(
        test_questions=test.test_questions,
        student_responses=request.responses,
        grade_level=grade_level
    )
    
    # Update test result
    completed_at = datetime.utcnow()
    time_spent = test_evaluator.calculate_time_spent(test_result.started_at, completed_at)
    
    await db.execute(
        update(TestResult)
        .where(TestResult.id == test_result_id)
        .values(
            responses=evaluation["responses"],
            overall_score=evaluation["overall_score"],
            completed_at=completed_at,
            time_spent_minutes=time_spent
        )
    )
    await db.commit()
    
    return TestResultResponse(
        id=test_result_id,
        test_id=test_result.test_id,
        overall_score=evaluation["overall_score"],
        responses=evaluation["responses"],
        started_at=test_result.started_at,
        completed_at=completed_at,
        time_spent_minutes=time_spent
    )


@router.get("/results/{test_result_id}", response_model=TestResultResponse)
async def get_test_results(
    test_result_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get test results (student can only see their own)."""
    
    # Build query based on user role
    query = select(TestResult).where(TestResult.id == test_result_id)
    
    if current_user.role == UserRole.STUDENT:
        query = query.where(TestResult.student_id == current_user.id)
    
    result = await db.execute(query)
    test_result = result.scalar_one_or_none()
    
    if not test_result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test result not found"
        )
    
    return TestResultResponse(
        id=test_result.id,
        test_id=test_result.test_id,
        overall_score=float(test_result.overall_score),
        responses=test_result.responses,
        started_at=test_result.started_at,
        completed_at=test_result.completed_at,
        time_spent_minutes=test_result.time_spent_minutes
    )
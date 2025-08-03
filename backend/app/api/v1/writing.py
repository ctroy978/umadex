from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_, update, delete
from sqlalchemy.orm import selectinload
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import logging

from app.core.database import get_db
from app.utils.supabase_deps import get_current_user_supabase as get_current_user
from app.models import WritingAssignment, StudentWritingSubmission, ClassroomAssignment, Classroom
from app.models.classroom import StudentAssignment, ClassroomStudent
from app.models.user import User, UserRole
from app.schemas.writing import (
    WritingAssignmentCreate,
    WritingAssignmentUpdate,
    WritingAssignmentResponse,
    WritingAssignmentListResponse,
    StudentWritingSubmissionCreate,
    StudentWritingSubmissionUpdate,
    StudentWritingSubmissionResponse,
    StudentWritingDraft,
    StudentWritingProgress
)
from app.services.writing_ai import WritingAIService

router = APIRouter(prefix="/writing", tags=["writing"])
logger = logging.getLogger(__name__)


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


@router.post("/assignments", response_model=WritingAssignmentResponse)
async def create_writing_assignment(
    assignment: WritingAssignmentCreate,
    current_user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Create a new writing assignment."""
    db_assignment = WritingAssignment(
        teacher_id=current_user.id,
        title=assignment.title,
        prompt_text=assignment.prompt_text,
        word_count_min=assignment.word_count_min,
        word_count_max=assignment.word_count_max,
        evaluation_criteria=assignment.evaluation_criteria.model_dump(),
        instructions=assignment.instructions,
        grade_level=assignment.grade_level,
        subject=assignment.subject
    )
    
    db.add(db_assignment)
    await db.commit()
    await db.refresh(db_assignment)
    
    # Get classroom count (only active assignments, not soft-deleted)
    result = await db.execute(
        select(func.count(ClassroomAssignment.id))
        .where(
            and_(
                ClassroomAssignment.assignment_id == db_assignment.id,
                ClassroomAssignment.assignment_type == "writing",
                ClassroomAssignment.removed_from_classroom_at.is_(None)
            )
        )
    )
    classroom_count = result.scalar() or 0
    
    response = WritingAssignmentResponse.model_validate(db_assignment)
    response.classroom_count = classroom_count
    response.is_archived = db_assignment.deleted_at is not None
    
    return response


@router.get("/assignments", response_model=WritingAssignmentListResponse)
async def list_writing_assignments(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    search: Optional[str] = None,
    grade_level: Optional[str] = None,
    subject: Optional[str] = None,
    archived: Optional[bool] = None,
    current_user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """List teacher's writing assignments with pagination and filters."""
    # Build base query
    stmt = select(WritingAssignment).where(
        WritingAssignment.teacher_id == current_user.id
    )
    
    # Apply filters
    if search:
        search_term = f"%{search}%"
        stmt = stmt.where(
            or_(
                WritingAssignment.title.ilike(search_term),
                WritingAssignment.prompt_text.ilike(search_term)
            )
        )
    
    if grade_level:
        stmt = stmt.where(WritingAssignment.grade_level == grade_level)
    
    if subject:
        stmt = stmt.where(WritingAssignment.subject == subject)
    
    if archived is not None:
        if archived:
            stmt = stmt.where(WritingAssignment.deleted_at.isnot(None))
        else:
            stmt = stmt.where(WritingAssignment.deleted_at.is_(None))
    
    # Get total count
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0
    
    # Apply pagination
    stmt = stmt.order_by(WritingAssignment.created_at.desc())
    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    
    result = await db.execute(stmt)
    assignments = result.scalars().all()
    
    # Get classroom counts for each assignment
    assignment_responses = []
    for assignment in assignments:
        count_result = await db.execute(
            select(func.count(ClassroomAssignment.id))
            .where(
                and_(
                    ClassroomAssignment.assignment_id == assignment.id,
                    ClassroomAssignment.assignment_type == "writing",
                    ClassroomAssignment.removed_from_classroom_at.is_(None)
                )
            )
        )
        classroom_count = count_result.scalar() or 0
        
        response = WritingAssignmentResponse.model_validate(assignment)
        response.classroom_count = classroom_count
        response.is_archived = assignment.deleted_at is not None
        assignment_responses.append(response)
    
    total_pages = (total + per_page - 1) // per_page
    
    return WritingAssignmentListResponse(
        assignments=assignment_responses,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages
    )


@router.get("/assignments/{assignment_id}", response_model=WritingAssignmentResponse)
async def get_writing_assignment(
    assignment_id: UUID,
    current_user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific writing assignment."""
    result = await db.execute(
        select(WritingAssignment).where(
            and_(
                WritingAssignment.id == assignment_id,
                WritingAssignment.teacher_id == current_user.id
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Writing assignment not found")
    
    # Get classroom count (only active assignments, not soft-deleted)
    count_result = await db.execute(
        select(func.count(ClassroomAssignment.id))
        .where(
            and_(
                ClassroomAssignment.assignment_id == assignment.id,
                ClassroomAssignment.assignment_type == "writing",
                ClassroomAssignment.removed_from_classroom_at.is_(None)
            )
        )
    )
    classroom_count = count_result.scalar() or 0
    
    response = WritingAssignmentResponse.model_validate(assignment)
    response.classroom_count = classroom_count
    response.is_archived = assignment.deleted_at is not None
    
    return response


@router.put("/assignments/{assignment_id}", response_model=WritingAssignmentResponse)
async def update_writing_assignment(
    assignment_id: UUID,
    update_data: WritingAssignmentUpdate,
    current_user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Update a writing assignment."""
    result = await db.execute(
        select(WritingAssignment).where(
            and_(
                WritingAssignment.id == assignment_id,
                WritingAssignment.teacher_id == current_user.id
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Writing assignment not found")
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    
    # Handle evaluation_criteria separately
    if 'evaluation_criteria' in update_dict and update_dict['evaluation_criteria'] is not None:
        update_dict['evaluation_criteria'] = update_data.evaluation_criteria.model_dump()
    
    for field, value in update_dict.items():
        setattr(assignment, field, value)
    
    assignment.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(assignment)
    
    # Get classroom count (only active assignments, not soft-deleted)
    count_result = await db.execute(
        select(func.count(ClassroomAssignment.id))
        .where(
            and_(
                ClassroomAssignment.assignment_id == assignment.id,
                ClassroomAssignment.assignment_type == "writing",
                ClassroomAssignment.removed_from_classroom_at.is_(None)
            )
        )
    )
    classroom_count = count_result.scalar() or 0
    
    response = WritingAssignmentResponse.model_validate(assignment)
    response.classroom_count = classroom_count
    response.is_archived = assignment.deleted_at is not None
    
    return response


@router.delete("/assignments/{assignment_id}")
async def archive_writing_assignment(
    assignment_id: UUID,
    current_user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Archive (soft delete) a writing assignment."""
    result = await db.execute(
        select(WritingAssignment).where(
            and_(
                WritingAssignment.id == assignment_id,
                WritingAssignment.teacher_id == current_user.id
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Writing assignment not found")
    
    # Check if assignment is attached to any ACTIVE classrooms (not soft-deleted)
    count_result = await db.execute(
        select(func.count(ClassroomAssignment.id))
        .where(
            and_(
                ClassroomAssignment.assignment_id == assignment.id,
                ClassroomAssignment.assignment_type == "writing",
                ClassroomAssignment.removed_from_classroom_at.is_(None)
            )
        )
    )
    classroom_count = count_result.scalar() or 0
    
    if classroom_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot archive assignment attached to {classroom_count} classroom(s). Remove from classrooms first."
        )
    
    assignment.deleted_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Writing assignment archived successfully"}


@router.post("/assignments/{assignment_id}/restore")
async def restore_writing_assignment(
    assignment_id: UUID,
    current_user: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """Restore an archived writing assignment."""
    result = await db.execute(
        select(WritingAssignment).where(
            and_(
                WritingAssignment.id == assignment_id,
                WritingAssignment.teacher_id == current_user.id,
                WritingAssignment.deleted_at.isnot(None)
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Archived writing assignment not found")
    
    assignment.deleted_at = None
    assignment.updated_at = datetime.utcnow()
    await db.commit()
    
    return {"message": "Writing assignment restored successfully"}


# Student endpoints

@router.get("/student/assignments/{assignment_id}", response_model=WritingAssignmentResponse)
async def get_student_writing_assignment(
    assignment_id: UUID,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Get a writing assignment for a student."""
    # First check if student has access to this assignment through their classrooms
    result = await db.execute(
        select(WritingAssignment)
        .join(ClassroomAssignment, and_(
            ClassroomAssignment.assignment_id == WritingAssignment.id,
            ClassroomAssignment.assignment_type == "writing",
            ClassroomAssignment.removed_from_classroom_at.is_(None)  # Only active assignments
        ))
        .join(Classroom, Classroom.id == ClassroomAssignment.classroom_id)
        .join(ClassroomStudent, and_(
            ClassroomStudent.classroom_id == Classroom.id,
            ClassroomStudent.student_id == current_user.id,
            ClassroomStudent.removed_at.is_(None)
        ))
        .where(
            and_(
                WritingAssignment.id == assignment_id,
                WritingAssignment.deleted_at.is_(None)
            )
        )
    )
    assignment = result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Writing assignment not found or access denied")
    
    response = WritingAssignmentResponse.model_validate(assignment)
    response.is_archived = False
    
    return response


@router.post("/student/assignments/{assignment_id}/start")
async def start_writing_assignment(
    assignment_id: UUID,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Start working on a writing assignment."""
    # First verify student has access and get the classroom assignment
    ca_result = await db.execute(
        select(ClassroomAssignment)
        .join(Classroom, Classroom.id == ClassroomAssignment.classroom_id)
        .join(ClassroomStudent, and_(
            ClassroomStudent.classroom_id == Classroom.id,
            ClassroomStudent.student_id == current_user.id,
            ClassroomStudent.removed_at.is_(None)
        ))
        .where(
            and_(
                ClassroomAssignment.assignment_id == assignment_id,
                ClassroomAssignment.assignment_type == "writing",
                ClassroomAssignment.removed_from_classroom_at.is_(None)  # Only active assignments
            )
        )
    )
    classroom_assignment = ca_result.scalar_one_or_none()
    
    if not classroom_assignment:
        raise HTTPException(status_code=404, detail="Assignment not found or access denied")
    
    # Check if student assignment already exists
    result = await db.execute(
        select(StudentAssignment)
        .where(
            and_(
                StudentAssignment.classroom_assignment_id == classroom_assignment.id,
                StudentAssignment.student_id == current_user.id
            )
        )
    )
    student_assignment = result.scalar_one_or_none()
    
    if not student_assignment:
        # Create new StudentAssignment record
        student_assignment = StudentAssignment(
            classroom_assignment_id=classroom_assignment.id,
            student_id=current_user.id,
            assignment_id=assignment_id,
            assignment_type="writing",
            progress_metadata={
                "draft_content": "",
                "selected_techniques": [],
                "submission_count": 0,
                "current_score": None,
                "technique_validations": {},
                "last_saved_at": datetime.utcnow().isoformat()
            },
            status="in_progress"
        )
        db.add(student_assignment)
        await db.commit()
        await db.refresh(student_assignment)
    elif not student_assignment.progress_metadata:
        # Initialize progress if not started
        student_assignment.progress_metadata = {
            "draft_content": "",
            "selected_techniques": [],
            "submission_count": 0,
            "current_score": None,
            "technique_validations": {},
            "last_saved_at": datetime.utcnow().isoformat()
        }
        student_assignment.status = "in_progress"
        await db.commit()
    
    return {"message": "Assignment started", "progress": student_assignment.progress_metadata}


@router.put("/student/assignments/{assignment_id}/draft")
async def save_writing_draft(
    assignment_id: UUID,
    draft: StudentWritingDraft,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Save a draft of the writing assignment."""
    # Get the student assignment record (only if classroom assignment is still active)
    result = await db.execute(
        select(StudentAssignment)
        .join(ClassroomAssignment, and_(
            ClassroomAssignment.id == StudentAssignment.classroom_assignment_id,
            ClassroomAssignment.assignment_type == "writing",
            ClassroomAssignment.assignment_id == assignment_id,
            ClassroomAssignment.removed_from_classroom_at.is_(None)  # Only active assignments
        ))
        .where(StudentAssignment.student_id == current_user.id)
    )
    student_assignment = result.scalar_one_or_none()
    
    if not student_assignment:
        # Try to create it if it doesn't exist
        ca_result = await db.execute(
            select(ClassroomAssignment)
            .join(Classroom, Classroom.id == ClassroomAssignment.classroom_id)
            .join(ClassroomStudent, and_(
                ClassroomStudent.classroom_id == Classroom.id,
                ClassroomStudent.student_id == current_user.id,
                ClassroomStudent.removed_at.is_(None)
            ))
            .where(
                and_(
                    ClassroomAssignment.assignment_id == assignment_id,
                    ClassroomAssignment.assignment_type == "writing",
                    ClassroomAssignment.removed_from_classroom_at.is_(None)  # Only active assignments
                )
            )
        )
        classroom_assignment = ca_result.scalar_one_or_none()
        
        if not classroom_assignment:
            raise HTTPException(status_code=404, detail="Assignment not found or access denied")
        
        # Create new StudentAssignment record
        student_assignment = StudentAssignment(
            classroom_assignment_id=classroom_assignment.id,
            student_id=current_user.id,
            assignment_id=assignment_id,
            assignment_type="writing",
            progress_metadata={},
            status="not_started"
        )
        db.add(student_assignment)
        await db.commit()
        await db.refresh(student_assignment)
    
    # Update progress
    if not student_assignment.progress_metadata:
        student_assignment.progress_metadata = {}
    
    student_assignment.progress_metadata.update({
        "draft_content": draft.content,
        "selected_techniques": draft.selected_techniques,
        "word_count": draft.word_count,
        "last_saved_at": datetime.utcnow().isoformat()
    })
    
    if student_assignment.status == "not_started":
        student_assignment.status = "in_progress"
    
    await db.commit()
    
    return {"message": "Draft saved successfully", "saved_at": student_assignment.progress_metadata["last_saved_at"]}


@router.post("/student/assignments/{assignment_id}/techniques")
async def update_selected_techniques(
    assignment_id: UUID,
    techniques: List[str],
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Update the selected writing techniques for an assignment."""
    # Get the student assignment record (only if classroom assignment is still active)
    result = await db.execute(
        select(StudentAssignment)
        .join(ClassroomAssignment, and_(
            ClassroomAssignment.id == StudentAssignment.classroom_assignment_id,
            ClassroomAssignment.assignment_type == "writing",
            ClassroomAssignment.assignment_id == assignment_id,
            ClassroomAssignment.removed_from_classroom_at.is_(None)  # Only active assignments
        ))
        .where(StudentAssignment.student_id == current_user.id)
    )
    student_assignment = result.scalar_one_or_none()
    
    if not student_assignment:
        raise HTTPException(status_code=404, detail="Assignment not found or access denied")
    
    # Update selected techniques
    if not student_assignment.progress_metadata:
        student_assignment.progress_metadata = {}
    
    student_assignment.progress_metadata["selected_techniques"] = techniques[:5]  # Limit to 5 techniques
    student_assignment.progress_metadata["last_saved_at"] = datetime.utcnow().isoformat()
    
    await db.commit()
    
    return {"message": "Techniques updated", "selected_techniques": student_assignment.progress_metadata["selected_techniques"]}


@router.post("/student/assignments/{assignment_id}/submit", response_model=StudentWritingSubmissionResponse)
async def submit_writing_assignment(
    assignment_id: UUID,
    submission: StudentWritingSubmissionCreate,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Submit a final writing response."""
    # Get the student assignment record (only if classroom assignment is still active)
    result = await db.execute(
        select(StudentAssignment)
        .join(ClassroomAssignment, and_(
            ClassroomAssignment.id == StudentAssignment.classroom_assignment_id,
            ClassroomAssignment.assignment_type == "writing",
            ClassroomAssignment.assignment_id == assignment_id,
            ClassroomAssignment.removed_from_classroom_at.is_(None)  # Only active assignments
        ))
        .where(StudentAssignment.student_id == current_user.id)
    )
    student_assignment = result.scalar_one_or_none()
    
    if not student_assignment:
        raise HTTPException(status_code=404, detail="Assignment not found or access denied")
    
    # Get the writing assignment details
    assignment_result = await db.execute(
        select(WritingAssignment).where(WritingAssignment.id == assignment_id)
    )
    writing_assignment = assignment_result.scalar_one()
    
    # Validate word count
    if submission.word_count < writing_assignment.word_count_min or submission.word_count > writing_assignment.word_count_max:
        raise HTTPException(
            status_code=400,
            detail=f"Word count must be between {writing_assignment.word_count_min} and {writing_assignment.word_count_max}"
        )
    
    # Check if this is a revision
    submission_count = student_assignment.progress_metadata.get("submission_count", 0) + 1 if student_assignment.progress_metadata else 1
    
    # Create submission record
    db_submission = StudentWritingSubmission(
        student_assignment_id=student_assignment.id,
        writing_assignment_id=assignment_id,
        student_id=current_user.id,
        response_text=submission.response_text,
        selected_techniques=submission.selected_techniques,
        word_count=submission.word_count,
        submission_attempt=submission_count,
        is_final_submission=submission.is_final
    )
    
    db.add(db_submission)
    
    # Update student assignment progress
    if not student_assignment.progress_metadata:
        student_assignment.progress_metadata = {}
    
    student_assignment.progress_metadata.update({
        "submission_count": submission_count,
        "last_saved_at": datetime.utcnow().isoformat()
    })
    
    if submission.is_final:
        student_assignment.status = "completed"
    
    await db.commit()
    await db.refresh(db_submission)
    
    # Store the ID before any additional operations
    submission_id = db_submission.id
    
    # Now update with the submission ID after it's been generated
    student_assignment.progress_metadata["last_submission_id"] = str(submission_id)
    await db.commit()
    
    # AI evaluation will be triggered asynchronously after response
    # For now, just log that we'll evaluate it
    logger.info(f"Writing submission {submission_id} will be evaluated asynchronously")
    
    # Prepare response data before potential session issues
    response_data = {
        'id': submission_id,
        'student_assignment_id': student_assignment.id,
        'writing_assignment_id': assignment_id,
        'student_id': current_user.id,
        'response_text': submission.response_text,
        'selected_techniques': submission.selected_techniques,
        'word_count': submission.word_count,
        'submission_attempt': submission_count,
        'is_final_submission': submission.is_final,
        'submitted_at': db_submission.submitted_at,
        'score': getattr(db_submission, 'score', None),
        'ai_feedback': getattr(db_submission, 'ai_feedback', None)
    }
    
    return StudentWritingSubmissionResponse(**response_data)


@router.post("/student/submissions/{submission_id}/evaluate")
async def evaluate_submission(
    submission_id: UUID,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Trigger AI evaluation for a submission."""
    # Get the submission
    result = await db.execute(
        select(StudentWritingSubmission)
        .where(
            and_(
                StudentWritingSubmission.id == submission_id,
                StudentWritingSubmission.student_id == current_user.id
            )
        )
    )
    submission = result.scalar_one_or_none()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    # Check if already evaluated
    if submission.score is not None:
        return {"message": "Submission already evaluated", "score": submission.score}
    
    # Get the writing assignment
    assignment_result = await db.execute(
        select(WritingAssignment).where(WritingAssignment.id == submission.writing_assignment_id)
    )
    writing_assignment = assignment_result.scalar_one()
    
    # Get student assignment for grade level
    sa_result = await db.execute(
        select(StudentAssignment, ClassroomAssignment, Classroom)
        .join(ClassroomAssignment, ClassroomAssignment.id == StudentAssignment.classroom_assignment_id)
        .join(Classroom, Classroom.id == ClassroomAssignment.classroom_id)
        .where(StudentAssignment.id == submission.student_assignment_id)
    )
    sa_data = sa_result.first()
    grade_level = sa_data.Classroom.name if sa_data else "Middle School"
    
    # Trigger AI evaluation
    ai_service = WritingAIService()
    
    try:
        logger.info(f"Starting AI evaluation for submission {submission_id}")
        logger.info(f"Assignment: {writing_assignment.id}, Grade level: {grade_level}")
        logger.info(f"Word count: {submission.word_count}, Techniques: {submission.selected_techniques}")
        
        evaluation_result = await ai_service.evaluate_writing_submission(
            student_response=submission.response_text,
            word_count=submission.word_count,
            selected_techniques=submission.selected_techniques,
            assignment=writing_assignment,
            grade_level=grade_level
        )
        
        logger.info(f"AI evaluation completed. Score: {evaluation_result.get('score', 'N/A')}")
        
        # Update submission with AI evaluation
        submission.score = float(evaluation_result['score'])
        submission.ai_feedback = evaluation_result['ai_feedback']
        
        # Update student assignment progress if exists
        if sa_data:
            student_assignment = sa_data.StudentAssignment
            if not student_assignment.progress_metadata:
                student_assignment.progress_metadata = {}
            student_assignment.progress_metadata['current_score'] = float(evaluation_result['score'])
            student_assignment.progress_metadata['technique_validations'] = evaluation_result['ai_feedback']['technique_validation']
        
        await db.commit()
        
        return {
            "message": "Evaluation completed",
            "score": evaluation_result['score'],
            "ai_feedback": evaluation_result['ai_feedback']
        }
        
    except Exception as e:
        logger.error(f"AI evaluation failed for submission {submission_id}: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail="Evaluation failed")


@router.get("/student/assignments/{assignment_id}/feedback")
async def get_writing_feedback(
    assignment_id: UUID,
    submission_id: Optional[UUID] = None,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Get AI feedback for a writing submission."""
    # First verify student still has access to this assignment
    access_check = await db.execute(
        select(ClassroomAssignment)
        .join(Classroom, Classroom.id == ClassroomAssignment.classroom_id)
        .join(ClassroomStudent, and_(
            ClassroomStudent.classroom_id == Classroom.id,
            ClassroomStudent.student_id == current_user.id,
            ClassroomStudent.removed_at.is_(None)
        ))
        .where(
            and_(
                ClassroomAssignment.assignment_id == assignment_id,
                ClassroomAssignment.assignment_type == "writing",
                ClassroomAssignment.removed_from_classroom_at.is_(None)  # Only active assignments
            )
        )
    )
    
    if not access_check.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Assignment not found or access denied")
    
    # Get the latest submission or specific submission
    stmt = select(StudentWritingSubmission).where(
        and_(
            StudentWritingSubmission.writing_assignment_id == assignment_id,
            StudentWritingSubmission.student_id == current_user.id
        )
    )
    
    if submission_id:
        stmt = stmt.where(StudentWritingSubmission.id == submission_id)
    else:
        stmt = stmt.order_by(StudentWritingSubmission.submitted_at.desc()).limit(1)
    
    result = await db.execute(stmt)
    submission = result.scalar_one_or_none()
    
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    
    if not submission.ai_feedback:
        return {"message": "Feedback is being generated. Please check back later."}
    
    return {
        "submission_id": submission.id,
        "score": submission.score,
        "feedback": submission.ai_feedback,
        "can_revise": not submission.is_final_submission
    }


@router.get("/student/assignments/{assignment_id}/progress", response_model=StudentWritingProgress)
async def get_writing_progress(
    assignment_id: UUID,
    current_user: User = Depends(require_student),
    db: AsyncSession = Depends(get_db)
):
    """Get the current progress for a writing assignment."""
    # First verify student has access to the assignment
    access_check = await db.execute(
        select(WritingAssignment)
        .join(ClassroomAssignment, and_(
            ClassroomAssignment.assignment_id == WritingAssignment.id,
            ClassroomAssignment.assignment_type == "writing",
            ClassroomAssignment.removed_from_classroom_at.is_(None)  # Only active assignments
        ))
        .join(Classroom, Classroom.id == ClassroomAssignment.classroom_id)
        .join(ClassroomStudent, and_(
            ClassroomStudent.classroom_id == Classroom.id,
            ClassroomStudent.student_id == current_user.id,
            ClassroomStudent.removed_at.is_(None)
        ))
        .where(
            and_(
                WritingAssignment.id == assignment_id,
                WritingAssignment.deleted_at.is_(None)
            )
        )
    )
    
    if not access_check.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Assignment not found or access denied")
    
    # Try to get existing progress from StudentAssignment
    result = await db.execute(
        select(StudentAssignment)
        .join(ClassroomAssignment, and_(
            ClassroomAssignment.id == StudentAssignment.classroom_assignment_id,
            ClassroomAssignment.assignment_type == "writing",
            ClassroomAssignment.assignment_id == assignment_id
        ))
        .where(StudentAssignment.student_id == current_user.id)
    )
    student_assignment = result.scalar_one_or_none()
    
    if not student_assignment:
        # Return empty progress if no record exists yet
        return StudentWritingProgress(
            student_assignment_id=None,
            draft_content="",
            selected_techniques=[],
            word_count=0,
            last_saved_at=None,
            status="not_started",
            submission_count=0,
            is_completed=False,
            submissions=[]
        )
    
    progress = student_assignment.progress_metadata or {}
    
    # Get all submissions for this assignment
    submissions_result = await db.execute(
        select(StudentWritingSubmission)
        .where(
            and_(
                StudentWritingSubmission.student_assignment_id == student_assignment.id,
                StudentWritingSubmission.student_id == current_user.id
            )
        )
        .order_by(StudentWritingSubmission.submission_attempt.desc())
    )
    submissions = submissions_result.scalars().all()
    
    # Convert submissions to response format
    submission_responses = []
    for submission in submissions:
        submission_responses.append(StudentWritingSubmissionResponse(
            id=submission.id,
            student_assignment_id=submission.student_assignment_id,
            writing_assignment_id=submission.writing_assignment_id,
            student_id=submission.student_id,
            response_text=submission.response_text,
            selected_techniques=submission.selected_techniques,
            word_count=submission.word_count,
            submission_attempt=submission.submission_attempt,
            is_final_submission=submission.is_final_submission,
            submitted_at=submission.submitted_at,
            score=submission.score,
            ai_feedback=submission.ai_feedback
        ))
    
    return StudentWritingProgress(
        student_assignment_id=student_assignment.id,
        draft_content=progress.get("draft_content", ""),
        selected_techniques=progress.get("selected_techniques", []),
        word_count=progress.get("word_count", 0),
        last_saved_at=progress.get("last_saved_at"),
        status=student_assignment.status,
        submission_count=progress.get("submission_count", 0),
        is_completed=student_assignment.status == "completed",
        submissions=submission_responses
    )
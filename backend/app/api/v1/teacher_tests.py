"""
Teacher test management API endpoints
"""
import logging
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, text
from pydantic import BaseModel, Field

from app.core.database import get_db
from app.models.user import User
from app.models.tests import AssignmentTest, StudentTestAttempt
from app.models.reading import ReadingAssignment
from app.models.classroom import ClassroomAssignment, ClassroomStudent
from app.utils.deps import get_current_user
from app.services.test_evaluation_v2 import TestEvaluationServiceV2

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/teacher/tests", tags=["teacher-tests"])


class ClassroomTestResultsResponse(BaseModel):
    assignment_id: UUID
    assignment_title: str
    total_students: int
    completed_tests: int
    pending_review: int
    average_score: float
    results: List[Dict[str, Any]]


class TestOverrideRequest(BaseModel):
    question_number: Optional[int] = Field(None, description="Question number (0-9) or None for overall score")
    override_score: int = Field(..., ge=0, le=100)
    override_reason: str = Field(..., min_length=10, max_length=500)
    override_feedback: Optional[str] = None


class EvaluationRegenerateRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=200)


@router.get("/classroom/{classroom_id}/results", response_model=List[ClassroomTestResultsResponse])
async def get_classroom_test_results(
    classroom_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get test results summary for all assignments in a classroom"""
    
    if current_user.role.value != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can view test results"
        )
    
    # Verify teacher owns the classroom
    classroom_check = await db.execute(
        text("""
        SELECT 1 FROM classrooms c
        WHERE c.id = :classroom_id AND c.teacher_id = :teacher_id
        """),
        {"classroom_id": classroom_id, "teacher_id": current_user.id}
    )
    
    if not classroom_check.first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this classroom"
        )
    
    # Get test results for all assignments in classroom
    results_query = await db.execute(
        text("""
        WITH classroom_tests AS (
            SELECT DISTINCT
                ra.id as assignment_id,
                ra.assignment_title,
                at.id as test_id
            FROM classroom_assignments ca
            JOIN reading_assignments ra ON ra.id = ca.assignment_id
            JOIN assignment_tests at ON at.assignment_id = ra.id
            WHERE ca.classroom_id = :classroom_id
            AND ca.assignment_type = 'reading'
            AND at.status = 'approved'
            AND ra.deleted_at IS NULL
        ),
        student_count AS (
            SELECT COUNT(DISTINCT cs.student_id) as total_students
            FROM classroom_students cs
            WHERE cs.classroom_id = :classroom_id
            AND cs.removed_at IS NULL
        ),
        test_results AS (
            SELECT 
                ct.assignment_id,
                ct.assignment_title,
                COUNT(sta.id) as completed_tests,
                COUNT(CASE WHEN sta.evaluation_status = 'manual_review' THEN 1 END) as pending_review,
                AVG(CASE WHEN sta.score IS NOT NULL THEN sta.score ELSE NULL END) as avg_score,
                JSON_AGG(
                    JSON_BUILD_OBJECT(
                        'attempt_id', sta.id,
                        'student_id', sta.student_id,
                        'student_name', u.first_name || ' ' || u.last_name,
                        'score', sta.score,
                        'passed', sta.passed,
                        'status', sta.status,
                        'evaluation_status', sta.evaluation_status,
                        'submitted_at', sta.submitted_at,
                        'evaluated_at', sta.evaluated_at,
                        'needs_review', COALESCE(tea.requires_review, false)
                    ) ORDER BY u.last_name, u.first_name
                ) FILTER (WHERE sta.id IS NOT NULL) as student_results
            FROM classroom_tests ct
            LEFT JOIN student_test_attempts sta ON sta.assignment_test_id = ct.test_id
                AND sta.status IN ('submitted', 'graded', 'completed')
            LEFT JOIN users u ON u.id = sta.student_id
            LEFT JOIN test_evaluation_audits tea ON tea.test_attempt_id = sta.id
            GROUP BY ct.assignment_id, ct.assignment_title
        )
        SELECT 
            tr.assignment_id,
            tr.assignment_title,
            sc.total_students,
            COALESCE(tr.completed_tests, 0) as completed_tests,
            COALESCE(tr.pending_review, 0) as pending_review,
            COALESCE(tr.avg_score, 0) as avg_score,
            COALESCE(tr.student_results, '[]'::json) as results
        FROM test_results tr
        CROSS JOIN student_count sc
        ORDER BY tr.assignment_title
        """),
        {"classroom_id": classroom_id}
    )
    
    classroom_results = []
    for row in results_query:
        classroom_results.append(ClassroomTestResultsResponse(
            assignment_id=row[0],
            assignment_title=row[1],
            total_students=row[2],
            completed_tests=row[3],
            pending_review=row[4],
            average_score=float(row[5]),
            results=row[6] or []
        ))
    
    return classroom_results


@router.get("/results/{test_attempt_id}/detailed")
async def get_detailed_test_result(
    test_attempt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed test result for teacher review (same as student endpoint but teacher accessible)"""
    
    if current_user.role.value != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can view detailed results"
        )
    
    # Use the same endpoint as students but verify teacher access
    from app.api.v1.student_tests import get_test_result_details
    return await get_test_result_details(test_attempt_id, current_user, db)


@router.post("/results/{test_attempt_id}/override")
async def override_test_score(
    test_attempt_id: UUID,
    override_data: TestOverrideRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Override AI evaluation with teacher score"""
    
    if current_user.role.value != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can override scores"
        )
    
    # Verify teacher has access to this test attempt
    access_check = await db.execute(
        text("""
        SELECT sta.id
        FROM student_test_attempts sta
        JOIN reading_assignments ra ON ra.id = sta.assignment_id
        WHERE sta.id = :attempt_id AND ra.teacher_id = :teacher_id
        """),
        {"attempt_id": test_attempt_id, "teacher_id": current_user.id}
    )
    
    if not access_check.first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this test attempt"
        )
    
    # Validate override score based on question vs overall
    if override_data.question_number is not None:
        # Question-level override (convert 0-100 to 0-4 rubric and back to points)
        if override_data.override_score > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question score cannot exceed 100"
            )
        # Convert to rubric score and points
        if override_data.override_score >= 90:
            rubric_score = 4
            points = 10
        elif override_data.override_score >= 80:
            rubric_score = 3
            points = 8
        elif override_data.override_score >= 60:
            rubric_score = 2
            points = 5
        elif override_data.override_score >= 30:
            rubric_score = 1
            points = 2
        else:
            rubric_score = 0
            points = 0
        
        # Check if question exists
        question_check = await db.execute(
            text("""
            SELECT 1 FROM test_question_evaluations
            WHERE test_attempt_id = :attempt_id AND question_number = :question_num
            """),
            {"attempt_id": test_attempt_id, "question_num": override_data.question_number}
        )
        
        if not question_check.first():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question evaluation not found"
            )
        
        # Store the override
        await db.execute(
            text("""
            INSERT INTO teacher_evaluation_overrides 
            (test_attempt_id, teacher_id, question_number, original_score, override_score, override_reason, override_feedback)
            VALUES (:attempt_id, :teacher_id, :question_num, 
                   (SELECT points_earned FROM test_question_evaluations 
                    WHERE test_attempt_id = :attempt_id AND question_number = :question_num),
                   :override_score, :reason, :feedback)
            ON CONFLICT (test_attempt_id, question_number)
            DO UPDATE SET
                override_score = :override_score,
                override_reason = :reason,
                override_feedback = :feedback,
                created_at = NOW()
            """),
            {
                "attempt_id": test_attempt_id,
                "teacher_id": current_user.id,
                "question_num": override_data.question_number,
                "override_score": points,
                "reason": override_data.override_reason,
                "feedback": override_data.override_feedback
            }
        )
        
        # Update the question evaluation
        await db.execute(
            text("""
            UPDATE test_question_evaluations
            SET rubric_score = :rubric_score, points_earned = :points
            WHERE test_attempt_id = :attempt_id AND question_number = :question_num
            """),
            {
                "attempt_id": test_attempt_id,
                "question_num": override_data.question_number,
                "rubric_score": rubric_score,
                "points": points
            }
        )
        
    else:
        # Overall score override
        if override_data.override_score > 100:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Overall score cannot exceed 100"
            )
        
        await db.execute(
            text("""
            INSERT INTO teacher_evaluation_overrides 
            (test_attempt_id, teacher_id, question_number, original_score, override_score, override_reason, override_feedback)
            VALUES (:attempt_id, :teacher_id, NULL,
                   (SELECT score FROM student_test_attempts WHERE id = :attempt_id),
                   :override_score, :reason, :feedback)
            ON CONFLICT (test_attempt_id, question_number)
            DO UPDATE SET
                override_score = :override_score,
                override_reason = :reason,
                override_feedback = :feedback,
                created_at = NOW()
            """),
            {
                "attempt_id": test_attempt_id,
                "teacher_id": current_user.id,
                "override_score": override_data.override_score,
                "reason": override_data.override_reason,
                "feedback": override_data.override_feedback
            }
        )
    
    # Recalculate final score using the database function
    await db.execute(
        text("SELECT calculate_test_final_score(:attempt_id)"),
        {"attempt_id": test_attempt_id}
    )
    
    # Update the student test attempt with the new score
    final_score_result = await db.execute(
        text("SELECT final_score FROM calculate_test_final_score(:attempt_id)"),
        {"attempt_id": test_attempt_id}
    )
    final_score = final_score_result.scalar()
    
    await db.execute(
        text("""
        UPDATE student_test_attempts
        SET score = :final_score,
            passed = :passed,
            evaluation_status = 'completed'
        WHERE id = :attempt_id
        """),
        {
            "attempt_id": test_attempt_id,
            "final_score": final_score,
            "passed": final_score >= 70
        }
    )
    
    await db.commit()
    
    return {
        "success": True,
        "message": "Score override applied successfully",
        "new_score": float(final_score),
        "override_type": "question" if override_data.question_number is not None else "overall"
    }


@router.post("/results/{test_attempt_id}/regenerate")
async def regenerate_evaluation(
    test_attempt_id: UUID,
    regen_data: EvaluationRegenerateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Regenerate AI evaluation for a test attempt"""
    
    if current_user.role.value != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can regenerate evaluations"
        )
    
    # Verify teacher has access
    access_check = await db.execute(
        text("""
        SELECT sta.id
        FROM student_test_attempts sta
        JOIN reading_assignments ra ON ra.id = sta.assignment_id
        WHERE sta.id = :attempt_id AND ra.teacher_id = :teacher_id
        """),
        {"attempt_id": test_attempt_id, "teacher_id": current_user.id}
    )
    
    if not access_check.first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this test attempt"
        )
    
    # Clear existing evaluation data
    await db.execute(
        text("DELETE FROM test_question_evaluations WHERE test_attempt_id = :attempt_id"),
        {"attempt_id": test_attempt_id}
    )
    
    await db.execute(
        text("DELETE FROM teacher_evaluation_overrides WHERE test_attempt_id = :attempt_id"),
        {"attempt_id": test_attempt_id}
    )
    
    # Reset attempt status
    await db.execute(
        text("""
        UPDATE student_test_attempts
        SET evaluation_status = 'pending',
            evaluated_at = NULL,
            score = NULL,
            passed = NULL,
            feedback = NULL
        WHERE id = :attempt_id
        """),
        {"attempt_id": test_attempt_id}
    )
    
    await db.commit()
    
    # Trigger new evaluation
    try:
        evaluation_service = TestEvaluationServiceV2(db)
        evaluation_result = await evaluation_service.evaluate_test_submission(
            test_attempt_id=test_attempt_id,
            trigger_source=f"teacher_regenerate:{current_user.id}"
        )
        
        # Log the regeneration
        await db.execute(
            text("""
            INSERT INTO test_evaluation_audits (test_attempt_id, evaluation_attempt_number, ai_model)
            VALUES (:attempt_id, 
                   (SELECT COALESCE(MAX(evaluation_attempt_number), 0) + 1 
                    FROM test_evaluation_audits WHERE test_attempt_id = :attempt_id),
                   'regenerated_by_teacher')
            """),
            {"attempt_id": test_attempt_id}
        )
        
        await db.commit()
        
        return {
            "success": True,
            "message": "Evaluation regenerated successfully",
            "new_score": evaluation_result.get("score"),
            "regeneration_reason": regen_data.reason
        }
        
    except Exception as e:
        logger.error(f"Error regenerating evaluation: {str(e)}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to regenerate evaluation: {str(e)}"
        )


@router.get("/evaluation-audits/{test_attempt_id}")
async def get_evaluation_audit_trail(
    test_attempt_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get audit trail for test evaluation"""
    
    if current_user.role.value != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can view audit trails"
        )
    
    # Verify access
    access_check = await db.execute(
        text("""
        SELECT sta.id
        FROM student_test_attempts sta
        JOIN reading_assignments ra ON ra.id = sta.assignment_id
        WHERE sta.id = :attempt_id AND ra.teacher_id = :teacher_id
        """),
        {"attempt_id": test_attempt_id, "teacher_id": current_user.id}
    )
    
    if not access_check.first():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this test attempt"
        )
    
    # Get evaluation audit data
    audit_result = await db.execute(
        text("""
        SELECT 
            tea.evaluation_attempt_number,
            tea.ai_model,
            tea.started_at,
            tea.completed_at,
            tea.duration_ms,
            tea.average_confidence,
            tea.score_distribution,
            tea.requires_review,
            tea.review_reason,
            tea.error_occurred,
            tea.error_message
        FROM test_evaluation_audits tea
        WHERE tea.test_attempt_id = :attempt_id
        ORDER BY tea.evaluation_attempt_number DESC
        """),
        {"attempt_id": test_attempt_id}
    )
    
    # Get teacher overrides
    override_result = await db.execute(
        text("""
        SELECT 
            teo.question_number,
            teo.original_score,
            teo.override_score,
            teo.override_reason,
            teo.override_feedback,
            teo.created_at,
            u.first_name || ' ' || u.last_name as teacher_name
        FROM teacher_evaluation_overrides teo
        JOIN users u ON u.id = teo.teacher_id
        WHERE teo.test_attempt_id = :attempt_id
        ORDER BY teo.question_number NULLS LAST, teo.created_at DESC
        """),
        {"attempt_id": test_attempt_id}
    )
    
    audit_data = []
    for row in audit_result:
        audit_data.append({
            "attempt_number": row[0],
            "ai_model": row[1],
            "started_at": row[2],
            "completed_at": row[3],
            "duration_ms": row[4],
            "average_confidence": float(row[5]) if row[5] else None,
            "score_distribution": row[6],
            "requires_review": row[7],
            "review_reason": row[8],
            "error_occurred": row[9],
            "error_message": row[10]
        })
    
    override_data = []
    for row in override_result:
        override_data.append({
            "question_number": row[0],
            "original_score": row[1],
            "override_score": row[2],
            "override_reason": row[3],
            "override_feedback": row[4],
            "created_at": row[5],
            "teacher_name": row[6]
        })
    
    return {
        "test_attempt_id": str(test_attempt_id),
        "evaluation_history": audit_data,
        "score_overrides": override_data
    }


@router.get("/pending-review")
async def get_tests_pending_review(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all test attempts that need teacher review"""
    
    if current_user.role.value != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can view pending reviews"
        )
    
    # Get tests needing review for this teacher's assignments
    pending_result = await db.execute(
        text("""
        SELECT 
            sta.id as attempt_id,
            ra.id as assignment_id,
            ra.assignment_title,
            u.first_name || ' ' || u.last_name as student_name,
            sta.score,
            sta.submitted_at,
            sta.evaluated_at,
            tea.review_reason,
            tea.average_confidence
        FROM student_test_attempts sta
        JOIN reading_assignments ra ON ra.id = sta.assignment_id
        JOIN users u ON u.id = sta.student_id
        LEFT JOIN test_evaluation_audits tea ON tea.test_attempt_id = sta.id
        WHERE ra.teacher_id = :teacher_id
        AND (
            sta.evaluation_status = 'manual_review'
            OR tea.requires_review = true
        )
        AND sta.status IN ('submitted', 'graded', 'completed')
        ORDER BY sta.submitted_at ASC
        """),
        {"teacher_id": current_user.id}
    )
    
    pending_tests = []
    for row in pending_result:
        pending_tests.append({
            "attempt_id": str(row[0]),
            "assignment_id": str(row[1]),
            "assignment_title": row[2],
            "student_name": row[3],
            "score": float(row[4]) if row[4] else None,
            "submitted_at": row[5],
            "evaluated_at": row[6],
            "review_reason": row[7],
            "confidence": float(row[8]) if row[8] else None
        })
    
    return {
        "pending_tests": pending_tests,
        "total_count": len(pending_tests)
    }
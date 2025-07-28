"""
Updated classroom detail endpoints that support both reading and vocabulary assignments
"""
from typing import List
from uuid import UUID
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_db
from app.utils.supabase_deps import get_current_user_supabase as get_current_user
from app.models.user import User, UserRole
from app.models.classroom import Classroom, ClassroomAssignment
from app.models.reading import ReadingAssignment as ReadingAssignmentModel
from app.models.vocabulary import VocabularyList
from app.models.debate import DebateAssignment
from app.models.writing import WritingAssignment
from app.schemas.classroom import AssignmentInClassroom

router = APIRouter()

def require_teacher(current_user: User = Depends(get_current_user)) -> User:
    """Require the current user to be a teacher"""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access this resource"
        )
    return current_user


@router.get("/classrooms/{classroom_id}/assignments/all", response_model=List[AssignmentInClassroom])
async def list_all_classroom_assignments(
    classroom_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db)
):
    """List all assignments (reading and vocabulary) in a classroom"""
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
    
    assignment_list = []
    
    # Get reading assignments
    reading_result = await db.execute(
        select(ReadingAssignmentModel, ClassroomAssignment)
        .join(ClassroomAssignment, 
              and_(
                  ClassroomAssignment.assignment_id == ReadingAssignmentModel.id,
                  ClassroomAssignment.assignment_type == "reading"
              ))
        .where(ClassroomAssignment.classroom_id == classroom_id)
        .order_by(ClassroomAssignment.display_order.nullsfirst(), ClassroomAssignment.assigned_at)
    )
    
    for assignment, ca in reading_result:
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
    vocab_result = await db.execute(
        select(VocabularyList, ClassroomAssignment)
        .join(ClassroomAssignment,
              and_(
                  ClassroomAssignment.vocabulary_list_id == VocabularyList.id,
                  ClassroomAssignment.assignment_type == "vocabulary"
              ))
        .where(ClassroomAssignment.classroom_id == classroom_id)
        .order_by(ClassroomAssignment.display_order.nullsfirst(), ClassroomAssignment.assigned_at)
    )
    
    for vocab_list, ca in vocab_result:
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
    
    # Get debate assignments
    debate_result = await db.execute(
        select(DebateAssignment, ClassroomAssignment)
        .join(ClassroomAssignment,
              and_(
                  ClassroomAssignment.assignment_id == DebateAssignment.id,
                  ClassroomAssignment.assignment_type == "debate"
              ))
        .where(ClassroomAssignment.classroom_id == classroom_id)
        .order_by(ClassroomAssignment.display_order.nullsfirst(), ClassroomAssignment.assigned_at)
    )
    
    for debate, ca in debate_result:
        assignment_list.append(AssignmentInClassroom(
            id=ca.id,
            assignment_id=debate.id,
            title=debate.title,
            assignment_type="UMADebate",
            assigned_at=ca.assigned_at,
            display_order=ca.display_order,
            start_date=ca.start_date,
            end_date=ca.end_date
        ))
    
    # Get writing assignments
    writing_result = await db.execute(
        select(WritingAssignment, ClassroomAssignment)
        .join(ClassroomAssignment,
              and_(
                  ClassroomAssignment.assignment_id == WritingAssignment.id,
                  ClassroomAssignment.assignment_type == "writing"
              ))
        .where(ClassroomAssignment.classroom_id == classroom_id)
        .order_by(ClassroomAssignment.display_order.nullsfirst(), ClassroomAssignment.assigned_at)
    )
    
    for writing, ca in writing_result:
        assignment_list.append(AssignmentInClassroom(
            id=ca.id,
            assignment_id=writing.id,
            title=writing.title,
            assignment_type="UMAWrite",
            assigned_at=ca.assigned_at,
            display_order=ca.display_order,
            start_date=ca.start_date,
            end_date=ca.end_date
        ))
    
    # Get UMALecture assignments (handle both "UMALecture" and "lecture" types for backward compatibility)
    lecture_result = await db.execute(
        select(ReadingAssignmentModel, ClassroomAssignment)
        .join(ClassroomAssignment,
              and_(
                  ClassroomAssignment.assignment_id == ReadingAssignmentModel.id,
                  ClassroomAssignment.assignment_type.in_(["UMALecture", "lecture"])
              ))
        .where(
            and_(
                ClassroomAssignment.classroom_id == classroom_id,
                ReadingAssignmentModel.assignment_type == "UMALecture"
            )
        )
        .order_by(ClassroomAssignment.display_order.nullsfirst(), ClassroomAssignment.assigned_at)
    )
    
    for lecture, ca in lecture_result:
        assignment_list.append(AssignmentInClassroom(
            id=ca.id,
            assignment_id=lecture.id,
            title=lecture.assignment_title,
            assignment_type="UMALecture",
            assigned_at=ca.assigned_at,
            display_order=ca.display_order,
            start_date=ca.start_date,
            end_date=ca.end_date
        ))
    
    # Sort by display order, then assigned date
    assignment_list.sort(key=lambda x: (x.display_order or float('inf'), x.assigned_at))
    
    return assignment_list
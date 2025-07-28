"""
Teacher vocabulary classroom integration endpoints
"""
from typing import Optional, List
from uuid import UUID
from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import get_db
from app.utils.supabase_deps import require_teacher_supabase as require_teacher
from app.models.user import User
from app.models.classroom import Classroom, ClassroomAssignment
from app.models.vocabulary import VocabularyList

router = APIRouter()


@router.get("/classrooms/{classroom_id}/vocabulary/available")
async def get_classroom_available_vocabulary(
    classroom_id: UUID,
    teacher: User = Depends(require_teacher),
    db: AsyncSession = Depends(get_db),
    search: Optional[str] = Query(None),
    grade_level: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100)
):
    """Get all teacher's vocabulary lists with their assignment status for this classroom"""
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
    
    # Get currently assigned vocabulary lists with their schedules
    assigned_result = await db.execute(
        select(ClassroomAssignment).where(
            and_(
                ClassroomAssignment.classroom_id == classroom_id,
                ClassroomAssignment.assignment_type == "vocabulary"
            )
        )
    )
    assigned_vocab = {ca.vocabulary_list_id: ca for ca in assigned_result.scalars()}
    assigned_ids = set(assigned_vocab.keys())
    
    # Build query for all teacher's vocabulary lists (include archived)
    query = select(VocabularyList).where(
        and_(
            VocabularyList.teacher_id == teacher.id,
            VocabularyList.status == "published"
        )
    )
    
    # Apply filters
    if search:
        query = query.where(
            or_(
                VocabularyList.title.ilike(f"%{search}%"),
                VocabularyList.context_description.ilike(f"%{search}%")
            )
        )
    
    if grade_level and grade_level != "all":
        query = query.where(VocabularyList.grade_level == grade_level)
    
    if status:
        if status == "assigned":
            query = query.where(VocabularyList.id.in_(assigned_ids))
        elif status == "unassigned":
            query = query.where(VocabularyList.id.notin_(assigned_ids))
    
    # Get total count
    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total_count = count_result.scalar() or 0
    
    # Apply pagination and sorting
    query = query.order_by(VocabularyList.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    
    # Execute query
    result = await db.execute(query)
    vocab_lists = result.scalars().all()
    
    # Get word counts
    word_counts = {}
    if vocab_lists:
        list_ids = [vl.id for vl in vocab_lists]
        count_query = """
            SELECT list_id, COUNT(*) as word_count 
            FROM vocabulary_words 
            WHERE list_id = ANY(:list_ids)
            GROUP BY list_id
        """
        count_result = await db.execute(count_query, {"list_ids": list_ids})
        word_counts = {row[0]: row[1] for row in count_result}
    
    # Format response
    available_vocabulary = []
    for vocab_list in vocab_lists:
        # Build vocabulary dict
        vocab_dict = {
            "id": vocab_list.id,
            "assignment_title": vocab_list.title,
            "work_title": vocab_list.context_description,
            "author": "",  # No author for vocabulary lists
            "assignment_type": "UMAVocab",
            "grade_level": vocab_list.grade_level,
            "work_type": vocab_list.subject_area,
            "status": vocab_list.status,
            "created_at": vocab_list.created_at,
            "is_assigned": vocab_list.id in assigned_ids,
            "is_archived": vocab_list.deleted_at is not None,
            "word_count": word_counts.get(vocab_list.id, 0)
        }
        
        # Add schedule info if assigned
        if vocab_list.id in assigned_ids:
            ca = assigned_vocab[vocab_list.id]
            vocab_dict["current_schedule"] = {
                "start_date": ca.start_date,
                "end_date": ca.end_date
            }
        
        available_vocabulary.append(vocab_dict)
    
    return {
        "assignments": available_vocabulary,
        "total_count": total_count,
        "page": page,
        "per_page": per_page
    }
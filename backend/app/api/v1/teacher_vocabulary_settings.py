from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, func, select
from sqlalchemy.orm import selectinload
from typing import Dict, Any
from uuid import UUID

from app.core.database import get_db
from app.utils.deps import get_current_user
from app.models.user import User, UserRole
from app.models.classroom import ClassroomAssignment, Classroom
from app.models.vocabulary import VocabularyList, VocabularyWord
from app.schemas.classroom import VocabularySettings, VocabularySettingsUpdate, VocabularySettingsResponse

router = APIRouter()


@router.get("/classrooms/{classroom_id}/vocabulary/{assignment_id}/settings", response_model=VocabularySettingsResponse)
async def get_vocabulary_settings(
    classroom_id: UUID,
    assignment_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get vocabulary settings for a specific assignment."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(status_code=403, detail="Only teachers can access vocabulary settings")
    
    # Get the classroom assignment with classroom relationship
    assignment_result = await db.execute(
        select(ClassroomAssignment)
        .options(selectinload(ClassroomAssignment.classroom))
        .where(
            and_(
                ClassroomAssignment.id == assignment_id,
                ClassroomAssignment.classroom_id == classroom_id,
                ClassroomAssignment.assignment_type == "vocabulary"
            )
        )
    )
    assignment = assignment_result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Vocabulary assignment not found")
    
    # Verify the teacher owns the classroom
    if assignment.classroom.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have access to this classroom")
    
    # Get vocabulary list details
    vocab_result = await db.execute(
        select(VocabularyList).where(VocabularyList.id == assignment.vocabulary_list_id)
    )
    vocab_list = vocab_result.scalar_one_or_none()
    
    if not vocab_list:
        raise HTTPException(status_code=404, detail="Vocabulary list not found")
    
    # Count total words
    word_count_result = await db.execute(
        select(func.count(VocabularyWord.id)).where(VocabularyWord.list_id == vocab_list.id)
    )
    total_words = word_count_result.scalar() or 0
    
    # Parse settings or use defaults
    settings = assignment.vocab_settings or {}
    vocab_settings = VocabularySettings(**settings)
    
    # Calculate groups count if applicable
    groups_count = None
    if vocab_settings.delivery_mode in ["in_groups", "teacher_controlled"] and vocab_settings.group_size:
        groups_count = (total_words + vocab_settings.group_size - 1) // vocab_settings.group_size
    
    return VocabularySettingsResponse(
        assignment_id=assignment.id,
        vocabulary_list_id=assignment.vocabulary_list_id,
        settings=vocab_settings,
        total_words=total_words,
        groups_count=groups_count
    )


@router.put("/classrooms/{classroom_id}/vocabulary/{assignment_id}/settings", response_model=VocabularySettingsResponse)
async def update_vocabulary_settings(
    classroom_id: UUID,
    assignment_id: int,
    settings_update: VocabularySettingsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update vocabulary settings for a specific assignment."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(status_code=403, detail="Only teachers can update vocabulary settings")
    
    # Get the classroom assignment
    assignment_result = await db.execute(
        select(ClassroomAssignment)
        .options(selectinload(ClassroomAssignment.classroom))
        .where(
            and_(
                ClassroomAssignment.id == assignment_id,
                ClassroomAssignment.classroom_id == classroom_id,
                ClassroomAssignment.assignment_type == "vocabulary"
            )
        )
    )
    assignment = assignment_result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Vocabulary assignment not found")
    
    # Verify the teacher owns the classroom
    if assignment.classroom.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have access to this classroom")
    
    # Get current settings
    current_settings = assignment.vocab_settings or {}
    vocab_settings = VocabularySettings(**current_settings)
    
    # Apply updates
    update_data = settings_update.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vocab_settings, field, value)
    
    # Validate the updated settings
    try:
        vocab_settings = VocabularySettings(**vocab_settings.dict())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    # Get vocabulary list details for validation
    vocab_result = await db.execute(
        select(VocabularyList).where(VocabularyList.id == assignment.vocabulary_list_id)
    )
    vocab_list = vocab_result.scalar_one_or_none()
    
    # Count total words
    word_count_result = await db.execute(
        select(func.count(VocabularyWord.id)).where(VocabularyWord.list_id == vocab_list.id)
    )
    total_words = word_count_result.scalar() or 0
    
    # Validate group size against total words
    if vocab_settings.delivery_mode in ["in_groups", "teacher_controlled"]:
        if vocab_settings.group_size and vocab_settings.group_size > total_words:
            raise HTTPException(
                status_code=400, 
                detail=f"Group size ({vocab_settings.group_size}) cannot be larger than total words ({total_words})"
            )
    
    # Update the assignment with new settings
    assignment.vocab_settings = vocab_settings.dict()
    await db.commit()
    
    # Calculate groups count if applicable
    groups_count = None
    if vocab_settings.delivery_mode in ["in_groups", "teacher_controlled"] and vocab_settings.group_size:
        groups_count = (total_words + vocab_settings.group_size - 1) // vocab_settings.group_size
    
    return VocabularySettingsResponse(
        assignment_id=assignment.id,
        vocabulary_list_id=assignment.vocabulary_list_id,
        settings=vocab_settings,
        total_words=total_words,
        groups_count=groups_count
    )


@router.post("/classrooms/{classroom_id}/vocabulary/{assignment_id}/release-group")
async def release_vocabulary_group(
    classroom_id: UUID,
    assignment_id: int,
    group_number: int = Query(..., description="Group number to release"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Release a specific group of vocabulary words (for teacher_controlled mode)."""
    if current_user.role != UserRole.TEACHER:
        raise HTTPException(status_code=403, detail="Only teachers can release vocabulary groups")
    
    # Get the classroom assignment
    assignment_result = await db.execute(
        select(ClassroomAssignment)
        .options(selectinload(ClassroomAssignment.classroom))
        .where(
            and_(
                ClassroomAssignment.id == assignment_id,
                ClassroomAssignment.classroom_id == classroom_id,
                ClassroomAssignment.assignment_type == "vocabulary"
            )
        )
    )
    assignment = assignment_result.scalar_one_or_none()
    
    if not assignment:
        raise HTTPException(status_code=404, detail="Vocabulary assignment not found")
    
    # Verify the teacher owns the classroom
    if assignment.classroom.teacher_id != current_user.id:
        raise HTTPException(status_code=403, detail="You don't have access to this classroom")
    
    # Get current settings
    current_settings = assignment.vocab_settings or {}
    vocab_settings = VocabularySettings(**current_settings)
    
    # Validate that we're in teacher_controlled mode
    if vocab_settings.delivery_mode != "teacher_controlled":
        raise HTTPException(
            status_code=400, 
            detail="Group release is only available in teacher-controlled mode"
        )
    
    # Count total words
    word_count_result = await db.execute(
        select(func.count(VocabularyWord.id)).where(VocabularyWord.list_id == assignment.vocabulary_list_id)
    )
    total_words = word_count_result.scalar() or 0
    
    # Calculate total groups
    if not vocab_settings.group_size:
        raise HTTPException(status_code=400, detail="Group size not configured")
    
    total_groups = (total_words + vocab_settings.group_size - 1) // vocab_settings.group_size
    
    # Validate group number
    if group_number < 1 or group_number > total_groups:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid group number. Must be between 1 and {total_groups}"
        )
    
    # Check if already released
    if group_number in vocab_settings.released_groups:
        raise HTTPException(status_code=400, detail=f"Group {group_number} has already been released")
    
    # Add to released groups
    vocab_settings.released_groups.append(group_number)
    vocab_settings.released_groups.sort()
    
    # Update the assignment
    assignment.vocab_settings = vocab_settings.dict()
    await db.commit()
    
    return {
        "message": f"Group {group_number} has been released",
        "released_groups": vocab_settings.released_groups,
        "total_groups": total_groups
    }
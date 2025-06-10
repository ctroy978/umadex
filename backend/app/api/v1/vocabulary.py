from typing import List, Optional
from uuid import UUID
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.utils.deps import get_current_user, require_admin
from app.models import User
from app.models.vocabulary import VocabularyStatus, VocabularyWord, VocabularyList
from app.schemas.vocabulary import (
    VocabularyListCreate, VocabularyListUpdate, VocabularyListResponse,
    VocabularyListSummary, VocabularyListPagination, VocabularyWordResponse,
    VocabularyWordReviewRequest, VocabularyWordManualUpdate,
    VocabularyWordReviewResponse, VocabularyExportFormat
)
from app.services.vocabulary import VocabularyService

router = APIRouter()


@router.post("/vocabulary", response_model=VocabularyListResponse, status_code=status.HTTP_201_CREATED)
async def create_vocabulary_list(
    vocabulary_data: VocabularyListCreate,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new vocabulary list"""
    if current_user.role.value != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can create vocabulary lists"
        )
    
    # Create the vocabulary list
    vocabulary_list = await VocabularyService.create_vocabulary_list(
        db, current_user.id, vocabulary_data
    )
    
    # Schedule AI generation in background
    background_tasks.add_task(
        VocabularyService.generate_ai_definitions,
        db,
        vocabulary_list.id
    )
    
    return VocabularyListResponse.model_validate(vocabulary_list)


@router.get("/vocabulary", response_model=VocabularyListPagination)
async def list_vocabulary_lists(
    status: Optional[VocabularyStatus] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """List vocabulary lists with pagination"""
    if current_user.role.value != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can view vocabulary lists"
        )
    
    lists, total = await VocabularyService.list_vocabulary_lists(
        db, current_user.id, status, search, page, per_page
    )
    
    # Calculate review progress for each list
    summaries = []
    for vocab_list in lists:
        # Temporarily skip progress calculation to avoid errors
        try:
            progress = await VocabularyService.get_review_progress(db, vocab_list.id)
            word_count = progress['total']
            review_progress = progress['progress_percentage']
        except Exception as e:
            print(f"Error getting progress for list {vocab_list.id}: {e}")
            # Count words directly as fallback
            word_result = await db.execute(
                select(func.count(VocabularyWord.id))
                .where(VocabularyWord.list_id == vocab_list.id)
            )
            word_count = word_result.scalar() or 0
            review_progress = 0
            
        summary = VocabularyListSummary(
            id=vocab_list.id,
            title=vocab_list.title,
            grade_level=vocab_list.grade_level,
            subject_area=vocab_list.subject_area,
            status=vocab_list.status,
            word_count=word_count,
            review_progress=review_progress,
            created_at=vocab_list.created_at,
            updated_at=vocab_list.updated_at
        )
        summaries.append(summary)
    
    return VocabularyListPagination(
        items=summaries,
        total=total,
        page=page,
        per_page=per_page,
        pages=(total + per_page - 1) // per_page
    )


@router.get("/vocabulary/{list_id}", response_model=VocabularyListResponse)
async def get_vocabulary_list(
    list_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific vocabulary list with all words"""
    vocabulary_list = await VocabularyService.get_vocabulary_list(db, list_id)
    
    if not vocabulary_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary list not found"
        )
    
    # Check permissions
    if (current_user.role.value != "teacher" or 
        vocabulary_list.teacher_id != current_user.id) and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this list"
        )
    
    response = VocabularyListResponse.model_validate(vocabulary_list)
    response.word_count = len(vocabulary_list.words)
    return response


@router.put("/vocabulary/{list_id}", response_model=VocabularyListResponse)
async def update_vocabulary_list(
    list_id: UUID,
    update_data: VocabularyListUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update vocabulary list metadata"""
    vocabulary_list = await VocabularyService.get_vocabulary_list(db, list_id, include_words=False, include_archived=True)
    
    if not vocabulary_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary list not found"
        )
    
    if vocabulary_list.teacher_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this list"
        )
    
    updated_list = await VocabularyService.update_vocabulary_list(db, list_id, update_data)
    
    # Create response manually to avoid relationship access issues
    response_data = {
        'id': updated_list.id,
        'teacher_id': updated_list.teacher_id,
        'title': updated_list.title,
        'context_description': updated_list.context_description,
        'grade_level': updated_list.grade_level,
        'subject_area': updated_list.subject_area,
        'status': updated_list.status,
        'created_at': updated_list.created_at,
        'updated_at': updated_list.updated_at,
        'deleted_at': updated_list.deleted_at,
        'words': None,
        'word_count': None
    }
    
    return VocabularyListResponse.model_validate(response_data)


@router.delete("/vocabulary/{list_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vocabulary_list(
    list_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete a vocabulary list"""
    vocabulary_list = await VocabularyService.get_vocabulary_list(db, list_id, include_words=False)
    
    if not vocabulary_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary list not found"
        )
    
    if vocabulary_list.teacher_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this list"
        )
    
    await VocabularyService.delete_vocabulary_list(db, list_id)


@router.post("/vocabulary/{list_id}/generate-ai", response_model=VocabularyListResponse)
async def generate_ai_definitions(
    list_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually trigger AI generation for a vocabulary list"""
    vocabulary_list = await VocabularyService.get_vocabulary_list(db, list_id, include_words=False)
    
    if not vocabulary_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary list not found"
        )
    
    if vocabulary_list.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to generate AI content for this list"
        )
    
    updated_list = await VocabularyService.generate_ai_definitions(db, list_id)
    
    # Reload the list with all relationships
    refreshed_list = await VocabularyService.get_vocabulary_list(db, list_id, include_words=True)
    return VocabularyListResponse.model_validate(refreshed_list)


@router.post("/vocabulary/words/{word_id}/review", response_model=VocabularyWordReviewResponse)
async def review_word(
    word_id: UUID,
    review_data: VocabularyWordReviewRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Review a vocabulary word (accept or reject)"""
    # Verify permissions through the vocabulary list
    result = await db.execute(
        select(VocabularyWord)
        .join(VocabularyList)
        .where(VocabularyWord.id == word_id)
        .options(selectinload(VocabularyWord.vocabulary_list))
    )
    word = result.scalar_one_or_none()
    
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Word not found"
        )
    
    if word.vocabulary_list.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to review this word"
        )
    
    review = await VocabularyService.review_word(
        db, word_id, review_data.action, review_data.rejection_feedback
    )
    
    return VocabularyWordReviewResponse.model_validate(review)


@router.put("/vocabulary/words/{word_id}/manual", response_model=VocabularyWordResponse)
async def update_word_manually(
    word_id: UUID,
    update_data: VocabularyWordManualUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Manually update a word with teacher-provided content"""
    # Verify permissions
    result = await db.execute(
        select(VocabularyWord)
        .join(VocabularyList)
        .where(VocabularyWord.id == word_id)
        .options(selectinload(VocabularyWord.vocabulary_list))
    )
    word = result.scalar_one_or_none()
    
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Word not found"
        )
    
    if word.vocabulary_list.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this word"
        )
    
    updated_word = await VocabularyService.update_word_manually(db, word_id, update_data)
    return VocabularyWordResponse.model_validate(updated_word)


@router.post("/vocabulary/words/{word_id}/regenerate", response_model=VocabularyWordResponse)
async def regenerate_word_definition(
    word_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Regenerate AI definition for a word"""
    # Verify permissions
    result = await db.execute(
        select(VocabularyWord)
        .join(VocabularyList)
        .where(VocabularyWord.id == word_id)
        .options(selectinload(VocabularyWord.vocabulary_list))
    )
    word = result.scalar_one_or_none()
    
    if not word:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Word not found"
        )
    
    if word.vocabulary_list.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to regenerate this word"
        )
    
    updated_word = await VocabularyService.regenerate_word_definition(db, word_id)
    return VocabularyWordResponse.model_validate(updated_word)


@router.post("/vocabulary/{list_id}/publish", response_model=VocabularyListResponse)
async def publish_vocabulary_list(
    list_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Publish a vocabulary list after review"""
    vocabulary_list = await VocabularyService.get_vocabulary_list(db, list_id, include_words=False)
    
    if not vocabulary_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary list not found"
        )
    
    if vocabulary_list.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to publish this list"
        )
    
    try:
        await VocabularyService.publish_vocabulary_list(db, list_id)
        # Reload the vocabulary list with proper relationship loading
        published_list = await VocabularyService.get_vocabulary_list(db, list_id, include_words=False)
        
        # Create response manually to avoid relationship access issues
        response_data = {
            'id': published_list.id,
            'teacher_id': published_list.teacher_id,
            'title': published_list.title,
            'context_description': published_list.context_description,
            'grade_level': published_list.grade_level,
            'subject_area': published_list.subject_area,
            'status': published_list.status,
            'created_at': published_list.created_at,
            'updated_at': published_list.updated_at,
            'deleted_at': published_list.deleted_at,
            'words': None,
            'word_count': None
        }
        
        return VocabularyListResponse.model_validate(response_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/vocabulary/{list_id}/progress")
async def get_review_progress(
    list_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get review progress for a vocabulary list"""
    vocabulary_list = await VocabularyService.get_vocabulary_list(db, list_id, include_words=False)
    
    if not vocabulary_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary list not found"
        )
    
    if vocabulary_list.teacher_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this list's progress"
        )
    
    return await VocabularyService.get_review_progress(db, list_id)


@router.get("/vocabulary/{list_id}/export-presentation")
async def export_vocabulary_presentation(
    list_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Export vocabulary list as an interactive HTML presentation"""
    # Get vocabulary list with all words
    vocabulary_list = await VocabularyService.get_vocabulary_list(db, list_id, include_words=True)
    
    if not vocabulary_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary list not found"
        )
    
    # Check permissions
    if vocabulary_list.teacher_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to export this list"
        )
    
    # Check if list is published
    if vocabulary_list.status != VocabularyStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only published vocabulary lists can be exported as presentations"
        )
    
    # Check minimum word count
    if len(vocabulary_list.words) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vocabulary list must have at least 3 words to create a presentation"
        )
    
    # Generate HTML presentation
    html_content = await VocabularyService.generate_presentation_html(vocabulary_list)
    
    # Create filename
    safe_title = "".join(c for c in vocabulary_list.title if c.isalnum() or c in (' ', '-', '_')).rstrip()
    safe_title = safe_title.replace(' ', '_')[:50]  # Limit length
    filename = f"vocab-presentation-{safe_title}-{datetime.now().strftime('%Y-%m-%d')}.html"
    
    # Return as downloadable file
    return Response(
        content=html_content,
        media_type="text/html",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Content-Type": "text/html; charset=utf-8"
        }
    )
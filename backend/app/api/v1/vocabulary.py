from typing import List, Optional
from uuid import UUID
from datetime import datetime
import asyncio
from fastapi import APIRouter, Depends, HTTPException, status, Query, BackgroundTasks
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.utils.deps import get_current_user, require_admin
from app.models import User
from app.models.vocabulary import VocabularyStatus, VocabularyWord, VocabularyList
from app.schemas.vocabulary import (
    VocabularyListCreate, VocabularyListUpdate, VocabularyListResponse,
    VocabularyListSummary, VocabularyListPagination, VocabularyWordResponse,
    VocabularyWordReviewRequest, VocabularyWordManualUpdate,
    VocabularyWordReviewResponse, VocabularyExportFormat,
    VocabularyTestConfig, VocabularyTestConfigResponse, VocabularyTestResponse,
    ClassroomAssignmentTestConfig
)
from app.services.vocabulary import VocabularyService
from app.services.vocabulary_story_generator import VocabularyStoryGenerator
from app.services.vocabulary_puzzle_generator import VocabularyPuzzleGenerator
from app.services.vocabulary_fill_in_blank_generator import VocabularyFillInBlankGenerator
from app.services.vocabulary_test import VocabularyTestService
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


async def pre_generate_vocabulary_assignments(list_id: UUID):
    """Background task to pre-generate all vocabulary practice assignments"""
    try:
        # Create a new database session for the background task
        from app.core.database import AsyncSessionLocal
        
        async with AsyncSessionLocal() as db:
            logger.info(f"Starting pre-generation of vocabulary assignments for list {list_id}")
            
            
            # Generate story prompts
            try:
                story_generator = VocabularyStoryGenerator(db)
                await story_generator.generate_story_prompts(list_id)
                logger.info(f"Successfully pre-generated story prompts for list {list_id}")
            except Exception as e:
                logger.error(f"Failed to pre-generate story prompts for list {list_id}: {e}")
            
            # Generate puzzle games
            try:
                puzzle_generator = VocabularyPuzzleGenerator(db)
                puzzle_data = await puzzle_generator.generate_puzzle_set(list_id)
                
                # Save puzzles to database
                from app.models.vocabulary_practice import VocabularyPuzzleGame
                for p_data in puzzle_data:
                    puzzle = VocabularyPuzzleGame(**p_data)
                    db.add(puzzle)
                
                await db.commit()
                logger.info(f"Successfully pre-generated puzzle games for list {list_id}")
            except Exception as e:
                logger.error(f"Failed to pre-generate puzzle games for list {list_id}: {e}")
            
            # Generate fill-in-the-blank sentences
            try:
                fill_in_blank_generator = VocabularyFillInBlankGenerator(db)
                await fill_in_blank_generator.generate_fill_in_blank_sentences(list_id)
                logger.info(f"Successfully pre-generated fill-in-the-blank sentences for list {list_id}")
            except Exception as e:
                logger.error(f"Failed to pre-generate fill-in-the-blank sentences for list {list_id}: {e}")
            
            logger.info(f"Completed pre-generation of vocabulary assignments for list {list_id}")
            
    except Exception as e:
        logger.error(f"Critical error in pre-generation task for list {list_id}: {e}")


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
    include_archived: bool = Query(False),
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
        db, current_user.id, status, search, page, per_page, include_archived
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
            updated_at=vocab_list.updated_at,
            deleted_at=vocab_list.deleted_at
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
    
    # Check if vocabulary list is attached to any classrooms
    from app.models.classroom import ClassroomAssignment
    from sqlalchemy import select, func, and_
    count_result = await db.execute(
        select(func.count(ClassroomAssignment.id))
        .where(
            and_(
                ClassroomAssignment.vocabulary_list_id == list_id,
                ClassroomAssignment.assignment_type == "vocabulary"
            )
        )
    )
    classroom_count = count_result.scalar() or 0
    
    if classroom_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot archive vocabulary list attached to {classroom_count} classroom(s). Remove from classrooms first."
        )
    
    await VocabularyService.delete_vocabulary_list(db, list_id)


@router.post("/vocabulary/{list_id}/restore")
async def restore_vocabulary_list(
    list_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Restore a soft-deleted vocabulary list"""
    # Get the vocabulary list including archived ones
    result = await db.execute(
        select(VocabularyList).where(
            and_(
                VocabularyList.id == list_id,
                VocabularyList.teacher_id == current_user.id,
                VocabularyList.deleted_at.is_not(None)
            )
        )
    )
    vocabulary_list = result.scalar_one_or_none()
    
    if not vocabulary_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Archived vocabulary list not found"
        )
    
    # Restore by clearing deleted_at
    vocabulary_list.deleted_at = None
    await db.commit()
    
    return {"message": "Vocabulary list restored successfully"}


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
    
    # Also fetch pronunciation data for words
    await VocabularyService.fetch_pronunciation_data(db, list_id)
    
    # Reload the list with all relationships
    refreshed_list = await VocabularyService.get_vocabulary_list(db, list_id, include_words=True)
    return VocabularyListResponse.model_validate(refreshed_list)


@router.post("/vocabulary/{list_id}/fetch-pronunciation")
async def fetch_pronunciation_data(
    list_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Fetch pronunciation data for all words in a vocabulary list"""
    vocabulary_list = await VocabularyService.get_vocabulary_list(db, list_id, include_words=False)
    
    if not vocabulary_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary list not found"
        )
    
    if vocabulary_list.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this list"
        )
    
    updated_count = await VocabularyService.fetch_pronunciation_data(db, list_id)
    
    return {
        "message": f"Pronunciation data fetched for {updated_count} words",
        "updated_count": updated_count
    }


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
    background_tasks: BackgroundTasks,
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
        
        # Schedule background pre-generation of practice assignments
        background_tasks.add_task(pre_generate_vocabulary_assignments, list_id)
        
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


# Vocabulary Test Configuration Endpoints
@router.get("/vocabulary/{list_id}/test/config")
async def get_test_config(
    list_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get test configuration for a vocabulary list"""
    if current_user.role.value != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can access test configurations"
        )
    
    # Verify vocabulary list ownership
    vocabulary_list = await VocabularyService.get_vocabulary_list(db, list_id, include_words=False)
    
    if not vocabulary_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary list not found"
        )
    
    if vocabulary_list.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to access this list's test configuration"
        )
    
    config = await VocabularyTestService.get_test_config(db, list_id)
    
    if not config:
        # Return default configuration
        return {
            "vocabulary_list_id": list_id,
            "chain_enabled": False,
            "weeks_to_include": 1,
            "questions_per_week": 5,
            "current_week_questions": 10,
            "max_attempts": 3,
            "time_limit_minutes": 30
        }
    
    return VocabularyTestConfigResponse.model_validate(config)


@router.put("/vocabulary/{list_id}/test/config", response_model=VocabularyTestConfigResponse)
async def update_test_config(
    list_id: UUID,
    config_data: VocabularyTestConfig,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update test configuration for a vocabulary list"""
    if current_user.role.value != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can update test configurations"
        )
    
    # Verify vocabulary list ownership
    vocabulary_list = await VocabularyService.get_vocabulary_list(db, list_id, include_words=False)
    
    if not vocabulary_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary list not found"
        )
    
    if vocabulary_list.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to update this list's test configuration"
        )
    
    # Validate chain configuration
    if config_data.chain_enabled and config_data.chain_type == "specific_lists":
        # Validate chained lists
        if not config_data.chained_list_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Must specify at least one list when using specific_lists chain type"
            )
        
        # Ensure chained lists are valid and accessible
        valid_list_ids = []
        for chained_id in config_data.chained_list_ids:
            # Check if the list exists and is published
            result = await db.execute(
                select(VocabularyList)
                .where(
                    and_(
                        VocabularyList.id == chained_id,
                        VocabularyList.status == 'published',
                        VocabularyList.deleted_at.is_(None)
                    )
                )
            )
            if result.scalar_one_or_none():
                valid_list_ids.append(chained_id)
        
        if not valid_list_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid published vocabulary lists found for chaining"
            )
        
        # Update config with only valid lists
        config_data.chained_list_ids = valid_list_ids
        
        # Validate total review words
        if not config_data.total_review_words or config_data.total_review_words < 1 or config_data.total_review_words > 4:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Total review words must be between 1 and 4"
            )
    
    config = await VocabularyTestService.save_test_config(
        db, list_id, config_data.model_dump()
    )
    
    return VocabularyTestConfigResponse.model_validate(config)


@router.post("/vocabulary/{list_id}/test/generate", response_model=VocabularyTestResponse)
async def generate_vocabulary_test(
    list_id: UUID,
    classroom_assignment_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Generate a vocabulary test for a student (used by student endpoints)"""
    # This endpoint is called by the student endpoints, so we need to validate differently
    # Check if test is already available/generated
    
    try:
        test_data = await VocabularyTestService.generate_test(
            db, list_id, classroom_assignment_id, current_user.id
        )
        return VocabularyTestResponse.model_validate(test_data)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/vocabulary/{list_id}/test/attempts")
async def get_test_attempts(
    list_id: UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get test attempts for a vocabulary list (teacher view)"""
    if current_user.role.value != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only teachers can view test attempts"
        )
    
    # Verify vocabulary list ownership
    vocabulary_list = await VocabularyService.get_vocabulary_list(db, list_id, include_words=False)
    
    if not vocabulary_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Vocabulary list not found"
        )
    
    if vocabulary_list.teacher_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this list's test attempts"
        )
    
    # Get all test attempts for this vocabulary list
    result = await db.execute(
        select(func.count())
        .select_from(
            select().select_from(text("""
                vocabulary_test_attempts vta
                JOIN vocabulary_tests vt ON vt.id = vta.test_id
                WHERE vt.vocabulary_list_id = :list_id
                AND vta.status = 'completed'
            """))
        ),
        {"list_id": str(list_id)}
    )
    
    return {
        "vocabulary_list_id": list_id,
        "total_attempts": result.scalar() or 0,
        "message": "Test attempts analytics will be available in the teacher dashboard"
    }
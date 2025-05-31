from typing import List, Optional, Dict, Any, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
import asyncio
from pydantic_ai import Agent
from pydantic import BaseModel

from app.models import User
from app.models.vocabulary import (
    VocabularyList, VocabularyWord, VocabularyWordReview,
    VocabularyStatus, DefinitionSource, ReviewStatus
)
from app.schemas.vocabulary import (
    VocabularyListCreate, VocabularyListUpdate, VocabularyWordUpdate,
    VocabularyWordManualUpdate, VocabularyAIRequest, VocabularyAIResponse
)
from app.config.ai_models import VOCABULARY_DEFINITION_MODEL


class VocabularyDefinitionResult(BaseModel):
    """AI response model for vocabulary definitions"""
    definition: str
    example_1: str
    example_2: str


class VocabularyService:
    """Service for managing vocabulary lists and AI generation"""
    
    @staticmethod
    async def create_vocabulary_list(
        db: AsyncSession,
        teacher_id: UUID,
        vocabulary_data: VocabularyListCreate
    ) -> VocabularyList:
        """Create a new vocabulary list with words"""
        # Create the list
        vocabulary_list = VocabularyList(
            teacher_id=teacher_id,
            title=vocabulary_data.title,
            context_description=vocabulary_data.context_description,
            grade_level=vocabulary_data.grade_level,
            subject_area=vocabulary_data.subject_area,
            status=VocabularyStatus.DRAFT
        )
        db.add(vocabulary_list)
        await db.flush()
        
        # Add words with positions
        for idx, word_data in enumerate(vocabulary_data.words):
            word = VocabularyWord(
                list_id=vocabulary_list.id,
                word=word_data.word,
                teacher_definition=word_data.teacher_definition,
                teacher_example_1=word_data.teacher_example_1,
                teacher_example_2=word_data.teacher_example_2,
                position=idx,
                definition_source=DefinitionSource.TEACHER if word_data.teacher_definition else DefinitionSource.PENDING,
                examples_source=DefinitionSource.TEACHER if word_data.teacher_example_1 else DefinitionSource.PENDING
            )
            db.add(word)
            await db.flush()  # Flush to get the word ID
            
            # Create review record
            review = VocabularyWordReview(
                word_id=word.id,
                review_status=ReviewStatus.PENDING
            )
            db.add(review)
        
        await db.commit()
        await db.refresh(vocabulary_list)
        
        # Load relationships
        await db.execute(
            select(VocabularyList)
            .where(VocabularyList.id == vocabulary_list.id)
            .options(selectinload(VocabularyList.words).selectinload(VocabularyWord.review))
        )
        
        return vocabulary_list
    
    @staticmethod
    async def get_vocabulary_list(
        db: AsyncSession,
        list_id: UUID,
        include_words: bool = True
    ) -> Optional[VocabularyList]:
        """Get a vocabulary list by ID"""
        query = select(VocabularyList).where(
            and_(
                VocabularyList.id == list_id,
                VocabularyList.deleted_at.is_(None)
            )
        )
        
        if include_words:
            query = query.options(
                selectinload(VocabularyList.words).selectinload(VocabularyWord.review)
            )
        
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    @staticmethod
    async def list_vocabulary_lists(
        db: AsyncSession,
        teacher_id: UUID,
        status: Optional[VocabularyStatus] = None,
        search: Optional[str] = None,
        page: int = 1,
        per_page: int = 20
    ) -> Tuple[List[VocabularyList], int]:
        """List vocabulary lists with pagination and filters"""
        query = select(VocabularyList).where(
            and_(
                VocabularyList.teacher_id == teacher_id,
                VocabularyList.deleted_at.is_(None)
            )
        )
        
        if status:
            query = query.where(VocabularyList.status == status)
        
        if search:
            query = query.where(
                or_(
                    VocabularyList.title.ilike(f"%{search}%"),
                    VocabularyList.subject_area.ilike(f"%{search}%")
                )
            )
        
        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get paginated results
        query = query.order_by(VocabularyList.created_at.desc())
        query = query.offset((page - 1) * per_page).limit(per_page)
        
        result = await db.execute(query)
        lists = result.scalars().all()
        
        return lists, total
    
    @staticmethod
    async def update_vocabulary_list(
        db: AsyncSession,
        list_id: UUID,
        update_data: VocabularyListUpdate
    ) -> Optional[VocabularyList]:
        """Update vocabulary list metadata"""
        vocabulary_list = await VocabularyService.get_vocabulary_list(db, list_id, include_words=False)
        if not vocabulary_list:
            return None
        
        for field, value in update_data.model_dump(exclude_unset=True).items():
            setattr(vocabulary_list, field, value)
        
        await db.commit()
        await db.refresh(vocabulary_list)
        return vocabulary_list
    
    @staticmethod
    async def delete_vocabulary_list(
        db: AsyncSession,
        list_id: UUID
    ) -> bool:
        """Soft delete a vocabulary list"""
        vocabulary_list = await VocabularyService.get_vocabulary_list(db, list_id, include_words=False)
        if not vocabulary_list:
            return False
        
        vocabulary_list.deleted_at = datetime.utcnow()
        vocabulary_list.status = VocabularyStatus.ARCHIVED
        await db.commit()
        return True
    
    @staticmethod
    async def generate_ai_definitions(
        db: AsyncSession,
        list_id: UUID
    ) -> VocabularyList:
        """Generate AI definitions for all pending words in a list"""
        vocabulary_list = await VocabularyService.get_vocabulary_list(db, list_id, include_words=True)
        if not vocabulary_list:
            raise ValueError("Vocabulary list not found")
        
        # Update status to processing
        vocabulary_list.status = VocabularyStatus.PROCESSING
        await db.commit()
        
        # Get AI agent
        agent = Agent(
            VOCABULARY_DEFINITION_MODEL,
            result_type=VocabularyDefinitionResult,
            system_prompt=(
                "You are an educational vocabulary expert. Generate clear, grade-appropriate "
                "definitions and example sentences for vocabulary words. Ensure content is "
                "educational, accurate, and engaging for students."
            )
        )
        
        # Process words that need AI generation
        tasks = []
        for word in vocabulary_list.words:
            if word.definition_source == DefinitionSource.PENDING:
                tasks.append(VocabularyService._generate_word_definition(
                    agent, word, vocabulary_list, db
                ))
        
        if tasks:
            # Process in batches to avoid overwhelming the AI
            batch_size = 5
            for i in range(0, len(tasks), batch_size):
                batch = tasks[i:i + batch_size]
                await asyncio.gather(*batch)
        
        # Update status to reviewing
        vocabulary_list.status = VocabularyStatus.REVIEWING
        await db.commit()
        await db.refresh(vocabulary_list)
        
        return vocabulary_list
    
    @staticmethod
    async def _generate_word_definition(
        agent: Agent,
        word: VocabularyWord,
        vocabulary_list: VocabularyList,
        db: AsyncSession
    ):
        """Generate AI definition for a single word"""
        prompt = f"""
        Generate a definition and two example sentences for the word: {word.word}
        
        Context: {vocabulary_list.context_description}
        Grade Level: {vocabulary_list.grade_level}
        Subject Area: {vocabulary_list.subject_area}
        
        Requirements:
        1. Definition should be clear and appropriate for the grade level
        2. Examples should demonstrate proper usage in context
        3. Content should relate to the subject area when possible
        """
        
        if word.review and word.review.rejection_feedback:
            prompt += f"\n\nPrevious feedback: {word.review.rejection_feedback}"
        
        try:
            result = await agent.run(prompt)
            
            # Update word with AI content
            word.ai_definition = result.data.definition
            word.ai_example_1 = result.data.example_1
            word.ai_example_2 = result.data.example_2
            
            # Set source to AI if no teacher content
            if not word.teacher_definition:
                word.definition_source = DefinitionSource.AI
            if not word.teacher_example_1:
                word.examples_source = DefinitionSource.AI
            
            # Save to database
            await db.commit()
                
        except Exception as e:
            # Log error but continue processing other words
            print(f"Error generating definition for {word.word}: {str(e)}")
    
    @staticmethod
    async def review_word(
        db: AsyncSession,
        word_id: UUID,
        action: str,
        rejection_feedback: Optional[str] = None
    ) -> VocabularyWordReview:
        """Review a word (accept or reject)"""
        # Get word with review
        result = await db.execute(
            select(VocabularyWord)
            .where(VocabularyWord.id == word_id)
            .options(selectinload(VocabularyWord.review))
        )
        word = result.scalar_one_or_none()
        
        if not word or not word.review:
            raise ValueError("Word or review not found")
        
        if action == "accept":
            word.review.review_status = ReviewStatus.ACCEPTED
            word.review.reviewed_at = datetime.utcnow()
            
            # Use AI content as final if accepted
            if word.ai_definition and word.definition_source == DefinitionSource.AI:
                word.definition_source = DefinitionSource.AI
            if word.ai_example_1 and word.examples_source == DefinitionSource.AI:
                word.examples_source = DefinitionSource.AI
                
        elif action == "reject":
            if word.review.review_status == ReviewStatus.PENDING:
                word.review.review_status = ReviewStatus.REJECTED_ONCE
            else:
                word.review.review_status = ReviewStatus.REJECTED_TWICE
            
            word.review.rejection_feedback = rejection_feedback
            word.review.reviewed_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(word.review)
        
        return word.review
    
    @staticmethod
    async def update_word_manually(
        db: AsyncSession,
        word_id: UUID,
        update_data: VocabularyWordManualUpdate
    ) -> VocabularyWord:
        """Update word with teacher-provided content"""
        result = await db.execute(
            select(VocabularyWord)
            .where(VocabularyWord.id == word_id)
            .options(selectinload(VocabularyWord.review))
        )
        word = result.scalar_one_or_none()
        
        if not word:
            raise ValueError("Word not found")
        
        # Update with teacher content
        word.teacher_definition = update_data.definition
        word.teacher_example_1 = update_data.example_1
        word.teacher_example_2 = update_data.example_2
        word.definition_source = DefinitionSource.TEACHER
        word.examples_source = DefinitionSource.TEACHER
        
        # Mark as accepted
        if word.review:
            word.review.review_status = ReviewStatus.ACCEPTED
            word.review.reviewed_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(word)
        
        return word
    
    @staticmethod
    async def regenerate_word_definition(
        db: AsyncSession,
        word_id: UUID
    ) -> VocabularyWord:
        """Regenerate AI definition for a rejected word"""
        result = await db.execute(
            select(VocabularyWord)
            .where(VocabularyWord.id == word_id)
            .options(
                selectinload(VocabularyWord.review),
                selectinload(VocabularyWord.vocabulary_list)
            )
        )
        word = result.scalar_one_or_none()
        
        if not word:
            raise ValueError("Word not found")
        
        # Get AI agent
        agent = Agent(
            VOCABULARY_DEFINITION_MODEL,
            result_type=VocabularyDefinitionResult,
            system_prompt=(
                "You are an educational vocabulary expert. Generate clear, grade-appropriate "
                "definitions and example sentences for vocabulary words."
            )
        )
        
        # Generate new definition
        await VocabularyService._generate_word_definition(agent, word, word.vocabulary_list, db)
        
        await db.commit()
        await db.refresh(word)
        
        return word
    
    @staticmethod
    async def publish_vocabulary_list(
        db: AsyncSession,
        list_id: UUID
    ) -> VocabularyList:
        """Publish a vocabulary list after review"""
        vocabulary_list = await VocabularyService.get_vocabulary_list(db, list_id, include_words=True)
        if not vocabulary_list:
            raise ValueError("Vocabulary list not found")
        
        # Check all words are reviewed
        unreviewed_count = sum(
            1 for word in vocabulary_list.words
            if word.review and word.review.review_status == ReviewStatus.PENDING
        )
        
        if unreviewed_count > 0:
            raise ValueError(f"{unreviewed_count} words still need review")
        
        vocabulary_list.status = VocabularyStatus.PUBLISHED
        await db.commit()
        await db.refresh(vocabulary_list)
        
        return vocabulary_list
    
    @staticmethod
    async def get_review_progress(
        db: AsyncSession,
        list_id: UUID
    ) -> Dict[str, Any]:
        """Get review progress statistics for a list"""
        # Simple query to get all reviews for this list
        result = await db.execute(
            select(VocabularyWordReview.review_status)
            .join(VocabularyWord)
            .where(VocabularyWord.list_id == list_id)
        )
        
        statuses = [row[0] for row in result.fetchall()]
        
        total = len(statuses)
        accepted = sum(1 for s in statuses if s == ReviewStatus.ACCEPTED)
        rejected = sum(1 for s in statuses if s in [ReviewStatus.REJECTED_ONCE, ReviewStatus.REJECTED_TWICE])
        pending = sum(1 for s in statuses if s == ReviewStatus.PENDING)
        
        return {
            'total': total,
            'accepted': accepted,
            'rejected': rejected,
            'pending': pending,
            'progress_percentage': (
                int((accepted / total * 100)) if total > 0 else 0
            )
        }
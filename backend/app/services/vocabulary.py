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
from app.services.pronunciation import PronunciationService


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
    async def fetch_pronunciation_data(
        db: AsyncSession,
        list_id: UUID
    ) -> int:
        """Fetch pronunciation data for all words in a vocabulary list"""
        from app.services.pronunciation import PronunciationService
        return await PronunciationService.batch_update_pronunciations(db, str(list_id))
    
    @staticmethod
    async def get_vocabulary_list(
        db: AsyncSession,
        list_id: UUID,
        include_words: bool = True,
        include_archived: bool = False
    ) -> Optional[VocabularyList]:
        """Get a vocabulary list by ID"""
        query = select(VocabularyList).where(VocabularyList.id == list_id)
        
        # Only filter deleted_at if not including archived
        if not include_archived:
            query = query.where(VocabularyList.deleted_at.is_(None))
        
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
        per_page: int = 20,
        include_archived: bool = False
    ) -> Tuple[List[VocabularyList], int]:
        """List vocabulary lists with pagination and filters"""
        conditions = [VocabularyList.teacher_id == teacher_id]
        
        # Only filter deleted_at if not including archived
        if not include_archived:
            conditions.append(VocabularyList.deleted_at.is_(None))
        
        query = select(VocabularyList).where(and_(*conditions))
        
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
        vocabulary_list = await VocabularyService.get_vocabulary_list(db, list_id, include_words=False, include_archived=True)
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
        await db.commit()
        return True
    
    @staticmethod
    async def generate_ai_definitions(
        db: AsyncSession,
        list_id: UUID
    ) -> VocabularyList:
        """Generate AI definitions for all pending words in a list and create fill-in-the-blank questions"""
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
        
        # Generate fill-in-the-blank questions for vocabulary challenge
        try:
            from app.services.vocabulary_game_generator import VocabularyGameGenerator
            game_generator = VocabularyGameGenerator(db)
            await game_generator.generate_game_questions(list_id)
        except Exception as e:
            # Don't fail the whole process if game generation fails
            print(f"Warning: Could not generate vocabulary challenge questions: {e}")
        
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
        
        # Reload with all relationships
        result = await db.execute(
            select(VocabularyWord)
            .where(VocabularyWord.id == word_id)
            .options(
                selectinload(VocabularyWord.review),
                selectinload(VocabularyWord.vocabulary_list)
            )
        )
        return result.scalar_one()
    
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
        
        # Fetch pronunciation data for all words before publishing
        try:
            pronunciation_count = await PronunciationService.batch_update_pronunciations(db, list_id)
            print(f"Updated pronunciation for {pronunciation_count} words in vocabulary list {list_id}")
        except Exception as e:
            print(f"Warning: Could not fetch pronunciation data: {e}")
            # Continue with publishing even if pronunciation fails
        
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
    
    @staticmethod
    async def generate_presentation_html(vocabulary_list: VocabularyList) -> str:
        """Generate a standalone HTML presentation for a vocabulary list"""
        # Sort words alphabetically
        sorted_words = sorted(vocabulary_list.words, key=lambda w: w.word.lower())
        
        # Escape HTML in content
        def escape_html(text: str) -> str:
            if not text:
                return ""
            return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
                .replace('"', "&quot;")
                .replace("'", "&#39;"))
        
        # Generate word slides HTML
        word_slides_html = ""
        for word in sorted_words:
            # Use teacher definition/examples if available, otherwise use AI
            definition = escape_html(word.teacher_definition or word.ai_definition or "")
            example = escape_html(word.teacher_example_1 or word.ai_example_1 or "")
            
            word_slides_html += f"""
    <div class="slide">
        <h2 class="word-title">{escape_html(word.word)}</h2>
        <div class="reveal-container">
            <button class="reveal-button" id="def-btn-{word.id}" onclick="revealDefinition('{word.id}')">
                Show Definition
            </button>
            <div class="definition hidden" id="def-{word.id}">{definition}</div>
            <button class="reveal-button hidden" id="ex-btn-{word.id}" onclick="revealExample('{word.id}')">
                Show Example
            </button>
            <div class="example hidden" id="ex-{word.id}">{example}</div>
        </div>
    </div>"""
        
        # Generate complete HTML
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{escape_html(vocabulary_list.title)} - Vocabulary Presentation</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
            overflow: hidden;
        }}
        
        .presentation-container {{
            width: 100%;
            height: 100vh;
            position: relative;
        }}
        
        .progress-bar {{
            position: absolute;
            top: 0;
            left: 0;
            height: 4px;
            background: rgba(255, 255, 255, 0.3);
            width: 100%;
            z-index: 10;
        }}
        
        .progress-fill {{
            height: 100%;
            background: #fff;
            width: 0;
            transition: width 0.3s ease;
        }}
        
        .slide-counter {{
            position: absolute;
            top: 20px;
            right: 20px;
            color: white;
            font-size: 18px;
            font-weight: 500;
            z-index: 10;
            background: rgba(0, 0, 0, 0.3);
            padding: 8px 16px;
            border-radius: 20px;
        }}
        
        .slide {{
            position: absolute;
            width: 100%;
            height: 100%;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            opacity: 0;
            transform: translateX(100%);
            transition: all 0.5s ease;
            padding: 40px;
            text-align: center;
        }}
        
        .slide.active {{
            opacity: 1;
            transform: translateX(0);
        }}
        
        .slide h1 {{
            color: white;
            font-size: clamp(48px, 8vw, 96px);
            font-weight: 700;
            margin-bottom: 30px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.3);
        }}
        
        .slide h2.word-title {{
            color: white;
            font-size: clamp(60px, 10vw, 120px);
            font-weight: 700;
            margin-bottom: 50px;
            text-shadow: 3px 3px 6px rgba(0, 0, 0, 0.3);
        }}
        
        .slide p {{
            color: white;
            font-size: clamp(20px, 3vw, 32px);
            line-height: 1.5;
            text-shadow: 1px 1px 2px rgba(0, 0, 0, 0.3);
            margin-bottom: 20px;
        }}
        
        .reveal-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 20px;
            margin-top: 40px;
        }}
        
        .reveal-button {{
            background: rgba(255, 255, 255, 0.2);
            border: 2px solid white;
            color: white;
            padding: 16px 32px;
            border-radius: 40px;
            font-size: clamp(18px, 2.5vw, 24px);
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s ease;
            backdrop-filter: blur(5px);
            box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
        }}
        
        .reveal-button:hover {{
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.3);
        }}
        
        .reveal-button:active {{
            transform: translateY(0);
        }}
        
        .definition, .example {{
            background: rgba(255, 255, 255, 0.95);
            color: #333;
            padding: 30px 50px;
            border-radius: 20px;
            font-size: clamp(20px, 3vw, 28px);
            line-height: 1.6;
            max-width: 900px;
            margin: 0 auto;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.3);
            animation: fadeIn 0.5s ease-out;
        }}
        
        .definition {{
            margin-bottom: 10px;
        }}
        
        .example {{
            font-style: italic;
            background: rgba(255, 255, 200, 0.95);
        }}
        
        .hidden {{
            display: none !important;
        }}
        
        @keyframes fadeIn {{
            from {{
                opacity: 0;
                transform: translateY(20px);
            }}
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
        
        .navigation {{
            position: absolute;
            bottom: 30px;
            left: 50%;
            transform: translateX(-50%);
            display: flex;
            gap: 20px;
            z-index: 10;
        }}
        
        .nav-button {{
            background: rgba(255, 255, 255, 0.2);
            border: 2px solid white;
            color: white;
            padding: 12px 24px;
            border-radius: 30px;
            font-size: 18px;
            cursor: pointer;
            transition: all 0.3s ease;
            backdrop-filter: blur(5px);
        }}
        
        .nav-button:hover {{
            background: rgba(255, 255, 255, 0.3);
            transform: translateY(-2px);
        }}
        
        .nav-button:disabled {{
            opacity: 0.5;
            cursor: not-allowed;
        }}
        
        .instructions {{
            position: absolute;
            bottom: 100px;
            left: 50%;
            transform: translateX(-50%);
            color: white;
            font-size: 16px;
            opacity: 0.8;
            text-align: center;
        }}
        
        @media print {{
            body {{
                background: white;
            }}
            
            .slide {{
                page-break-after: always;
                position: relative;
                transform: none !important;
                opacity: 1 !important;
                height: auto;
                min-height: 100vh;
            }}
            
            .slide h1, .slide h2, .slide p {{
                color: #333;
                text-shadow: none;
            }}
            
            .progress-bar, .slide-counter, .navigation, .instructions {{
                display: none;
            }}
            
            .definition, .example {{
                opacity: 1 !important;
                transform: scale(1) !important;
                display: block !important;
            }}
        }}
        
        @media (max-width: 768px) {{
            .slide h1 {{
                font-size: 48px;
            }}
            
            .slide h2.word-title {{
                font-size: 60px;
            }}
            
            .definition, .example {{
                padding: 20px 30px;
                font-size: 20px;
            }}
            
            .navigation {{
                bottom: 20px;
            }}
            
            .nav-button {{
                padding: 10px 20px;
                font-size: 16px;
            }}
        }}
    </style>
</head>
<body>
    <div class="presentation-container">
        <div class="progress-bar">
            <div class="progress-fill"></div>
        </div>
        <div class="slide-counter">1 / {len(sorted_words) + 2}</div>
        
        <!-- Title Slide -->
        <div class="slide active">
            <h1>{escape_html(vocabulary_list.title)}</h1>
            <p>{escape_html(vocabulary_list.grade_level)} • {escape_html(vocabulary_list.subject_area)}</p>
            <p>{len(sorted_words)} Vocabulary Words</p>
        </div>
        
        <!-- Word Slides -->
        {word_slides_html}
        
        <!-- Summary Slide -->
        <div class="slide">
            <h1>Excellent Work!</h1>
            <p>You've learned {len(sorted_words)} new vocabulary words</p>
        </div>
        
        <div class="navigation">
            <button class="nav-button" id="prevButton" onclick="previousSlide()">← Previous</button>
            <button class="nav-button" id="nextButton" onclick="nextSlide()">Next →</button>
        </div>
        
        <div class="instructions">
            Press arrow keys to navigate • Spacebar or click buttons to reveal content
        </div>
    </div>
    
    <script>
        let currentSlide = 0;
        const slides = document.querySelectorAll('.slide');
        const totalSlides = slides.length;
        const progressFill = document.querySelector('.progress-fill');
        const slideCounter = document.querySelector('.slide-counter');
        const prevButton = document.getElementById('prevButton');
        const nextButton = document.getElementById('nextButton');
        
        function updateSlide() {{
            slides.forEach((slide, index) => {{
                slide.classList.toggle('active', index === currentSlide);
            }});
            
            // Update progress bar
            const progress = ((currentSlide + 1) / totalSlides) * 100;
            progressFill.style.width = progress + '%';
            
            // Update slide counter
            slideCounter.textContent = `${{currentSlide + 1}} / ${{totalSlides}}`;
            
            // Update button states
            prevButton.disabled = currentSlide === 0;
            nextButton.disabled = currentSlide === totalSlides - 1;
        }}
        
        function revealDefinition(wordId) {{
            const defBtn = document.getElementById(`def-btn-${{wordId}}`);
            const def = document.getElementById(`def-${{wordId}}`);
            const exBtn = document.getElementById(`ex-btn-${{wordId}}`);
            
            defBtn.classList.add('hidden');
            def.classList.remove('hidden');
            exBtn.classList.remove('hidden');
        }}
        
        function revealExample(wordId) {{
            const exBtn = document.getElementById(`ex-btn-${{wordId}}`);
            const ex = document.getElementById(`ex-${{wordId}}`);
            
            exBtn.classList.add('hidden');
            ex.classList.remove('hidden');
        }}
        
        function nextSlide() {{
            if (currentSlide < totalSlides - 1) {{
                currentSlide++;
                updateSlide();
            }}
        }}
        
        function previousSlide() {{
            if (currentSlide > 0) {{
                currentSlide--;
                updateSlide();
            }}
        }}
        
        // Keyboard navigation
        document.addEventListener('keydown', (e) => {{
            switch(e.key) {{
                case 'ArrowRight':
                    e.preventDefault();
                    nextSlide();
                    break;
                case 'ArrowLeft':
                    e.preventDefault();
                    previousSlide();
                    break;
                case ' ':
                    e.preventDefault();
                    // Spacebar triggers the first visible button on the current slide
                    const currentSlideElement = slides[currentSlide];
                    const visibleButton = currentSlideElement.querySelector('.reveal-button:not(.hidden)');
                    if (visibleButton) {{
                        visibleButton.click();
                    }} else {{
                        nextSlide();
                    }}
                    break;
            }}
        }});
        
        // Initialize
        updateSlide();
    </script>
</body>
</html>"""
        
        return html_content
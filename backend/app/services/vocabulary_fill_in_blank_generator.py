"""
Vocabulary fill-in-the-blank sentence generation service
Generates sentences with blanks for vocabulary practice activities
"""
import random
import json
from typing import List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.vocabulary import VocabularyList, VocabularyWord
from app.models.vocabulary_practice import VocabularyFillInBlankSentence
import logging

logger = logging.getLogger(__name__)


class VocabularyFillInBlankGenerator:
    """Generates fill-in-the-blank sentences for vocabulary practice"""
    
    # Number of sentences per word
    SENTENCES_PER_WORD = 2
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_fill_in_blank_sentences(
        self, 
        vocabulary_list_id: UUID,
        regenerate: bool = False
    ) -> List[Dict[str, Any]]:
        """Generate fill-in-the-blank sentences for vocabulary assignment"""
        
        # Check if sentences already exist
        if not regenerate:
            existing_result = await self.db.execute(
                select(VocabularyFillInBlankSentence)
                .where(VocabularyFillInBlankSentence.vocabulary_list_id == vocabulary_list_id)
                .order_by(VocabularyFillInBlankSentence.sentence_order)
            )
            existing_sentences = existing_result.scalars().all()
            
            if existing_sentences:
                return [self._format_sentence(sentence) for sentence in existing_sentences]
        
        # Get vocabulary list with words
        result = await self.db.execute(
            select(VocabularyList)
            .where(VocabularyList.id == vocabulary_list_id)
        )
        vocab_list = result.scalar_one_or_none()
        
        if not vocab_list:
            raise ValueError(f"Vocabulary list {vocabulary_list_id} not found")
        
        # Get all words for this list
        words_result = await self.db.execute(
            select(VocabularyWord)
            .where(VocabularyWord.list_id == vocabulary_list_id)
            .order_by(VocabularyWord.position)
        )
        words = words_result.scalars().all()
        
        if not words:
            raise ValueError("No words found in vocabulary list")
        
        # Generate sentences for each word
        all_sentences = []
        sentence_order = 1
        
        for word in words:
            try:
                sentences = self._generate_sentences_for_word(word, vocab_list)
                
                for sentence_with_blank in sentences:
                    sentence_data = {
                        'vocabulary_list_id': vocabulary_list_id,
                        'word_id': word.id,
                        'sentence_with_blank': sentence_with_blank,
                        'correct_answer': word.word,
                        'sentence_order': sentence_order
                    }
                    all_sentences.append(sentence_data)
                    sentence_order += 1
                    
            except Exception as e:
                logger.error(f"Error generating sentences for word '{word.word}': {str(e)}")
                # Fall back to simple template sentences
                fallback_sentences = self._create_simple_sentences(word)
                for sentence in fallback_sentences:
                    sentence_data = {
                        'vocabulary_list_id': vocabulary_list_id,
                        'word_id': word.id,
                        'sentence_with_blank': sentence,
                        'correct_answer': word.word,
                        'sentence_order': sentence_order
                    }
                    all_sentences.append(sentence_data)
                    sentence_order += 1
        
        # Save sentences to database
        sentence_models = []
        for sentence_data in all_sentences:
            sentence = VocabularyFillInBlankSentence(**sentence_data)
            sentence_models.append(sentence)
            self.db.add(sentence)
        
        await self.db.commit()
        
        return [self._format_sentence(sentence) for sentence in sentence_models]
    
    def _generate_sentences_for_word(
        self,
        word: VocabularyWord,
        vocab_list: VocabularyList
    ) -> List[str]:
        """Generate sentences for a specific word using templates"""
        
        # Use existing examples if available
        sentences = []
        
        # Check for teacher examples
        if word.teacher_example_1 and word.word in word.teacher_example_1:
            sentences.append(word.teacher_example_1.replace(word.word, "_____"))
        if word.teacher_example_2 and word.word in word.teacher_example_2:
            sentences.append(word.teacher_example_2.replace(word.word, "_____"))
        
        # Check for AI examples
        if len(sentences) < self.SENTENCES_PER_WORD and word.ai_example_1 and word.word in word.ai_example_1:
            sentences.append(word.ai_example_1.replace(word.word, "_____"))
        if len(sentences) < self.SENTENCES_PER_WORD and word.ai_example_2 and word.word in word.ai_example_2:
            sentences.append(word.ai_example_2.replace(word.word, "_____"))
        
        # Generate template sentences if we need more
        while len(sentences) < self.SENTENCES_PER_WORD:
            template_sentences = self._create_template_sentences(word, vocab_list)
            for sentence in template_sentences:
                if len(sentences) < self.SENTENCES_PER_WORD:
                    sentences.append(sentence)
        
        return sentences[:self.SENTENCES_PER_WORD]
    
    def _create_template_sentences(
        self,
        word: VocabularyWord,
        vocab_list: VocabularyList
    ) -> List[str]:
        """Create template sentences using the word"""
        
        templates = [
            f"The students learned about _____ in their {vocab_list.subject_area} lesson.",
            f"Understanding _____ is important for this topic.",
            f"The teacher explained what _____ means in this context.",
            f"Students can practice using _____ in different sentences.",
            f"The definition of _____ helps us understand the concept.",
            f"When we study {vocab_list.subject_area}, we often encounter _____.",
            f"The word _____ is key to understanding this lesson.",
            f"_____ is an important term in {vocab_list.subject_area}.",
        ]
        
        return templates
    
    def _create_simple_sentences(self, word: VocabularyWord) -> List[str]:
        """Create simple fallback sentences"""
        
        return [
            f"The word _____ has a specific meaning.",
            f"Students should understand what _____ means."
        ]
    
    def _format_sentence(self, sentence: VocabularyFillInBlankSentence) -> Dict[str, Any]:
        """Format a sentence for the frontend"""
        return {
            'id': str(sentence.id),
            'sentence_with_blank': sentence.sentence_with_blank,
            'correct_answer': sentence.correct_answer,
            'word_id': str(sentence.word_id),
            'sentence_order': sentence.sentence_order
        }
    
    def calculate_assignment_requirements(self, word_count: int) -> Dict[str, int]:
        """Calculate assignment requirements based on word count"""
        
        total_sentences = word_count * self.SENTENCES_PER_WORD
        passing_score = 70  # 70% required to pass
        
        return {
            'total_sentences': total_sentences,
            'sentences_per_word': self.SENTENCES_PER_WORD,
            'passing_score': passing_score,
            'minimum_correct': int((total_sentences * passing_score) / 100)
        }
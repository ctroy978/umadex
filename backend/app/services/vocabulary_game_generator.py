"""
Vocabulary fill-in-the-blank question generation service
Generates fill-in-the-blank sentences for vocabulary practice
"""
import json
import random
from typing import List, Dict, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.vocabulary import VocabularyList, VocabularyWord
from app.models.vocabulary_practice import VocabularyGameQuestion
from app.core.config import settings
import httpx
import asyncio
import logging

logger = logging.getLogger(__name__)


class VocabularyGameGenerator:
    """Generates fill-in-the-blank questions for vocabulary practice"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_game_questions(
        self, 
        vocabulary_list_id: UUID,
        regenerate: bool = False
    ) -> List[Dict[str, Any]]:
        """Generate fill-in-the-blank questions for vocabulary list"""
        
        # Check if questions already exist
        if not regenerate:
            existing_questions = await self.db.execute(
                select(VocabularyGameQuestion)
                .where(VocabularyGameQuestion.vocabulary_list_id == vocabulary_list_id)
                .order_by(VocabularyGameQuestion.question_order)
            )
            if existing_questions.scalars().first():
                logger.info(f"Questions already exist for vocabulary list {vocabulary_list_id}")
                return []
        
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
        
        # Generate exactly 2 fill-in-the-blank sentences per word
        questions = []
        question_order = 1
        
        for word in words:
            word_questions = await self._generate_questions_for_word(
                word, 
                vocab_list,
                question_order
            )
            questions.extend(word_questions)
            question_order += 2  # 2 questions per word
        
        # Save questions to database
        for question_data in questions:
            question = VocabularyGameQuestion(**question_data)
            self.db.add(question)
        
        await self.db.commit()
        logger.info(f"Generated {len(questions)} fill-in-the-blank questions for vocabulary list {vocabulary_list_id}")
        
        return questions
    
    async def _generate_questions_for_word(
        self,
        word: VocabularyWord,
        vocab_list: VocabularyList,
        start_order: int
    ) -> List[Dict[str, Any]]:
        """Generate exactly 2 fill-in-the-blank sentences for a word"""
        
        # Get word definition and examples
        definition = word.teacher_definition or word.ai_definition or "No definition available"
        example_1 = word.teacher_example_1 or word.ai_example_1
        example_2 = word.teacher_example_2 or word.ai_example_2
        examples = [ex for ex in [example_1, example_2] if ex]
        
        # Generate 2 fill-in-the-blank sentences
        sentences = await self._generate_fill_in_blank_sentences(
            word=word.word,
            definition=definition,
            examples=examples,
            context=vocab_list.context_description,
            grade_level=vocab_list.grade_level
        )
        
        questions = []
        for i, sentence in enumerate(sentences[:2]):  # Ensure exactly 2
            questions.append({
                'vocabulary_list_id': vocab_list.id,
                'word_id': word.id,
                'question_type': 'fill_in_blank',
                'difficulty_level': 'medium',  # All questions are medium difficulty
                'question_text': sentence,
                'correct_answer': word.word,
                'explanation': '',  # No explanation needed per requirements
                'question_order': start_order + i
            })
        
        return questions
    
    async def _generate_fill_in_blank_sentences(
        self,
        word: str,
        definition: str,
        examples: List[str],
        context: str,
        grade_level: str
    ) -> List[str]:
        """Generate fill-in-the-blank sentences using AI or templates"""
        
        try:
            # Try AI generation first
            sentences = await self._generate_with_ai(word, definition, examples, context, grade_level)
            if sentences and len(sentences) >= 2:
                return sentences
        except Exception as e:
            logger.error(f"AI generation failed for word '{word}': {e}")
        
        # Fallback to template generation
        return self._generate_template_sentences(word, definition, context, grade_level)
    
    async def _generate_with_ai(
        self,
        word: str,
        definition: str,
        examples: List[str],
        context: str,
        grade_level: str
    ) -> List[str]:
        """Generate sentences using AI"""
        
        examples_text = "\n".join([f"- {ex}" for ex in examples]) if examples else "No examples provided"
        
        prompt = f"""Generate exactly 2 fill-in-the-blank sentences for the vocabulary word '{word}'.

Word: {word}
Definition: {definition}
Examples:
{examples_text}
Context: {context}
Grade Level: {grade_level}

CRITICAL REQUIREMENT - EXACT WORD FORM MATCHING:
The sentence must work with the vocabulary word '{word}' in its EXACT form as provided.
- NO tense changes (past/present/future)
- NO inflections (plural/singular changes)
- NO modifications (verb to noun, adjective to adverb, etc.)
- The word '{word}' must fit the blank exactly as written

Instructions:
1. Create 2 different sentences where '{word}' fits the blank in its exact form
2. Verify that '{word}' works grammatically without any changes
3. Structure the sentence to require the exact word form provided
4. Each sentence should provide enough context for a student to infer '{word}'
5. Make sentences appropriate for {grade_level} students
6. Ensure sentences are clear and contextually rich
7. The blank should accept ONLY '{word}' - not variations or related words

Word Form Guidelines:
- If '{word}' is a verb (like "recant"), use structures like "must _____", "to _____", "will _____"
- If '{word}' is an adjective (like "spurious"), use structures like "was _____", "seems _____", "appeared _____"
- If '{word}' is a noun (like "analysis"), use structures like "the _____ of", "her _____", "this _____"

VERIFICATION: After creating each sentence, test it by inserting '{word}' exactly as written. The sentence must be grammatically correct and make logical sense.

Format your response as:
1. [First sentence with _____ where '{word}' fits exactly]
2. [Second sentence with _____ where '{word}' fits exactly]

Example format for adjective "spurious":
1. The detective found the evidence was _____ and couldn't be trusted.
2. Her _____ claims were quickly exposed by investigators."""
        
        response = await self._call_ai_api(prompt)
        
        # Parse the response
        sentences = []
        lines = response.strip().split('\n')
        for line in lines:
            # Remove numbering and clean up
            if line.strip():
                sentence = line.strip()
                if sentence[0].isdigit() and sentence[1] in '.):':
                    sentence = sentence[2:].strip()
                if '_____' in sentence and sentence not in sentences:
                    sentences.append(sentence)
        
        # Ensure we have exactly 2 sentences
        if len(sentences) < 2:
            # Generate additional sentences with templates
            sentences.extend(self._generate_template_sentences(word, definition, context, grade_level))
        
        return sentences[:2]
    
    def _generate_template_sentences(
        self,
        word: str,
        definition: str,
        context: str,
        grade_level: str
    ) -> List[str]:
        """Generate word-specific sentences using templates when AI is not available"""
        
        # Determine word characteristics from definition and word form
        definition_lower = definition.lower()
        word_lower = word.lower()
        
        # Enhanced word form detection
        is_noun = any(marker in definition_lower for marker in [
            'person', 'place', 'thing', 'object', 'concept', 'idea', 'state', 'condition',
            'someone who', 'something that', 'a ', 'an ', 'the study of', 'examination of'
        ])
        
        # Check for verb patterns - prioritize infinitive form detection
        is_verb = (
            any(marker in definition_lower for marker in [
                'to ', 'action of', 'act of', 'process of', 'doing', 'make', 'cause',
                'remove', 'force', 'prove', 'show', 'demonstrate'
            ]) and not word_lower.endswith('ed')  # Avoid past participles/adjectives
        )
        
        # Check for adjective patterns - including past participles used as adjectives
        is_adjective = (
            any(marker in definition_lower for marker in [
                'describing', 'quality', 'characteristic', 'having', 'showing',
                'genuine', 'authentic', 'false', 'true', 'important', 'necessary',
                'practical', 'realistic', 'justified', 'permitted', 'guaranteed'
            ]) or 
            (word_lower.endswith('ed') and 'justified' in definition_lower)  # Past participles as adjectives
        )
        
        # Special handling for specific words that might be ambiguous
        if word_lower == 'warranted':
            # "warranted" is an adjective meaning "justified"
            is_adjective = True
            is_verb = False
        
        sentences = []
        
        # Generate word-specific sentences based on the actual definition
        if is_verb:
            # For verbs, create sentences using infinitive structures (to/must/will/should)
            if 'remove' in definition_lower or 'force' in definition_lower:
                sentences.extend([
                    f"The board voted to _____ the corrupt official from office.",
                    f"Security had to _____ the disruptive protester from the meeting.",
                    f"The committee will _____ any members who violate the rules.",
                    f"They decided to _____ the outdated policy from the handbook."
                ])
            elif 'prove' in definition_lower or 'disprove' in definition_lower:
                sentences.extend([
                    f"The scientist was able to _____ the theory with new evidence.",
                    f"Her research helped _____ the common misconception.",
                    f"The lawyer attempted to _____ the witness's testimony.",
                    f"No one could _____ his claims about the discovery."
                ])
            else:
                # Generic verb templates using infinitive structures
                sentences.extend([
                    f"The committee decided to _____ the proposal after careful consideration.",
                    f"Students must _____ their understanding through practical application.",
                    f"The manager chose to _____ the new policy immediately.",
                    f"They will _____ the decision at the next meeting."
                ])
        
        elif is_adjective:
            # For adjectives, create sentences where the blank needs an adjective
            if 'false' in definition_lower or 'not genuine' in definition_lower:
                sentences.extend([
                    f"The detective found the evidence to be _____ and unreliable.",
                    f"His _____ claims were quickly exposed by investigators."
                ])
            elif 'practical' in definition_lower or 'realistic' in definition_lower:
                sentences.extend([
                    f"Her _____ approach to problem-solving impressed everyone.",
                    f"The manager took a _____ stance on the budget issues."
                ])
            elif 'necessary' in definition_lower or 'important' in definition_lower:
                sentences.extend([
                    f"The medicine was _____ for the patient's recovery.",
                    f"Fresh water is _____ for all forms of life."
                ])
            elif 'justified' in definition_lower or word_lower == 'warranted':
                # Special handling for "warranted" and similar adjectives
                sentences.extend([
                    f"The criticism was _____ given the circumstances.",
                    f"Her concerns about safety were completely _____.",
                    f"The extreme security measures seemed _____ after the threat.",
                    f"Such drastic action was _____ by the emergency situation."
                ])
            else:
                # Generic adjective templates
                sentences.extend([
                    f"The _____ nature of the evidence made the case compelling.",
                    f"Her _____ understanding of the subject was impressive."
                ])
        
        elif is_noun:
            # For nouns, create sentences where the blank needs a noun
            sentences.extend([
                f"The _____ between the two concepts became clear during the discussion.",
                f"Understanding this _____ is essential for success in the field."
            ])
        
        else:
            # Fallback for unclear part of speech - create contextually neutral sentences
            sentences.extend([
                f"The concept of _____ is important to understand in this context.",
                f"Students should be familiar with the term _____ and its applications."
            ])
        
        # Ensure we have exactly 2 sentences
        if len(sentences) < 2:
            # Add generic fallback sentences
            sentences.extend([
                f"The meaning of _____ becomes clear when examined in context.",
                f"This example demonstrates the proper use of _____."
            ])
        
        return sentences[:2]
    
    async def _call_ai_api(self, prompt: str) -> str:
        """Call AI API with proper error handling"""
        try:
            # Check if AI is configured
            if hasattr(settings, 'LLM_PROVIDER') and settings.LLM_PROVIDER:
                if settings.LLM_PROVIDER == "openai" and hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
                    return await self._call_openai(prompt)
                elif settings.LLM_PROVIDER == "anthropic" and hasattr(settings, 'ANTHROPIC_API_KEY') and settings.ANTHROPIC_API_KEY:
                    return await self._call_anthropic(prompt)
                elif settings.LLM_PROVIDER == "gemini" and hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
                    return await self._call_gemini(prompt)
            
            # Try Gemini if available (fallback for backward compatibility)
            if hasattr(settings, 'GEMINI_API_KEY') and settings.GEMINI_API_KEY:
                return await self._call_gemini(prompt)
            
            # If no AI configured, return empty
            logger.info("AI not configured, using template generation")
            return ""
        except Exception as e:
            logger.error(f"AI API call failed: {e}")
            return ""
    
    async def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        if not hasattr(settings, 'OPENAI_API_KEY') or not settings.OPENAI_API_KEY:
            raise Exception("OpenAI API key not configured")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": getattr(settings, 'OPENAI_MODEL', 'gpt-3.5-turbo'),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 200
                },
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
    
    async def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API"""
        if not hasattr(settings, 'ANTHROPIC_API_KEY') or not settings.ANTHROPIC_API_KEY:
            raise Exception("Anthropic API key not configured")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "Authorization": f"Bearer {settings.ANTHROPIC_API_KEY}",
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": getattr(settings, 'ANTHROPIC_MODEL', 'claude-3-haiku-20240307'),
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 200
                },
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            return result['content'][0]['text']
    
    async def _call_gemini(self, prompt: str) -> str:
        """Call Google Gemini API"""
        if not hasattr(settings, 'GEMINI_API_KEY') or not settings.GEMINI_API_KEY:
            raise Exception("Gemini API key not configured")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash-latest:generateContent?key={settings.GEMINI_API_KEY}",
                headers={
                    "Content-Type": "application/json"
                },
                json={
                    "contents": [{
                        "parts": [{
                            "text": prompt
                        }]
                    }],
                    "generationConfig": {
                        "temperature": 0.7,
                        "maxOutputTokens": 200
                    }
                },
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            return result['candidates'][0]['content']['parts'][0]['text']
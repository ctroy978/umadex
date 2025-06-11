"""
Vocabulary Puzzle Generator Service
Generates 4 types of puzzles for vocabulary words using AI
"""
import json
import logging
import os
import random
import re
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from uuid import UUID

from app.models.vocabulary import VocabularyList, VocabularyWord

logger = logging.getLogger(__name__)


class VocabularyPuzzleGenerator:
    """Service for generating vocabulary puzzles using AI"""
    
    PUZZLE_TYPES = ['scrambled', 'crossword_clue', 'fill_blank', 'word_match']
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_puzzle_set(self, vocabulary_list_id: UUID) -> List[Dict[str, Any]]:
        """Generate a complete set of puzzles for a vocabulary list"""
        
        # Get vocabulary words with explicit loading to avoid lazy loading issues
        vocab_list_result = await self.db.execute(
            select(VocabularyList)
            .where(VocabularyList.id == vocabulary_list_id)
            .options(selectinload(VocabularyList.words))
        )
        vocab_list = vocab_list_result.scalar_one_or_none()
        
        if not vocab_list or not vocab_list.words:
            raise ValueError("Vocabulary list not found or has no words")
        
        # Load words explicitly to ensure all data is available
        words_result = await self.db.execute(
            select(VocabularyWord)
            .where(VocabularyWord.list_id == vocabulary_list_id)
            .order_by(VocabularyWord.id)
        )
        words = words_result.scalars().all()
        
        if not words:
            raise ValueError("No words found in vocabulary list")
        
        puzzles = []
        
        for order, word in enumerate(words):
            # Assign puzzle type based on rotation for variety
            puzzle_type = self.PUZZLE_TYPES[order % len(self.PUZZLE_TYPES)]
            
            try:
                # Create word data dict to avoid lazy loading issues
                word_data = {
                    'id': word.id,
                    'word': word.word,
                    'definition': word.definition,
                    'part_of_speech': word.part_of_speech,
                    'list_id': word.list_id
                }
                
                puzzle_data = await self._generate_puzzle_for_word_data(
                    word_data, puzzle_type, vocab_list.grade_level
                )
                
                puzzles.append({
                    'vocabulary_list_id': vocabulary_list_id,
                    'word_id': word.id,
                    'puzzle_type': puzzle_type,
                    'puzzle_data': puzzle_data['puzzle_data'],
                    'correct_answer': puzzle_data['correct_answer'],
                    'puzzle_order': order + 1
                })
                
            except Exception as e:
                logger.error(f"Failed to generate puzzle for word {word.word}: {e}")
                # Create a fallback puzzle using word data dict
                word_data = {
                    'id': word.id,
                    'word': word.word,
                    'definition': word.definition,
                    'part_of_speech': word.part_of_speech,
                    'list_id': word.list_id
                }
                puzzles.append(self._create_fallback_puzzle_from_data(word_data, puzzle_type, order + 1, vocabulary_list_id))
        
        return puzzles
    
    async def _generate_puzzle_for_word(
        self, 
        word: VocabularyWord, 
        puzzle_type: str, 
        grade_level: str
    ) -> Dict[str, Any]:
        """Generate a specific puzzle type for a word using AI"""
        
        if puzzle_type == 'scrambled':
            return await self._generate_scrambled_puzzle(word, grade_level)
        elif puzzle_type == 'crossword_clue':
            return await self._generate_crossword_clue_puzzle(word, grade_level)
        elif puzzle_type == 'fill_blank':
            return await self._generate_fill_blank_puzzle(word, grade_level)
        elif puzzle_type == 'word_match':
            return await self._generate_word_match_puzzle(word, grade_level)
        else:
            raise ValueError(f"Unknown puzzle type: {puzzle_type}")
    
    async def _generate_puzzle_for_word_data(
        self, 
        word_data: Dict[str, Any], 
        puzzle_type: str, 
        grade_level: str
    ) -> Dict[str, Any]:
        """Generate a specific puzzle type for a word using word data dict"""
        
        if puzzle_type == 'scrambled':
            return await self._generate_scrambled_puzzle_from_data(word_data, grade_level)
        elif puzzle_type == 'crossword_clue':
            return await self._generate_crossword_clue_puzzle_from_data(word_data, grade_level)
        elif puzzle_type == 'fill_blank':
            return await self._generate_fill_blank_puzzle_from_data(word_data, grade_level)
        elif puzzle_type == 'word_match':
            return await self._generate_word_match_puzzle_from_data(word_data, grade_level)
        else:
            raise ValueError(f"Unknown puzzle type: {puzzle_type}")
    
    async def _generate_scrambled_puzzle_from_data(self, word_data: Dict[str, Any], grade_level: str) -> Dict[str, Any]:
        """Generate a scrambled word puzzle from word data"""
        
        # Create scrambled version
        letters = list(word_data['word'].upper())
        scrambled = letters.copy()
        
        # Ensure we actually scramble the word (not just return original)
        max_attempts = 10
        attempt = 0
        while scrambled == letters and attempt < max_attempts:
            random.shuffle(scrambled)
            attempt += 1
        
        scrambled_letters = "-".join(scrambled)
        
        # Generate hint using AI
        hint = await self._generate_ai_hint_from_data(word_data, grade_level, "scrambled")
        
        return {
            'puzzle_data': {
                'scrambled_letters': scrambled_letters,
                'hint': hint,
                'letter_count': len(word_data['word'])
            },
            'correct_answer': word_data['word'].lower()
        }
    
    async def _generate_crossword_clue_puzzle_from_data(self, word_data: Dict[str, Any], grade_level: str) -> Dict[str, Any]:
        """Generate a crossword clue puzzle from word data"""
        
        clue = await self._generate_ai_hint_from_data(word_data, grade_level, "crossword_clue")
        
        return {
            'puzzle_data': {
                'clue': clue,
                'letter_count': len(word_data['word']),
                'first_letter': word_data['word'][0].lower()
            },
            'correct_answer': word_data['word'].lower()
        }
    
    async def _generate_fill_blank_puzzle_from_data(self, word_data: Dict[str, Any], grade_level: str) -> Dict[str, Any]:
        """Generate a fill-in-the-blank puzzle from word data"""
        
        sentence = await self._generate_ai_sentence_from_data(word_data, grade_level)
        context_hint = await self._generate_ai_hint_from_data(word_data, grade_level, "context")
        
        return {
            'puzzle_data': {
                'sentence': sentence,
                'word_length': len(word_data['word']),
                'context_hint': context_hint
            },
            'correct_answer': word_data['word'].lower()
        }
    
    async def _generate_word_match_puzzle_from_data(self, word_data: Dict[str, Any], grade_level: str) -> Dict[str, Any]:
        """Generate a word match puzzle from word data"""
        
        options = await self._generate_ai_multiple_choice_from_data(word_data, grade_level)
        
        return {
            'puzzle_data': {
                'target_word': word_data['word'],
                'options': options['options']
            },
            'correct_answer': options['correct_answer']
        }
    
    async def _generate_scrambled_puzzle(self, word: VocabularyWord, grade_level: str) -> Dict[str, Any]:
        """Generate a scrambled word puzzle"""
        
        # Create scrambled version
        letters = list(word.word.upper())
        scrambled = letters.copy()
        
        # Ensure we actually scramble the word (not just return original)
        max_attempts = 10
        attempt = 0
        while scrambled == letters and attempt < max_attempts:
            random.shuffle(scrambled)
            attempt += 1
        
        scrambled_letters = "-".join(scrambled)
        
        # Generate hint using AI
        hint = await self._generate_ai_hint(word, grade_level, "scrambled")
        
        return {
            'puzzle_data': {
                'scrambled_letters': scrambled_letters,
                'hint': hint,
                'letter_count': len(word.word)
            },
            'correct_answer': word.word.lower()
        }
    
    async def _generate_crossword_clue_puzzle(self, word: VocabularyWord, grade_level: str) -> Dict[str, Any]:
        """Generate a crossword clue puzzle"""
        
        clue = await self._generate_ai_hint(word, grade_level, "crossword_clue")
        
        return {
            'puzzle_data': {
                'clue': clue,
                'letter_count': len(word.word),
                'first_letter': word.word[0].lower()
            },
            'correct_answer': word.word.lower()
        }
    
    async def _generate_fill_blank_puzzle(self, word: VocabularyWord, grade_level: str) -> Dict[str, Any]:
        """Generate a fill-in-the-blank puzzle"""
        
        sentence = await self._generate_ai_sentence(word, grade_level)
        context_hint = await self._generate_ai_hint(word, grade_level, "context")
        
        return {
            'puzzle_data': {
                'sentence': sentence,
                'word_length': len(word.word),
                'context_hint': context_hint
            },
            'correct_answer': word.word.lower()
        }
    
    async def _generate_word_match_puzzle(self, word: VocabularyWord, grade_level: str) -> Dict[str, Any]:
        """Generate a word match puzzle"""
        
        options = await self._generate_ai_multiple_choice(word, grade_level)
        
        return {
            'puzzle_data': {
                'target_word': word.word,
                'options': options['options']
            },
            'correct_answer': options['correct_answer']
        }
    
    async def _generate_ai_hint(self, word: VocabularyWord, grade_level: str, hint_type: str) -> str:
        """Generate an AI hint for the word"""
        
        if hint_type == "scrambled":
            prompt = f"""Create a short, helpful hint for a {grade_level} grade student to unscramble the word "{word.word}".

The hint should:
- Be 3-8 words long
- Give a clue about the meaning without giving away the word
- Be age-appropriate for {grade_level} grade
- Help students think of the word without being too obvious

Word definition: {word.definition}
Part of speech: {word.part_of_speech}

Return only the hint text, nothing else."""

        elif hint_type == "crossword_clue":
            prompt = f"""Create a crossword-style clue for the word "{word.word}" for a {grade_level} grade student.

The clue should:
- Be clear and specific enough to identify the target word
- Be age-appropriate for {grade_level} grade
- Follow crossword clue style (brief but descriptive)
- Not include the target word or obvious variations

Word definition: {word.definition}
Part of speech: {word.part_of_speech}

Return only the clue text, nothing else."""

        elif hint_type == "context":
            prompt = f"""Create a context hint for the word "{word.word}" for a {grade_level} grade student.

The hint should:
- Describe what kind of word it is or when it's used
- Be helpful for understanding context
- Be age-appropriate for {grade_level} grade
- Be 5-12 words long

Word definition: {word.definition}
Part of speech: {word.part_of_speech}

Return only the context hint, nothing else."""

        try:
            import google.generativeai as genai
            
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            
            hint = response.text.strip()
            # Clean up any quotes or extra formatting
            hint = hint.strip('"\'')
            
            return hint if hint else self._get_fallback_hint(word, hint_type)
            
        except Exception as e:
            logger.error(f"Error generating AI hint: {e}")
            return self._get_fallback_hint(word, hint_type)
    
    async def _generate_ai_sentence(self, word: VocabularyWord, grade_level: str) -> str:
        """Generate a fill-in-the-blank sentence"""
        
        prompt = f"""Create a fill-in-the-blank sentence for the word "{word.word}" for a {grade_level} grade student.

Requirements:
- Replace the target word with "___" (exactly 3 underscores)
- The sentence should clearly indicate what word belongs in the blank
- Use age-appropriate vocabulary and context for {grade_level} grade
- Make the sentence interesting and relatable
- Ensure grammatical correctness
- The blank should make sense only with the target word

Word definition: {word.definition}
Part of speech: {word.part_of_speech}

Return only the sentence with the blank, nothing else."""

        try:
            import google.generativeai as genai
            
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            
            sentence = response.text.strip()
            
            # Ensure the sentence has the blank
            if "___" not in sentence:
                return self._get_fallback_sentence(word)
            
            return sentence
            
        except Exception as e:
            logger.error(f"Error generating AI sentence: {e}")
            return self._get_fallback_sentence(word)
    
    async def _generate_ai_multiple_choice(self, word: VocabularyWord, grade_level: str) -> Dict[str, Any]:
        """Generate multiple choice options for word match"""
        
        prompt = f"""Create a multiple choice question for the word "{word.word}" for a {grade_level} grade student.

Generate exactly 4 options where:
- ONE is the correct definition/meaning
- THREE are plausible but incorrect distractors
- All options should be age-appropriate for {grade_level} grade
- Distractors should be clearly wrong but not obviously so
- Each option should be 3-10 words long

Word: {word.word}
Definition: {word.definition}
Part of speech: {word.part_of_speech}

Return your response in this exact JSON format:
{{
  "correct_answer": "the correct definition here",
  "options": [
    {{"text": "the correct definition here", "correct": true}},
    {{"text": "first distractor here", "correct": false}},
    {{"text": "second distractor here", "correct": false}},
    {{"text": "third distractor here", "correct": false}}
  ]
}}"""

        try:
            import google.generativeai as genai
            
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            
            response_text = response.text.strip()
            
            # Extract JSON from response
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            result = json.loads(response_text.strip())
            
            # Validate the response structure
            if "correct_answer" not in result or "options" not in result:
                raise ValueError("Invalid response structure")
            
            if len(result["options"]) != 4:
                raise ValueError("Must have exactly 4 options")
            
            # Shuffle the options to randomize position
            options = result["options"]
            random.shuffle(options)
            
            return {
                "correct_answer": result["correct_answer"],
                "options": options
            }
            
        except Exception as e:
            logger.error(f"Error generating AI multiple choice: {e}")
            return self._get_fallback_multiple_choice(word)
    
    async def _generate_ai_hint_from_data(self, word_data: Dict[str, Any], grade_level: str, hint_type: str) -> str:
        """Generate an AI hint for the word from word data"""
        
        if hint_type == "scrambled":
            prompt = f"""Create a short, helpful hint for a {grade_level} grade student to unscramble the word "{word_data['word']}".

The hint should:
- Be 3-8 words long
- Give a clue about the meaning without giving away the word
- Be age-appropriate for {grade_level} grade
- Help students think of the word without being too obvious

Word definition: {word_data['definition']}
Part of speech: {word_data['part_of_speech']}

Return only the hint text, nothing else."""

        elif hint_type == "crossword_clue":
            prompt = f"""Create a crossword-style clue for the word "{word_data['word']}" for a {grade_level} grade student.

The clue should:
- Be clear and specific enough to identify the target word
- Be age-appropriate for {grade_level} grade
- Follow crossword clue style (brief but descriptive)
- Not include the target word or obvious variations

Word definition: {word_data['definition']}
Part of speech: {word_data['part_of_speech']}

Return only the clue text, nothing else."""

        elif hint_type == "context":
            prompt = f"""Create a context hint for the word "{word_data['word']}" for a {grade_level} grade student.

The hint should:
- Describe what kind of word it is or when it's used
- Be helpful for understanding context
- Be age-appropriate for {grade_level} grade
- Be 5-12 words long

Word definition: {word_data['definition']}
Part of speech: {word_data['part_of_speech']}

Return only the context hint, nothing else."""

        try:
            import google.generativeai as genai
            
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            
            hint = response.text.strip()
            # Clean up any quotes or extra formatting
            hint = hint.strip('"\'')
            
            return hint if hint else self._get_fallback_hint_from_data(word_data, hint_type)
            
        except Exception as e:
            logger.error(f"Error generating AI hint: {e}")
            return self._get_fallback_hint_from_data(word_data, hint_type)
    
    async def _generate_ai_sentence_from_data(self, word_data: Dict[str, Any], grade_level: str) -> str:
        """Generate a fill-in-the-blank sentence from word data"""
        
        prompt = f"""Create a fill-in-the-blank sentence for the word "{word_data['word']}" for a {grade_level} grade student.

Requirements:
- Replace the target word with "___" (exactly 3 underscores)
- The sentence should clearly indicate what word belongs in the blank
- Use age-appropriate vocabulary and context for {grade_level} grade
- Make the sentence interesting and relatable
- Ensure grammatical correctness
- The blank should make sense only with the target word

Word definition: {word_data['definition']}
Part of speech: {word_data['part_of_speech']}

Return only the sentence with the blank, nothing else."""

        try:
            import google.generativeai as genai
            
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            
            sentence = response.text.strip()
            
            # Ensure the sentence has the blank
            if "___" not in sentence:
                return self._get_fallback_sentence_from_data(word_data)
            
            return sentence
            
        except Exception as e:
            logger.error(f"Error generating AI sentence: {e}")
            return self._get_fallback_sentence_from_data(word_data)
    
    async def _generate_ai_multiple_choice_from_data(self, word_data: Dict[str, Any], grade_level: str) -> Dict[str, Any]:
        """Generate multiple choice options for word match from word data"""
        
        prompt = f"""Create a multiple choice question for the word "{word_data['word']}" for a {grade_level} grade student.

Generate exactly 4 options where:
- ONE is the correct definition/meaning
- THREE are plausible but incorrect distractors
- All options should be age-appropriate for {grade_level} grade
- Distractors should be clearly wrong but not obviously so
- Each option should be 3-10 words long

Word: {word_data['word']}
Definition: {word_data['definition']}
Part of speech: {word_data['part_of_speech']}

Return your response in this exact JSON format:
{{
  "correct_answer": "the correct definition here",
  "options": [
    {{"text": "the correct definition here", "correct": true}},
    {{"text": "first distractor here", "correct": false}},
    {{"text": "second distractor here", "correct": false}},
    {{"text": "third distractor here", "correct": false}}
  ]
}}"""

        try:
            import google.generativeai as genai
            
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            
            response_text = response.text.strip()
            
            # Extract JSON from response
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]
            
            result = json.loads(response_text.strip())
            
            # Validate the response structure
            if "correct_answer" not in result or "options" not in result:
                raise ValueError("Invalid response structure")
            
            if len(result["options"]) != 4:
                raise ValueError("Must have exactly 4 options")
            
            # Shuffle the options to randomize position
            options = result["options"]
            random.shuffle(options)
            
            return {
                "correct_answer": result["correct_answer"],
                "options": options
            }
            
        except Exception as e:
            logger.error(f"Error generating AI multiple choice: {e}")
            return self._get_fallback_multiple_choice_from_data(word_data)
    
    def _get_fallback_hint(self, word: VocabularyWord, hint_type: str) -> str:
        """Provide fallback hints when AI is unavailable"""
        
        if hint_type == "scrambled":
            return f"A {word.part_of_speech} that means something like this"
        elif hint_type == "crossword_clue":
            return f"{word.part_of_speech.title()}, {len(word.word)} letters"
        elif hint_type == "context":
            return f"describes something or someone"
        
        return "Think about the meaning of this word"
    
    def _get_fallback_hint_from_data(self, word_data: Dict[str, Any], hint_type: str) -> str:
        """Provide fallback hints when AI is unavailable"""
        
        if hint_type == "scrambled":
            return f"A {word_data['part_of_speech']} that means something like this"
        elif hint_type == "crossword_clue":
            return f"{word_data['part_of_speech'].title()}, {len(word_data['word'])} letters"
        elif hint_type == "context":
            return f"describes something or someone"
        
        return "Think about the meaning of this word"
    
    def _get_fallback_sentence_from_data(self, word_data: Dict[str, Any]) -> str:
        """Provide fallback sentence when AI is unavailable"""
        return f"The ___ was exactly what we needed in this situation."
    
    def _get_fallback_multiple_choice_from_data(self, word_data: Dict[str, Any]) -> Dict[str, Any]:
        """Provide fallback multiple choice when AI is unavailable"""
        
        # Use the actual definition as correct answer
        correct_answer = word_data['definition']
        
        # Generic distractors
        distractors = [
            "something very large and heavy",
            "a person who is always happy",
            "an object used for decoration"
        ]
        
        options = [
            {"text": correct_answer, "correct": True},
            {"text": distractors[0], "correct": False},
            {"text": distractors[1], "correct": False},
            {"text": distractors[2], "correct": False}
        ]
        
        random.shuffle(options)
        
        return {
            "correct_answer": correct_answer,
            "options": options
        }
    
    def _get_fallback_sentence(self, word: VocabularyWord) -> str:
        """Provide fallback sentence when AI is unavailable"""
        return f"The ___ was exactly what we needed in this situation."
    
    def _get_fallback_multiple_choice(self, word: VocabularyWord) -> Dict[str, Any]:
        """Provide fallback multiple choice when AI is unavailable"""
        
        # Use the actual definition as correct answer
        correct_answer = word.definition
        
        # Generic distractors
        distractors = [
            "something very large and heavy",
            "a person who is always happy",
            "an object used for decoration"
        ]
        
        options = [
            {"text": correct_answer, "correct": True},
            {"text": distractors[0], "correct": False},
            {"text": distractors[1], "correct": False},
            {"text": distractors[2], "correct": False}
        ]
        
        random.shuffle(options)
        
        return {
            "correct_answer": correct_answer,
            "options": options
        }
    
    def _create_fallback_puzzle(self, word: VocabularyWord, puzzle_type: str, order: int) -> Dict[str, Any]:
        """Create a basic puzzle when AI generation fails"""
        
        if puzzle_type == 'scrambled':
            letters = list(word.word.upper())
            random.shuffle(letters)
            scrambled_letters = "-".join(letters)
            
            return {
                'vocabulary_list_id': word.vocabulary_list_id,
                'word_id': word.id,
                'puzzle_type': puzzle_type,
                'puzzle_data': {
                    'scrambled_letters': scrambled_letters,
                    'hint': f"A {word.part_of_speech}",
                    'letter_count': len(word.word)
                },
                'correct_answer': word.word.lower(),
                'puzzle_order': order
            }
        
        elif puzzle_type == 'crossword_clue':
            return {
                'vocabulary_list_id': word.vocabulary_list_id,
                'word_id': word.id,
                'puzzle_type': puzzle_type,
                'puzzle_data': {
                    'clue': f"{word.part_of_speech.title()}, {len(word.word)} letters",
                    'letter_count': len(word.word),
                    'first_letter': word.word[0].lower()
                },
                'correct_answer': word.word.lower(),
                'puzzle_order': order
            }
        
        elif puzzle_type == 'fill_blank':
            return {
                'vocabulary_list_id': word.vocabulary_list_id,
                'word_id': word.id,
                'puzzle_type': puzzle_type,
                'puzzle_data': {
                    'sentence': f"The ___ was exactly what we needed.",
                    'word_length': len(word.word),
                    'context_hint': f"A {word.part_of_speech}"
                },
                'correct_answer': word.word.lower(),
                'puzzle_order': order
            }
        
        else:  # word_match
            return {
                'vocabulary_list_id': word.vocabulary_list_id,
                'word_id': word.id,
                'puzzle_type': puzzle_type,
                'puzzle_data': {
                    'target_word': word.word,
                    'options': [
                        {"text": word.definition, "correct": True},
                        {"text": "something very large", "correct": False},
                        {"text": "a type of food", "correct": False},
                        {"text": "a musical instrument", "correct": False}
                    ]
                },
                'correct_answer': word.definition,
                'puzzle_order': order
            }
    
    def _create_fallback_puzzle_from_data(self, word_data: Dict[str, Any], puzzle_type: str, order: int, vocabulary_list_id: UUID) -> Dict[str, Any]:
        """Create a basic puzzle when AI generation fails using word data"""
        
        if puzzle_type == 'scrambled':
            letters = list(word_data['word'].upper())
            random.shuffle(letters)
            scrambled_letters = "-".join(letters)
            
            return {
                'vocabulary_list_id': vocabulary_list_id,
                'word_id': word_data['id'],
                'puzzle_type': puzzle_type,
                'puzzle_data': {
                    'scrambled_letters': scrambled_letters,
                    'hint': f"A {word_data['part_of_speech']}",
                    'letter_count': len(word_data['word'])
                },
                'correct_answer': word_data['word'].lower(),
                'puzzle_order': order
            }
        
        elif puzzle_type == 'crossword_clue':
            return {
                'vocabulary_list_id': vocabulary_list_id,
                'word_id': word_data['id'],
                'puzzle_type': puzzle_type,
                'puzzle_data': {
                    'clue': f"{word_data['part_of_speech'].title()}, {len(word_data['word'])} letters",
                    'letter_count': len(word_data['word']),
                    'first_letter': word_data['word'][0].lower()
                },
                'correct_answer': word_data['word'].lower(),
                'puzzle_order': order
            }
        
        elif puzzle_type == 'fill_blank':
            return {
                'vocabulary_list_id': vocabulary_list_id,
                'word_id': word_data['id'],
                'puzzle_type': puzzle_type,
                'puzzle_data': {
                    'sentence': f"The ___ was exactly what we needed.",
                    'word_length': len(word_data['word']),
                    'context_hint': f"A {word_data['part_of_speech']}"
                },
                'correct_answer': word_data['word'].lower(),
                'puzzle_order': order
            }
        
        else:  # word_match
            return {
                'vocabulary_list_id': vocabulary_list_id,
                'word_id': word_data['id'],
                'puzzle_type': puzzle_type,
                'puzzle_data': {
                    'target_word': word_data['word'],
                    'options': [
                        {"text": word_data['definition'], "correct": True},
                        {"text": "something very large", "correct": False},
                        {"text": "a type of food", "correct": False},
                        {"text": "a musical instrument", "correct": False}
                    ]
                },
                'correct_answer': word_data['definition'],
                'puzzle_order': order
            }
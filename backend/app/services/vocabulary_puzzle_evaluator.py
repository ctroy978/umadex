"""
Vocabulary Puzzle Evaluator Service
Evaluates student puzzle responses using AI and rule-based methods
"""
import json
import logging
import os
import re
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class VocabularyPuzzleEvaluator:
    """Service for evaluating student puzzle responses"""
    
    def __init__(self):
        pass
    
    async def evaluate_puzzle_response(
        self,
        puzzle_type: str,
        puzzle_data: Dict[str, Any],
        correct_answer: str,
        student_answer: str,
        word: str,
        grade_level: str
    ) -> Dict[str, Any]:
        """Evaluate a student's puzzle response"""
        
        if puzzle_type == 'scrambled':
            return await self._evaluate_scrambled_response(
                puzzle_data, correct_answer, student_answer, word, grade_level
            )
        elif puzzle_type == 'crossword_clue':
            return await self._evaluate_crossword_response(
                puzzle_data, correct_answer, student_answer, word, grade_level
            )
        elif puzzle_type == 'word_match':
            return await self._evaluate_word_match_response(
                puzzle_data, correct_answer, student_answer, word, grade_level
            )
        elif puzzle_type == 'fill_blank':
            return await self._evaluate_fill_blank_response(
                puzzle_data, correct_answer, student_answer, word, grade_level
            )
        else:
            raise ValueError(f"Unknown puzzle type: {puzzle_type}")
    
    async def _evaluate_scrambled_response(
        self, 
        puzzle_data: Dict[str, Any], 
        correct_answer: str, 
        student_answer: str, 
        word: str, 
        grade_level: str
    ) -> Dict[str, Any]:
        """Evaluate scrambled word puzzle response"""
        
        # Normalize answers for comparison
        correct = correct_answer.lower().strip()
        student = student_answer.lower().strip()
        
        # Check for exact match only (case-insensitive)
        if student == correct:
            return {
                'score': 4,
                'accuracy': 'perfect',
                'feedback': f"Excellent! You correctly unscrambled '{word}'!",
                'areas_checked': ['spelling', 'completeness', 'correctness']
            }
        else:
            # No partial credit - either right or wrong
            return {
                'score': 1,
                'accuracy': 'incorrect',
                'feedback': f"That's not quite right. The word '{correct}' can be unscrambled from those letters.",
                'areas_checked': ['correctness']
            }
    
    async def _evaluate_crossword_response(
        self, 
        puzzle_data: Dict[str, Any], 
        correct_answer: str, 
        student_answer: str, 
        word: str, 
        grade_level: str
    ) -> Dict[str, Any]:
        """Evaluate crossword clue puzzle response"""
        
        # Similar logic to scrambled word
        correct = correct_answer.lower().strip()
        student = student_answer.lower().strip()
        
        # Check for exact match only (case-insensitive)
        if student == correct:
            return {
                'score': 4,
                'accuracy': 'perfect',
                'feedback': f"Perfect! '{word}' is exactly right for that clue!",
                'areas_checked': ['clue_comprehension', 'spelling', 'correctness']
            }
        else:
            # No partial credit - either right or wrong
            return {
                'score': 1,
                'accuracy': 'incorrect',
                'feedback': f"Not quite. The clue points to '{correct}'.",
                'areas_checked': ['clue_comprehension']
            }
    
    async def _evaluate_word_match_response(
        self, 
        puzzle_data: Dict[str, Any], 
        correct_answer: str, 
        student_answer: str, 
        word: str, 
        grade_level: str
    ) -> Dict[str, Any]:
        """Evaluate word match puzzle response"""
        
        # For word match, student_answer should be the selected option text
        if student_answer.strip() == correct_answer.strip():
            return {
                'score': 4,
                'accuracy': 'perfect',
                'feedback': f"Perfect! You correctly matched '{word}' with its definition!",
                'areas_checked': ['definition_recognition', 'meaning_comprehension']
            }
        else:
            return {
                'score': 1,
                'accuracy': 'incorrect',
                'feedback': f"Not quite. '{word}' means: {correct_answer}",
                'areas_checked': ['definition_recognition']
            }
    
    async def _evaluate_fill_blank_response(
        self, 
        puzzle_data: Dict[str, Any], 
        correct_answer: str, 
        student_answer: str, 
        word: str, 
        grade_level: str
    ) -> Dict[str, Any]:
        """Evaluate fill in the blank puzzle response"""
        
        # Normalize answers for comparison
        correct = correct_answer.lower().strip()
        student = student_answer.lower().strip()
        
        # Check for exact match (case-insensitive)
        if student == correct:
            return {
                'score': 4,
                'accuracy': 'perfect',
                'feedback': f"Excellent! '{word}' is the correct word for that sentence!",
                'areas_checked': ['context_understanding', 'spelling', 'correctness']
            }
        else:
            # No partial credit - either right or wrong
            return {
                'score': 1,
                'accuracy': 'incorrect',
                'feedback': f"Not quite. The correct word is '{word}'.",
                'areas_checked': ['context_understanding']
            }
    
    def _is_close_spelling(self, student_answer: str, correct_answer: str) -> bool:
        """Check if student answer is close in spelling to correct answer"""
        
        if len(student_answer) != len(correct_answer):
            return False
        
        # Count character differences
        differences = sum(1 for s, c in zip(student_answer, correct_answer) if s != c)
        
        # Allow 1-2 character differences for words longer than 3 characters
        if len(correct_answer) > 3:
            return differences <= 2
        else:
            return differences <= 1
    
    async def _is_related_word(self, student_answer: str, correct_answer: str, grade_level: str) -> bool:
        """Check if student answer is semantically related using AI"""
        
        if len(student_answer) < 2:
            return False
        
        prompt = f"""Are these two words related in meaning for a {grade_level} grade student?

Word 1: {student_answer}
Word 2: {correct_answer}

Consider if they are:
- Synonyms or near-synonyms
- Words that could be confused for each other
- Related concepts that a student might mix up

Respond with only "YES" or "NO"."""

        try:
            import google.generativeai as genai
            
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            
            result = response.text.strip().upper()
            return result == "YES"
            
        except Exception as e:
            logger.error(f"Error checking word relationship: {e}")
            # Fallback: very basic check
            return student_answer in correct_answer or correct_answer in student_answer
    
    async def _fits_context(self, student_answer: str, sentence: str, grade_level: str) -> bool:
        """Check if the student answer fits grammatically in the sentence"""
        
        if len(student_answer) < 2:
            return False
        
        # Replace blank with student answer
        filled_sentence = sentence.replace("___", student_answer)
        
        prompt = f"""Does this sentence make grammatical sense for a {grade_level} grade level?

Sentence: {filled_sentence}

Consider:
- Grammar correctness
- Logical meaning
- Age-appropriate language

Respond with only "YES" or "NO"."""

        try:
            import google.generativeai as genai
            
            genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            
            result = response.text.strip().upper()
            return result == "YES"
            
        except Exception as e:
            logger.error(f"Error checking context fit: {e}")
            # Fallback: basic word length and alphabet check
            return len(student_answer) > 2 and student_answer.isalpha()
    
    def validate_student_input(
        self,
        puzzle_type: str,
        student_answer: str,
        puzzle_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Validate student input for different puzzle types"""
        
        errors = {}
        
        # Basic validation
        if not student_answer or not student_answer.strip():
            errors['answer'] = 'Please provide an answer'
            return {'valid': False, 'errors': errors}
        
        answer = student_answer.strip()
        
        if puzzle_type in ['scrambled', 'crossword_clue', 'fill_blank']:
            # Single word validation
            if len(answer) < 2:
                errors['answer'] = 'Answer is too short'
            elif len(answer) > 50:
                errors['answer'] = 'Answer is too long'
            elif not re.match(r'^[a-zA-Z\s\-\']+$', answer):
                errors['answer'] = 'Please use only letters'
        
        elif puzzle_type == 'word_match':
            # Multiple choice validation - should be one of the options
            if 'options' in puzzle_data:
                valid_options = [opt['text'] for opt in puzzle_data['options']]
                if answer not in valid_options:
                    errors['answer'] = 'Please select one of the provided options'
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
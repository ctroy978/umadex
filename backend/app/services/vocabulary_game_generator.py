"""
Vocabulary game question generation service
Generates varied question types for vocabulary practice activities
"""
import json
import random
from typing import List, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from app.models.vocabulary import VocabularyList, VocabularyWord
from app.core.config import settings
import httpx
import asyncio
import logging

logger = logging.getLogger(__name__)


class VocabularyGameGenerator:
    """Generates questions for vocabulary practice games"""
    
    QUESTION_TYPES = ['riddle', 'poem', 'sentence_completion', 'word_association', 'scenario']
    DIFFICULTY_DISTRIBUTION = {
        'easy': 0.4,
        'medium': 0.4,
        'hard': 0.2
    }
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_game_questions(
        self, 
        vocabulary_list_id: UUID,
        regenerate: bool = False
    ) -> List[Dict[str, Any]]:
        """Generate questions for vocabulary challenge game"""
        
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
        
        # Calculate question distribution
        word_count = len(words)
        question_distribution = self._calculate_question_distribution(words)
        
        # Generate questions for each word
        questions = []
        question_order = 1
        
        for word, num_questions in question_distribution:
            word_questions = await self._generate_questions_for_word(
                word, 
                vocab_list,
                num_questions,
                question_order
            )
            questions.extend(word_questions)
            question_order += num_questions
        
        # Shuffle questions while maintaining order
        random.shuffle(questions)
        for i, question in enumerate(questions):
            question['question_order'] = i + 1
        
        return questions
    
    def _calculate_question_distribution(self, words: List[VocabularyWord]) -> List[Tuple[VocabularyWord, int]]:
        """Calculate how many questions each word should get"""
        
        word_count = len(words)
        
        # Minimum 10 questions rule
        if word_count <= 6:
            # For 6 or fewer words: 4 words get 2 questions, rest get 1
            distribution = []
            words_with_2 = min(4, word_count - 2) if word_count > 2 else word_count
            
            for i, word in enumerate(words[:word_count]):
                if i < words_with_2:
                    distribution.append((word, 2))
                else:
                    distribution.append((word, 1))
            
            # Ensure minimum 10 questions
            total_questions = sum(q[1] for q in distribution)
            while total_questions < 10 and distribution:
                # Add questions to words that have only 1
                for i, (word, count) in enumerate(distribution):
                    if count == 1 and total_questions < 10:
                        distribution[i] = (word, 2)
                        total_questions += 1
        else:
            # For more than 6 words: each word gets 1 question, 
            # plus additional questions distributed evenly
            base_questions = 10
            extra_questions = word_count - 6
            total_questions = base_questions + extra_questions
            
            # Start with 1 question per word
            distribution = [(word, 1) for word in words[:word_count]]
            
            # Distribute extra questions
            extra_to_distribute = total_questions - word_count
            for i in range(extra_to_distribute):
                idx = i % word_count
                word, count = distribution[idx]
                distribution[idx] = (word, count + 1)
        
        return distribution
    
    async def _generate_questions_for_word(
        self,
        word: VocabularyWord,
        vocab_list: VocabularyList,
        num_questions: int,
        start_order: int
    ) -> List[Dict[str, Any]]:
        """Generate specified number of questions for a word"""
        
        questions = []
        
        # Get word definition and examples
        definition = word.teacher_definition or word.ai_definition
        example_1 = word.teacher_example_1 or word.ai_example_1
        example_2 = word.teacher_example_2 or word.ai_example_2
        
        # Determine question types for this word
        question_types = self._select_question_types(num_questions)
        
        for i, (q_type, difficulty) in enumerate(question_types):
            question = await self._generate_single_question(
                word=word.word,
                definition=definition,
                examples=[ex for ex in [example_1, example_2] if ex],
                question_type=q_type,
                difficulty=difficulty,
                context=vocab_list.context_description,
                grade_level=vocab_list.grade_level
            )
            
            questions.append({
                'vocabulary_list_id': str(vocab_list.id),
                'word_id': str(word.id),
                'question_type': q_type,
                'difficulty_level': difficulty,
                'question_text': question['question_text'],
                'correct_answer': word.word,
                'explanation': question['explanation'],
                'question_order': start_order + i
            })
        
        return questions
    
    def _select_question_types(self, num_questions: int) -> List[Tuple[str, str]]:
        """Select question types and difficulties for a word"""
        
        # If only 1 question, make it medium difficulty
        if num_questions == 1:
            q_type = random.choice(self.QUESTION_TYPES)
            return [(q_type, 'medium')]
        
        # For 2 questions, one easy/medium and one medium/hard
        if num_questions == 2:
            types = random.sample(self.QUESTION_TYPES, 2)
            return [
                (types[0], random.choice(['easy', 'medium'])),
                (types[1], random.choice(['medium', 'hard']))
            ]
        
        # For more questions, follow difficulty distribution
        questions = []
        difficulties = []
        
        # Calculate difficulty counts
        easy_count = int(num_questions * self.DIFFICULTY_DISTRIBUTION['easy'])
        hard_count = int(num_questions * self.DIFFICULTY_DISTRIBUTION['hard'])
        medium_count = num_questions - easy_count - hard_count
        
        difficulties.extend(['easy'] * easy_count)
        difficulties.extend(['medium'] * medium_count)
        difficulties.extend(['hard'] * hard_count)
        
        # Shuffle difficulties
        random.shuffle(difficulties)
        
        # Assign question types
        for difficulty in difficulties:
            q_type = random.choice(self.QUESTION_TYPES)
            questions.append((q_type, difficulty))
        
        return questions
    
    async def _generate_single_question(
        self,
        word: str,
        definition: str,
        examples: List[str],
        question_type: str,
        difficulty: str,
        context: str,
        grade_level: str
    ) -> Dict[str, str]:
        """Generate a single question using AI"""
        
        prompt = self._build_generation_prompt(
            word, definition, examples, question_type, 
            difficulty, context, grade_level
        )
        
        # Use appropriate AI model
        response = await self._call_ai_api(prompt)
        
        # Parse the response
        try:
            # Expected format: Question: ... | Explanation: ...
            parts = response.split(' | ')
            question_text = parts[0].replace('Question: ', '').strip()
            explanation = parts[1].replace('Explanation: ', '').strip() if len(parts) > 1 else f"'{word}' means {definition}"
            
            return {
                'question_text': question_text,
                'explanation': explanation
            }
        except Exception as e:
            logger.error(f"Error parsing AI response: {e}")
            # Fallback question
            return self._generate_fallback_question(word, definition, question_type)
    
    def _build_generation_prompt(
        self,
        word: str,
        definition: str,
        examples: List[str],
        question_type: str,
        difficulty: str,
        context: str,
        grade_level: str
    ) -> str:
        """Build prompt for AI question generation"""
        
        examples_text = "\n".join([f"- {ex}" for ex in examples]) if examples else "No examples provided"
        
        type_instructions = {
            'riddle': f"Create a {difficulty} riddle that leads to the answer '{word}'. The riddle should be clever and fun, appropriate for {grade_level} students.",
            'poem': f"Create a {difficulty} short poem (2-4 lines) that describes '{word}' without using the word itself. Make it rhythmic and memorable for {grade_level} students.",
            'sentence_completion': f"Create a {difficulty} sentence with a blank that should be filled with '{word}'. The sentence should clearly indicate the word needed for {grade_level} students.",
            'word_association': f"Create a {difficulty} word association clue that connects to '{word}'. List 3-4 related concepts that point to the answer for {grade_level} students.",
            'scenario': f"Create a {difficulty} scenario or situation where '{word}' is the answer to 'What word describes this?' Make it relatable for {grade_level} students."
        }
        
        prompt = f"""Generate a vocabulary question for the word '{word}'.

Word: {word}
Definition: {definition}
Examples:
{examples_text}
Context: {context}
Grade Level: {grade_level}
Question Type: {question_type}
Difficulty: {difficulty}

{type_instructions[question_type]}

The answer must be exactly the word '{word}'.

Format your response as:
Question: [Your question here]
Explanation: [Brief explanation of why '{word}' is the answer]

Make the question engaging and educational."""
        
        return prompt
    
    def _generate_fallback_question(
        self, 
        word: str, 
        definition: str, 
        question_type: str
    ) -> Dict[str, str]:
        """Generate a fallback question if AI fails"""
        
        fallback_questions = {
            'riddle': {
                'question_text': f"I am a word that means '{definition}'. What am I?",
                'explanation': f"The answer is '{word}' because it matches the definition given."
            },
            'poem': {
                'question_text': f"A word that means to {definition},\nStarts with '{word[0]}' as you can see.\nWhat word am I?",
                'explanation': f"'{word}' fits the description in the poem."
            },
            'sentence_completion': {
                'question_text': f"Fill in the blank: When something is {definition}, we say it is ______.",
                'explanation': f"'{word}' is the word that means {definition}."
            },
            'word_association': {
                'question_text': f"What word connects to: {definition}?",
                'explanation': f"'{word}' is associated with all these concepts."
            },
            'scenario': {
                'question_text': f"If you need a word that means '{definition}', what word would you use?",
                'explanation': f"'{word}' is the word that describes this scenario."
            }
        }
        
        return fallback_questions.get(question_type, fallback_questions['riddle'])
    
    async def _call_ai_api(self, prompt: str) -> str:
        """Simple AI API call with fallback"""
        try:
            # Check if AI is configured
            if hasattr(settings, 'LLM_PROVIDER') and settings.LLM_PROVIDER:
                if settings.LLM_PROVIDER == "openai" and hasattr(settings, 'OPENAI_API_KEY') and settings.OPENAI_API_KEY:
                    return await self._call_openai_simple(prompt)
                elif settings.LLM_PROVIDER == "anthropic" and hasattr(settings, 'ANTHROPIC_API_KEY') and settings.ANTHROPIC_API_KEY:
                    return await self._call_anthropic_simple(prompt)
            
            # If no AI configured, use template-based generation
            logger.info("AI not configured, using template-based question generation")
            return await self._generate_template_question(prompt)
        except Exception as e:
            logger.error(f"AI API call failed: {e}")
            # Return a simple fallback response
            return "Question: What word fits this definition? | Explanation: This is a vocabulary question."
    
    async def _call_openai_simple(self, prompt: str) -> str:
        """Simple OpenAI API call"""
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
                    "temperature": 0.8,
                    "max_tokens": 300
                },
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
    
    async def _call_anthropic_simple(self, prompt: str) -> str:
        """Simple Anthropic API call"""
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
                    "temperature": 0.8,
                    "max_tokens": 300
                },
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            return result['content'][0]['text']
    
    async def _generate_template_question(self, prompt: str) -> str:
        """Generate questions using templates when AI is not available"""
        import re
        
        # Extract key information from the prompt
        word_match = re.search(r"Word: (\w+)", prompt)
        definition_match = re.search(r"Definition: (.+?)(?:\n|Examples:)", prompt, re.DOTALL)
        question_type_match = re.search(r"Question Type: (\w+)", prompt)
        difficulty_match = re.search(r"Difficulty: (\w+)", prompt)
        
        word = word_match.group(1) if word_match else "unknown"
        definition = definition_match.group(1).strip() if definition_match else "unknown definition"
        question_type = question_type_match.group(1) if question_type_match else "riddle"
        difficulty = difficulty_match.group(1) if difficulty_match else "medium"
        
        # Generate different types of questions
        if question_type == "riddle":
            question_text = f"I'm a word that means '{definition}'. What word am I?"
        elif question_type == "poem":
            question_text = f"In riddles and rhymes, I'm found,\nA word meaning '{definition}' is what I sound.\nWhat word am I?"
        elif question_type == "sentence_completion":
            question_text = f"Fill in the blank: Something that is {definition} can be described as ______."
        elif question_type == "word_association":
            question_text = f"What word connects to these concepts: {definition}?"
        elif question_type == "scenario":
            question_text = f"In a situation where something shows '{definition}', what word would you use to describe it?"
        else:
            question_text = f"What word means '{definition}'?"
        
        explanation = f"'{word}' is the correct answer because it means {definition}."
        
        return f"Question: {question_text} | Explanation: {explanation}"
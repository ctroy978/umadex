"""
Vocabulary story prompt generation service
Generates story writing prompts for vocabulary practice activities
"""
import random
from typing import List, Dict, Any, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.vocabulary import VocabularyList, VocabularyWord
from app.models.vocabulary_practice import VocabularyStoryPrompt
import logging

logger = logging.getLogger(__name__)


class VocabularyStoryGenerator:
    """Generates story prompts for vocabulary practice"""
    
    # Available settings for story prompts
    SETTINGS = [
        "enchanted forest", "abandoned space station", "underwater city", "ancient castle",
        "bustling marketplace", "mysterious island", "time machine laboratory", "dragon's lair",
        "robot factory", "magical library", "pirate ship", "mountain peak",
        "desert oasis", "hidden cave", "futuristic city"
    ]
    
    # Available tones for stories
    TONES = [
        "mysterious", "humorous", "adventurous", "suspenseful", "dramatic",
        "whimsical", "heroic", "peaceful", "exciting", "eerie"
    ]
    
    # Words per prompt configuration
    MIN_WORDS_PER_PROMPT = 3
    MAX_WORDS_PER_PROMPT = 5
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_story_prompts(
        self, 
        vocabulary_list_id: UUID,
        regenerate: bool = False
    ) -> List[Dict[str, Any]]:
        """Generate story prompts for vocabulary assignment"""
        
        # Check if prompts already exist
        if not regenerate:
            existing_result = await self.db.execute(
                select(VocabularyStoryPrompt)
                .where(VocabularyStoryPrompt.vocabulary_list_id == vocabulary_list_id)
                .order_by(VocabularyStoryPrompt.prompt_order)
            )
            existing_prompts = existing_result.scalars().all()
            
            if existing_prompts:
                return [self._format_prompt(prompt) for prompt in existing_prompts]
        
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
        
        # Generate prompts
        prompts = self._create_prompts_for_words(words, vocab_list)
        
        # Save prompts to database
        prompt_models = []
        for i, prompt_data in enumerate(prompts):
            prompt = VocabularyStoryPrompt(
                vocabulary_list_id=vocabulary_list_id,
                prompt_text=prompt_data['prompt_text'],
                required_words=prompt_data['required_words'],
                setting=prompt_data['setting'],
                tone=prompt_data['tone'],
                max_score=prompt_data['max_score'],
                prompt_order=i + 1
            )
            prompt_models.append(prompt)
            self.db.add(prompt)
        
        await self.db.commit()
        
        return [self._format_prompt(prompt) for prompt in prompt_models]
    
    def _create_prompts_for_words(
        self, 
        words: List[VocabularyWord], 
        vocab_list: VocabularyList
    ) -> List[Dict[str, Any]]:
        """Create story prompts that cover all vocabulary words"""
        
        word_list = [word.word for word in words]
        word_count = len(word_list)
        
        # Calculate number of prompts needed
        # Ensure all words are used at least once
        words_per_prompt = max(self.MIN_WORDS_PER_PROMPT, 
                              min(self.MAX_WORDS_PER_PROMPT, word_count // 2))
        
        if word_count <= self.MAX_WORDS_PER_PROMPT:
            # Small list: one prompt with all words
            num_prompts = 1
        else:
            # Larger list: multiple prompts
            num_prompts = max(2, (word_count + words_per_prompt - 1) // words_per_prompt)
        
        # Distribute words across prompts
        word_distribution = self._distribute_words(word_list, num_prompts)
        
        # Generate prompts
        prompts = []
        used_settings = set()
        used_tones = set()
        
        for i, prompt_words in enumerate(word_distribution):
            # Select unique setting and tone
            setting = self._select_unique_item(self.SETTINGS, used_settings)
            tone = self._select_unique_item(self.TONES, used_tones)
            
            # Generate prompt text
            prompt_text = self._create_prompt_text(prompt_words, setting, tone)
            
            prompts.append({
                'prompt_text': prompt_text,
                'required_words': prompt_words,
                'setting': setting,
                'tone': tone,
                'max_score': 100,
                'prompt_order': i + 1
            })
        
        return prompts
    
    def _distribute_words(self, words: List[str], num_prompts: int) -> List[List[str]]:
        """Distribute words evenly across prompts"""
        
        # Shuffle words for random distribution
        words_copy = words.copy()
        random.shuffle(words_copy)
        
        # Create prompt groups
        prompts = [[] for _ in range(num_prompts)]
        
        # Distribute words round-robin style
        for i, word in enumerate(words_copy):
            prompt_index = i % num_prompts
            prompts[prompt_index].append(word)
        
        # Ensure each prompt has at least MIN_WORDS_PER_PROMPT
        for i, prompt_words in enumerate(prompts):
            if len(prompt_words) < self.MIN_WORDS_PER_PROMPT:
                # Move words from larger prompts
                for j, other_prompt in enumerate(prompts):
                    if i != j and len(other_prompt) > self.MIN_WORDS_PER_PROMPT:
                        needed = self.MIN_WORDS_PER_PROMPT - len(prompt_words)
                        can_move = len(other_prompt) - self.MIN_WORDS_PER_PROMPT
                        move_count = min(needed, can_move)
                        
                        if move_count > 0:
                            moved_words = other_prompt[-move_count:]
                            prompts[j] = other_prompt[:-move_count]
                            prompts[i].extend(moved_words)
                            
                            if len(prompts[i]) >= self.MIN_WORDS_PER_PROMPT:
                                break
        
        # Remove empty prompts
        prompts = [p for p in prompts if p]
        
        return prompts
    
    def _select_unique_item(self, items: List[str], used_items: set) -> str:
        """Select an item that hasn't been used, or random if all used"""
        available = [item for item in items if item not in used_items]
        
        if not available:
            # All items used, reset and pick randomly
            used_items.clear()
            available = items
        
        selected = random.choice(available)
        used_items.add(selected)
        return selected
    
    def _create_prompt_text(self, words: List[str], setting: str, tone: str) -> str:
        """Create the actual prompt text"""
        
        words_text = ", ".join(f"'{word}'" for word in words[:-1])
        if len(words) > 1:
            words_text += f", and '{words[-1]}'"
        else:
            words_text = f"'{words[0]}'"
        
        prompt = (
            f"Write a 3-5 sentence story about {setting}, "
            f"using the words {words_text} in a {tone} tone. "
            f"Make sure each word is used correctly and fits naturally into your story."
        )
        
        return prompt
    
    def _format_prompt(self, prompt: VocabularyStoryPrompt) -> Dict[str, Any]:
        """Format a prompt for the frontend"""
        return {
            'id': str(prompt.id),
            'prompt_text': prompt.prompt_text,
            'required_words': prompt.required_words,
            'setting': prompt.setting,
            'tone': prompt.tone,
            'max_score': prompt.max_score,
            'prompt_order': prompt.prompt_order
        }
    
    def calculate_prompt_requirements(self, word_count: int) -> Dict[str, int]:
        """Calculate how many prompts and what scoring for a word count"""
        
        if word_count <= 5:
            num_prompts = 1
            words_per_prompt = word_count
        else:
            words_per_prompt = max(3, min(5, word_count // 2))
            num_prompts = max(2, (word_count + words_per_prompt - 1) // words_per_prompt)
        
        total_possible_score = num_prompts * 100
        passing_score = int(total_possible_score * 0.7)  # 70% threshold
        
        return {
            'num_prompts': num_prompts,
            'words_per_prompt_avg': words_per_prompt,
            'total_possible_score': total_possible_score,
            'passing_score': passing_score
        }
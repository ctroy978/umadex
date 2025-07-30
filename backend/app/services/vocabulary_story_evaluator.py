"""
Vocabulary story evaluation service
Evaluates student stories for vocabulary usage, coherence, tone, and creativity
"""
import re
import json
from typing import List, Dict, Any, Optional
from app.core.config import settings
from app.config.ai_config import get_gemini_config
import google.generativeai as genai
import asyncio
import logging

logger = logging.getLogger(__name__)


class VocabularyStoryEvaluator:
    """Evaluates student stories using AI and template-based methods"""
    
    # Scoring weights
    VOCABULARY_WEIGHT = 0.40  # 40 points
    COHERENCE_WEIGHT = 0.25   # 25 points
    TONE_WEIGHT = 0.20        # 20 points
    CREATIVITY_WEIGHT = 0.15  # 15 points
    
    def __init__(self):
        self.gemini_config = get_gemini_config()
        
        # Initialize Gemini if API key is available
        if self.gemini_config.api_key:
            genai.configure(api_key=self.gemini_config.api_key)
            self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            self.gemini_model = None
    
    async def evaluate_story(
        self,
        story_text: str,
        required_words: List[str],
        setting: str,
        tone: str,
        max_score: int = 100
    ) -> Dict[str, Any]:
        """Evaluate a student story and provide detailed feedback"""
        
        try:
            # Use AI evaluation if available, otherwise fall back to template
            if await self._is_ai_available():
                return await self._ai_evaluate_story(story_text, required_words, setting, tone, max_score)
            else:
                return await self._template_evaluate_story(story_text, required_words, setting, tone, max_score)
        except Exception as e:
            logger.error(f"Story evaluation failed: {e}")
            return self._fallback_evaluation(story_text, required_words, max_score)
    
    async def _ai_evaluate_story(
        self,
        story_text: str,
        required_words: List[str],
        setting: str,
        tone: str,
        max_score: int
    ) -> Dict[str, Any]:
        """Evaluate story using AI service"""
        
        prompt = self._build_evaluation_prompt(story_text, required_words, setting, tone)
        
        try:
            # Call AI service
            ai_response = await self._call_ai_api(prompt)
            
            # Parse AI response
            evaluation = self._parse_ai_evaluation(ai_response, max_score)
            
            # Validate and adjust scores
            evaluation = self._validate_scores(evaluation, story_text, required_words, max_score)
            
            return evaluation
            
        except Exception as e:
            logger.error(f"AI evaluation failed: {e}")
            return await self._template_evaluate_story(story_text, required_words, setting, tone, max_score)
    
    async def _template_evaluate_story(
        self,
        story_text: str,
        required_words: List[str],
        setting: str,
        tone: str,
        max_score: int
    ) -> Dict[str, Any]:
        """Evaluate story using template-based analysis"""
        
        # Vocabulary usage analysis
        vocab_analysis = self._analyze_vocabulary_usage(story_text, required_words)
        vocab_score = min(int(max_score * self.VOCABULARY_WEIGHT), 
                         int(vocab_analysis['words_used_correctly'] / len(required_words) * max_score * self.VOCABULARY_WEIGHT))
        
        # Story coherence analysis
        coherence_analysis = self._analyze_coherence(story_text)
        coherence_score = int(coherence_analysis['score'] * max_score * self.COHERENCE_WEIGHT)
        
        # Tone analysis
        tone_analysis = self._analyze_tone(story_text, tone)
        tone_score = int(tone_analysis['score'] * max_score * self.TONE_WEIGHT)
        
        # Creativity analysis
        creativity_analysis = self._analyze_creativity(story_text)
        creativity_score = int(creativity_analysis['score'] * max_score * self.CREATIVITY_WEIGHT)
        
        total_score = vocab_score + coherence_score + tone_score + creativity_score
        
        return {
            'total_score': min(total_score, max_score),
            'breakdown': {
                'vocabulary_usage': {
                    'score': vocab_score,
                    'max': int(max_score * self.VOCABULARY_WEIGHT),
                    'feedback': vocab_analysis['feedback']
                },
                'story_coherence': {
                    'score': coherence_score,
                    'max': int(max_score * self.COHERENCE_WEIGHT),
                    'feedback': coherence_analysis['feedback']
                },
                'tone_adherence': {
                    'score': tone_score,
                    'max': int(max_score * self.TONE_WEIGHT),
                    'feedback': tone_analysis['feedback']
                },
                'creativity': {
                    'score': creativity_score,
                    'max': int(max_score * self.CREATIVITY_WEIGHT),
                    'feedback': creativity_analysis['feedback']
                }
            },
            'overall_feedback': self._generate_overall_feedback(total_score, max_score, vocab_analysis),
            'revision_suggestion': self._generate_revision_suggestion(vocab_analysis, coherence_analysis, tone_analysis)
        }
    
    def _analyze_vocabulary_usage(self, story_text: str, required_words: List[str]) -> Dict[str, Any]:
        """Analyze how well vocabulary words are used"""
        
        story_lower = story_text.lower()
        words_found = []
        words_used_correctly = 0
        feedback_parts = []
        
        for word in required_words:
            word_lower = word.lower()
            if word_lower in story_lower:
                words_found.append(word)
                # Simple context check - word should not be isolated
                if self._check_word_context(story_text, word):
                    words_used_correctly += 1
                    feedback_parts.append(f"Great use of '{word}'!")
                else:
                    feedback_parts.append(f"'{word}' could be used more naturally in context.")
            else:
                feedback_parts.append(f"Missing required word: '{word}'.")
        
        if words_used_correctly == len(required_words):
            feedback = "Excellent vocabulary usage! All words are used correctly."
        elif words_used_correctly >= len(required_words) * 0.7:
            feedback = "Good vocabulary usage. " + " ".join(feedback_parts[:2])
        else:
            feedback = "Try to use all required words more naturally. " + " ".join(feedback_parts[:3])
        
        return {
            'words_found': words_found,
            'words_used_correctly': words_used_correctly,
            'total_words': len(required_words),
            'feedback': feedback
        }
    
    def _check_word_context(self, story_text: str, word: str) -> bool:
        """Simple check if word is used in proper context"""
        # Look for the word with surrounding text
        pattern = rf'\b{re.escape(word.lower())}\b'
        matches = re.finditer(pattern, story_text.lower())
        
        for match in matches:
            start, end = match.span()
            # Check for surrounding words (basic context)
            before = story_text[max(0, start-20):start].strip()
            after = story_text[end:end+20].strip()
            
            # If word has surrounding context, consider it properly used
            if len(before) > 0 and len(after) > 0:
                return True
        
        return len(list(re.finditer(pattern, story_text.lower()))) > 0
    
    def _analyze_coherence(self, story_text: str) -> Dict[str, float]:
        """Analyze story coherence and structure"""
        
        sentences = re.split(r'[.!?]+', story_text.strip())
        sentences = [s.strip() for s in sentences if s.strip()]
        
        score = 0.6  # Base score
        feedback = "Your story has a basic structure."
        
        # Check sentence count
        if len(sentences) >= 3:
            score += 0.2
            feedback = "Good story length with multiple sentences."
        
        # Check for story elements
        if any(word in story_text.lower() for word in ['then', 'next', 'after', 'finally', 'suddenly']):
            score += 0.1
            feedback += " Nice use of transition words."
        
        # Check for story progression
        if len(sentences) >= 4:
            score += 0.1
            feedback += " Good story development."
        
        return {
            'score': min(score, 1.0),
            'feedback': feedback
        }
    
    def _analyze_tone(self, story_text: str, expected_tone: str) -> Dict[str, float]:
        """Analyze if story matches expected tone"""
        
        tone_keywords = {
            'mysterious': ['mystery', 'unknown', 'hidden', 'secret', 'strange', 'puzzling', 'enigmatic'],
            'humorous': ['funny', 'laughed', 'giggled', 'silly', 'amusing', 'chuckled', 'hilarious'],
            'adventurous': ['journey', 'explore', 'discover', 'quest', 'adventure', 'brave', 'daring'],
            'suspenseful': ['tension', 'worried', 'anxious', 'danger', 'thrilling', 'edge', 'suspense'],
            'dramatic': ['intense', 'powerful', 'emotional', 'dramatic', 'climax', 'tension'],
            'whimsical': ['magical', 'playful', 'delightful', 'charming', 'fantastical', 'whimsical'],
            'heroic': ['brave', 'courage', 'hero', 'noble', 'valiant', 'fearless', 'champion'],
            'peaceful': ['calm', 'serene', 'quiet', 'tranquil', 'gentle', 'peaceful', 'relaxed'],
            'exciting': ['thrilling', 'amazing', 'incredible', 'fantastic', 'awesome', 'exciting'],
            'eerie': ['spooky', 'haunting', 'ghostly', 'creepy', 'eerie', 'chilling', 'supernatural']
        }
        
        story_lower = story_text.lower()
        keywords = tone_keywords.get(expected_tone, [])
        
        matches = sum(1 for keyword in keywords if keyword in story_lower)
        
        if matches >= 2:
            score = 0.9
            feedback = f"Excellent {expected_tone} tone! Your word choices really capture the feeling."
        elif matches >= 1:
            score = 0.7
            feedback = f"Good {expected_tone} tone. Try adding more descriptive words to enhance the feeling."
        else:
            score = 0.5
            feedback = f"Try to enhance the {expected_tone} tone with more fitting descriptive words."
        
        return {
            'score': score,
            'feedback': feedback
        }
    
    def _analyze_creativity(self, story_text: str) -> Dict[str, float]:
        """Analyze story creativity and descriptive language"""
        
        # Count descriptive elements
        adjectives = len(re.findall(r'\b(?:amazing|beautiful|mysterious|incredible|fantastic|wonderful|terrible|enormous|tiny|bright|dark|colorful)\b', story_text.lower()))
        
        # Check for vivid details
        details = len(re.findall(r'\b(?:shimmering|glowing|echoing|rustling|sparkling|gleaming|thunderous|whispered)\b', story_text.lower()))
        
        # Check for unique elements
        unique_elements = len(re.findall(r'\b(?:suddenly|unexpectedly|amazingly|miraculously|incredibly)\b', story_text.lower()))
        
        total_creative_elements = adjectives + details + unique_elements
        
        if total_creative_elements >= 3:
            score = 0.9
            feedback = "Very creative story with vivid details and interesting elements!"
        elif total_creative_elements >= 2:
            score = 0.7
            feedback = "Good creativity! Try adding more descriptive details or unique elements."
        elif total_creative_elements >= 1:
            score = 0.6
            feedback = "Some creative elements present. Add more vivid descriptions to enhance your story."
        else:
            score = 0.4
            feedback = "Try adding more descriptive words and unique details to make your story more engaging."
        
        return {
            'score': score,
            'feedback': feedback
        }
    
    def _generate_overall_feedback(self, total_score: int, max_score: int, vocab_analysis: Dict) -> str:
        """Generate encouraging overall feedback"""
        
        percentage = (total_score / max_score) * 100
        
        if percentage >= 90:
            return "Outstanding story! You've demonstrated excellent vocabulary usage and creative writing skills."
        elif percentage >= 80:
            return "Great job! Your story shows strong vocabulary understanding and good writing skills."
        elif percentage >= 70:
            return "Good work! You're on the right track with vocabulary usage and story structure."
        elif percentage >= 60:
            return "Nice effort! Focus on using all required words naturally and adding more descriptive details."
        else:
            missing_words = vocab_analysis['total_words'] - len(vocab_analysis['words_found'])
            if missing_words > 0:
                return f"Remember to include all {missing_words} required words in your story. Try again!"
            else:
                return "Keep working on making your story more detailed and engaging. You can do it!"
    
    def _generate_revision_suggestion(self, vocab_analysis: Dict, coherence_analysis: Dict, tone_analysis: Dict) -> str:
        """Generate specific revision suggestions"""
        
        suggestions = []
        
        if vocab_analysis['words_used_correctly'] < vocab_analysis['total_words']:
            missing = vocab_analysis['total_words'] - vocab_analysis['words_used_correctly']
            suggestions.append(f"Include {missing} more required vocabulary words naturally in your story.")
        
        if coherence_analysis['score'] < 0.7:
            suggestions.append("Add transition words like 'then', 'next', or 'finally' to improve story flow.")
        
        if tone_analysis['score'] < 0.7:
            suggestions.append("Use more descriptive words that match the required tone.")
        
        if not suggestions:
            return "Your story is well-written! Consider adding one unique detail to make it even more memorable."
        
        return " ".join(suggestions[:2])  # Limit to top 2 suggestions
    
    def _build_evaluation_prompt(self, story_text: str, required_words: List[str], setting: str, tone: str) -> str:
        """Build prompt for AI story evaluation"""
        
        words_list = ", ".join(f"'{word}'" for word in required_words)
        
        prompt = f"""Evaluate this student story for a vocabulary assignment:

STORY: "{story_text}"

REQUIREMENTS:
- Setting: {setting}
- Tone: {tone}  
- Required words: {words_list}

EVALUATION CRITERIA:
1. Vocabulary Usage (40 points): Are all required words used correctly and naturally?
2. Story Coherence (25 points): Does the story have logical flow with beginning, middle, end?
3. Tone Adherence (20 points): Does the story match the required {tone} tone?
4. Creativity (15 points): Are there vivid details and engaging elements?

Provide scores and specific feedback for each criterion. Format as:
VOCABULARY: [score]/40 - [feedback]
COHERENCE: [score]/25 - [feedback]  
TONE: [score]/20 - [feedback]
CREATIVITY: [score]/15 - [feedback]
TOTAL: [total score]/100
OVERALL: [encouraging overall feedback]
SUGGESTION: [one specific revision suggestion]"""

        return prompt
    
    async def _call_ai_api(self, prompt: str) -> str:
        """Call Gemini AI service for story evaluation"""
        
        try:
            if not self.gemini_config.api_key:
                raise Exception("Gemini API key not configured")
            
            logger.debug(f"Calling Gemini API with model: gemini-2.0-flash")
            
            # Configure generation settings for consistent evaluation
            generation_config = {
                "temperature": 0.3,  # Lower temperature for consistent evaluation
                "max_output_tokens": 1000,
                "top_p": 0.95,
            }
            
            # Generate response in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.gemini_model.generate_content(
                    prompt,
                    generation_config=generation_config
                )
            )
            
            if response.text:
                logger.info("Gemini API call successful")
                return response.text.strip()
            else:
                logger.error("No text in Gemini response")
                raise Exception("Empty response from Gemini")
            
        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            raise e
    
    
    def _parse_ai_evaluation(self, ai_response: str, max_score: int) -> Dict[str, Any]:
        """Parse AI evaluation response"""
        
        try:
            # Extract scores using regex
            vocab_match = re.search(r'VOCABULARY:\s*(\d+)/\d+\s*-\s*(.+?)(?=\n|COHERENCE:)', ai_response)
            coherence_match = re.search(r'COHERENCE:\s*(\d+)/\d+\s*-\s*(.+?)(?=\n|TONE:)', ai_response)
            tone_match = re.search(r'TONE:\s*(\d+)/\d+\s*-\s*(.+?)(?=\n|CREATIVITY:)', ai_response)
            creativity_match = re.search(r'CREATIVITY:\s*(\d+)/\d+\s*-\s*(.+?)(?=\n|TOTAL:)', ai_response)
            total_match = re.search(r'TOTAL:\s*(\d+)/\d+', ai_response)
            overall_match = re.search(r'OVERALL:\s*(.+?)(?=\n|SUGGESTION:)', ai_response)
            suggestion_match = re.search(r'SUGGESTION:\s*(.+?)(?=\n|$)', ai_response)
            
            vocab_score = int(vocab_match.group(1)) if vocab_match else 20
            vocab_feedback = vocab_match.group(2).strip() if vocab_match else "Vocabulary usage evaluated."
            
            coherence_score = int(coherence_match.group(1)) if coherence_match else 15
            coherence_feedback = coherence_match.group(2).strip() if coherence_match else "Story structure evaluated."
            
            tone_score = int(tone_match.group(1)) if tone_match else 12
            tone_feedback = tone_match.group(2).strip() if tone_match else "Tone evaluated."
            
            creativity_score = int(creativity_match.group(1)) if creativity_match else 8
            creativity_feedback = creativity_match.group(2).strip() if creativity_match else "Creativity evaluated."
            
            total_score = int(total_match.group(1)) if total_match else vocab_score + coherence_score + tone_score + creativity_score
            
            overall_feedback = overall_match.group(1).strip() if overall_match else "Good effort on your story!"
            revision_suggestion = suggestion_match.group(1).strip() if suggestion_match else "Keep up the good work!"
            
            return {
                'total_score': min(total_score, max_score),
                'breakdown': {
                    'vocabulary_usage': {
                        'score': vocab_score,
                        'max': int(max_score * self.VOCABULARY_WEIGHT),
                        'feedback': vocab_feedback
                    },
                    'story_coherence': {
                        'score': coherence_score,
                        'max': int(max_score * self.COHERENCE_WEIGHT),
                        'feedback': coherence_feedback
                    },
                    'tone_adherence': {
                        'score': tone_score,
                        'max': int(max_score * self.TONE_WEIGHT),
                        'feedback': tone_feedback
                    },
                    'creativity': {
                        'score': creativity_score,
                        'max': int(max_score * self.CREATIVITY_WEIGHT),
                        'feedback': creativity_feedback
                    }
                },
                'overall_feedback': overall_feedback,
                'revision_suggestion': revision_suggestion
            }
            
        except Exception as e:
            logger.error(f"Error parsing AI evaluation: {e}")
            # Fall back to template evaluation
            raise e
    
    def _validate_scores(self, evaluation: Dict[str, Any], story_text: str, required_words: List[str], max_score: int) -> Dict[str, Any]:
        """Validate and adjust AI scores based on basic checks"""
        
        # Ensure vocabulary score makes sense
        vocab_analysis = self._analyze_vocabulary_usage(story_text, required_words)
        max_vocab_score = int(max_score * self.VOCABULARY_WEIGHT)
        
        # If AI gave high vocab score but words are missing, adjust
        if evaluation['breakdown']['vocabulary_usage']['score'] > max_vocab_score * 0.8:
            if vocab_analysis['words_used_correctly'] < len(required_words) * 0.8:
                evaluation['breakdown']['vocabulary_usage']['score'] = int(max_vocab_score * 0.6)
        
        # Recalculate total
        total = sum(evaluation['breakdown'][category]['score'] for category in evaluation['breakdown'])
        evaluation['total_score'] = min(total, max_score)
        
        return evaluation
    
    async def _is_ai_available(self) -> bool:
        """Check if Gemini AI service is available"""
        return bool(self.gemini_config.api_key and self.gemini_model)
    
    def _fallback_evaluation(self, story_text: str, required_words: List[str], max_score: int) -> Dict[str, Any]:
        """Fallback evaluation when all else fails"""
        
        word_count = len(story_text.split())
        has_required_words = sum(1 for word in required_words if word.lower() in story_text.lower())
        
        # Basic scoring
        vocab_score = int((has_required_words / len(required_words)) * max_score * self.VOCABULARY_WEIGHT)
        coherence_score = int(max_score * self.COHERENCE_WEIGHT * 0.6)  # Default decent score
        tone_score = int(max_score * self.TONE_WEIGHT * 0.6)  # Default decent score
        creativity_score = int(max_score * self.CREATIVITY_WEIGHT * 0.5)  # Default moderate score
        
        total_score = vocab_score + coherence_score + tone_score + creativity_score
        
        return {
            'total_score': total_score,
            'breakdown': {
                'vocabulary_usage': {
                    'score': vocab_score,
                    'max': int(max_score * self.VOCABULARY_WEIGHT),
                    'feedback': f"Found {has_required_words} of {len(required_words)} required words."
                },
                'story_coherence': {
                    'score': coherence_score,
                    'max': int(max_score * self.COHERENCE_WEIGHT),
                    'feedback': "Your story has good basic structure."
                },
                'tone_adherence': {
                    'score': tone_score,
                    'max': int(max_score * self.TONE_WEIGHT),
                    'feedback': "Story tone evaluated."
                },
                'creativity': {
                    'score': creativity_score,
                    'max': int(max_score * self.CREATIVITY_WEIGHT),
                    'feedback': "Story shows creative elements."
                }
            },
            'overall_feedback': "Good effort on your story! Keep practicing to improve.",
            'revision_suggestion': "Try to include all required vocabulary words naturally in your story."
        }
"""
AI-powered vocabulary definition evaluator service
Evaluates student-provided definitions based on context and understanding
"""
import re
import json
from typing import Dict, Any, Optional
from app.core.config import settings
from app.config.ai_config import get_claude_config, get_openai_config
import httpx
import asyncio
import logging
from datetime import datetime
from uuid import UUID

logger = logging.getLogger(__name__)


class AIVocabularyEvaluator:
    """Evaluates student vocabulary definitions using AI"""
    
    # Scoring criteria weights
    CORE_MEANING_WEIGHT = 0.40      # 40 points
    CONTEXT_APPROPRIATENESS_WEIGHT = 0.30  # 30 points
    COMPLETENESS_WEIGHT = 0.20      # 20 points
    CLARITY_WEIGHT = 0.10           # 10 points
    
    def __init__(self):
        self.claude_config = get_claude_config()
        self.openai_config = get_openai_config()
    
    async def evaluate_definition(
        self,
        word: str,
        example_sentence: str,
        reference_definition: str,
        student_definition: str,
        grade_level: Optional[int] = None,
        subject_area: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a student's vocabulary definition using AI
        
        Args:
            word: The vocabulary word
            example_sentence: Sentence showing word in context
            reference_definition: Teacher/AI reference definition
            student_definition: Student's submitted definition
            grade_level: Student's grade level (for appropriate expectations)
            subject_area: Subject area for context
        
        Returns:
            Dictionary with score, feedback, strengths, and areas for growth
        """
        
        # Basic validation
        if not student_definition or len(student_definition.strip()) < 5:
            return self._create_minimal_response_feedback(word)
        
        try:
            # Use AI evaluation if available
            if await self._is_ai_available():
                result = await self._ai_evaluate_definition(
                    word, example_sentence, reference_definition, 
                    student_definition, grade_level, subject_area
                )
            else:
                # Fallback to rule-based evaluation
                result = self._fallback_evaluate_definition(
                    word, example_sentence, reference_definition, 
                    student_definition
                )
            
            # Ensure result has all required fields
            return self._validate_evaluation_result(result)
            
        except Exception as e:
            logger.error(f"Definition evaluation failed: {e}")
            return self._create_error_response(word, student_definition)
    
    async def _ai_evaluate_definition(
        self,
        word: str,
        example_sentence: str,
        reference_definition: str,
        student_definition: str,
        grade_level: Optional[int],
        subject_area: Optional[str]
    ) -> Dict[str, Any]:
        """Evaluate definition using AI service"""
        
        prompt = self._build_evaluation_prompt(
            word, example_sentence, reference_definition,
            student_definition, grade_level, subject_area
        )
        
        try:
            # Call AI service
            ai_response = await self._call_ai_api(prompt)
            
            # Parse AI response
            evaluation = self._parse_ai_response(ai_response)
            
            # Validate scores are reasonable
            evaluation = self._validate_scores(evaluation)
            
            return evaluation
            
        except Exception as e:
            logger.error(f"AI evaluation failed: {e}")
            # Fall back to rule-based evaluation
            return self._fallback_evaluate_definition(
                word, example_sentence, reference_definition, 
                student_definition
            )
    
    def _build_evaluation_prompt(
        self,
        word: str,
        example_sentence: str,
        reference_definition: str,
        student_definition: str,
        grade_level: Optional[int],
        subject_area: Optional[str]
    ) -> str:
        """Build prompt for AI evaluation"""
        
        grade_context = f"Grade Level: {grade_level}" if grade_level else "Grade Level: Not specified"
        subject_context = f"Subject Area: {subject_area}" if subject_area else ""
        
        prompt = f"""You are an encouraging educational evaluator assessing a student's vocabulary understanding. Your goal is to reward understanding over perfection.

Word: {word}
Context Sentence: {example_sentence}
Reference Definition: {reference_definition}
{grade_context}
{subject_context}

Student's Definition: {student_definition}

SCORING PHILOSOPHY:
- Students who demonstrate understanding deserve high scores (75%+)
- Simple language that shows comprehension is EXCELLENT
- Academic language is NOT required - clarity of understanding matters most
- Focus on what the student got RIGHT, not what they missed
- If the core concept is understood, be generous with points

SCORING EXAMPLES:
- "spurious → fake or false" should score 35-40/40 for core meaning (captures essence perfectly)
- "skeptical → doesn't trust something" should score 30-35/40 for core meaning (shows clear understanding)
- "pragmatic → practical, focused on results" should score 35-40/40 for core meaning (excellent grasp)
- Even partial understanding deserves 20-25/40 for core meaning

Evaluate on a 0-100 scale:
1. Core meaning understanding (40 points) - Does the student grasp the essential concept?
   - Full understanding = 35-40 points
   - Good understanding = 30-35 points  
   - Partial understanding = 20-30 points
   - Minimal understanding = 10-20 points
   - No understanding = 0-10 points

2. Context appropriateness (30 points) - Does it fit the example?
   - Start at 20 points for any reasonable attempt
   - Add points for matching the contextual usage

3. Completeness (20 points) - Is enough detail provided?
   - Start at 15 points for any complete thought
   - Simple but complete definitions deserve full points

4. Communication clarity (10 points) - Is it clearly expressed?
   - Start at 7 points for any coherent response
   - Simple, clear language deserves full points

CRITICAL REMINDERS:
- A student showing they understand "spurious = fake" deserves 85-95% total
- Don't penalize informal language or simple explanations
- Grade-appropriate expectations: younger students need less sophistication
- Minimum 50% total score for genuine effort (answers >10 characters)
- Always start feedback with what the student did WELL

Return your evaluation as JSON with this exact structure:
{{
    "score": [total score 0-100],
    "feedback": "[Start with praise for what they understood, then gentle suggestions]",
    "strengths": ["What they got right", "Evidence of understanding"],
    "areas_for_growth": ["Gentle suggestion 1", "Encouraging tip 2"],
    "component_scores": {{
        "core_meaning": [0-40],
        "context_appropriateness": [0-30],
        "completeness": [0-20],
        "clarity": [0-10]
    }}
}}"""
        
        return prompt
    
    async def _call_ai_api(self, prompt: str) -> str:
        """Call AI service for evaluation"""
        
        try:
            # Prefer Claude for evaluation
            if self.claude_config.api_key:
                return await self._call_claude_api(prompt)
            elif self.openai_config.api_key:
                return await self._call_openai_api(prompt)
            else:
                raise Exception("No AI service configured")
                
        except Exception as e:
            logger.error(f"AI API call failed: {e}")
            raise
    
    async def _call_claude_api(self, prompt: str) -> str:
        """Call Claude API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.claude_config.api_key,
                    "Content-Type": "application/json",
                    "anthropic-version": "2023-06-01"
                },
                json={
                    "model": self.claude_config.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,  # Lower temperature for consistent evaluation
                    "max_tokens": 1000
                },
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            return result['content'][0]['text']
    
    async def _call_openai_api(self, prompt: str) -> str:
        """Call OpenAI API"""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.openai_config.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.openai_config.model,
                    "messages": [
                        {"role": "system", "content": "You are an educational assessment tool that evaluates student vocabulary definitions with encouraging, constructive feedback."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 1000,
                    "response_format": {"type": "json_object"}
                },
                timeout=30.0
            )
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
    
    def _parse_ai_response(self, ai_response: str) -> Dict[str, Any]:
        """Parse AI response into structured evaluation"""
        try:
            # Try to parse as JSON
            evaluation = json.loads(ai_response)
            
            # Ensure all required fields are present
            required_fields = ['score', 'feedback', 'strengths', 'areas_for_growth']
            for field in required_fields:
                if field not in evaluation:
                    raise ValueError(f"Missing required field: {field}")
            
            return evaluation
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse AI response: {e}")
            # Return a generous default evaluation
            return {
                "score": 75,
                "feedback": "Good job! Your definition shows solid understanding of the word.",
                "strengths": ["Shows good effort", "Demonstrates understanding"],
                "areas_for_growth": ["You could add a bit more detail", "Keep practicing with new words"],
                "component_scores": {
                    "core_meaning": 30,
                    "context_appropriateness": 23,
                    "completeness": 15,
                    "clarity": 7
                }
            }
    
    def _fallback_evaluate_definition(
        self,
        word: str,
        example_sentence: str,
        reference_definition: str,
        student_definition: str
    ) -> Dict[str, Any]:
        """Rule-based fallback evaluation - generous and encouraging"""
        
        student_def_lower = student_definition.lower()
        reference_def_lower = reference_definition.lower()
        word_lower = word.lower()
        
        strengths = []
        areas_for_growth = []
        
        # Check for core meaning (40 points) - START GENEROUS
        core_meaning_score = 20  # Base score for any genuine attempt
        
        # Extract key words from reference definition
        reference_words = set(re.findall(r'\b\w{3,}\b', reference_def_lower))  # Include 3+ letter words
        student_words = set(re.findall(r'\b\w{3,}\b', student_def_lower))
        
        # Remove common words that don't carry meaning
        common_stop_words = {'the', 'and', 'for', 'with', 'that', 'this', 'are', 'was', 'were', 'been'}
        reference_words -= common_stop_words
        student_words -= common_stop_words
        
        # Calculate overlap
        common_words = reference_words & student_words
        if common_words:
            overlap_ratio = len(common_words) / max(len(reference_words), 1)
            # Generous scoring: even 20% overlap gets good points
            if overlap_ratio >= 0.3:
                core_meaning_score = 35  # Excellent understanding
                strengths.append("Excellent grasp of the core meaning")
            elif overlap_ratio >= 0.2:
                core_meaning_score = 30  # Good understanding
                strengths.append("Good understanding of the word")
            else:
                core_meaning_score = 25  # Partial understanding
                strengths.append("Shows understanding of key concepts")
        else:
            # Check for synonyms or related concepts
            if any(word in student_def_lower for word in ['similar', 'like', 'type', 'kind', 'means']):
                core_meaning_score = 25
                strengths.append("Attempts to explain the meaning")
            areas_for_growth.append("Try to capture more of the word's specific meaning")
        
        # Context appropriateness (30 points) - START HIGH
        context_score = 20  # Base score for any attempt
        if len(student_definition) > 10:
            context_score = 25  # Good effort
            strengths.append("Provides a thoughtful response")
        if len(student_definition) > 20:
            context_score = 28  # Excellent effort
        
        # Completeness (20 points) - GENEROUS
        completeness_score = 15  # Base score
        word_count = len(student_def_lower.split())
        if word_count >= 3:
            completeness_score = 17
            if "Complete thought" not in str(strengths):
                strengths.append("Complete thought provided")
        if word_count >= 6:
            completeness_score = 19
        
        # Clarity (10 points) - ASSUME GOOD CLARITY
        clarity_score = 8  # Default high clarity
        if len(student_definition) > 15:
            clarity_score = 9  # Very clear
        
        # Calculate total - ENSURE MINIMUM 50% FOR GENUINE EFFORT
        total_score = core_meaning_score + context_score + completeness_score + clarity_score
        
        # Ensure minimum 50% for any genuine effort (>10 characters)
        if len(student_definition) > 10 and total_score < 50:
            total_score = 50
            # Adjust component scores proportionally
            adjustment_ratio = 50 / (core_meaning_score + context_score + completeness_score + clarity_score)
            core_meaning_score = int(core_meaning_score * adjustment_ratio)
            context_score = int(context_score * adjustment_ratio)
            completeness_score = int(completeness_score * adjustment_ratio)
            clarity_score = int(clarity_score * adjustment_ratio)
        
        # Generate ENCOURAGING feedback
        if total_score >= 80:
            feedback = f"Excellent work with '{word}'! You clearly understand what this word means."
        elif total_score >= 70:
            feedback = f"Good job with '{word}'! You show solid understanding of its meaning."
        elif total_score >= 60:
            feedback = f"Nice effort with '{word}'! You're demonstrating good comprehension."
        else:
            feedback = f"Good try with '{word}'! You're on the right path to understanding this word."
        
        # Always have positive strengths
        if not strengths:
            strengths = ["Shows effort and engagement", "Attempts to explain the meaning"]
        
        # Gentle, encouraging growth areas
        if not areas_for_growth:
            if total_score < 80:
                areas_for_growth = ["Consider how the word is used in the example", "You might add a bit more detail"]
            else:
                areas_for_growth = ["Keep up the great work", "Continue building your vocabulary"]
        
        return {
            "score": total_score,
            "feedback": feedback,
            "strengths": strengths[:2],  # Limit to 2
            "areas_for_growth": areas_for_growth[:2],  # Limit to 2
            "component_scores": {
                "core_meaning": core_meaning_score,
                "context_appropriateness": context_score,
                "completeness": completeness_score,
                "clarity": clarity_score
            }
        }
    
    def _validate_scores(self, evaluation: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and adjust scores to be reasonable"""
        
        # Ensure score is within valid range
        if 'score' in evaluation:
            evaluation['score'] = max(0, min(100, evaluation['score']))
        
        # Validate component scores if present
        if 'component_scores' in evaluation:
            cs = evaluation['component_scores']
            cs['core_meaning'] = max(0, min(40, cs.get('core_meaning', 20)))
            cs['context_appropriateness'] = max(0, min(30, cs.get('context_appropriateness', 15)))
            cs['completeness'] = max(0, min(20, cs.get('completeness', 10)))
            cs['clarity'] = max(0, min(10, cs.get('clarity', 5)))
            
            # Recalculate total if components don't match
            component_total = sum(cs.values())
            if abs(component_total - evaluation['score']) > 5:
                evaluation['score'] = component_total
        
        return evaluation
    
    def _validate_evaluation_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure evaluation result has all required fields"""
        
        # Required fields with defaults
        defaults = {
            "score": 50,
            "feedback": "Your definition has been evaluated.",
            "strengths": ["Shows effort"],
            "areas_for_growth": ["Keep practicing"],
            "component_scores": {
                "core_meaning": 20,
                "context_appropriateness": 15,
                "completeness": 10,
                "clarity": 5
            }
        }
        
        # Merge with defaults
        for key, default_value in defaults.items():
            if key not in result:
                result[key] = default_value
        
        return result
    
    def _create_minimal_response_feedback(self, word: str) -> Dict[str, Any]:
        """Create feedback for minimal/empty responses"""
        return {
            "score": 0,
            "feedback": f"Please provide a definition for '{word}'. Try explaining what the word means based on how it's used in the sentence.",
            "strengths": [],
            "areas_for_growth": ["Provide a definition", "Use the context sentence to help"],
            "component_scores": {
                "core_meaning": 0,
                "context_appropriateness": 0,
                "completeness": 0,
                "clarity": 0
            }
        }
    
    def _create_error_response(self, word: str, student_definition: str) -> Dict[str, Any]:
        """Create response when evaluation fails"""
        
        # Give partial credit for effort
        base_score = 50 if len(student_definition) > 20 else 30
        
        return {
            "score": base_score,
            "feedback": f"Your definition of '{word}' has been recorded. Keep up the good work!",
            "strengths": ["Provided a definition", "Shows effort"],
            "areas_for_growth": ["Review the word in context", "Practice defining words"],
            "component_scores": {
                "core_meaning": base_score * 0.4,
                "context_appropriateness": base_score * 0.3,
                "completeness": base_score * 0.2,
                "clarity": base_score * 0.1
            }
        }
    
    async def _is_ai_available(self) -> bool:
        """Check if AI service is available"""
        return bool(self.claude_config.api_key or self.openai_config.api_key)
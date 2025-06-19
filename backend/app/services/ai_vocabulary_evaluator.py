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
        
        prompt = f"""You are evaluating a student's vocabulary definition. The student was given a word in context and asked to define it.

Word: {word}
Context Sentence: {example_sentence}
Reference Definition: {reference_definition}
{grade_context}
{subject_context}

Student's Definition: {student_definition}

Evaluate on a 0-100 scale considering:
1. Core meaning understanding (40 points) - Does the student grasp the essential meaning?
2. Context appropriateness (30 points) - Does the definition fit how the word is used in the sentence?
3. Completeness (20 points) - Is the definition thorough without being overly wordy?
4. Communication clarity (10 points) - Is the definition clearly expressed?

Important guidelines:
- Be encouraging and constructive in feedback
- Give partial credit generously for approximate understanding
- Consider age-appropriate vocabulary and expression
- Focus on what the student understood correctly
- Recognize effort and partial understanding
- For younger students, simpler definitions that capture the essence are acceptable
- Accept definitions that may use simpler language but show understanding

Return your evaluation as JSON with this exact structure:
{{
    "score": [total score 0-100],
    "feedback": "[Encouraging feedback about what the student understood and suggestions for improvement]",
    "strengths": ["strength 1", "strength 2"],
    "areas_for_growth": ["suggestion 1", "suggestion 2"],
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
            # Return a default evaluation
            return {
                "score": 70,
                "feedback": "Good effort! Your definition shows understanding of the word.",
                "strengths": ["Shows effort", "Attempted to explain the meaning"],
                "areas_for_growth": ["Try to be more specific", "Consider the context"],
                "component_scores": {
                    "core_meaning": 28,
                    "context_appropriateness": 21,
                    "completeness": 14,
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
        """Rule-based fallback evaluation"""
        
        student_def_lower = student_definition.lower()
        reference_def_lower = reference_definition.lower()
        word_lower = word.lower()
        
        score = 0
        strengths = []
        areas_for_growth = []
        
        # Check for core meaning (40 points)
        core_meaning_score = 0
        
        # Extract key words from reference definition
        reference_words = set(re.findall(r'\b\w{4,}\b', reference_def_lower))
        student_words = set(re.findall(r'\b\w{4,}\b', student_def_lower))
        
        # Calculate overlap
        common_words = reference_words & student_words
        if common_words:
            overlap_ratio = len(common_words) / len(reference_words)
            core_meaning_score = int(40 * overlap_ratio)
            strengths.append("Captures key aspects of the meaning")
        else:
            core_meaning_score = 10  # Minimal points for effort
            areas_for_growth.append("Try to identify the main meaning of the word")
        
        # Context appropriateness (30 points)
        context_score = 20  # Default middle score
        if len(student_definition) > 10:
            context_score = 25
            strengths.append("Provides a complete response")
        
        # Completeness (20 points)
        completeness_score = 10
        if len(student_def_lower.split()) >= 5:
            completeness_score = 15
            strengths.append("Good level of detail")
        
        # Clarity (10 points)
        clarity_score = 7  # Default good clarity
        
        # Calculate total
        total_score = core_meaning_score + context_score + completeness_score + clarity_score
        
        # Generate feedback
        if total_score >= 80:
            feedback = f"Great job defining '{word}'! You show strong understanding of the word's meaning."
        elif total_score >= 70:
            feedback = f"Good effort defining '{word}'! You understand the basic meaning."
        elif total_score >= 60:
            feedback = f"Nice try with '{word}'! You're on the right track."
        else:
            feedback = f"Keep working on understanding '{word}'. Think about how it's used in the sentence."
        
        if not strengths:
            strengths = ["Shows effort", "Attempted to provide a definition"]
        
        if not areas_for_growth:
            areas_for_growth = ["Consider adding more detail", "Think about the context"]
        
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
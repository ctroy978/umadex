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
            logger.info(f"Minimal response for word '{word}': '{student_definition}'")
            return self._create_minimal_response_feedback(word)
        
        try:
            # Check if AI is available and log the result
            ai_available = await self._is_ai_available()
            logger.info(f"AI evaluation available: {ai_available}")
            logger.info(f"Evaluating definition for '{word}': '{student_definition}' (Reference: '{reference_definition}')")
            
            # Use AI evaluation if available
            if ai_available:
                logger.info("Using AI evaluation method")
                result = await self._ai_evaluate_definition(
                    word, example_sentence, reference_definition, 
                    student_definition, grade_level, subject_area
                )
            else:
                # Fallback to rule-based evaluation
                logger.warning("AI not available, using fallback evaluation method")
                result = self._fallback_evaluate_definition(
                    word, example_sentence, reference_definition, 
                    student_definition
                )
            
            logger.info(f"Evaluation result for '{word}': score={result.get('score', 'N/A')}, method={'AI' if ai_available else 'fallback'}")
            
            # Ensure result has all required fields
            return self._validate_evaluation_result(result)
            
        except Exception as e:
            logger.error(f"Definition evaluation failed: {e}", exc_info=True)
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
        
        prompt = f"""You are a fair and accurate educational evaluator assessing a student's vocabulary understanding. Your goal is to provide honest, accurate scoring that reflects the student's actual understanding.

Word: {word}
Context Sentence: {example_sentence}
Reference Definition: {reference_definition}
{grade_context}
{subject_context}

Student's Definition: {student_definition}

SCORING PHILOSOPHY:
- Accuracy is paramount - wrong answers must receive low scores
- Understanding must be demonstrated, not just effort
- Be encouraging in feedback but honest in scoring
- Grade based on correctness, not length or complexity

SCORING EXAMPLES:
- "discord → love" should score 0-5/40 for core meaning (completely wrong)
- "incite → to put on makeup" should score 0-5/40 for core meaning (completely wrong)
- "benevolent → trying hard" should score 5-10/40 for core meaning (shows effort but wrong)
- "spurious → fake or false" should score 35-40/40 for core meaning (correct)
- "skeptical → doesn't trust something" should score 30-35/40 for core meaning (essentially correct)
- "defunct → to make cool music" should score 0-5/40 for core meaning (completely wrong)

Evaluate on a 0-100 scale:
1. Core meaning understanding (40 points) - Does the student grasp the actual meaning?
   - Correct understanding = 30-40 points
   - Mostly correct with minor issues = 20-30 points  
   - Partial/related understanding = 10-20 points
   - Minimal/tangential understanding = 5-10 points
   - Completely wrong = 0-5 points

2. Context appropriateness (30 points) - Does the definition fit the example sentence?
   - If core meaning is wrong, maximum 5 points
   - If core meaning is partially correct, scale appropriately
   - Full points only for definitions that work in context

3. Completeness (20 points) - Is the definition adequate?
   - Wrong answers get 0-5 points regardless of length
   - Partial understanding gets 5-10 points
   - Correct answers can get full points even if brief

4. Communication clarity (10 points) - Is it clearly expressed?
   - Even wrong answers can get 5-10 points if clearly stated
   - Confused or incoherent responses get 0-5 points

STRICT SCORING RULES:
- Completely wrong answers (like "love" for "discord") must score 5-15% total
- Effort alone does not warrant points - accuracy matters
- No minimum score guarantees - wrong is wrong
- Be honest about what the student doesn't understand

Return your evaluation as JSON with this exact structure:
{{
    "score": [total score 0-100],
    "feedback": "[Honest assessment - acknowledge effort but be clear about accuracy]",
    "strengths": ["What they actually got right", "Any positive aspects"],
    "areas_for_growth": ["What they need to understand", "Specific improvements needed"],
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
                logger.info("Attempting to call Claude API")
                return await self._call_claude_api(prompt)
            elif self.openai_config.api_key:
                logger.info("Attempting to call OpenAI API")
                return await self._call_openai_api(prompt)
            else:
                logger.error("No AI service configured - both CLAUDE_API_KEY and OPENAI_API_KEY are missing")
                raise Exception("No AI service configured")
                
        except Exception as e:
            logger.error(f"AI API call failed: {e}", exc_info=True)
            raise
    
    async def _call_claude_api(self, prompt: str) -> str:
        """Call Claude API"""
        try:
            async with httpx.AsyncClient() as client:
                logger.debug(f"Calling Claude API with model: {self.claude_config.model}")
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
                logger.info("Claude API call successful")
                return result['content'][0]['text']
        except httpx.HTTPStatusError as e:
            logger.error(f"Claude API HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Claude API call failed: {type(e).__name__}: {e}")
            raise
    
    async def _call_openai_api(self, prompt: str) -> str:
        """Call OpenAI API"""
        try:
            async with httpx.AsyncClient() as client:
                logger.debug(f"Calling OpenAI API with model: {self.openai_config.model}")
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.openai_config.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.openai_config.model,
                        "messages": [
                            {"role": "system", "content": "You are an educational assessment tool that evaluates student vocabulary definitions accurately and fairly. Be honest about incorrect answers while maintaining an encouraging tone."},
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
                logger.info("OpenAI API call successful")
                return result['choices'][0]['message']['content']
        except httpx.HTTPStatusError as e:
            logger.error(f"OpenAI API HTTP error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"OpenAI API call failed: {type(e).__name__}: {e}")
            raise
    
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
        """Rule-based fallback evaluation - strict and accurate"""
        
        logger.info(f"Using fallback evaluation for '{word}'")
        
        student_def_lower = student_definition.lower().strip()
        reference_def_lower = reference_definition.lower().strip()
        word_lower = word.lower()
        
        strengths = []
        areas_for_growth = []
        
        # Check for core meaning (40 points) - STRICT SCORING
        core_meaning_score = 0  # Start at 0, build up based on accuracy
        
        # Extract key words from reference definition
        reference_words = set(re.findall(r'\b\w{3,}\b', reference_def_lower))
        student_words = set(re.findall(r'\b\w{3,}\b', student_def_lower))
        
        # Remove common words that don't carry meaning
        common_stop_words = {'the', 'and', 'for', 'with', 'that', 'this', 'are', 'was', 'were', 'been', 'have', 'has', 'had', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'could'}
        reference_words -= common_stop_words
        student_words -= common_stop_words
        
        # Check for completely wrong answers first
        # Special cases for common wrong patterns
        wrong_answer_indicators = [
            # If the student uses antonyms or opposite concepts
            ('discord', ['harmony', 'love', 'peace', 'agreement', 'unity']),
            ('benevolent', ['evil', 'mean', 'cruel', 'harsh', 'malevolent']),
            ('spurious', ['genuine', 'real', 'authentic', 'true', 'valid']),
            ('incite', ['calm', 'soothe', 'peaceful', 'makeup', 'cosmetic']),
            ('defunct', ['alive', 'working', 'functional', 'music', 'cool', 'active'])
        ]
        
        for check_word, wrong_terms in wrong_answer_indicators:
            if word_lower == check_word.lower():
                if any(term in student_def_lower for term in wrong_terms):
                    core_meaning_score = 2  # Completely wrong
                    areas_for_growth.append(f"Your definition suggests the opposite of what '{word}' means")
                    logger.info(f"Detected completely wrong answer for '{word}': '{student_definition}'")
                    break
        
        # If not completely wrong, calculate word overlap
        if core_meaning_score == 0:  # Not yet scored as completely wrong
            common_words = reference_words & student_words
            if common_words:
                overlap_ratio = len(common_words) / max(len(reference_words), 1)
                # Much stricter scoring based on overlap
                if overlap_ratio >= 0.5:
                    core_meaning_score = 35  # Excellent understanding
                    strengths.append("Strong understanding of the core meaning")
                elif overlap_ratio >= 0.35:
                    core_meaning_score = 28  # Good understanding
                    strengths.append("Good grasp of the word's meaning")
                elif overlap_ratio >= 0.2:
                    core_meaning_score = 20  # Partial understanding
                    strengths.append("Shows some understanding")
                else:
                    core_meaning_score = 10  # Minimal understanding
                    areas_for_growth.append("Review the word's actual meaning")
            else:
                # No meaningful overlap
                core_meaning_score = 5  # Very low score for no understanding
                areas_for_growth.append("Your definition doesn't capture the word's meaning")
        
        # Context appropriateness (30 points) - Based on core meaning accuracy
        if core_meaning_score <= 5:
            context_score = 3  # Wrong answers get minimal context points
        elif core_meaning_score <= 10:
            context_score = 8
        elif core_meaning_score <= 20:
            context_score = 15
        elif core_meaning_score <= 28:
            context_score = 22
        else:
            context_score = 27  # Only high accuracy gets high context score
        
        # Completeness (20 points) - Based on accuracy, not just length
        word_count = len(student_def_lower.split())
        if core_meaning_score <= 5:
            completeness_score = 2  # Wrong answers get minimal points
        elif word_count >= 5 and core_meaning_score >= 20:
            completeness_score = 15
            if "Complete definition" not in str(strengths):
                strengths.append("Complete definition provided")
        elif word_count >= 3 and core_meaning_score >= 10:
            completeness_score = 10
        else:
            completeness_score = 5
        
        # Clarity (10 points) - Can be decent even for wrong answers if clearly stated
        if len(student_definition) > 10 and word_count >= 3:
            clarity_score = 7  # Clear expression
        elif len(student_definition) > 5:
            clarity_score = 5  # Basic clarity
        else:
            clarity_score = 2  # Minimal clarity
        
        # Calculate total - NO MINIMUM GUARANTEES
        total_score = core_meaning_score + context_score + completeness_score + clarity_score
        
        # Generate HONEST feedback
        if total_score >= 80:
            feedback = f"Excellent work! You clearly understand what '{word}' means."
        elif total_score >= 60:
            feedback = f"Good effort! You have a decent understanding of '{word}'."
        elif total_score >= 40:
            feedback = f"You're making progress with '{word}', but there's room for improvement."
        elif total_score >= 20:
            feedback = f"Your understanding of '{word}' needs work. Review the word's meaning and try again."
        else:
            feedback = f"Your definition of '{word}' is not accurate. Please study this word more carefully."
        
        # Be honest about strengths
        if not strengths:
            if core_meaning_score > 10:
                strengths = ["Shows some effort", "Attempts to provide a definition"]
            else:
                strengths = ["Provided an answer"]  # Minimal strength for wrong answers
        
        # Clear growth areas
        if not areas_for_growth:
            if core_meaning_score < 20:
                areas_for_growth = ["Study the word's actual meaning", "Use the context sentence to understand the word better"]
            else:
                areas_for_growth = ["Could be more precise", "Consider adding more detail"]
        
        result = {
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
        
        logger.info(f"Fallback evaluation result for '{word}': {result}")
        return result
    
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
        claude_available = bool(self.claude_config.api_key)
        openai_available = bool(self.openai_config.api_key)
        
        logger.debug(f"Claude API key present: {claude_available}")
        logger.debug(f"OpenAI API key present: {openai_available}")
        
        return claude_available or openai_available
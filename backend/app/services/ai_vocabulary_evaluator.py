"""
AI-powered vocabulary definition evaluator service
Evaluates student-provided definitions based on context and understanding
"""
import re
import json
from typing import Dict, Any, Optional
from app.core.config import settings
from app.config.ai_config import get_claude_config, get_openai_config, get_gemini_config
import httpx
import asyncio
import logging
import google.generativeai as genai
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
        self.gemini_config = get_gemini_config()
        self.claude_config = get_claude_config()
        self.openai_config = get_openai_config()
        
        # Initialize Gemini if API key is available
        if self.gemini_config.api_key:
            genai.configure(api_key=self.gemini_config.api_key)
            self.gemini_model = genai.GenerativeModel('gemini-2.0-flash')
        else:
            self.gemini_model = None
    
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
            Raises exception if AI evaluation is not available
        """
        
        # Basic validation
        if not student_definition or len(student_definition.strip()) < 5:
            logger.info(f"Minimal response for word '{word}': '{student_definition}'")
            return self._create_minimal_response_feedback(word)
        
        # Check if AI is available
        ai_available = await self._is_ai_available()
        logger.info(f"AI evaluation available: {ai_available}")
        logger.info(f"Claude API key present: {bool(self.claude_config.api_key)}")
        logger.info(f"OpenAI API key present: {bool(self.openai_config.api_key)}")
        
        if not ai_available:
            error_msg = "AI evaluation is required but no AI service is configured. Please set GEMINI_API_KEY, CLAUDE_API_KEY, or OPENAI_API_KEY environment variable."
            logger.error(error_msg)
            raise Exception(error_msg)
        
        try:
            logger.info(f"Starting AI evaluation for '{word}': '{student_definition}' (Reference: '{reference_definition}')")
            
            # AI evaluation is mandatory
            result = await self._ai_evaluate_definition(
                word, example_sentence, reference_definition, 
                student_definition, grade_level, subject_area
            )
            
            logger.info(f"AI evaluation successful for '{word}': score={result.get('score', 'N/A')}")
            
            # Ensure result has all required fields
            return self._validate_evaluation_result(result)
            
        except Exception as e:
            logger.error(f"AI evaluation failed for '{word}': {str(e)}", exc_info=True)
            # Re-raise the exception - no fallback allowed
            raise Exception(f"AI evaluation failed: {str(e)}")
    
    async def _ai_evaluate_definition(
        self,
        word: str,
        example_sentence: str,
        reference_definition: str,
        student_definition: str,
        grade_level: Optional[int],
        subject_area: Optional[str]
    ) -> Dict[str, Any]:
        """Evaluate definition using AI service - no fallback allowed"""
        
        prompt = self._build_evaluation_prompt(
            word, example_sentence, reference_definition,
            student_definition, grade_level, subject_area
        )
        
        logger.debug(f"AI evaluation prompt length: {len(prompt)} characters")
        
        try:
            # Call AI service
            logger.info("Calling AI API for evaluation...")
            ai_response = await self._call_ai_api(prompt)
            logger.info("AI API call completed successfully")
            
            # Parse AI response
            logger.debug("Parsing AI response...")
            evaluation = self._parse_ai_response(ai_response)
            
            # Validate scores are reasonable
            evaluation = self._validate_scores(evaluation)
            
            logger.info(f"AI evaluation completed: score={evaluation.get('score', 'N/A')}")
            return evaluation
            
        except Exception as e:
            logger.error(f"AI evaluation failed: {type(e).__name__}: {str(e)}", exc_info=True)
            # No fallback - re-raise the exception
            raise
    
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

Return your evaluation as a valid JSON object with this exact structure:
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
}}

Ensure all arrays contain string values and all numbers are integers."""
        
        return prompt
    
    async def _call_ai_api(self, prompt: str) -> str:
        """Call AI service for evaluation"""
        
        try:
            # Prefer Gemini for evaluation (consistent with rest of app)
            if self.gemini_config.api_key:
                logger.info("Attempting to call Gemini API")
                return await self._call_gemini_api(prompt)
            elif self.claude_config.api_key:
                logger.info("Attempting to call Claude API")
                return await self._call_claude_api(prompt)
            elif self.openai_config.api_key:
                logger.info("Attempting to call OpenAI API")
                return await self._call_openai_api(prompt)
            else:
                logger.error("No AI service configured - GEMINI_API_KEY, CLAUDE_API_KEY, and OPENAI_API_KEY are all missing")
                raise Exception("No AI service configured")
                
        except Exception as e:
            logger.error(f"AI API call failed: {e}", exc_info=True)
            raise
    
    async def _call_gemini_api(self, prompt: str) -> str:
        """Call Gemini API"""
        try:
            logger.debug(f"Calling Gemini API with model: gemini-2.0-flash")
            
            # Configure generation settings to return JSON
            generation_config = {
                "temperature": 0.3,  # Lower temperature for consistent evaluation
                "max_output_tokens": 1000,
                "top_p": 0.95,
            }
            
            # Add instruction to return JSON
            json_prompt = prompt + "\n\nIMPORTANT: Return ONLY valid JSON without any markdown formatting or code blocks."
            
            # Generate response in a thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.gemini_model.generate_content(
                    json_prompt,
                    generation_config=generation_config
                )
            )
            
            if response.text:
                logger.info("Gemini API call successful")
                # Clean up response - remove any markdown code blocks if present
                text = response.text.strip()
                if text.startswith("```json"):
                    text = text[7:]  # Remove ```json
                if text.startswith("```"):
                    text = text[3:]  # Remove ```
                if text.endswith("```"):
                    text = text[:-3]  # Remove closing ```
                return text.strip()
            else:
                logger.error("No text in Gemini response")
                raise Exception("Empty response from Gemini")
                
        except Exception as e:
            logger.error(f"Gemini API call failed: {type(e).__name__}: {e}")
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
                            {"role": "system", "content": "You are an educational assessment tool that evaluates student vocabulary definitions accurately and fairly. Be honest about incorrect answers while maintaining an encouraging tone. Always return valid JSON."},
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
            
            logger.debug(f"Successfully parsed AI response with score: {evaluation.get('score')}")
            return evaluation
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse AI response: {e}")
            logger.error(f"Raw AI response: {ai_response[:500]}...")  # Log first 500 chars
            # No default evaluation - raise exception
            raise Exception(f"Failed to parse AI response: {str(e)}")
    
    # Removed fallback evaluation method - AI evaluation is mandatory
    
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
    
    # Removed error response method - AI evaluation is mandatory, errors should be raised
    
    async def _is_ai_available(self) -> bool:
        """Check if AI service is available"""
        gemini_available = bool(self.gemini_config.api_key and self.gemini_config.api_key.strip())
        claude_available = bool(self.claude_config.api_key and self.claude_config.api_key.strip())
        openai_available = bool(self.openai_config.api_key and self.openai_config.api_key.strip())
        
        logger.info(f"Gemini API key present: {gemini_available} (length: {len(self.gemini_config.api_key) if self.gemini_config.api_key else 0})")
        logger.info(f"Claude API key present: {claude_available} (length: {len(self.claude_config.api_key) if self.claude_config.api_key else 0})")
        logger.info(f"OpenAI API key present: {openai_available} (length: {len(self.openai_config.api_key) if self.openai_config.api_key else 0})")
        
        if not gemini_available and not claude_available and not openai_available:
            logger.error("No AI service available - all API keys are missing or empty")
        
        return gemini_available or claude_available or openai_available
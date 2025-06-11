"""
Vocabulary Concept Map Evaluator Service
Evaluates student concept maps using AI
"""
import json
import logging
import os
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class VocabularyConceptMapEvaluator:
    """Service for evaluating student concept maps using AI"""
    
    def __init__(self):
        pass
    
    async def evaluate_concept_map(
        self,
        word: str,
        grade_level: str,
        definition: str,
        synonyms: str,
        antonyms: str,
        context_theme: str,
        connotation: str,
        example_sentence: str
    ) -> Dict[str, Any]:
        """Evaluate a student's concept map for a vocabulary word"""
        
        prompt = f"""You are evaluating a {grade_level} grade student's concept map for the vocabulary word "{word}".
        
The student has provided the following responses:

1. Definition: {definition}
2. Synonyms: {synonyms}
3. Antonyms: {antonyms}
4. Context/Theme (where/when the word is used): {context_theme}
5. Connotation (emotional feeling): {connotation}
6. Example Sentence: {example_sentence}

Evaluate each component on a scale of 1-4:
- 4: Excellent understanding, accurate and complete
- 3: Good understanding with minor issues
- 2: Partial understanding with significant gaps
- 1: Little to no understanding

Consider these criteria:
- Definition: Is it accurate and shows clear understanding?
- Synonyms: Are they truly similar in meaning and appropriate?
- Antonyms: Do they represent true opposites?
- Context/Theme: Does the student understand where/when to use the word?
- Connotation: Does the student grasp the emotional tone (positive/negative/neutral)?
- Example Sentence: Is the word used correctly in a meaningful context?

For a {grade_level} grade student, be appropriately encouraging while maintaining standards.

Return a JSON response with this exact structure:
{{
    "overall_score": <average of all component scores, to 1 decimal place>,
    "component_scores": {{
        "definition": {{
            "score": <1-4>,
            "feedback": "<specific, constructive feedback>"
        }},
        "synonyms": {{
            "score": <1-4>,
            "feedback": "<specific, constructive feedback>"
        }},
        "antonyms": {{
            "score": <1-4>,
            "feedback": "<specific, constructive feedback>"
        }},
        "context_theme": {{
            "score": <1-4>,
            "feedback": "<specific, constructive feedback>"
        }},
        "connotation": {{
            "score": <1-4>,
            "feedback": "<specific, constructive feedback>"
        }},
        "example_sentence": {{
            "score": <1-4>,
            "feedback": "<specific, constructive feedback>"
        }}
    }},
    "overall_feedback": "<2-3 sentences of encouraging overall feedback>",
    "areas_for_improvement": [<list 1-2 specific areas to focus on>]
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
            
            evaluation = json.loads(response_text.strip())
            
            # Validate response structure
            required_fields = ["overall_score", "component_scores", "overall_feedback", "areas_for_improvement"]
            if not all(field in evaluation for field in required_fields):
                raise ValueError("Invalid evaluation response structure")
            
            # Validate component scores
            required_components = ["definition", "synonyms", "antonyms", "context_theme", "connotation", "example_sentence"]
            for component in required_components:
                if component not in evaluation["component_scores"]:
                    raise ValueError(f"Missing component score: {component}")
                if not isinstance(evaluation["component_scores"][component].get("score"), (int, float)):
                    raise ValueError(f"Invalid score for component: {component}")
                if not 1 <= evaluation["component_scores"][component]["score"] <= 4:
                    raise ValueError(f"Score out of range for component: {component}")
            
            return evaluation
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI response as JSON: {e}")
            return self._get_fallback_evaluation(word)
        except Exception as e:
            logger.error(f"Error evaluating concept map: {e}")
            if "rate limit" in str(e).lower():
                return self._get_fallback_evaluation(word, "The evaluation service is temporarily busy. Your work has been saved.")
            return self._get_fallback_evaluation(word)
    
    def _get_fallback_evaluation(self, word: str, message: str = None) -> Dict[str, Any]:
        """Provide a fallback evaluation when AI is unavailable"""
        
        default_message = message or "Your concept map has been submitted. Please check with your teacher for detailed feedback."
        
        return {
            "overall_score": 2.5,
            "component_scores": {
                "definition": {
                    "score": 3,
                    "feedback": "Your definition shows understanding of the word."
                },
                "synonyms": {
                    "score": 2,
                    "feedback": "Consider finding more precise synonyms."
                },
                "antonyms": {
                    "score": 2,
                    "feedback": "Think about true opposites of this word."
                },
                "context_theme": {
                    "score": 3,
                    "feedback": "You've identified appropriate contexts."
                },
                "connotation": {
                    "score": 2,
                    "feedback": "Consider the emotional tone more carefully."
                },
                "example_sentence": {
                    "score": 3,
                    "feedback": "Your sentence uses the word correctly."
                }
            },
            "overall_feedback": f"You've completed your concept map for '{word}'. {default_message}",
            "areas_for_improvement": ["synonyms and antonyms", "connotation analysis"]
        }
    
    async def validate_student_input(
        self,
        definition: str,
        synonyms: str,
        antonyms: str,
        context_theme: str,
        connotation: str,
        example_sentence: str,
        word: str
    ) -> Dict[str, Any]:
        """Validate that student inputs are meaningful and not just random text"""
        
        # Basic validation rules
        min_lengths = {
            "definition": 10,
            "synonyms": 3,
            "antonyms": 3,
            "context_theme": 10,
            "connotation": 3,
            "example_sentence": 15
        }
        
        errors = {}
        
        # Check minimum lengths
        if len(definition.strip()) < min_lengths["definition"]:
            errors["definition"] = "Please provide a more complete definition."
        
        if len(synonyms.strip()) < min_lengths["synonyms"]:
            errors["synonyms"] = "Please provide at least one synonym."
        
        if len(antonyms.strip()) < min_lengths["antonyms"]:
            errors["antonyms"] = "Please provide at least one antonym."
        
        if len(context_theme.strip()) < min_lengths["context_theme"]:
            errors["context_theme"] = "Please describe where or when this word is used."
        
        if len(connotation.strip()) < min_lengths["connotation"]:
            errors["connotation"] = "Please describe the emotional tone (positive, negative, or neutral)."
        
        if len(example_sentence.strip()) < min_lengths["example_sentence"]:
            errors["example_sentence"] = "Please write a complete sentence using the word."
        
        # Check if example sentence contains the word
        if word.lower() not in example_sentence.lower():
            errors["example_sentence"] = f"Your example sentence must include the word '{word}'."
        
        # Check for repetitive or nonsense text
        for field, value in [
            ("definition", definition),
            ("context_theme", context_theme),
            ("example_sentence", example_sentence)
        ]:
            # Check for repeated characters (e.g., "aaaaa")
            if any(char * 5 in value.lower() for char in 'abcdefghijklmnopqrstuvwxyz'):
                errors[field] = "Please provide a meaningful response."
            
            # Check for keyboard mashing (e.g., "asdfasdf")
            common_patterns = ["asdf", "qwer", "zxcv", "1234", "abcd"]
            if any(pattern in value.lower() for pattern in common_patterns):
                if len(value) < 20:  # Allow these patterns in longer, meaningful text
                    errors[field] = "Please provide a thoughtful response."
        
        return {
            "valid": len(errors) == 0,
            "errors": errors
        }
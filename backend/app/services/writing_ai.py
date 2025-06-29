"""
Writing AI evaluation service using Google Gemini
"""
import json
import logging
from typing import Dict, List, Optional, Tuple
from decimal import Decimal

from app.utils.ai_helper import get_ai_response
from app.schemas.writing import EvaluationCriteria
from app.models.writing import WritingAssignment

logger = logging.getLogger(__name__)


class WritingAIService:
    """Service for AI-powered writing evaluation"""
    
    async def evaluate_writing_submission(
        self,
        student_response: str,
        word_count: int,
        selected_techniques: List[str],
        assignment: WritingAssignment,
        grade_level: str
    ) -> Dict:
        """
        Evaluate student writing submission based on rubric.
        Returns scores, feedback, and technique validation.
        """
        logger.info(f"Starting writing evaluation for assignment {assignment.id}")
        
        # Build the evaluation prompt
        prompt = self._build_evaluation_prompt(
            student_response=student_response,
            word_count=word_count,
            selected_techniques=selected_techniques,
            assignment=assignment,
            grade_level=grade_level
        )
        
        # Get AI evaluation
        try:
            logger.info("Calling AI for evaluation...")
            response = await get_ai_response(prompt, max_tokens=2000)
            logger.info(f"Received AI evaluation response: {len(response)} chars")
            
            # Parse the JSON response
            evaluation = self._parse_evaluation_response(response)
            
            # Validate and adjust scores if needed
            evaluation = self._validate_evaluation(evaluation, student_response, selected_techniques)
            
            # Calculate final scores
            final_scores = self._calculate_final_scores(evaluation)
            
            # Handle both old and new JSON structures
            revision_suggestions = evaluation['final_assessment'].get('priority_improvements', 
                                                                    evaluation['final_assessment'].get('next_steps', []))
            
            # Add any technique recommendations to suggestions
            tech_recommendations = evaluation['final_assessment'].get('technique_recommendations', '')
            if tech_recommendations and isinstance(tech_recommendations, str):
                revision_suggestions.append(tech_recommendations)
            
            return {
                'score': final_scores['final_percentage'],
                'ai_feedback': {
                    'overall_score': final_scores['final_percentage'],
                    'core_score': final_scores['core_score'],
                    'bonus_points': final_scores['bonus_points'],
                    'criteria_scores': {
                        'content_purpose': evaluation['content_purpose'],
                        'teacher_criteria': evaluation['teacher_criteria'],
                        'conventions_clarity': evaluation['conventions_clarity']
                    },
                    'technique_validation': evaluation['technique_validation'],
                    'general_feedback': evaluation['final_assessment']['overall_feedback'],
                    'revision_suggestions': revision_suggestions
                }
            }
            
        except Exception as e:
            logger.error(f"Error in AI evaluation: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            # Return a default evaluation if AI fails
            return self._get_default_evaluation(selected_techniques)
    
    def _build_evaluation_prompt(
        self,
        student_response: str,
        word_count: int,
        selected_techniques: List[str],
        assignment: WritingAssignment,
        grade_level: str
    ) -> str:
        """Build a comprehensive evaluation prompt that handles all writing techniques"""
        
        # Format teacher criteria
        criteria_list = []
        evaluation_criteria = assignment.evaluation_criteria or {}
        
        if hasattr(evaluation_criteria, 'items'):
            criteria_items = evaluation_criteria.items()
        else:
            criteria_items = evaluation_criteria if isinstance(evaluation_criteria, dict) else {}
            
        for key, values in criteria_items:
            if values and isinstance(values, list):
                criteria_list.append(f"{key}: {', '.join(str(v) for v in values)}")
        teacher_criteria = '; '.join(criteria_list) if criteria_list else "General writing quality"

        # Create technique definitions for selected techniques
        technique_definitions = {
            'metaphor': 'Direct comparison WITHOUT "like" or "as" (e.g., "Her voice was music")',
            'simile': 'Comparison USING "like" or "as" (e.g., "She ran like the wind")',
            'personification': 'Giving human qualities to non-human things (e.g., "The wind whispered")',
            'alliteration': 'Repeating same sound at word beginnings (e.g., "Peter Piper picked")',
            'hyperbole': 'Extreme exaggeration for effect (e.g., "I\'ve told you a million times")',
            'dialogue': 'Characters speaking in quotation marks (e.g., "Where are you going?" she asked)',
            'flashback': 'Scene from before the main story (e.g., "She remembered when...")',
            'foreshadowing': 'Hints about future events (e.g., "Little did she know...")',
            'varied_sentence_length': 'Mix of short and long sentences for rhythm',
            'parallelism': 'Same pattern of words/phrases (e.g., "reading, writing, and painting")',
            'transitions': 'Words connecting ideas (e.g., "Furthermore," "However," "In addition")'
        }
        
        selected_definitions = []
        for technique in selected_techniques:
            clean_tech = technique.lower().replace(' ', '_')
            if clean_tech in technique_definitions:
                selected_definitions.append(f"• {technique.upper()}: {technique_definitions[clean_tech]}")
        
        technique_guide = '\n'.join(selected_definitions) if selected_definitions else "No specific techniques selected"

        prompt = f"""WRITING EVALUATION - {grade_level} Student

## ASSIGNMENT
Prompt: {assignment.prompt_text}
Teacher's Required Criteria: {teacher_criteria}
Word Count: {word_count} (Range: {assignment.word_count_min}-{assignment.word_count_max})
Student's Selected Techniques: {', '.join(selected_techniques) if selected_techniques else 'None'}

## STUDENT WRITING
{student_response}

## CRITICAL INSTRUCTIONS
**ONLY evaluate what was specifically requested:**
1. For Teacher Criteria: ONLY check the criteria listed above ({teacher_criteria})
   - Do NOT comment on criteria not mentioned by the teacher
   - If teacher specified "first person, hopeful tone" - ONLY check those two things
   
2. For Student Techniques: ONLY validate the techniques listed above
   - Do NOT look for or comment on techniques the student didn't select
   - If student selected "metaphor" - ONLY check for metaphor, ignore other techniques

## SCORING SYSTEM
**Core Score (100 points):**
- Content/Purpose: 40 points (how well prompt was addressed)
- Teacher Criteria: 35 points (ONLY the specific criteria listed above)
- Conventions/Clarity: 25 points (basic readability and grammar)

**Technique Bonus (up to 25 points):**
- +5 points: Technique used correctly and effectively
- +3 points: Technique present but weak execution
- +0 points: Not present or incorrectly identified

## SELECTED TECHNIQUE DEFINITIONS
{technique_guide}

## EVALUATION RULES

### FOR TEACHER CRITERIA - Check ONLY what was specified:
{teacher_criteria}
- If "first person" is listed: Check for I/me/my usage
- If "hopeful tone" is listed: Check for optimistic language
- If "narrative style" is listed: Check for storytelling elements
- If "sentence variety" is listed: Check for mixed sentence lengths
- DO NOT evaluate criteria that aren't listed above

### FOR STUDENT TECHNIQUES - Validate ONLY selected techniques:
Look ONLY for: {', '.join(selected_techniques) if selected_techniques else 'None'}
- Be STRICT: Award points only for correctly executed techniques
- Quote EXACT examples from student text
- Explain WHY technique does/doesn't qualify
- IGNORE any techniques not in the student's list

### IMPORTANT REMINDERS
- Do NOT provide feedback on elements not requested
- Do NOT suggest techniques the student didn't attempt
- Do NOT evaluate criteria the teacher didn't specify
- Focus feedback ONLY on what was flagged by teacher and student

Return ONLY this JSON structure:
{{
  "content_purpose": {{
    "score": [0-40],
    "reasoning": "How well prompt was addressed with specific examples",
    "strengths": ["specific strength 1", "specific strength 2"],
    "suggestions": ["concrete improvement 1", "concrete improvement 2"]
  }},
  "teacher_criteria": {{
    "score": [0-35],
    "reasoning": "Assessment of ONLY the teacher's specified criteria: {teacher_criteria}",
    "criteria_analysis": "How each specified criterion was met/missed (ignore unspecified criteria)",
    "perspective_check": "Only if perspective was specified by teacher",
    "strengths": ["which of the SPECIFIED criteria were achieved"],
    "suggestions": ["how to better meet the SPECIFIED criteria only"]
  }},
  "conventions_clarity": {{
    "score": [0-25], 
    "reasoning": "Grammar, mechanics, and readability assessment",
    "error_patterns": ["types of errors found"],
    "strengths": ["technical writing strengths"],
    "suggestions": ["specific technical improvements"]
  }},
  "technique_validation": {{
    "total_bonus": [0-25],
    "techniques": [
      {{
        "name": "ONLY techniques from: {', '.join(selected_techniques) if selected_techniques else 'None'}",
        "found": true/false,
        "example": "exact quote from text OR explanation why not found",
        "analysis": "detailed explanation of why it qualifies/doesn't qualify",
        "effectiveness": "how well the technique was executed",
        "points_awarded": [0, 3, or 5],
        "feedback": "specific guidance for this technique only"
      }}
    ]
  }},
  "final_assessment": {{
    "core_score": [sum of content + criteria + conventions],
    "bonus_points": [total technique bonus],
    "final_score": [core + bonus],
    "percentage": [final score as percentage],
    "overall_feedback": "Summary focused on the SPECIFIED criteria and techniques only",
    "priority_improvements": ["improvement for specified criteria/techniques", "second priority", "third priority"],
    "technique_recommendations": "Suggestions ONLY for the techniques student selected"
  }}
}}"""
        
        return prompt
    
    def _validate_evaluation(self, evaluation: Dict, student_response: str, selected_techniques: List[str]) -> Dict:
        """Validate AI evaluation and correct obvious errors"""
        try:
            response_lower = student_response.lower()
            
            # Validate all technique types
            if 'technique_validation' in evaluation and 'techniques' in evaluation['technique_validation']:
                for technique in evaluation['technique_validation']['techniques']:
                    tech_name = technique.get('name', '').lower()
                    example = technique.get('example', '').lower()
                    
                    # Validate metaphor vs simile
                    if tech_name == 'metaphor' and technique.get('found'):
                        if ' like ' in example or ' as ' in example:
                            logger.warning(f"AI incorrectly identified simile as metaphor: {example}")
                            technique['found'] = False
                            technique['points_awarded'] = 0
                            technique['feedback'] = "This is a simile (uses 'like' or 'as'), not a metaphor. A metaphor makes a direct comparison without these words."
                            technique['effectiveness'] = "Not a metaphor"
                    
                    # Validate dialogue
                    elif tech_name == 'dialogue' and technique.get('found'):
                        if '"' not in student_response and "'" not in student_response:
                            technique['found'] = False
                            technique['points_awarded'] = 0
                            technique['feedback'] = "No dialogue found. Dialogue requires quotation marks and speech tags."
                    
                    # Validate alliteration
                    elif tech_name == 'alliteration' and technique.get('found'):
                        # Simple check - would need more sophisticated analysis
                        words = example.split()
                        if len(words) < 2:
                            technique['found'] = False
                            technique['points_awarded'] = 0
                            technique['feedback'] = "Alliteration requires multiple words starting with the same sound."
            
            # Recalculate total bonus after corrections
            if 'technique_validation' in evaluation and 'techniques' in evaluation['technique_validation']:
                total_bonus = sum(t.get('points_awarded', 0) for t in evaluation['technique_validation']['techniques'])
                evaluation['technique_validation']['total_bonus'] = total_bonus
            
            # Check for perspective issues
            first_person_indicators = ['i ', 'i\'', 'me ', 'my ', 'myself', 'we ', 'our ']
            third_person_indicators = ['she ', 'he ', 'her ', 'his ', 'they ', 'their ']
            
            has_first_person = any(indicator in response_lower for indicator in first_person_indicators)
            has_third_person = any(indicator in response_lower for indicator in third_person_indicators)
            
            # Only check perspective if it was actually specified by the teacher
            if 'teacher_criteria' in evaluation:
                # Get the original teacher criteria string from the prompt
                teacher_criteria_str = str(evaluation.get('teacher_criteria', {})).lower()
                
                # Only validate perspective if teacher explicitly requested it
                if any(term in teacher_criteria_str for term in ['first person', 'perspective: first person', 'first-person']):
                    if has_third_person and not has_first_person:
                        current_score = evaluation['teacher_criteria'].get('score', 35)
                        evaluation['teacher_criteria']['score'] = min(current_score, 17)
                        evaluation['teacher_criteria']['reasoning'] = "Failed to use first person perspective as required. The writing uses third person throughout."
                        
                        # Update perspective_check if it exists
                        if 'perspective_check' in evaluation['teacher_criteria']:
                            evaluation['teacher_criteria']['perspective_check'] = "Required: first person. Used: third person"
                    
            return evaluation
            
        except Exception as e:
            logger.error(f"Error validating evaluation: {e}")
            return evaluation
    
    def _parse_evaluation_response(self, response: str) -> Dict:
        """Parse the AI evaluation response"""
        try:
            # First, try to remove markdown code blocks if present
            cleaned_response = response.strip()
            if cleaned_response.startswith('```json'):
                cleaned_response = cleaned_response[7:]  # Remove ```json
            elif cleaned_response.startswith('```'):
                cleaned_response = cleaned_response[3:]  # Remove ```
            
            if cleaned_response.endswith('```'):
                cleaned_response = cleaned_response[:-3]  # Remove trailing ```
            
            cleaned_response = cleaned_response.strip()
            
            # Try to extract JSON from the response
            # Sometimes AI might include extra text before/after JSON
            json_start = cleaned_response.find('{')
            json_end = cleaned_response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = cleaned_response[json_start:json_end]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            logger.error(f"Full response length: {len(response)} characters")
            # Log the full response for debugging
            if len(response) <= 1000:
                logger.error(f"Full response: {response}")
            else:
                logger.error(f"Response start: {response[:500]}...")
                logger.error(f"Response end: ...{response[-500:]}")
            
            # Return a default structure if parsing fails
            return self._get_default_evaluation_structure()
    
    def _calculate_final_scores(self, evaluation: Dict) -> Dict:
        """Calculate final scores from evaluation"""
        try:
            # Get core scores
            content_score = evaluation['content_purpose']['score']
            criteria_score = evaluation['teacher_criteria']['score']
            conventions_score = evaluation['conventions_clarity']['score']
            
            # Calculate core total
            core_score = content_score + criteria_score + conventions_score
            
            # Get bonus points
            bonus_points = evaluation['technique_validation']['total_bonus']
            
            # Calculate final score and percentage
            final_score = core_score + bonus_points
            final_percentage = min(125, final_score)  # Cap at 125%
            
            return {
                'core_score': core_score,
                'bonus_points': bonus_points,
                'final_score': final_score,
                'final_percentage': final_percentage
            }
            
        except Exception as e:
            logger.error(f"Error calculating scores: {e}")
            return {
                'core_score': 70,
                'bonus_points': 0,
                'final_score': 70,
                'final_percentage': 70
            }
    
    def _get_default_evaluation(self, selected_techniques: List[str]) -> Dict:
        """Return a default evaluation if AI fails"""
        return {
            'score': 75.0,
            'ai_feedback': {
                'overall_score': 75.0,
                'core_score': 75,
                'bonus_points': 0,
                'criteria_scores': {
                    'content_purpose': {
                        'score': 30,
                        'reasoning': 'Unable to evaluate at this time',
                        'strengths': ['Writing submitted successfully'],
                        'suggestions': ['Continue practicing your writing']
                    },
                    'teacher_criteria': {
                        'score': 26,
                        'reasoning': 'Unable to evaluate at this time',
                        'strengths': [],
                        'suggestions': []
                    },
                    'conventions_clarity': {
                        'score': 19,
                        'reasoning': 'Unable to evaluate at this time',
                        'strengths': [],
                        'suggestions': []
                    }
                },
                'technique_validation': {
                    'total_bonus': 0,
                    'techniques': [
                        {
                            'name': tech,
                            'found': False,
                            'example': '',
                            'effectiveness': 'Unable to evaluate',
                            'points_awarded': 0,
                            'feedback': 'Technical evaluation unavailable'
                        } for tech in selected_techniques
                    ]
                },
                'general_feedback': 'Your writing has been submitted successfully. Due to technical issues, detailed feedback is temporarily unavailable.',
                'revision_suggestions': ['Keep practicing your writing skills', 'Review the assignment requirements', 'Try using different writing techniques']
            }
        }
    
    def _get_default_evaluation_structure(self) -> Dict:
        """Return default evaluation structure when parsing fails"""
        return {
            'content_purpose': {
                'score': 30,
                'reasoning': 'Evaluation processing error',
                'strengths': [],
                'suggestions': []
            },
            'teacher_criteria': {
                'score': 26,
                'reasoning': 'Evaluation processing error',
                'criteria_analysis': 'Unable to analyze criteria at this time',
                'perspective_check': 'Unable to verify perspective',
                'strengths': [],
                'suggestions': []
            },
            'conventions_clarity': {
                'score': 19,
                'reasoning': 'Evaluation processing error',
                'error_patterns': [],
                'strengths': [],
                'suggestions': []
            },
            'technique_validation': {
                'total_bonus': 0,
                'techniques': []
            },
            'final_assessment': {
                'core_score': 75,
                'bonus_points': 0,
                'final_score': 75,
                'percentage': '75%',
                'overall_feedback': 'Technical evaluation error occurred',
                'priority_improvements': ['Unable to generate specific feedback at this time'],
                'technique_recommendations': 'Please try submitting again'
            }
        }
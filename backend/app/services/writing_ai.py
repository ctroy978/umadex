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
            
            # Calculate final scores
            final_scores = self._calculate_final_scores(evaluation)
            
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
                    'revision_suggestions': evaluation['final_assessment']['next_steps']
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
        """Build the evaluation prompt for the AI"""
        
        # Format teacher criteria
        criteria_list = []
        evaluation_criteria = assignment.evaluation_criteria or {}
        
        # Handle both dict and object attribute access
        if hasattr(evaluation_criteria, 'items'):
            criteria_items = evaluation_criteria.items()
        else:
            # Try to convert from model dump if needed
            criteria_items = evaluation_criteria if isinstance(evaluation_criteria, dict) else {}
            
        for key, values in criteria_items:
            if values and isinstance(values, list):
                criteria_list.append(f"{key}: {', '.join(str(v) for v in values)}")
        teacher_criteria = '; '.join(criteria_list) if criteria_list else "General writing quality"
        
        prompt = f"""You are an expert writing evaluator for the UMA Educational Platform. Evaluate this student writing assignment using the provided rubric structure.

## Assignment Context
**Assignment Prompt**: {assignment.prompt_text}
**Teacher Instructions**: {assignment.instructions or 'None provided'}
**Student Grade Level**: {grade_level}
**Word Count Range**: {assignment.word_count_min} - {assignment.word_count_max} words
**Teacher-Selected Criteria**: {teacher_criteria}
**Student-Tagged Techniques**: {', '.join(selected_techniques) if selected_techniques else 'None'}

## Student Response
**Student Writing**: {student_response}
**Actual Word Count**: {word_count}

## Evaluation Instructions

### CORE SCORING (100 points total)

#### 1. Content & Purpose Assessment (40 points)
Evaluate how well the student addressed the assignment prompt:
- Excellent (36-40): Fully addresses prompt with engaging, well-developed ideas
- Proficient (28-35): Adequately addresses most aspects with clear, relevant ideas
- Developing (20-27): Partially addresses prompt with basic but related ideas
- Beginning (0-19): Does not adequately address the prompt or shows confusion

#### 2. Teacher-Selected Criteria Achievement (35 points)
Evaluate how well the student demonstrated: {teacher_criteria}
- Excellent (32-35): Demonstrates mastery of ALL selected criteria naturally
- Proficient (25-31): Successfully demonstrates MOST selected criteria competently
- Developing (18-24): Demonstrates SOME criteria with inconsistent application
- Beginning (0-17): Fails to demonstrate most selected criteria

#### 3. Writing Conventions & Clarity (25 points)
Evaluate technical aspects and readability:
- Excellent (23-25): Consistently correct with varied, well-constructed sentences
- Proficient (18-22): Minor errors that don't impede reading
- Developing (13-17): Some errors that occasionally affect clarity
- Beginning (0-12): Frequent errors that significantly impede comprehension

### BONUS SCORING (Up to +25 points)
For each technique in [{', '.join(selected_techniques)}]:
- +5 points: Technique is present, effective, and appropriate
- +3 points: Technique is present but could be more effective
- +0 points: Technique is not actually present

### IMPORTANT GUIDELINES
- Be encouraging and specific in feedback
- Use exact examples from the student's writing
- Adjust expectations to {grade_level} level
- Focus on growth and improvement
- Award partial credit for attempted techniques

Provide your evaluation in this EXACT JSON format:
{{
  "content_purpose": {{
    "score": [number between 0-40],
    "reasoning": "Detailed explanation",
    "strengths": ["Strength 1", "Strength 2"],
    "suggestions": ["Suggestion 1", "Suggestion 2"]
  }},
  "teacher_criteria": {{
    "score": [number between 0-35],
    "reasoning": "How well each criterion was demonstrated",
    "criteria_breakdown": {{
      "criterion_name": "Assessment of this criterion"
    }},
    "strengths": ["What criteria were handled well"],
    "suggestions": ["How to better achieve criteria"]
  }},
  "conventions_clarity": {{
    "score": [number between 0-25],
    "reasoning": "Technical quality assessment",
    "strengths": ["Convention strengths"],
    "suggestions": ["Technical improvements"]
  }},
  "technique_validation": {{
    "total_bonus": [number between 0-25],
    "techniques": [
      {{
        "name": "technique_name",
        "found": true/false,
        "example": "Quote showing technique",
        "effectiveness": "How well used",
        "points_awarded": [0, 3, or 5],
        "feedback": "Specific comment"
      }}
    ]
  }},
  "final_assessment": {{
    "core_score": [sum of three scores],
    "bonus_points": [technique bonus],
    "final_score": [core + bonus],
    "percentage": "[percentage]%",
    "overall_feedback": "Encouraging summary",
    "next_steps": ["Suggestion 1", "Suggestion 2", "Suggestion 3"]
  }}
}}"""
        
        return prompt
    
    def _parse_evaluation_response(self, response: str) -> Dict:
        """Parse the AI evaluation response"""
        try:
            # Try to extract JSON from the response
            # Sometimes AI might include extra text before/after JSON
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
        except Exception as e:
            logger.error(f"Failed to parse AI response: {e}")
            logger.error(f"Response was: {response[:500]}...")
            
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
                'criteria_breakdown': {},
                'strengths': [],
                'suggestions': []
            },
            'conventions_clarity': {
                'score': 19,
                'reasoning': 'Evaluation processing error',
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
                'next_steps': []
            }
        }
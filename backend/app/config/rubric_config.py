"""
UmaRead Test Evaluation Rubric Configuration

This module defines the 4-point scoring rubric used for evaluating
student responses in UmaRead comprehension tests.
"""

from typing import Dict, Any

# 4-Point Scoring Rubric
# Each score level has associated points and criteria
UMAREAD_SCORING_RUBRIC = {
    4: {
        "points": 10,
        "label": "Excellent",
        "description": "Complete understanding demonstrated",
        "criteria": [
            "Fully answers the question with accurate information",
            "Shows deep comprehension of the text",
            "Makes appropriate inferences when required",
            "Uses specific evidence from the text effectively",
            "Response is clear, complete, and well-organized"
        ]
    },
    3: {
        "points": 8,
        "label": "Good",
        "description": "Strong understanding with minor gaps",
        "criteria": [
            "Answers the question with mostly accurate information",
            "Shows good comprehension of the main ideas",
            "Makes reasonable inferences with minor errors",
            "Uses some evidence from the text",
            "Response is generally clear but may lack some detail"
        ]
    },
    2: {
        "points": 5,
        "label": "Fair",
        "description": "Partial understanding evident",
        "criteria": [
            "Partially answers the question",
            "Shows basic understanding of some key concepts",
            "Makes attempts at inference but with significant gaps",
            "Limited use of textual evidence",
            "Response may be unclear or incomplete"
        ]
    },
    1: {
        "points": 2,
        "label": "Poor",
        "description": "Minimal understanding shown",
        "criteria": [
            "Attempts to answer but largely incorrect",
            "Shows very limited comprehension",
            "Significant misunderstandings evident",
            "Little to no textual evidence used",
            "Response is unclear or mostly irrelevant"
        ]
    },
    0: {
        "points": 0,
        "label": "No Credit",
        "description": "No understanding demonstrated",
        "criteria": [
            "Does not answer the question",
            "Shows no comprehension of the text",
            "Response is completely incorrect or irrelevant",
            "No evidence of engagement with the material",
            "May be blank, off-topic, or nonsensical"
        ]
    }
}

# Grade-level adjustment factors
# These can be used to adjust expectations based on student grade
GRADE_LEVEL_ADJUSTMENTS = {
    "3": {"description": "Elementary expectations", "factor": 0.8},
    "4": {"description": "Elementary expectations", "factor": 0.85},
    "5": {"description": "Elementary expectations", "factor": 0.9},
    "6": {"description": "Middle school expectations", "factor": 0.95},
    "7": {"description": "Middle school expectations", "factor": 1.0},
    "8": {"description": "Middle school expectations", "factor": 1.0},
    "9": {"description": "High school expectations", "factor": 1.05},
    "10": {"description": "High school expectations", "factor": 1.1},
    "11": {"description": "High school expectations", "factor": 1.15},
    "12": {"description": "High school expectations", "factor": 1.2},
}

# Question type weightings (if needed for future enhancements)
QUESTION_TYPE_WEIGHTS = {
    "literal": 1.0,      # Direct comprehension questions
    "inference": 1.0,    # Questions requiring inference
    "analysis": 1.0,     # Analytical questions
    "summary": 1.0,      # Summary or synthesis questions
}

def get_rubric_score_points(rubric_score: int) -> int:
    """Get the point value for a given rubric score."""
    if rubric_score not in UMAREAD_SCORING_RUBRIC:
        raise ValueError(f"Invalid rubric score: {rubric_score}. Must be 0-4.")
    return UMAREAD_SCORING_RUBRIC[rubric_score]["points"]

def get_rubric_criteria(rubric_score: int) -> Dict[str, Any]:
    """Get the full criteria for a given rubric score."""
    if rubric_score not in UMAREAD_SCORING_RUBRIC:
        raise ValueError(f"Invalid rubric score: {rubric_score}. Must be 0-4.")
    return UMAREAD_SCORING_RUBRIC[rubric_score]

def calculate_total_score(rubric_scores: list[int]) -> int:
    """Calculate total test score from individual question rubric scores."""
    if len(rubric_scores) != 10:
        raise ValueError("Must provide exactly 10 rubric scores")
    
    total = 0
    for score in rubric_scores:
        total += get_rubric_score_points(score)
    
    return total

def get_grade_adjustment_factor(grade_level: str) -> float:
    """Get the grade level adjustment factor for scoring expectations."""
    return GRADE_LEVEL_ADJUSTMENTS.get(
        str(grade_level), 
        {"factor": 1.0}
    )["factor"]

# Evaluation prompt templates
EVALUATION_PROMPT_INTRO = """You are an expert educational evaluator assessing student responses to reading comprehension questions. 
Use the following 4-point rubric scale to evaluate each response:

4 - Excellent (10 points): {rubric_4_desc}
3 - Good (8 points): {rubric_3_desc}
2 - Fair (5 points): {rubric_2_desc}
1 - Poor (2 points): {rubric_1_desc}
0 - No Credit (0 points): {rubric_0_desc}

Consider the student's grade level ({grade_level}) when evaluating responses.
"""

FEEDBACK_GUIDELINES = """
When providing feedback for scores below 4:
- Keep feedback brief and constructive (50-150 words)
- Focus on what the student missed or misunderstood
- Use encouraging language while being instructionally helpful
- Provide hints or areas to review rather than direct answers
- Tailor feedback to the student's grade level
"""
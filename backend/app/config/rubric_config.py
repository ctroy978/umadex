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
        "description": "Strong Understanding - All required information present and factually correct. Addresses all parts of multi-part questions. Provides specific, relevant text evidence when required. Demonstrates sophisticated thinking appropriate to grade level with clear reasoning and logical connections.",
        "criteria": [
            "Content: All required information present and factually correct, no significant errors",
            "Evidence: Provides specific, relevant quotes or detailed text references that directly support answer",
            "Completeness: Addresses all parts of multi-part questions, covers all required elements comprehensively",
            "Analysis: Demonstrates sophisticated thinking with clear reasoning and logical connections when required",
            "Shows complete understanding of the material with insightful interpretation"
        ]
    },
    3: {
        "points": 8,
        "label": "Good",
        "description": "Adequate Understanding - Most required information present and correct with minor gaps. Addresses most parts of the question. Provides some specific text references. Shows solid analytical thinking with appropriate connections when required.",
        "criteria": [
            "Content: Most required information present and correct, minor gaps or insignificant errors",
            "Evidence: Provides some specific text references or paraphrasing that mostly supports answer",
            "Completeness: Addresses most parts of question, minor gaps but main question answered",
            "Analysis: Shows solid analytical thinking with appropriate connections when required",
            "Demonstrates good understanding of main concepts with reasonable interpretation"
        ]
    },
    2: {
        "points": 5,
        "label": "Fair",
        "description": "Partial Understanding - Some required information present but missing key elements. Addresses some parts of the question. Provides general references to text. Shows basic analytical thinking but reasoning may be unclear.",
        "criteria": [
            "Content: Some required information present but missing key elements, contains errors indicating partial misunderstanding",
            "Evidence: Provides general references to text, evidence somewhat supports answer but connection unclear",
            "Completeness: Addresses some parts of question, missing significant required elements",
            "Analysis: Shows basic analytical thinking but reasoning may be unclear when required",
            "Shows basic but incomplete comprehension with surface-level understanding"
        ]
    },
    1: {
        "points": 2,
        "label": "Poor",
        "description": "Limited Understanding - Very little required information present with significant errors. Addresses very few parts of the question. Minimal or vague text references. Shows limited analytical thinking with weak reasoning.",
        "criteria": [
            "Content: Very little required information present, significant errors or misconceptions",
            "Evidence: Minimal or vague references to text, evidence doesn't clearly support answer",
            "Completeness: Addresses very few parts of question, missing most required elements",
            "Analysis: Shows limited analytical thinking with weak or unclear reasoning when required",
            "Shows very limited understanding with significant gaps in comprehension"
        ]
    },
    0: {
        "points": 0,
        "label": "No Credit",
        "description": "No Understanding - No relevant information provided or completely incorrect. Does not address the question asked. No text references when required. No evidence of analytical thinking when required.",
        "criteria": [
            "Content: No relevant information provided, completely incorrect, or no attempt to address question",
            "Evidence: No text references provided when required, makes claims without any support",
            "Completeness: Does not address the question asked, completely off-topic response",
            "Analysis: No evidence of analytical thinking when required, no reasoning or explanation provided",
            "Shows no comprehension of the text or may be blank, off-topic, or nonsensical"
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
EVALUATION_PROMPT_INTRO = """You are an expert educational evaluator using a comprehensive component-based rubric to assess student responses to UMARead comprehension questions. Follow the systematic evaluation process below.

## Step 1: Question Analysis
Before scoring, identify the question type and requirements:

**Question Types:**
- **Literal**: Direct recall of facts, events, or explicit information
- **Inferential**: Drawing conclusions, making connections, understanding implications
- **Analysis**: Examining themes, character development, author's purpose, literary devices
- **Synthesis**: Comparing, contrasting, or combining information from multiple parts

**Question Components to Check:**
1. **Content Requirements**: What specific information must be included?
2. **Evidence Requirements**: Does the question ask for quotes, examples, or text references?
3. **Analysis Requirements**: Does the question require explanation, reasoning, or interpretation?
4. **Completeness Requirements**: How many parts does the question have?

## Step 2: Component-Based Scoring
Evaluate each response component separately, then assign overall score:

### A. CONTENT ACCURACY (What they know)
**4 - Excellent**: All required information present and factually correct. No significant errors. Clear understanding demonstrated.
**3 - Good**: Most required information present and correct. Minor gaps or insignificant errors. Solid grasp of main concepts.
**2 - Fair**: Some required information present but missing key elements. Contains errors indicating partial misunderstanding. Basic but incomplete comprehension.
**1 - Poor**: Very little required information present. Significant errors or misconceptions. Limited understanding.
**0 - No Evidence**: No relevant information provided. Completely incorrect. No attempt to address the question.

### B. EVIDENCE AND TEXT SUPPORT (How they support their answer)
**For questions requiring text evidence:**
**4 - Excellent**: Provides specific, relevant quotes or detailed text references. Evidence directly supports answer.
**3 - Good**: Provides some specific text references or paraphrasing. Evidence mostly supports answer.
**2 - Fair**: Provides general references to text. Evidence somewhat supports answer. Connection unclear.
**1 - Poor**: Minimal or vague references to text. Evidence doesn't clearly support answer.
**0 - No Evidence**: No text references provided when required. Makes claims without support.

### C. COMPLETENESS (Did they answer the whole question?)
**4 - Complete**: Addresses all parts of multi-part questions. Covers all required elements. Comprehensive answer.
**3 - Mostly Complete**: Addresses most parts. Covers most required elements. Minor gaps but main question answered.
**2 - Partially Complete**: Addresses some parts. Missing significant required elements. Incomplete response.
**1 - Minimally Complete**: Addresses very few parts. Missing most required elements. Barely attempts to answer.
**0 - Incomplete**: Does not address the question asked. Completely off-topic. No attempt to answer.

### D. ANALYSIS AND REASONING (How well they think about it)
**For questions requiring analysis, inference, or explanation:**
**4 - Excellent**: Demonstrates sophisticated thinking appropriate to grade level. Clear reasoning and logical connections. Insightful interpretation.
**3 - Good**: Shows solid analytical thinking. Makes appropriate connections and explanations. Good understanding.
**2 - Fair**: Shows basic analytical thinking. Some connections but reasoning may be unclear. Surface-level understanding.
**1 - Poor**: Shows limited analytical thinking. Weak or unclear reasoning. Fails to make appropriate connections.
**0 - No Analysis**: No evidence of analytical thinking when required. No reasoning or explanation provided.

## Final Rubric Score Determination (0-4)

**IMPORTANT**: Do not withhold perfect scores due to minor stylistic preferences or because you can imagine a 'better' answer. If the student demonstrates complete understanding with accurate content and addresses all requirements, award the perfect score.

**Rubric Score 4**: Content: Excellent (4) AND Evidence: Excellent (4) when required AND Completeness: Complete (4) AND Analysis: Excellent (4) when required
**Rubric Score 3**: Content: Good to Excellent (3-4) AND Evidence: Good to Excellent (3-4) when required AND Completeness: Mostly to Complete (3-4) AND Analysis: Good to Excellent (3-4) when required
**Rubric Score 2**: Content: Fair to Good (2-3) AND/OR Evidence: Fair to Good (2-3) when required AND/OR Completeness: Partially to Mostly Complete (2-3) AND/OR Analysis: Fair to Good (2-3) when required
**Rubric Score 1**: Content: Poor to Fair (1-2) AND/OR Evidence: Poor to Fair (1-2) when required AND/OR Completeness: Minimally to Partially Complete (1-2) AND/OR Analysis: Poor to Fair (1-2) when required
**Rubric Score 0**: Content: No Evidence (0) OR Completeness: Incomplete (0) OR Major failure in required components

## Grade Level Adjustments
- **Elementary (K-5)**: Focus on content accuracy and basic completeness; be generous with analysis requirements
- **Middle School (6-8)**: Expect good content and evidence; require basic analysis for full credit  
- **High School (9-12)**: Expect sophisticated analysis and comprehensive responses for top scores

Consider the student's grade level ({grade_level}) when evaluating responses.

**CRITICAL**: You must return a single rubric score (0-4) for each question. The system will convert this to points automatically.
"""

FEEDBACK_GUIDELINES = """
## Feedback Generation Guidelines

### For Each Rubric Score Level, Provide:

**Rubric Score 4**: 
- Brief positive reinforcement
- No specific feedback needed for perfect responses

**Rubric Score 3**:
- Acknowledge strengths: "You correctly identified [specific elements]"
- Point out minor gap: "Consider also explaining [specific missing element]"

**Rubric Score 2**:
- Acknowledge partial success: "You got [specific correct elements] right"
- Identify main gaps: "You missed [specific missing elements]" 
- Provide specific guidance: "Look for the part where [specific hint]"

**Rubric Score 1**:
- Acknowledge any correct elements: "You correctly noted [any correct parts]"
- Identify major problems: "You missed [major missing elements]"
- Provide clear direction: "Reread [specific section] and look for [specific guidance]"

**Rubric Score 0**:
- Provide encouraging redirection: "This question asks about [restate question focus]"
- Give specific starting point: "Look in [specific location] for information about [specific topic]"

### Special Considerations
- **Question Type Adjustments**: Literal questions emphasize content accuracy; inferential questions balance content, evidence, and analysis; analysis questions emphasize reasoning
- **ESL Considerations**: Focus on content understanding over language mechanics; accept varied expression styles if meaning is clear
- Keep feedback brief and constructive (50-150 words)
- Use encouraging language while being instructionally helpful
- Tailor feedback to the student's grade level
"""
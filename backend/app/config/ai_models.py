"""
Centralized AI Model Configuration
All AI model identifiers used throughout the application are defined here.
Update this file when switching models or upgrading versions.
"""

import os
from typing import Optional

# Image Analysis AI
# Used in: Teacher assignment creation - analyzes uploaded images to extract
# educational content (charts, graphs, illustrations) for question generation
IMAGE_ANALYSIS_MODEL = os.getenv("IMAGE_ANALYSIS_MODEL", "gemini-2.0-flash")  # Currently using 2.0-flash, not flash-lite

# Question Generation AI  
# Used in: Automatic question creation from reading chunks and image descriptions
# Generates 2 questions per chunk scaled to student ability level
QUESTION_GENERATION_MODEL = os.getenv("QUESTION_GENERATION_MODEL", "claude-3-5-sonnet-20241022")

# Answer Evaluation AI
# Used in: Student answer grading - evaluates free-form responses 
# for comprehension and provides feedback
ANSWER_EVALUATION_MODEL = os.getenv("ANSWER_EVALUATION_MODEL", "claude-3-5-sonnet-20241022")

# Vocabulary Definition AI
# Used in: UMAVocab module - generates grade-appropriate definitions
# and example sentences for vocabulary words
VOCABULARY_DEFINITION_MODEL = os.getenv("VOCABULARY_DEFINITION_MODEL", "gemini-2.0-flash-exp")

# Debate Prompt Generation AI
# Used in: UMADebate module - creates debate topics and supporting materials
# based on reading content
DEBATE_GENERATION_MODEL = os.getenv("DEBATE_GENERATION_MODEL", "claude-3-5-sonnet-20241022")  # placeholder for future

# Speech Analysis AI
# Used in: UMASpeak module - analyzes student speech submissions
# for pronunciation and fluency
SPEECH_ANALYSIS_MODEL = os.getenv("SPEECH_ANALYSIS_MODEL", "whisper-large-v3")  # placeholder for future

# Writing Assistance AI
# Used in: UMAWrite module - provides writing feedback and suggestions
# for student essays and creative writing
WRITING_ASSISTANCE_MODEL = os.getenv("WRITING_ASSISTANCE_MODEL", "claude-3-5-sonnet-20241022")  # placeholder for future

# Lecture Generation AI
# Used in: UMALecture module - creates interactive lecture content
# from source materials
LECTURE_GENERATION_MODEL = os.getenv("LECTURE_GENERATION_MODEL", "gpt-4-turbo")  # placeholder for future


def get_model_config(model_type: str) -> Optional[str]:
    """
    Get the configured model for a specific use case.
    
    Args:
        model_type: Type of AI model needed (e.g., 'image_analysis', 'question_generation')
        
    Returns:
        Model identifier string or None if not configured
    """
    model_mapping = {
        'image_analysis': IMAGE_ANALYSIS_MODEL,
        'question_generation': QUESTION_GENERATION_MODEL,
        'answer_evaluation': ANSWER_EVALUATION_MODEL,
        'vocabulary_definition': VOCABULARY_DEFINITION_MODEL,
        'debate_generation': DEBATE_GENERATION_MODEL,
        'speech_analysis': SPEECH_ANALYSIS_MODEL,
        'writing_assistance': WRITING_ASSISTANCE_MODEL,
        'lecture_generation': LECTURE_GENERATION_MODEL,
    }
    
    return model_mapping.get(model_type)


def get_all_models() -> dict:
    """
    Get all configured AI models for debugging/admin purposes.
    
    Returns:
        Dictionary of all model configurations
    """
    return {
        'image_analysis': IMAGE_ANALYSIS_MODEL,
        'question_generation': QUESTION_GENERATION_MODEL,
        'answer_evaluation': ANSWER_EVALUATION_MODEL,
        'vocabulary_definition': VOCABULARY_DEFINITION_MODEL,
        'debate_generation': DEBATE_GENERATION_MODEL,
        'speech_analysis': SPEECH_ANALYSIS_MODEL,
        'writing_assistance': WRITING_ASSISTANCE_MODEL,
        'lecture_generation': LECTURE_GENERATION_MODEL,
    }
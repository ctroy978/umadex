"""
AI and Application Configuration Module
"""

from .ai_models import (
    IMAGE_ANALYSIS_MODEL,
    QUESTION_GENERATION_MODEL,
    ANSWER_EVALUATION_MODEL,
    VOCABULARY_DEFINITION_MODEL,
    DEBATE_GENERATION_MODEL,
    SPEECH_ANALYSIS_MODEL,
    WRITING_ASSISTANCE_MODEL,
    LECTURE_GENERATION_MODEL,
    get_model_config,
    get_all_models
)

from .ai_config import (
    GeminiConfig,
    ClaudeConfig,
    OpenAIConfig,
    WhisperConfig,
    get_gemini_config,
    get_claude_config,
    get_openai_config,
    get_whisper_config
)

__all__ = [
    # AI Models
    'IMAGE_ANALYSIS_MODEL',
    'QUESTION_GENERATION_MODEL',
    'ANSWER_EVALUATION_MODEL',
    'VOCABULARY_DEFINITION_MODEL',
    'DEBATE_GENERATION_MODEL',
    'SPEECH_ANALYSIS_MODEL',
    'WRITING_ASSISTANCE_MODEL',
    'LECTURE_GENERATION_MODEL',
    'get_model_config',
    'get_all_models',
    
    # AI Configs
    'GeminiConfig',
    'ClaudeConfig',
    'OpenAIConfig',
    'WhisperConfig',
    'get_gemini_config',
    'get_claude_config',
    'get_openai_config',
    'get_whisper_config'
]
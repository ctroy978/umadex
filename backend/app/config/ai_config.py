"""
AI Service Configuration Classes
Provides structured configuration for each AI service provider
"""

from pydantic_settings import BaseSettings
from typing import Optional
import os


class GeminiConfig(BaseSettings):
    """Configuration for Google Gemini AI"""
    api_key: str = os.getenv("GEMINI_API_KEY", "")
    model: str = os.getenv("IMAGE_ANALYSIS_MODEL", "gemini-2.0-flash")
    max_retries: int = 3
    timeout: int = 30
    temperature: float = 0.7
    max_output_tokens: int = 2048
    
    class Config:
        env_prefix = "GEMINI_"


class ClaudeConfig(BaseSettings):
    """Configuration for Anthropic Claude AI"""
    api_key: str = os.getenv("CLAUDE_API_KEY", "")
    model: str = os.getenv("QUESTION_GENERATION_MODEL", "claude-3-5-sonnet-20241022")
    max_tokens: int = 4000
    temperature: float = 0.7
    top_p: float = 0.9
    max_retries: int = 3
    timeout: int = 60
    
    class Config:
        env_prefix = "CLAUDE_"


class OpenAIConfig(BaseSettings):
    """Configuration for OpenAI GPT models"""
    api_key: str = os.getenv("OPENAI_API_KEY", "")
    model: str = os.getenv("VOCAB_EXTRACTION_MODEL", "gpt-4-turbo")
    max_tokens: int = 2000
    temperature: float = 0.7
    top_p: float = 0.9
    max_retries: int = 3
    timeout: int = 45
    
    class Config:
        env_prefix = "OPENAI_"


class WhisperConfig(BaseSettings):
    """Configuration for OpenAI Whisper speech recognition"""
    api_key: str = os.getenv("OPENAI_API_KEY", "")  # Uses same key as OpenAI
    model: str = os.getenv("SPEECH_ANALYSIS_MODEL", "whisper-large-v3")
    language: str = "en"
    response_format: str = "json"
    temperature: float = 0.0  # Lower temperature for more accurate transcription
    
    class Config:
        env_prefix = "WHISPER_"


# Singleton instances
_gemini_config: Optional[GeminiConfig] = None
_claude_config: Optional[ClaudeConfig] = None
_openai_config: Optional[OpenAIConfig] = None
_whisper_config: Optional[WhisperConfig] = None


def get_gemini_config() -> GeminiConfig:
    """Get Gemini configuration singleton"""
    global _gemini_config
    if _gemini_config is None:
        _gemini_config = GeminiConfig()
    return _gemini_config


def get_claude_config() -> ClaudeConfig:
    """Get Claude configuration singleton"""
    global _claude_config
    if _claude_config is None:
        _claude_config = ClaudeConfig()
    return _claude_config


def get_openai_config() -> OpenAIConfig:
    """Get OpenAI configuration singleton"""
    global _openai_config
    if _openai_config is None:
        _openai_config = OpenAIConfig()
    return _openai_config


def get_whisper_config() -> WhisperConfig:
    """Get Whisper configuration singleton"""
    global _whisper_config
    if _whisper_config is None:
        _whisper_config = WhisperConfig()
    return _whisper_config
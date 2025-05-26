# AI Configuration Module

This module centralizes all AI model configuration for the UMA Educational Assignment Platform.

## Quick Start

### Using AI Models in Your Code

```python
from app.config.ai_models import IMAGE_ANALYSIS_MODEL
from app.config.ai_config import get_gemini_config

class MyService:
    def __init__(self):
        config = get_gemini_config()
        self.model = IMAGE_ANALYSIS_MODEL
        self.api_key = config.api_key
```

### Changing Models

1. Update `.env` file:
```bash
IMAGE_ANALYSIS_MODEL=gemini-2.0-pro
```

2. Restart the application

## Files

- `ai_models.py` - All AI model identifiers
- `ai_config.py` - Configuration classes for AI providers
- `__init__.py` - Module exports

## Available Models

- `IMAGE_ANALYSIS_MODEL` - For analyzing educational images
- `QUESTION_GENERATION_MODEL` - For creating comprehension questions
- `ANSWER_EVALUATION_MODEL` - For grading student responses
- `VOCAB_EXTRACTION_MODEL` - For vocabulary extraction (future)
- `DEBATE_GENERATION_MODEL` - For debate topics (future)
- `SPEECH_ANALYSIS_MODEL` - For speech analysis (future)
- `WRITING_ASSISTANCE_MODEL` - For writing feedback (future)
- `LECTURE_GENERATION_MODEL` - For lecture creation (future)

## Configuration Classes

- `GeminiConfig` - Google Gemini configuration
- `ClaudeConfig` - Anthropic Claude configuration
- `OpenAIConfig` - OpenAI GPT configuration
- `WhisperConfig` - OpenAI Whisper configuration

## Environment Variables

See `.env.example` for all available configuration options.
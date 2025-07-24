# AI Model Configuration Guide

## Overview

All AI models used in the UMA Educational Assignment Platform are centrally configured in `app/config/ai_models.py`. This provides a single source of truth for AI model management, making it easy to update models, switch providers, or upgrade versions across the entire application.

## Configuration Files

### 1. `app/config/ai_models.py`
Central configuration file containing all AI model identifiers.

### 2. `app/config/ai_config.py`
Configuration classes for each AI service provider (Gemini, Claude, OpenAI, Whisper).

### 3. `.env` / `.env.example`
Environment variables for model names and API keys.

## Current Models

### Image Analysis (Gemini)
- **Current Model**: `gemini-2.0-flash`
- **Environment Variable**: `IMAGE_ANALYSIS_MODEL`
- **Purpose**: Analyzes images in reading assignments to extract educational content
- **Used By**: `services/image_analyzer.py`
- **Features**:
  - Identifies image types (quantitative, diagram, photograph)
  - Extracts data from charts, graphs, and tables
  - Generates comprehensive descriptions for question generation
  - Identifies key learning points and potential misconceptions

### Question Generation (Claude)
- **Current Model**: `claude-3-5-sonnet-20241022`
- **Environment Variable**: `QUESTION_GENERATION_MODEL`
- **Purpose**: Generates comprehension questions from reading chunks and images
- **Used By**: `services/question_generator.py` (to be implemented)
- **Features**:
  - Creates 2 questions per reading chunk
  - Scales difficulty to student grade level
  - Incorporates image-based questions

### Answer Evaluation (Claude)
- **Current Model**: `claude-3-5-sonnet-20241022`
- **Environment Variable**: `ANSWER_EVALUATION_MODEL`
- **Purpose**: Evaluates student free-form responses
- **Used By**: `services/answer_evaluator.py` (to be implemented)
- **Features**:
  - Assesses comprehension accuracy
  - Provides constructive feedback
  - Scales evaluation to grade level

## Future Models (Placeholders)

### Vocabulary Extraction (GPT-4)
- **Planned Model**: `gpt-4-turbo`
- **Environment Variable**: `VOCAB_EXTRACTION_MODEL`
- **Purpose**: Identifies challenging vocabulary and creates contextual definitions
- **Module**: UMAVocab

### Debate Generation (Claude)
- **Planned Model**: `claude-3-5-sonnet-20241022`
- **Environment Variable**: `DEBATE_GENERATION_MODEL`
- **Purpose**: Creates debate topics and supporting materials
- **Module**: UMADebate

### Speech Analysis (Whisper)
- **Planned Model**: `whisper-large-v3`
- **Environment Variable**: `SPEECH_ANALYSIS_MODEL`
- **Purpose**: Analyzes student speech for pronunciation and fluency
- **Module**: UMASpeak

### Writing Assistance (Claude)
- **Planned Model**: `claude-3-5-sonnet-20241022`
- **Environment Variable**: `WRITING_ASSISTANCE_MODEL`
- **Purpose**: Provides writing feedback and suggestions
- **Module**: UMAWrite

### Lecture Generation (Gemini)
- **Current Model**: `gemini-2.0-flash`
- **Environment Variable**: `LECTURE_GENERATION_MODEL`
- **Purpose**: Creates interactive lecture content
- **Module**: UMALecture
- **Used By**: `services/umalecture_ai.py`
- **Features**:
  - Generates multi-level difficulty content for each topic
  - Creates comprehension questions for each difficulty level
  - Evaluates student answers with educational feedback
  - Processes educational images for enhanced learning

## Switching Models

### Step 1: Update Environment Variables
Edit your `.env` file:
```bash
# Example: Upgrade to Gemini 2.0 Pro
IMAGE_ANALYSIS_MODEL=gemini-2.0-pro
```

### Step 2: Update API Keys (if needed)
Ensure you have valid API keys for the new model:
```bash
GEMINI_API_KEY=your-new-api-key
```

### Step 3: Test the Integration
Run the test suite or manually test the affected features:
```bash
# Test image analysis
python -m pytest tests/test_image_analyzer.py

# Or use the admin endpoint
curl http://localhost:8000/api/v1/admin/ai-config
```

### Step 4: Deploy
After successful testing, deploy the changes.

## Adding New AI Services

### 1. Add Model to Configuration
Edit `app/config/ai_models.py`:
```python
# New AI Model
# Used in: [describe usage]
NEW_MODEL_NAME = os.getenv("NEW_MODEL_ENV_VAR", "default-model-name")
```

### 2. Add to Environment Variables
Update `.env.example`:
```bash
# New model description
NEW_MODEL_ENV_VAR=model-identifier
NEW_MODEL_API_KEY=your-api-key-here
```

### 3. Create Service Configuration (if new provider)
Add to `app/config/ai_config.py`:
```python
class NewProviderConfig(BaseSettings):
    api_key: str = os.getenv("NEW_PROVIDER_API_KEY", "")
    model: str = os.getenv("NEW_MODEL_ENV_VAR", "default-model")
    # ... other settings
```

### 4. Implement Service
Create your service using the centralized config:
```python
from app.config.ai_models import NEW_MODEL_NAME
from app.config.ai_config import get_new_provider_config

class NewAIService:
    def __init__(self):
        config = get_new_provider_config()
        self.model = NEW_MODEL_NAME
        # ... initialize with config
```

### 5. Document
Update this documentation file with the new model details.

## Best Practices

1. **Always use environment variables** - Never hardcode model names or API keys
2. **Test before deploying** - Verify model changes work correctly
3. **Document model capabilities** - Note what each model is optimized for
4. **Monitor costs** - Different models have different pricing
5. **Version control** - Track model changes in git commits
6. **Gradual rollout** - Test new models with a subset of users first

## Troubleshooting

### Model Not Found
- Check environment variable is set correctly
- Verify model name matches provider's exact identifier
- Ensure API key has access to the specified model

### Authentication Errors
- Verify API key is valid and active
- Check API key has necessary permissions
- Ensure billing is set up for the provider

### Performance Issues
- Consider model size vs. speed tradeoffs
- Check rate limits for your API tier
- Monitor response times and adjust timeout settings

## Admin Endpoint

Check current AI configuration:
```bash
GET /api/v1/admin/ai-config

Response:
{
  "image_analysis": "gemini-2.0-flash",
  "question_generation": "claude-3-5-sonnet-20241022",
  "answer_evaluation": "claude-3-5-sonnet-20241022",
  ...
}
```

## Cost Optimization

### Model Selection Guidelines
- **Development**: Use smaller, faster models (e.g., flash variants)
- **Production**: Use optimal balance of quality and cost
- **High-stakes tasks**: Use most capable models (e.g., GPT-4, Claude Opus)

### Monitoring Usage
- Track API calls per model
- Monitor token usage
- Set up billing alerts
- Review usage patterns monthly

## Security Considerations

1. **API Key Management**
   - Store keys in environment variables only
   - Rotate keys regularly
   - Use separate keys for dev/staging/production
   - Never commit keys to version control

2. **Access Control**
   - Limit model access to necessary services
   - Use rate limiting to prevent abuse
   - Monitor for unusual usage patterns

3. **Data Privacy**
   - Be aware of data retention policies
   - Avoid sending PII to AI models
   - Use appropriate models for sensitive content
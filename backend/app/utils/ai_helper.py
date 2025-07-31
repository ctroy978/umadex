"""
AI Helper for debate responses using Google Gemini
"""
import google.generativeai as genai
from typing import Optional
import logging
import asyncio
from app.config.ai_config import get_gemini_config

logger = logging.getLogger(__name__)

# Initialize Gemini
config = get_gemini_config()
genai.configure(api_key=config.api_key)
model = genai.GenerativeModel('gemini-2.0-flash')

async def get_ai_response(prompt: str, max_tokens: int = 300, timeout: int = 30) -> str:
    """
    Generate AI response using Google Gemini with timeout.
    
    Args:
        prompt: The prompt for AI generation
        max_tokens: Maximum tokens to generate
        timeout: Timeout in seconds (default 30)
    """
    try:
        # Configure generation settings
        generation_config = {
            "temperature": config.temperature,
            "max_output_tokens": max_tokens,
            "top_p": 0.95,
        }
        
        # Generate response in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        
        # Create the generation task with timeout
        try:
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: model.generate_content(
                        prompt,
                        generation_config=generation_config
                    )
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(f"AI response generation timed out after {timeout} seconds")
            raise TimeoutError(f"AI response generation timed out after {timeout} seconds")
        
        # Extract text from response
        if response.text:
            return response.text.strip()
        else:
            logger.error("No text in Gemini response")
            return "I apologize, but I'm unable to generate a response at this moment."
            
    except TimeoutError:
        # Re-raise timeout errors to be handled by caller
        raise
    except Exception as e:
        logger.error(f"Error generating Gemini response: {str(e)}")
        # Return a fallback response
        return "I apologize, but I'm experiencing technical difficulties. Please try again."